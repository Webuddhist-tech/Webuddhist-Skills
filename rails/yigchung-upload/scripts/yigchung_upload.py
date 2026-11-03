#!/usr/bin/env python3
"""Parse the <small>…</small> yigchung marks out of an uploaded note and attach
them to its live edition as yigchung annotations.

    POST /v2/editions/{edition_id}/yigchungs   {"span": {"start": N, "end": M}}

One call per mark. `start` is inclusive, `end` exclusive, both offsets into the
edition content — the tags themselves never entered that content (the upload
parser strips them), so each span covers exactly the text between a pair of tags.

How the offsets are made safe. The spans are computed by replaying the upload
parser's own content build line for line (same blocks, same skips, same
trimming), with the tag positions carried along. Before a plan is printed:

  1. the replayed content must equal the upload parser's content, char for char
     (so this script cannot drift from the parser that built the edition);
  2. it must equal the live edition content, char for char (so the offsets are
     offsets into what the backend actually holds);
  3. the text under each span must equal the text between its tags in the note.

Any mismatch aborts. Nothing is sent without --execute.

Usage (from the vault root):

    set -a; source 4-SYSTEM/scripts/.env; set +a
    python3 4-SYSTEM/Skills/yigchung-upload/scripts/yigchung_upload.py <note>            # dry run + review file
    python3 4-SYSTEM/Skills/yigchung-upload/scripts/yigchung_upload.py <note> --execute
    python3 4-SYSTEM/Skills/yigchung-upload/scripts/yigchung_upload.py <note> --verify

Env: WEBUDDHIST_API_KEY (X-API-Key), WEBUDDHIST_APP (optional X-Application),
WEBUDDHIST_API_BASE (default https://library.webuddhist.com), LEDGER_PATH.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

SKILL_DIR = pathlib.Path(__file__).resolve().parent
PARSER_PATH = SKILL_DIR.parents[1] / "translation-upload" / "scripts" / "parser-root-text" / "parser.py"
OUTPUT_DIR = SKILL_DIR / "output"
LEDGER = pathlib.Path(os.environ.get("LEDGER_PATH", SKILL_DIR / "upload_ledger.json"))
BASE = os.environ.get("WEBUDDHIST_API_BASE", "https://library.webuddhist.com").rstrip("/")

TAG_RE = re.compile(r"<(/?)small>", re.IGNORECASE)


def load_parser():
    if not PARSER_PATH.exists():
        sys.exit(f"upload parser not found: {PARSER_PATH}")
    spec = importlib.util.spec_from_file_location("upload_parser", PARSER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "SMALL_TAG_RE"):
        sys.exit("the upload parser does not strip <small> tags, so the live content would contain them — "
                 "offsets computed here would not match. Fix the parser first.")
    return mod


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def headers(body=False):
    h = {"Accept": "application/json"}
    key = os.environ.get("WEBUDDHIST_API_KEY")
    if key:
        h["X-API-Key"] = key
    if os.environ.get("WEBUDDHIST_APP"):
        h["X-Application"] = os.environ["WEBUDDHIST_APP"]
    if body:
        h["Content-Type"] = "application/json"
    return h


def call(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers(data is not None))
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} {method} {url}\n         {exc.read()[:400].decode('utf-8', 'replace')}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url}: {exc.reason}")


# ---------------------------------------------------------------------------
# Span extraction — a replay of parser._build_content_and_segmentation
# ---------------------------------------------------------------------------

def _strip_with_events(raw_line):
    """Remove the tags from a line; return the cleaned line and the tag events
    as (position in the cleaned line, is_close)."""
    out, events, last = [], [], 0
    for m in TAG_RE.finditer(raw_line):
        out.append(raw_line[last:m.start()])
        events.append((sum(len(p) for p in out), m.group(1) == "/"))
        last = m.end()
    out.append(raw_line[last:])
    return "".join(out), events


def extract(parser, blocks):
    """Return (content, marks, warnings, included). Each mark: start, end, ref.
    `included` is the raw text of the blocks that reach the edition."""
    parts, marks, warnings, included = [], [], [], []
    pos = 0
    open_at = open_ref = None   # global offset and block of an unclosed <small>

    for block_num, block in enumerate(blocks, start=1):
        ref = block["ref"]
        raw_lines = block["lines"]
        content_lines = [l for l in raw_lines if not parser.TRANSCLUSION_RE.match(l)]
        tagged = any(TAG_RE.search(l) for l in content_lines)
        if not any(l.strip() for l in content_lines):
            continue
        if not ref or block["is_header"] or parser._ref_part_count(ref) > parser.VERSE_REF_MAX_PARTS:
            if tagged:
                why = "heading" if block["is_header"] else "block not in the edition"
                warnings.append(f"block {block_num} ({ref or 'no ref'}): <small> in a {why} — not annotated")
            continue
        included.append("\n".join(content_lines))
        ref_bare = ref.lstrip("^")

        last_nonempty_idx = -1
        for i in range(len(content_lines) - 1, -1, -1):
            if content_lines[i].rstrip():
                last_nonempty_idx = i
                break

        for i, raw_line in enumerate(content_lines):
            clean, events = _strip_with_events(raw_line)
            # the parser's trimming: rstrip, then on the last line cut the ref and rstrip again.
            # Every step only shortens from the end, so the kept text is clean[:keep].
            text = clean.rstrip()
            if i == last_nonempty_idx:
                ref_idx = text.rfind(ref)
                if ref_idx != -1:
                    text = text[:ref_idx].rstrip()
            keep = len(text)
            for at, is_close in events:
                at = min(at, keep)
                if not is_close:
                    if open_at is not None:
                        raise ValueError(f"block {block_num} ({ref}): nested <small>")
                    open_at = pos + at if text else pos
                    open_ref = ref_bare
                else:
                    if open_at is None:
                        raise ValueError(f"block {block_num} ({ref}): </small> without <small>")
                    end = pos + at if text else pos
                    marks.append({"start": open_at, "end": end, "ref": open_ref})
                    open_at = None
            if not text:
                continue
            parts.append(text)
            pos += len(text)

    if open_at is not None:
        raise ValueError(f"unclosed <small> opened in {open_ref}")
    return "".join(parts), marks, warnings, included


def expected_texts(body):
    """The text between each pair of tags, straight from the note — the
    independent side of check 3. Line breaks and line-end whitespace are
    dropped because the edition content joins lines without a separator."""
    out = []
    for m in re.finditer(r"<small>(.*?)</small>", body, re.IGNORECASE | re.DOTALL):
        out.append("".join(l.rstrip() if i < m.group(1).count("\n") else l
                           for i, l in enumerate(m.group(1).split("\n"))))
    return out


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

def load_ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}


def save_ledger(ledger):
    tmp = LEDGER.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, LEDGER)


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("note")
    ap.add_argument("--execute", action="store_true", help="POST the spans (needs human confirmation)")
    ap.add_argument("--verify", action="store_true", help="GET the live yigchungs and compare")
    ap.add_argument("--no-live", action="store_true", help="skip the live checks (offline dry run only)")
    args = ap.parse_args(argv)

    note = pathlib.Path(args.note)
    if not note.exists():
        sys.exit(f"not found: {note}")
    parser = load_parser()
    fm, body = parser._read_source(note)
    edition_id = fm.get("edition_id")
    if not edition_id and not args.no_live:
        sys.exit(f"{note.name}: no edition_id in frontmatter — upload the text first")

    blocks = parser._extract_blocks(body)
    try:
        content, marks, warnings, included = extract(parser, blocks)
    except ValueError as exc:
        sys.exit(f"ABORT: {exc}")
    for w in warnings:
        print(f"  WARN {w}")

    # ---- checks -----------------------------------------------------------
    problems = []
    parser_content, segs, _ = parser._build_content_and_segmentation(blocks, "verse")
    if content != parser_content:
        problems.append("replayed content differs from the upload parser's content")

    live_content = None
    if not args.no_live:
        live_content = call("GET", f"{BASE}/v2/editions/{edition_id}/content")
        if not isinstance(live_content, str):
            live_content = (live_content or {}).get("content")
        if live_content != content:
            n = next((i for i, (a, b) in enumerate(zip(live_content or "", content)) if a != b),
                     min(len(live_content or ""), len(content)))
            problems.append(f"live edition content differs from the note at offset {n} "
                            f"(live {len(live_content or '')} chars, note {len(content)}) — the note changed "
                            f"since upload, or the edition is not this note's")

    expected = expected_texts("\n\n".join(included))
    annotated = [m for m in marks if m["end"] > m["start"]]
    empty = [m for m in marks if m["end"] <= m["start"]]
    for m in empty:
        print(f"  WARN empty <small></small> in {m['ref']} — skipped")
    if len(expected) != len(marks):
        problems.append(f"{len(expected)} tag pairs in the note but {len(marks)} marks extracted")
    ws_only = 0   # whitespace inside a tag at a line end: the parser trims it, so no span can hold it
    for i, (m, exp) in enumerate(zip(marks, expected), start=1):
        got = content[m["start"]:m["end"]]
        m["text"] = got
        if got.strip() != exp.strip():
            problems.append(f"mark {i} ({m['ref']}): span text {got[:40]!r} != tag text {exp[:40]!r}")
        elif got != exp:
            ws_only += 1

    ranges = [(s["reference"], s["lines"][0]["start"], s["lines"][-1]["end"]) for s in segs]
    for m in annotated:
        m["segments"] = [r for r, a, b in ranges if a < m["end"] and b > m["start"]]

    # ---- outputs ----------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = [{"span": {"start": m["start"], "end": m["end"]}} for m in annotated]
    pay_path = OUTPUT_DIR / f"{note.stem}.yigchungs.json"
    pay_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rev_path = OUTPUT_DIR / f"{note.stem}.yigchung-review.md"
    lines = [f"# Yigchung review — {note.name}", "",
             f"edition `{edition_id}` · {len(annotated)} spans · content {len(content)} chars · "
             f"live match: {'n/a (offline)' if args.no_live else ('yes' if live_content == content else 'NO')}", "",
             "| # | segment | start | end | text under the span |", "|---|---|---|---|---|"]
    for i, m in enumerate(annotated, start=1):
        seg = ", ".join(m["segments"]) + ("" if m["segments"] == [m["ref"]] else " ⚑")
        cell = m["text"].replace("|", r"\|")
        lines.append(f"| {i} | {seg} | {m['start']} | {m['end']} | {cell} |")
    rev_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n== checks ==")
    print(f"  {len(annotated)} spans over {len(content)} chars; payload {pay_path.name}; review {rev_path.name}")
    print(f"  replayed content == upload parser content : {content == parser_content}")
    if not args.no_live:
        print(f"  replayed content == live edition content : {live_content == content}")
    print(f"  span text == tag text for every mark       : {not any('span text' in p for p in problems)}"
          + (f"  ({ws_only} differ only by edge whitespace the parser trimmed)" if ws_only else ""))
    cross = [m for m in annotated if m["segments"] != [m["ref"]]]
    if cross:
        print(f"  NOTE {len(cross)} span(s) not confined to their own segment (⚑ in the review file)")
    if problems:
        for p in problems:
            print(f"  ERROR {p}")
        sys.exit("ABORT: checks failed — nothing sent")

    if args.no_live:
        print("\noffline dry run: nothing sent.")
        return 0

    live = call("GET", f"{BASE}/v2/editions/{edition_id}/yigchungs") or []
    live_spans = {(y["span"]["start"], y["span"]["end"]) for y in live}
    want = [(p["span"]["start"], p["span"]["end"]) for p in payload]

    if args.verify:
        missing = [s for s in want if s not in live_spans]
        extra = sorted(live_spans - set(want))
        print(f"\n== VERIFY ==\n  live yigchungs: {len(live)}   expected: {len(want)}   missing: {len(missing)}   unexpected: {len(extra)}")
        for s in missing[:10]:
            print(f"  MISSING {s} {content[s[0]:s[1]][:50]!r}")
        for s in extra[:10]:
            print(f"  UNEXPECTED {s} {content[s[0]:s[1]][:50]!r}")
        return 0 if not missing and not extra else 1

    extra = live_spans - set(want)
    if extra:
        sys.exit(f"ABORT: the live edition already has {len(extra)} yigchung(s) not in this payload — "
                 f"a human decides whether to remove them first.")
    todo = [s for s in want if s not in live_spans]
    print(f"\n== {'EXECUTE' if args.execute else 'DRY RUN'} ==")
    print(f"  POST {BASE}/v2/editions/{edition_id}/yigchungs  x {len(todo)}"
          f"  ({len(want) - len(todo)} already live, skipped)")
    if not args.execute:
        print("\ndry run: nothing sent. Review the review file, then re-run with --execute after confirmation.")
        return 0
    if not os.environ.get("WEBUDDHIST_API_KEY"):
        sys.exit("WEBUDDHIST_API_KEY is not set")

    ledger = load_ledger()
    entry = ledger.setdefault(edition_id, {"source_file": str(note), "yigchungs": []})
    try:
        for n, (s, e) in enumerate(todo, start=1):
            res = call("POST", f"{BASE}/v2/editions/{edition_id}/yigchungs", {"span": {"start": s, "end": e}})
            if n == 1:
                # A 201 with an id is not proof of a write: the backend returns a
                # generated id even when its CREATE matched nothing (e.g. no
                # MarkType 'yigchung' node). Read the first one back before going on.
                try:
                    call("GET", f"{BASE}/v2/yigchungs/{res['id']}")
                except RuntimeError:
                    raise RuntimeError(f"POST returned id {res['id']} but GET finds no such yigchung — the backend "
                                       f"did not store it (check that a MarkType 'yigchung' node exists). "
                                       f"Stopped after 1 call; nothing to clean up.")
            entry["yigchungs"].append({"id": res["id"], "start": s, "end": e,
                                       "ts": datetime.datetime.now().isoformat(timespec="seconds")})
            save_ledger(ledger)
        print(f"  created {len(todo)} yigchung(s)")
    except RuntimeError as exc:
        if not entry["yigchungs"]:
            ledger.pop(edition_id, None)
        save_ledger(ledger)
        print(f"\nFAIL {exc}\nledger: {LEDGER} — re-run to resume; live spans are skipped.", file=sys.stderr)
        return 1
    now_live = {(y["span"]["start"], y["span"]["end"]) for y in call("GET", f"{BASE}/v2/editions/{edition_id}/yigchungs") or []}
    missing = [s for s in want if s not in now_live]
    if missing:
        print(f"\nFAIL {len(missing)} of {len(want)} spans are not live after posting — run --verify", file=sys.stderr)
        return 1
    print(f"  read back: all {len(want)} spans live")
    print(f"\ndone. ledger: {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
