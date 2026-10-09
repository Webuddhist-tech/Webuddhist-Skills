#!/usr/bin/env python3
"""
find_toc_contexts.py -- rewrite [[context]] in a TOC tree with accurate body contexts.

Gemini-first approach: no string matching. Gemini acts as a Tibetan Buddhist
text expert and locates each section's body description directly.

For each TOC entry Gemini receives:
  - The full TOC structure (all entries with their decimal numbers and titles)
  - The source passage covering the expected region (numbered lines)
  - The section's position in the hierarchy (parent, preceding siblings)

Gemini returns the line number and verbatim opening words of the BODY
DESCRIPTION -- where the commentary actually explains the topic -- not the
dkar-chag heading where the title is merely listed.

The search window advances strictly after each located body line so sibling
sections never overlap.

Usage:
    python 4-SYSTEM/Skills/seg-toc-lib/toc_tree_extractor/find_toc_contexts.py \\
        0-INBOX/toc-tree-BCAC20_TG_bo.md \\
        1-SOURCES/Commentaries/BCAC20_TG_bo.md
"""

import argparse
import os
import re
import sys
from pathlib import Path


# ── Gemini API key ────────────────────────────────────────────────────────────
_KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _gemini_api_key():
    """
    The Gemini API key: from the environment if set, otherwise from the `.env`
    file at the vault root (a folder that contains 4-SYSTEM/), found by walking
    up from this script's own location, then from the current directory; the
    nearest vault root with a .env wins (so a benchmark copy inside the vault
    still uses the vault's own .env).
    Only GEMINI_API_KEY / GOOGLE_API_KEY are read; nothing else from .env is
    loaded, and the key is never printed or logged.
    """
    for n in _KEY_NAMES:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    roots = []          # every folder containing 4-SYSTEM/, nearest first
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        for d in (start, *start.parents):
            if (d / "4-SYSTEM").is_dir() and d not in roots:
                roots.append(d)
    for root in roots:
        envf = root / ".env"
        if not envf.is_file():
            continue
        try:
            lines = envf.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            continue
        found = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k.startswith("export "):
                k = k[len("export "):].strip()
            if k not in _KEY_NAMES:
                continue
            v = v.strip()
            if v[:1] in ("'", '"') and v[-1:] == v[:1] and len(v) >= 2:
                v = v[1:-1]
            else:
                v = v.split(" #", 1)[0].strip()
            if v:
                found[k] = v
        for n in _KEY_NAMES:
            if n in found:
                return found[n]
    return None


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

DEFAULT_MODEL  = "gemini-3.8-flash"

# Gemini 3.8 Flash with high thinking. On Gemini 3.x thinking cannot be switched off and
# counts against max_output_tokens; temperature stays at the API default (Google advises
# against lowering it on 3.x — it causes looping). A reply cut off at the limit is an
# error and is retried, never used as an answer.
GEMINI_THINKING   = "high"
GEMINI_MAX_OUTPUT = 65536


def _check_finish(resp):
    """Raise if the reply was cut off at max_output_tokens (thinking counts too)."""
    cand = (getattr(resp, "candidates", None) or [None])[0]
    if "MAX_TOKENS" in str(getattr(cand, "finish_reason", "") or ""):
        raise RuntimeError(f"reply cut off at max_output_tokens={GEMINI_MAX_OUTPUT} "
                           f"(thinking counts too)")

DEFAULT_WINDOW = 200   # source lines per search window
SLIDE_STEP     = 50   # lines to advance when section not found in window
MAX_SLIDES     = 5     # max times to slide before giving up
MAX_RETRIES    = 5
RETRY_BACKOFF  = 6

# ---------------------------------------------------------------------------
# Tibetan helpers
# ---------------------------------------------------------------------------
_TSHEG = "་"
_SHAD_CHARS = "།༎༏༐༑༒༔"
_SHAD_OR_WS_RE = re.compile("[" + _SHAD_CHARS + r"\s]+")


def tib_canon(s):
    if not s:
        return ""
    s = _SHAD_OR_WS_RE.sub(_TSHEG, s)
    s = re.sub(re.escape(_TSHEG) + "+", _TSHEG, s)
    return s.strip(_TSHEG)


def trim_syllables(text, max_sylls=20):
    sylls = text.split(_TSHEG)
    if len(sylls) > max_sylls:
        return _TSHEG.join(sylls[:max_sylls])
    return text


# ---------------------------------------------------------------------------
# TOC tree parser / writer
# ---------------------------------------------------------------------------
_TREE_RE = re.compile(
    r"^(?P<indent>\s*\*\s+(?P<dec>\d+(?:\.\d+)*)\.?\s+)"
    r"(?P<title>[^\[]+?)(?:\s*\[\[(?P<ctx>[^\]]*)\]\])?\s*$"
)


def parse_toc(path):
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = _TREE_RE.match(raw)
        if not m:
            continue
        title = m.group("title").strip().rstrip("།").strip()
        entries.append({
            "dec":   m.group("dec"),
            "title": title,
            "ctx":   (m.group("ctx") or "").strip() or None,
            "raw":   raw,
        })
    return entries


def rewrite_toc(path, new_contexts, out_path=None):
    """Write updated toc-tree to out_path. Backs up original as .bak."""
    if out_path is None:
        out_path = path
    raw_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    for raw in raw_lines:
        m = _TREE_RE.match(raw.rstrip("\n\r"))
        if m and m.group("dec") in new_contexts:
            dec    = m.group("dec")
            indent = m.group("indent")
            title  = m.group("title").strip().rstrip("།").strip()
            ctx    = new_contexts[dec]
            out.append(f"{indent}{title} [[{ctx}]]\n")
        else:
            out.append(raw)
    bak = path.with_suffix(path.suffix + ".bak")
    bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(out), encoding="utf-8")
    return bak


def find_vault_root(start):
    for p in [start] + list(start.parents):
        if (p / "4-SYSTEM").is_dir():
            return p
    return start


def toc_summary(entries):
    """Full TOC as a compact reference string to give Gemini structural context."""
    lines = []
    for e in entries:
        depth  = len(e["dec"].split("."))
        indent = "  " * (depth - 1)
        ctx    = f" [[{e['ctx']}]]" if e["ctx"] and e["ctx"] != "?" else ""
        lines.append(f"{indent}{e['dec']}. {e['title']}{ctx}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------
def get_client():
    try:
        from google import genai
    except ImportError:
        sys.exit("Error: google-genai not installed. Run: pip install google-genai")
    api_key = _gemini_api_key()
    if not api_key:
        sys.exit("Error: no Gemini API key found.\n  Put GEMINI_API_KEY=your-key in the .env file at the vault root (next to 4-SYSTEM/),\n  or set GEMINI_API_KEY in the environment.")
    return genai.Client(api_key=api_key)


# ---------------------------------------------------------------------------
# Core: Gemini locates the body description
# ---------------------------------------------------------------------------
def gemini_locate_body(client, model,
                       lines, start_line, end_line,
                       dec, title,
                       toc_ref,
                       parent_dec=None, parent_title=None,
                       prev_siblings=None):
    """
    Ask Gemini -- as a Tibetan Buddhist text expert -- to find where section
    `dec` (`title`) is DESCRIBED in the body commentary, within the passage
    lines[start_line:end_line].

    The passage is presented with line numbers so Gemini can cite the exact line.

    Returns (snippet, body_line_idx) where:
      snippet        -- verbatim opening ≤20 syllables of the body description
      body_line_idx  -- 0-based index in `lines` (None if not determinable)

    Returns (None, None) if Gemini cannot locate the section.
    """
    import time as _t
    from google.genai import types

    end_line = min(end_line, len(lines))
    passage_lines = lines[start_line:end_line]
    if not passage_lines:
        return None, None

    numbered = "".join(
        f"[L{start_line + i + 1}] {ln}"
        for i, ln in enumerate(passage_lines)
    )

    hier_parts = []
    if parent_dec and parent_title:
        hier_parts.append(f"Parent: {parent_dec}. {parent_title}")
    if prev_siblings:
        hier_parts.append("Preceding siblings (already located):")
        for s in prev_siblings[-4:]:
            hier_parts.append(f"  {s}")
    hier_block = ("\n\nHIERARCHY:\n" + "\n".join(hier_parts)) if hier_parts else ""

    prompt = (
        "You are an expert in Tibetan Buddhist texts and commentaries.\n\n"
        "FULL TABLE OF CONTENTS (for structural reference):\n"
        f"{toc_ref}\n"
        f"{hier_block}\n\n"
        "YOUR TASK:\n"
        f"Locate section  {dec}. {title}\n\n"
        "Find the line in the NUMBERED PASSAGE below where this section BEGINS.\n\n"
        "WHERE A SECTION BEGINS (the convention of the vault's human-edited files):\n"
        "  1. A section WITH sub-sections begins at its own division announcement --\n"
        "     the sentence naming it and counting its parts (…ལ་གཉིས། / དང་པོ་ལ་དྲུག །).\n"
        "  2. Section 1 (the first top-level section) begins at the sentence that\n"
        "     announces the work's top-level division (…ལ་གསུམ། A། B། C།).\n"
        "  3. Any other section begins at its opener: ordinal + title restated\n"
        "     (དང་པོ་ནི།, གཉིས་པ་ … ནི།, གསུམ་པ་ … ལ་N།), EVEN IF the line holds\n"
        "     only that opener and the quoted root verse follows it.\n"
        "  4. NEVER return the place where the title is merely LISTED in the parent's\n"
        "     enumeration (a dkar-chag naming several titles in a row).\n"
        "  5. Use the TOC and hierarchy to know WHICH section you are looking for; if\n"
        f"     the passage holds openers of several siblings, return only section {dec}'s.\n\n"
        "NUMBERED PASSAGE:\n"
        f"{numbered}\n\n"
        "REPLY FORMAT (two lines, nothing else):\n"
        "LINE: <[L…] tag of the body-description opening line, or NONE>\n"
        "TEXT: <verbatim 15-20 Tibetan syllables starting exactly at the section's\n"
        "       beginning (it may be mid-line), copied character for character>"
    )

    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING),
        max_output_tokens=GEMINI_MAX_OUTPUT,
    )
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp   = client.models.generate_content(
                model=model, contents=prompt, config=config)
            _check_finish(resp)
            raw    = (resp.text or "").strip()

            line_num = None
            snippet  = None
            for ln in raw.splitlines():
                ln = ln.strip()
                if ln.upper().startswith("LINE:"):
                    val = ln.split(":", 1)[1].strip()
                    if val.upper() == "NONE":
                        return None, None
                    m = re.search(r"L(\d+)", val, re.IGNORECASE)
                    if m:
                        line_num = int(m.group(1)) - 1   # 0-based
                elif ln.upper().startswith("TEXT:"):
                    snippet = ln.split(":", 1)[1].strip().strip("[]\"'")

            if not snippet:
                return None, None

            snippet = trim_syllables(snippet)

            # Validate line_num is within our window
            if line_num is not None and not (start_line <= line_num < end_line):
                line_num = None

            # If no valid line_num, try to find snippet in passage
            if line_num is None:
                canon_snip = tib_canon(snippet)
                half = max(4, len(canon_snip) // 2)
                prefix = canon_snip[:half]
                for i, pline in enumerate(passage_lines):
                    if prefix and prefix in tib_canon(pline):
                        line_num = start_line + i
                        break

            return snippet, line_num

        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                print(f"      ! Gemini error (attempt {attempt}): {e}; "
                      f"retrying in {wait}s", file=sys.stderr)
                _t.sleep(wait)

    print(f"      ! gemini_locate_body failed after retries: {last_err}",
          file=sys.stderr)
    return None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Rewrite [[context]] in a TOC tree using Gemini as Buddhist text expert.")
    ap.add_argument("toc_file",    help="toc-tree-<id>.md")
    ap.add_argument("source_file", help="Commentary .md")
    ap.add_argument("--model",  default=DEFAULT_MODEL,
                    help=f"Gemini model (default: {DEFAULT_MODEL})")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                    help=f"Source lines per search window (default: {DEFAULT_WINDOW})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print proposed contexts without writing the file")
    args = ap.parse_args()

    toc_path = Path(args.toc_file).expanduser().resolve()
    src_path = Path(args.source_file).expanduser().resolve()
    for p in (toc_path, src_path):
        if not p.exists():
            sys.exit(f"Error: not found: {p}")

    entries = parse_toc(toc_path)
    if not entries:
        sys.exit("No TOC entries found.")

    lines    = src_path.read_text(encoding="utf-8").splitlines(keepends=True)
    toc_ref  = toc_summary(entries)
    client   = get_client()

    print(f"TOC:    {toc_path}  ({len(entries)} entries)")
    print(f"Source: {src_path}  ({len(lines)} lines)")
    print()

    # dec -> {body_line, ctx}  accumulated as we go
    dec_body_line = {}   # 0-based line where body description was found
    dec_ctx       = {}   # resolved snippet
    dec_title     = {e["dec"]: e["title"] for e in entries}
    new_contexts  = {}

    def parent_dec(dec):
        parts = dec.split(".")
        return ".".join(parts[:-1]) if len(parts) > 1 else None

    def ancestors(dec):
        """All ancestor decs from root down."""
        parts = dec.split(".")
        return [".".join(parts[:i]) for i in range(1, len(parts))]

    def search_start_for(dec):
        """
        Best lower bound for the search window:
        - previous sibling's body line + 1   (strongest: section must follow)
        - parent's body line + 1             (fallback)
        - 0                                  (root fallback)
        """
        cur_parts = dec.split(".")
        # look for preceding sibling
        for e in reversed(entries):
            e_parts = e["dec"].split(".")
            if (len(e_parts) == len(cur_parts) and
                    e_parts[:-1] == cur_parts[:-1] and
                    e["dec"] < dec):
                bl = dec_body_line.get(e["dec"])
                if bl is not None:
                    return bl + 1
        # parent
        pdec = parent_dec(dec)
        if pdec:
            bl = dec_body_line.get(pdec)
            if bl is not None:
                return bl + 1
        return 0

    def prev_siblings_info(dec):
        cur_parts = dec.split(".")
        siblings  = []
        for e in entries:
            e_parts = e["dec"].split(".")
            if (len(e_parts) == len(cur_parts) and
                    e_parts[:-1] == cur_parts[:-1] and
                    e["dec"] < dec):
                ctx = dec_ctx.get(e["dec"], "?")
                siblings.append(f"{e['dec']}. {e['title']} [[{ctx}]]")
        return siblings

    for entry in entries:
        dec   = entry["dec"]
        title = entry["title"]
        depth = len(dec.split("."))

        # Hierarchy context
        pdec  = parent_dec(dec)
        ptitle = dec_title.get(pdec, "") if pdec else None
        prev_sibs = prev_siblings_info(dec)

        start = search_start_for(dec)
        snippet   = None
        body_line = None

        # Slide the window forward if not found on first attempt
        for slide in range(MAX_SLIDES):
            w_start = start + slide * SLIDE_STEP
            w_end   = w_start + args.window
            if w_start >= len(lines):
                break

            if slide > 0:
                print(f"  [{dec}] not found in window, sliding +{slide * SLIDE_STEP} lines …",
                      flush=True)

            snippet, body_line = gemini_locate_body(
                client, args.model,
                lines, w_start, w_end,
                dec, title,
                toc_ref,
                parent_dec=pdec, parent_title=ptitle,
                prev_siblings=prev_sibs,
            )
            if snippet:
                break

        if snippet:
            new_contexts[dec] = snippet
            dec_ctx[dec]      = snippet
            if body_line is not None:
                dec_body_line[dec] = body_line
                line_tag = f"line {body_line + 1:4}"
            else:
                line_tag = "line ?"
            slides_tag = f" (slide×{slide})" if slide > 0 else ""
            print(f"  [{dec}] {line_tag}{slides_tag}  ctx: {snippet[:60]}",
                  flush=True)
        else:
            # Keep existing context rather than losing data
            fallback = entry["ctx"] or "?"
            new_contexts[dec] = fallback
            dec_ctx[dec]      = fallback
            print(f"  [{dec}] NOT FOUND -- kept: {fallback[:50]}", flush=True)

    print()

    if args.dry_run:
        print("Dry run -- no file written.")
        return

    commentary_id = re.sub(r"^toc-tree-", "", toc_path.stem)
    vault_root    = find_vault_root(toc_path)
    out_path      = (vault_root / "0-INBOX" / "temp"
                     / f"TOC-{commentary_id}" / toc_path.name)

    bak = rewrite_toc(toc_path, new_contexts, out_path=out_path)
    print(f"Written -> {out_path}")
    print(f"Backup  -> {bak}")


if __name__ == "__main__":
    main()
