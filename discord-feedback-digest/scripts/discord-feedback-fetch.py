#!/usr/bin/env python3
"""
discord-feedback-fetch.py — pull recent messages + image attachments from a
Discord UX-feedback channel into a staging folder, ready for the
discord-feedback-digest skill to OCR and summarise.

Used by the `discord-feedback-digest` skill. Runs where the network is open
(your Mac: Terminal or Claude Code). The Cowork sandbox cannot reach
discord.com, so the *fetch* runs Mac-side; the *summarise* step is pure Claude
work and runs anywhere.

Auth: a Discord bot token in the DISCORD_BOT_TOKEN env var (see SETUP.md).
The bot needs View Channel + Read Message History in the target channel, and
the Message Content privileged intent enabled in the Developer Portal.

Usage:
    export DISCORD_BOT_TOKEN="..."            # or put it in ~/.zshrc

    # Daily / scheduled — only what's new since the last run (no overlap, no gap):
    python3 discord-feedback-fetch.py --channel 123... --since-last --out ./staging

    # Manual backfill — a fixed time window:
    python3 discord-feedback-fetch.py --channel 123... --hours 24 --out ./staging

Pass --channel more than once to pull several channels into one messages.json.

--since-last reads/writes a watermark (last message ID per channel) in a state
file next to this script. First run with no watermark falls back to --hours as a
bootstrap. Use --no-save-state for test runs that shouldn't move the watermark.

Output (in --out):
    messages.json   — list of {id, channel, author, timestamp, content, jump_url, images[]}
    images/         — downloaded attachment files referenced by messages.json
    manifest.txt    — human-readable summary of what was pulled
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

API = "https://discord.com/api/v10"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".tiff"}
STATE_FILE = Path(__file__).resolve().parent / ".discord-feedback-state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {}


def save_watermark(channel_id: str, last_id: str):
    state = load_state()
    state[channel_id] = {
        "last_message_id": last_id,
        "last_run": datetime.now(timezone.utc).isoformat(),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def get_token() -> str:
    tok = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not tok:
        die("DISCORD_BOT_TOKEN is not set. See SETUP.md (store it in ~/.zshrc).")
    return tok


def get_guild_id(channel_id: str, token: str) -> str:
    """Look up the channel's guild so we can build working jump-to-message URLs.
    (The messages endpoint doesn't return guild_id.)"""
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "WeBuddhistFeedbackBot (https://webuddhist.com, 1.0)",
    }
    try:
        r = requests.get(f"{API}/channels/{channel_id}", headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json().get("guild_id") or "@me"
    except Exception:  # noqa: BLE001
        pass
    return "@me"


def fetch_messages(channel_id: str, token: str, after_dt: datetime, max_pages: int = 20):
    """Page backwards through channel history, keeping messages newer than after_dt."""
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "WeBuddhistFeedbackBot (https://webuddhist.com, 1.0)",
    }
    collected = []
    before = None
    for _ in range(max_pages):
        params = {"limit": 100}
        if before:
            params["before"] = before
        r = requests.get(
            f"{API}/channels/{channel_id}/messages",
            headers=headers, params=params, timeout=30,
        )
        if r.status_code == 401:
            die("401 Unauthorized — bad token. Check DISCORD_BOT_TOKEN.")
        if r.status_code == 403:
            die("403 Forbidden — the bot lacks View Channel / Read Message "
                "History in this channel, or isn't in the server. See SETUP.md.")
        if r.status_code == 429:
            retry = float(r.headers.get("Retry-After", "2"))
            print(f"Rate limited; sleeping {retry}s", file=sys.stderr)
            time.sleep(retry)
            continue
        if r.status_code != 200:
            die(f"Discord API {r.status_code}: {r.text[:300]}")

        batch = r.json()
        if not batch:
            break

        stop = False
        for m in batch:
            ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
            if ts < after_dt:
                stop = True
                break
            collected.append(m)
        before = batch[-1]["id"]
        if stop or len(batch) < 100:
            break
        time.sleep(0.3)  # be polite to the rate limiter
    return collected


def fetch_after(channel_id: str, token: str, after_id: str, max_pages: int = 50):
    """Page forward through history, returning every message newer than after_id."""
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "WeBuddhistFeedbackBot (https://webuddhist.com, 1.0)",
    }
    collected = []
    seen = set()
    after = after_id
    for _ in range(max_pages):
        params = {"limit": 100, "after": after}
        r = requests.get(
            f"{API}/channels/{channel_id}/messages",
            headers=headers, params=params, timeout=30,
        )
        if r.status_code == 401:
            die("401 Unauthorized — bad token. Check DISCORD_BOT_TOKEN.")
        if r.status_code == 403:
            die("403 Forbidden — the bot lacks View Channel / Read Message "
                "History in this channel, or isn't in the server. See SETUP.md.")
        if r.status_code == 429:
            retry = float(r.headers.get("Retry-After", "2"))
            print(f"Rate limited; sleeping {retry}s", file=sys.stderr)
            time.sleep(retry)
            continue
        if r.status_code != 200:
            die(f"Discord API {r.status_code}: {r.text[:300]}")

        batch = r.json()  # NOTE: Discord returns newest-first even when using `after`
        if not batch:
            break
        new = [m for m in batch if m["id"] not in seen]
        if not new:
            break  # safety: nothing new came back, stop instead of looping
        for m in new:
            seen.add(m["id"])
        collected.extend(new)
        after = max(batch, key=lambda m: int(m["id"]))["id"]  # highest ID seen
        if len(batch) < 100:
            break
        time.sleep(0.3)
    # Return newest-first, matching fetch_messages (download_images reverses it).
    collected.sort(key=lambda m: int(m["id"]), reverse=True)
    return collected


def downscale_image(path: Path, max_edge: int):
    """Shrink an image in place so its longest side <= max_edge px. Vision models
    bill images by size, so this directly cuts vision-token cost. No-op if
    max_edge<=0, Pillow is missing, or the image is already small enough."""
    if max_edge <= 0:
        return
    try:
        from PIL import Image  # optional dep; skip silently if not installed
    except Exception:  # noqa: BLE001
        return
    try:
        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) <= max_edge:
                return
            scale = max_edge / float(max(w, h))
            resized = im.resize((max(1, round(w * scale)), max(1, round(h * scale))))
            if path.suffix.lower() in (".jpg", ".jpeg"):
                resized.convert("RGB").save(path, "JPEG", quality=85, optimize=True)
            else:
                resized.save(path)
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not downscale {path.name}: {e}", file=sys.stderr)


def download_images(messages, channel_id: str, img_dir: Path, guild_id: str = "@me",
                    max_edge: int = 1280):
    img_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for m in reversed(messages):  # oldest first, reads more naturally
        author = m.get("author", {}).get("global_name") \
            or m.get("author", {}).get("username", "unknown")
        ts = m["timestamp"]
        guild_hint = m.get("guild_id") or guild_id
        jump = f"https://discord.com/channels/{guild_hint}/{channel_id}/{m['id']}"
        image_paths = []
        for att in m.get("attachments", []):
            url = att.get("url", "")
            name = att.get("filename", "")
            ext = Path(urlparse(url).path).suffix.lower()
            ctype = (att.get("content_type") or "").lower()
            if ext in IMAGE_EXTS or ctype.startswith("image/"):
                safe = f"{m['id']}_{name}".replace("/", "_")
                dest = img_dir / safe
                last_err = None
                for attempt in range(3):  # transient CDN 5xx/timeouts usually clear on retry
                    try:
                        resp = requests.get(url, timeout=60)
                        resp.raise_for_status()
                        dest.write_bytes(resp.content)
                        downscale_image(dest, max_edge)
                        image_paths.append(str(dest))
                        last_err = None
                        break
                    except Exception as e:  # noqa: BLE001
                        last_err = e
                        if attempt < 2:
                            time.sleep(2 * (attempt + 1))  # 2s, then 4s
                if last_err is not None:
                    print(f"  ! failed to download {name} after 3 tries: {last_err}",
                          file=sys.stderr)
        records.append({
            "id": m["id"],
            "author": author,
            "timestamp": ts,
            "content": m.get("content", ""),
            "jump_url": jump,
            "images": image_paths,
        })
    return records


def fetch_channel(channel: str, args, token: str, state: dict, img_dir: Path):
    """Fetch one channel. Returns (records, window_desc)."""
    guild_id = get_guild_id(channel, token)
    watermark = state.get(channel, {}).get("last_message_id")
    if args.full_history:
        print(f"[{channel}] Fetching full channel history...")
        epoch = datetime(2015, 1, 1, tzinfo=timezone.utc)  # predates Discord
        messages = fetch_messages(channel, token, epoch, max_pages=10000)
        window_desc = "full history"
    elif args.since_last and watermark:
        print(f"[{channel}] Fetching messages after last run (id {watermark})...")
        messages = fetch_after(channel, token, watermark)
        window_desc = f"since last run (after id {watermark})"
    else:
        if args.since_last:
            print(f"[{channel}] No saved watermark yet — bootstrapping with --hours window.")
        after_dt = datetime.now(timezone.utc) - timedelta(hours=args.hours)
        print(f"[{channel}] Fetching messages since {after_dt.isoformat()} ({args.hours}h)...")
        messages = fetch_messages(channel, token, after_dt)
        window_desc = f"last {args.hours}h"
    print(f"  {len(messages)} message(s) in window")

    records = download_images(messages, channel, img_dir, guild_id, args.max_image_edge)
    for r in records:
        r["channel"] = channel
    return records, window_desc


def main():
    ap = argparse.ArgumentParser(description="Fetch Discord feedback for the digest skill.")
    ap.add_argument("--channel", action="append", required=True, dest="channels",
                    help="Discord channel ID (repeat for multiple channels)")
    ap.add_argument("--hours", type=float, default=24, help="Look back this many hours (default 24)")
    ap.add_argument("--since-last", action="store_true",
                    help="Fetch only messages newer than the last saved run (no overlap). "
                         "Falls back to --hours on first run.")
    ap.add_argument("--full-history", action="store_true",
                    help="Fetch every message in the channel(s). Overrides --hours/--since-last.")
    ap.add_argument("--no-save-state", action="store_true",
                    help="Don't advance the watermark (use for test runs).")
    ap.add_argument("--max-image-edge", type=int, default=1280,
                    help="Downscale screenshots so the longest side is <= this many px "
                         "(0 = off). Cuts vision-token cost; needs Pillow.")
    ap.add_argument("--out", default="./staging", help="Output directory")
    args = ap.parse_args()

    token = get_token()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    state = load_state()

    all_records, summaries = [], []
    for channel in dict.fromkeys(args.channels):  # dedupe, keep order
        records, window_desc = fetch_channel(channel, args, token, state, out / "images")
        all_records.extend(records)
        summaries.append((channel, window_desc, records))

    all_records.sort(key=lambda r: int(r["id"]))  # snowflake IDs are time-ordered
    n_imgs = sum(len(r["images"]) for r in all_records)
    print(f"  {len(all_records)} message(s), {n_imgs} image(s) across {len(summaries)} channel(s)")

    (out / "messages.json").write_text(json.dumps(all_records, indent=2, ensure_ascii=False))

    # Advance watermarks only after messages.json is safely written.
    if not args.no_save_state:
        for channel, _, records in summaries:
            if records:
                save_watermark(channel, max((r["id"] for r in records), key=int))

    with (out / "manifest.txt").open("w") as f:
        f.write(f"Discord feedback fetch — {datetime.now(timezone.utc).isoformat()}\n")
        for channel, window_desc, records in summaries:
            imgs = sum(len(r["images"]) for r in records)
            f.write(f"Channel {channel}: {window_desc} — {len(records)} msg, {imgs} img\n")
        f.write(f"Total: {len(all_records)} messages, {n_imgs} images\n\n")
        for r in all_records:
            f.write(f"- [{r['timestamp']}] ({r['channel']}) {r['author']}: "
                    f"{(r['content'] or '(no text)')[:80]}"
                    f"{'  [' + str(len(r['images'])) + ' img]' if r['images'] else ''}\n")

    print(f"Done. Wrote {out/'messages.json'} and {n_imgs} image(s) to {out/'images'}")
    if not all_records:
        print("NOTE: nothing in the window — channels may have been quiet.")


if __name__ == "__main__":
    main()
