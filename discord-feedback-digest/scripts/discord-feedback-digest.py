#!/usr/bin/env python3
"""
discord-feedback-digest.py — turn a staged Discord fetch into Digest.md + Thread.md.

Stage 2 of the feedback digest (stage 1 is discord-feedback-fetch.py). One call to
Kimi (OpenAI-compatible API) does the reading and triage. Everything else is plain
Python: copying screenshots into the vault, writing the thread, and rendering the
digest with screenshots embedded under each item so it reads on one page in Obsidian.

The triage rules (what counts as P0, lanes, feature names, the JSON shape) live in
digest-prompt.md (in the skill folder) and are sent as the
system prompt. Change behaviour there; change layout here.

Auth / config (env):
    KIMI_API_KEY      required — Moonshot / Kimi API key
    KIMI_MODEL        default kimi-k3.1-pro
    KIMI_BASE_URL     default https://api.moonshot.ai/v1  (api.moonshot.cn/v1 for China keys)
    KIMI_MAX_TOKENS   default 64000 (reasoning counts toward it)
    KIMI_REASONING_EFFORT  default low — low | high | max (Kimi's own default, max, is slow)

Usage:
    python3 scripts/discord-feedback-digest.py \
        --stage .wb-feedback/2026-10-26 \
        --out "20_PRODUCTS/26_Webuddhist/Feedback/UX Feedback Digest 2026-10-26" \
        --date 2026-10-26
    # --dry-run   build the request and write it to <stage>/request-preview.txt, no API call
    # --response  render from a saved model JSON instead of calling the API
"""

import argparse
import base64
import io
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

REPO = Path(__file__).resolve().parent.parent
# The triage prompt ships with the skill (digest-prompt.md in the skill folder). Look for it
# next to this script's parent (scripts/ inside the skill folder), then at the install path used
# by webuddhist-knowledge. Override with --prompt or DIGEST_PROMPT_FILE.
PROMPT_CANDIDATES = [
    REPO / "digest-prompt.md",
    REPO / "80_SYSTEM/82_Skills/UX/discord-feedback-digest/digest-prompt.md",
    REPO / ".claude/skills/discord-feedback-digest/digest-prompt.md",
]
PROMPT_FILE = Path(os.environ["DIGEST_PROMPT_FILE"]) if os.environ.get("DIGEST_PROMPT_FILE") else \
    next((c for c in PROMPT_CANDIDATES if c.exists()), PROMPT_CANDIDATES[0])

STITCH_GAP_SECONDS = 10 * 60   # same author within 10 min = one feedback unit
VISION_MAX_EDGE = 768          # downscale for the request only; vault copy is untouched
ITEM_IMAGE_CAP = 4             # screenshots embedded under one digest item
THUMB = 250                    # Obsidian width for embedded screenshots

SECTIONS = [
    ("dev", "🛠 Dev"),
    ("design", "🎨 Design"),
    ("l10n", "🌐 Localization"),
    ("unclear", "🤔 Needs clarification / not actionable yet"),
]
PRIORITY = {"P0": (0, "🔴"), "P1": (1, "🟠"), "P2": (2, "🟡")}

VAGUE_WORDS = re.compile(
    r"\b(this|these|that|here|there|see|look|above|below|attached|screenshot|"
    r"like so|wrong|weird|strange|broken|issue|bug|error|why|what)\b|\?",
    re.IGNORECASE,
)


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- input ----------

def clean_text(s: str) -> str:
    """Discord markup → readable text (mentions, channels, custom emoji)."""
    s = re.sub(r"<@!?&?\d+>", "@someone", s)
    s = re.sub(r"<#\d+>", "#channel", s)
    s = re.sub(r"<a?:(\w+):\d+>", r":\1:", s)
    return s.strip()


def load_messages(stage: Path):
    path = stage / "messages.json"
    if not path.exists():
        die(f"{path} not found — run discord-feedback-fetch.py first.")
    raw = json.loads(path.read_text())
    msgs, images = [], {}
    for n, r in enumerate(raw, 1):
        img_ids = []
        for p in r.get("images", []):
            src = Path(p)
            if not src.exists():                       # absolute paths from another machine
                src = stage / "images" / src.name
            if not src.exists():
                continue
            iid = f"i{len(images) + 1}"
            images[iid] = {"src": src, "name": src.name, "msg": f"m{n}"}
            img_ids.append(iid)
        msgs.append({
            "id": f"m{n}",
            "author": r.get("author") or "unknown",
            "ts": datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")),
            "text": clean_text(r.get("content", "")),
            "images": img_ids,
        })
    return msgs, images


def stitch(msgs):
    """Group consecutive same-author messages sent close together."""
    units = []
    for m in msgs:
        last = units[-1] if units else None
        if (last and last[-1]["author"] == m["author"]
                and (m["ts"] - last[-1]["ts"]).total_seconds() <= STITCH_GAP_SECONDS):
            last.append(m)
        else:
            units.append([m])
    return units


def is_vague(text: str) -> bool:
    t = text.strip()
    return len(t) < 60 or (len(t) < 160 and bool(VAGUE_WORDS.search(t)))


def pick_vision_images(units, cap: int):
    """Screenshots worth sending: those whose unit text doesn't explain itself."""
    picked = []
    for u in units:
        imgs = [i for m in u for i in m["images"]]
        if imgs and is_vague(" ".join(m["text"] for m in u)):
            picked.extend(imgs[:3])
    return picked[:cap]


def encode_image(path: Path) -> str:
    data, mime = path.read_bytes(), "image/png"
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((VISION_MAX_EDGE, VISION_MAX_EDGE))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80)
            data, mime = buf.getvalue(), "image/jpeg"
    except Exception:  # noqa: BLE001 — no Pillow / odd format: send the original
        ext = path.suffix.lower().lstrip(".")
        mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def unit_parts(u, vision, enc):
    """One stitched unit as content parts: its text, then the screenshots sent for vision."""
    lines = [f"--- {u[0]['author']} ({u[0]['ts']:%Y-%m-%d %H:%M})"]
    for m in u:
        imgs = f"  {{images: {', '.join(m['images'])}}}" if m["images"] else ""
        lines.append(f"[{m['id']}] {m['text'] or '(no text)'}{imgs}")
    parts = [{"type": "text", "text": "\n".join(lines)}]
    for m in u:
        for iid in m["images"]:
            if iid in vision:
                parts.append({"type": "text", "text": f"{iid}:"})
                parts.append({"type": "image_url", "image_url": {"url": enc(iid)}})
    return parts


def build_content(units, images, vision, enc):
    n = sum(len(u) for u in units)
    sent = sum(1 for u in units for m in u for i in m["images"] if i in vision)
    content = [{"type": "text", "text":
                f"Messages ({n}), oldest first. Screenshots sent for you to see ({sent} of "
                f"{len(images)}) follow the message that posted them."}]
    for u in units:
        content += unit_parts(u, vision, enc)
    content.append({"type": "text", "text": "Return the JSON object now."})
    return content


def system_prompt() -> str:
    text = PROMPT_FILE.read_text()
    return re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()  # drop frontmatter


# ---------- model ----------

class ContentFilter(Exception):
    """Kimi's moderation rejected the prompt (HTTP 400, type content_filter)."""


def kimi_post(content, max_tokens, stream):
    key = os.environ.get("KIMI_API_KEY", "").strip()
    if not key:
        die("KIMI_API_KEY is not set.")
    base = os.environ.get("KIMI_BASE_URL", "").strip() or "https://api.moonshot.ai/v1"
    body = {
        "model": os.environ.get("KIMI_MODEL", "").strip() or "kimi-k3.1-pro",
        "messages": [{"role": "system", "content": system_prompt()},
                     {"role": "user", "content": content}],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens,
        "reasoning_effort": os.environ.get("KIMI_REASONING_EFFORT", "").strip() or "low",
        "stream": stream,
    }
    for attempt in range(4):
        try:
            r = requests.post(f"{base.rstrip('/')}/chat/completions", json=body, stream=stream,
                              headers={"Authorization": f"Bearer {key}"}, timeout=(30, 600))
            if r.status_code == 400 and "content_filter" in r.text:
                raise ContentFilter(r.text[:300])
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code != 200:
                die(f"Kimi API {r.status_code}: {r.text[:500]}")
            return r
        except (requests.RequestException, RuntimeError) as e:
            if attempt == 3:
                die(f"Kimi API failed after 4 tries: {e}")
            wait = 15 * (attempt + 1)
            print(f"  ! {e} — retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)


def call_kimi(content) -> str:
    r = kimi_post(content, int(os.environ.get("KIMI_MAX_TOKENS", "") or "64000"),
                  stream=True)  # long generations; streaming keeps the connection alive
    out, reasoning, finish = [], 0, None
    for raw in r.iter_lines():
        line = raw.decode("utf-8")  # SSE often omits charset; requests would guess Latin-1
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        choice = json.loads(data)["choices"][0]
        delta = choice.get("delta", {})
        out.append(delta.get("content") or "")
        reasoning += len(delta.get("reasoning_content") or "")
        finish = choice.get("finish_reason") or finish
    if finish == "length":
        die(f"Model hit max_tokens before finishing ({reasoning} chars of reasoning, "
            f"{sum(map(len, out))} chars of answer) — raise KIMI_MAX_TOKENS or lower "
            f"KIMI_REASONING_EFFORT.")
    return "".join(out)


def find_blocked(units, vision, enc):
    """Bisect the units with tiny probe calls to find what the content filter rejects.
    Returns (unit indexes to leave out entirely, screenshot ids to stop sending)."""
    bad_units, bad_imgs = set(), set()

    def passes(idx, with_images=True):
        parts = [p for i in idx for p in unit_parts(units[i], vision if with_images else set(), enc)]
        try:
            kimi_post(parts + [{"type": "text", "text": "Reply with {}."}], 16, stream=False)
            return True
        except ContentFilter:
            return False

    def bisect(idx, known_bad=False):
        if not known_bad and passes(idx):
            return
        if len(idx) == 1:
            imgs = {i for m in units[idx[0]] for i in m["images"] if i in vision}
            if imgs and passes(idx, with_images=False):
                bad_imgs.update(imgs)
            else:
                bad_units.add(idx[0])
            return
        mid = len(idx) // 2
        bisect(idx[:mid])
        bisect(idx[mid:])

    bisect(list(range(len(units))), known_bad=True)
    return bad_units, bad_imgs


def triage(units, images, vision, enc):
    """One Kimi call; if moderation rejects it, isolate the flagged messages and retry."""
    print(f"Calling {os.environ.get('KIMI_MODEL') or 'kimi-k3.1-pro'} ...")
    try:
        return call_kimi(build_content(units, images, vision, enc)), []
    except ContentFilter as e:
        print(f"  ! content filter rejected the batch ({e}) — isolating flagged messages")
    bad_units, bad_imgs = find_blocked(units, vision, enc)
    kept = [u for n, u in enumerate(units) if n not in bad_units]
    blocked = [u for n, u in enumerate(units) if n in bad_units]
    print(f"  {len(blocked)} unit(s) left out, {len(bad_imgs)} screenshot(s) not sent")
    vision = vision - bad_imgs
    for attempt_vision in (vision, set()):  # last resort: text only
        try:
            return call_kimi(build_content(kept, images, attempt_vision, enc)), blocked
        except ContentFilter:
            print("  ! still rejected — retrying without screenshots", file=sys.stderr)
    die("Kimi's content filter rejects the batch even text-only.")


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            die("Model reply contained no JSON object.")
        return json.loads(text[start:end + 1])


# ---------- render ----------

def img_md(images, iid, caption=""):
    alt = " ".join(re.sub(r"[\[\]|]", " ", caption or "screenshot").split())
    return f"![{alt}|{THUMB}]({quote('screenshots/' + images[iid]['name'])})"


def short_date(ts) -> str:
    return f"{ts:%b} {ts.day}"


def reporters_md(names, dates=None):
    """Reporter names, each followed by the day(s) they reported it (UTC)."""
    dates = dates or {}
    names = list(dict.fromkeys(n for n in names if n))
    if not names:
        return ""
    who = [f"{n} ({', '.join(dates[n])})" if dates.get(n) else n for n in names]
    if len(who) == 1:
        return f"reported by {who[0]}"
    return f"{len(who)} reporters: {'; '.join(who)}"


def normalise_items(result, msgs, images):
    msg_by_id = {m["id"]: m for m in msgs}
    items = []
    for it in result.get("items", []):
        section = it.get("section") if it.get("section") in dict(SECTIONS) else "unclear"
        prio = it.get("priority") if it.get("priority") in PRIORITY else "P2"
        mids = [m for m in it.get("messages", []) if m in msg_by_id]
        # Screenshots of the cited messages first, then any extra ones the model named.
        iids = [i for m in mids for i in msg_by_id[m]["images"]]
        iids += [i for i in it.get("images", []) if i in images]
        iids = list(dict.fromkeys(iids))
        dates = {}
        for m in sorted((msg_by_id[m] for m in mids), key=lambda m: m["ts"]):
            day = short_date(m["ts"])
            if day not in dates.setdefault(m["author"], []):
                dates[m["author"]].append(day)
        items.append({
            "section": section,
            "feature": (it.get("feature") or "General").strip(),
            "priority": prio,
            "title": (it.get("title") or "").strip() or "(untitled)",
            "detail": (it.get("detail") or "").strip(),
            "reporters": it.get("reporters") or sorted({msg_by_id[m]["author"] for m in mids}),
            "dates": dates,
            "tags": [t.strip("`[] ") for t in it.get("tags", []) if t],
            "done": bool(it.get("done")),
            "images": iids,
        })
    return items


def render_digest(date, window, msgs, images, result, items, blocked=()):
    captions = result.get("captions", {})
    counts = {p: sum(1 for i in items if i["priority"] == p) for p in PRIORITY}
    first, last = msgs[0]["ts"], msgs[-1]["ts"]
    out = [
        "---",
        f"updated: {date}",
        "source: Discord #ux-feedback",
        f"window: {first:%Y-%m-%d} → {last:%Y-%m-%d}",
        "---",
        "",
        f"# UX Feedback Digest — {date}",
        "",
        f"> {len(msgs)} messages, {len(images)} screenshots, {first:%b %d} → {last:%b %d}. "
        f"{result.get('gist', '').strip()} Full transcript → [Thread](Thread.md).",
        f"> 🔴 {counts['P0']} P0 · 🟠 {counts['P1']} P1 · 🟡 {counts['P2']} P2",
        "",
    ]
    for key, heading in SECTIONS:
        sec = [i for i in items if i["section"] == key]
        if not sec:
            continue
        out += [f"## {heading}", ""]
        features = {}
        for i in sec:
            features.setdefault(i["feature"], []).append(i)
        rank = lambda i: (PRIORITY[i["priority"]][0], -len(i["reporters"]))  # noqa: E731
        ordered = sorted(features.items(), key=lambda kv: (min(rank(i) for i in kv[1]), -len(kv[1])))
        for feature, feats in ordered:
            out += [f"### {feature}", ""]
            for i in sorted(feats, key=rank):
                box = "x" if i["done"] else " "
                parts = [f"- [{box}] {PRIORITY[i['priority']][1]} **{i['title']}**"]
                if i["detail"]:
                    parts.append(f" — {i['detail']}")
                who = reporters_md(i["reporters"], i["dates"])
                if who:
                    parts.append(f" · {who}")
                if i["tags"]:
                    parts.append(" " + " ".join(f"`[{t}]`" for t in i["tags"]))
                out.append("".join(parts))
                if i["images"]:
                    shown = i["images"][:ITEM_IMAGE_CAP]
                    more = len(i["images"]) - len(shown)
                    line = " ".join(img_md(images, s, captions.get(s, "")) for s in shown)
                    if more > 0:
                        line += f" *+{more} more in [Thread](Thread.md)*"
                    out.append(f"  {line}")
                out.append("")
    if blocked:
        out += ["## ⚠️ Not triaged (rejected by Kimi's content filter)", "",
                "*Kimi's moderation refused these messages, so read them yourself.*", ""]
        for u in blocked:
            text = "\n\n".join(m["text"] for m in u if m["text"]) or "(no text)"
            out.append(f"- [ ] **{u[0]['author']}** ({short_date(u[0]['ts'])}):")
            out += [f"  {line}".rstrip() for line in text.splitlines()]  # keeps code fences inside the item
            iids = [i for m in u for i in m["images"]][:ITEM_IMAGE_CAP]
            if iids:
                out.append("  " + " ".join(img_md(images, i) for i in iids))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_thread(date, window, units, images, captions):
    out = [
        "---",
        f"updated: {date}",
        "---",
        "",
        f"# UX Feedback Thread — {date}",
        "",
        "⬅ Back to [Digest](Digest.md)",
        "",
        f"Discord #ux-feedback · {window} · {sum(len(u) for u in units)} messages, "
        f"{len(images)} screenshots",
        "",
        "---",
        "",
    ]
    for u in units:
        text = "\n".join(m["text"] for m in u if m["text"])
        if "```" in text:  # a fence can't open mid-line after the author's name
            out += [f"**{u[0]['author']}:**", "", text]
        else:
            out.append(f"**{u[0]['author']}:** {text}".rstrip())
        iids = [i for m in u for i in m["images"]]
        if iids:
            out += ["", " ".join(img_md(images, i, captions.get(i, "")) for i in iids)]
            caps = [captions[i] for i in iids if captions.get(i)]
            out += [f"*{c}*" for c in caps]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def read_window(stage: Path) -> str:
    manifest = stage / "manifest.txt"
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            if line.startswith("Window:"):
                return line.split(":", 1)[1].strip()
    return "since last run"


def main():
    ap = argparse.ArgumentParser(description="Write the feedback digest from a staged fetch.")
    ap.add_argument("--stage", required=True, help="Folder written by discord-feedback-fetch.py")
    ap.add_argument("--out", required=True, help="Digest folder to write")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--max-vision", type=int, default=80,
                    help="Max screenshots sent to the model (cost cap)")
    ap.add_argument("--dry-run", action="store_true", help="Build the request, don't call the API")
    ap.add_argument("--response", help="Render from a saved model JSON instead of calling the API")
    ap.add_argument("--prompt", help="Path to digest-prompt.md (default: found next to the skill)")
    args = ap.parse_args()
    if args.prompt:
        global PROMPT_FILE
        PROMPT_FILE = Path(args.prompt)

    stage, out = Path(args.stage), Path(args.out)
    msgs, images = load_messages(stage)
    window = read_window(stage)
    out.mkdir(parents=True, exist_ok=True)

    if not msgs:
        (out / "Digest.md").write_text(f"---\nupdated: {args.date}\n---\n\nNo feedback in window.\n")
        print("No messages — wrote a one-line digest.")
        return

    units = stitch(msgs)
    vision = set(pick_vision_images(units, args.max_vision))
    print(f"{len(msgs)} messages in {len(units)} units, {len(images)} screenshots "
          f"({len(vision)} sent for vision)")

    cache = {}
    enc = lambda iid: cache.setdefault(iid, encode_image(images[iid]["src"]))  # noqa: E731
    if args.dry_run:
        text = "\n\n".join(p["text"] for p in build_content(units, images, vision, lambda i: "")
                           if p["type"] == "text")
        (stage / "request-preview.txt").write_text(
            f"{system_prompt()}\n\n===== USER =====\n{text}\n")
        print(f"Dry run — wrote {stage / 'request-preview.txt'}")
        return

    blocked = []
    if args.response:
        reply = Path(args.response).read_text()
    else:
        reply, blocked = triage(units, images, vision, enc)
        (stage / "model-response.json").write_text(reply)  # staged only, never committed
    result = parse_json(reply)
    items = normalise_items(result, msgs, images)
    if not items and not blocked:
        die("Model returned no items — see model-response.json in the stage folder.")

    shots = out / "screenshots"
    shots.mkdir(exist_ok=True)
    for img in images.values():
        shutil.copy2(img["src"], shots / img["name"])

    captions = {k: v for k, v in result.get("captions", {}).items() if k in images}
    (out / "Digest.md").write_text(render_digest(args.date, window, msgs, images, result, items, blocked))
    (out / "Thread.md").write_text(render_thread(args.date, window, units, images, captions))
    p0 = [i["title"] for i in items if i["priority"] == "P0"]
    print(f"Wrote {out / 'Digest.md'}: {len(items)} items, {len(p0)} P0")
    for t in p0:
        print(f"  🔴 {t}")


if __name__ == "__main__":
    main()
