#!/usr/bin/env python3
"""
resegment.py — meaningful block re-segmentation for Tibetan commentaries.

Takes a Stage-1 rule-segmented commentary (with TOC headings embedded by a
separate TOC-inclusion step) and uses an LLM to flag merge/split operations
that produce semantically coherent, citation-sized blocks. A deterministic
script applies the operations and verifies text integrity.

Pipeline:
    commentary-segment (Stage 1)
         ↓
    [TOC inclusion — headings embedded]
         ↓
    resegment.py   ← THIS SCRIPT
         ↓
    block-ID stamping

Setup:
    pip install google-genai
    GEMINI_API_KEY is read from the .env file at the vault root (next to 4-SYSTEM/);
    an environment variable of the same name takes precedence.

Usage:
    # basic run (commentary-id inferred from filename):
    python3 4-SYSTEM/Skills/commentary-resegment/scripts/resegment.py \\
        "0-INBOX/segmented/bo-kunpal.md"

    # explicit id:
    python3 4-SYSTEM/Skills/commentary-resegment/scripts/resegment.py \\
        "0-INBOX/segmented/bo-kunpal.md" --commentary-id kunpal

    # resume interrupted run (skips windows already staged):
    python3 ... "0-INBOX/segmented/bo-kunpal.md" --commentary-id kunpal

    # force reprocess all windows:
    python3 ... "0-INBOX/segmented/bo-kunpal.md" --commentary-id kunpal --force

    # apply already-staged ops without new LLM calls:
    python3 ... "0-INBOX/segmented/bo-kunpal.md" --commentary-id kunpal --apply-only

    # integrity check only, write nothing:
    python3 ... "0-INBOX/segmented/bo-kunpal.md" --commentary-id kunpal --dry-run
"""

import argparse
import json
import os
import random
import re
import sys
import time
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

# ── defaults ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL          = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODEL = ""   # gemini-2.0-flash was retired (June 2026); no fallback

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

DEFAULT_WINDOW_SIZE    = 40    # blocks per LLM window
DEFAULT_OVERLAP        = 5     # overlap blocks between adjacent windows
MAX_RETRIES            = 8
RETRY_BACKOFF_BASE     = 8     # seconds; grows exponentially per attempt
MAX_BACKOFF            = 120   # cap on a single wait

TEMP_BASE   = "0-INBOX/temp"
OUTPUT_BASE = "0-INBOX/resegmented"

# ── prompts ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert in classical Tibetan Buddhist commentary (འགྲེལ་པ་) structure.

You are given a numbered list of blocks from a Tibetan verse commentary. A
rule-based segmenter has already cut them; most cuts are right. Your job is to
output the few merge/split operations that bring the blocks to the layout the
human editors of this vault use.

━━━ TARGET LAYOUT — one block per FUNCTIONAL UNIT ━━━

OPENER       A node's division announcement together with the first-child opener
             that follows it is ONE block:
               "<topic> ལ་གསུམ། A། B། C་འོ། །དང་པོ་ནི།"
             A sibling opener "གཉིས་པ་ <title> ནི།" is its own block.
ROOT QUOTE   A quoted root stanza is its own block. These blocks are tagged
             [VERSE]; they are protected — never include them in any operation.
EXPLANATION  The gloss that follows a quote ("ཞེས་པ་སྟེ། …", "ཞེས་པ་ནི། …", or a
             running explanation) is ONE block up to the next opener, quote or
             heading — even when it is long (100–250 syllables) and contains several
             sentence ends, a question and answer ("…ལོ། །གང་ལ་ན། …"), a side remark
             on a variant reading ("…ཞེས་འགྱུར་བཅོས་…"), a cross-reference
             ("འདི་དང་འོག་གི་ས་བཅད་…"), or a mantra cited in passing.
SECOND LEVEL A passage that re-reads the same stanza on another level — opening
             "སྦས་དོན་ནི།", "ངེས་དོན་ནི།", "ངེས་པའི་དོན་དུ།", "ཟབ་དོན་ནི།",
             "དེའི་ནང་གི་དོན་ལ།", "མཐར་ཐུག་གི་དོན་ནི།" or the like after the literal
             gloss — is its OWN block, never merged into the literal gloss before it
             (the editors keep the two readings apart). Within that passage, M1 applies.
FRAME        The namo line alone; each of the author's own verses one block;
             "སྨྲས་པ།" alone; the colophon ("ཅེས་ … སྦྱར་བའོ། །" + closing wishes) one block.

━━━ MERGE — adjacent blocks that are one unit ━━━

M1  CONTINUED EXPLANATION
    A block that goes on explaining the same quote/topic as the block before it —
    no new opener, no new quote, no new verse being treated — belongs to that block.
    This is the most common fix. Do NOT keep a cut just because a sentence ends.
    Exception: a SECOND LEVEL opener (see above) always starts a new block.
M2  INCOMPLETE SENTENCE
    A block ending in a connector (དང་། / ཞིང་། / ཅིང་། / ནས། / སྟེ། / ཏེ།) that
    the next block completes.
M3  OPENER CHAIN
    An enumeration block followed by "དང་པོ་ནི།" / "དང་པོ་ལ་ N།" (and further
    nested first-child enumerations) — merge them into one opener block.
M4  COLOPHON
    The parts of the closing colophon and its final wishes form one block.

━━━ SPLIT — one block that holds two units ━━━

S1  A new node opener (ordinal + title + "ནི།" or "ལ་ N།") buried mid-block:
    split before it.
S2  The treatment of a new verse/topic starts mid-block (e.g. "ཡང་ཕྱག་གང་ལ་འཚལ་ན"
    starting the next homage): split before it.
S3  An introductory opener "… ནི།" fused to the explanation of the PREVIOUS
    quote: split so the opener starts the next unit.

Never split a block only because it is long.

━━━ HEADING / VERSE BLOCKS — always KEEP ━━━

Blocks tagged [HEADING] or [VERSE] are NEVER part of any operation.

━━━ OUTPUT FORMAT ━━━

A JSON array of operations. Blocks not mentioned are kept as-is.

[
  {"op": "merge", "blocks": [N, M]},
  {"op": "merge", "blocks": [N, M, P]},
  {"op": "split", "block": N, "after": "<verbatim unique substring ending at split point>"},
  {"op": "split", "block": N, "after": ["<sub1>", "<sub2>", "<sub3>"]}
]

Rules for the output:
- Block numbers are CONTINUOUS and INCLUDE heading and verse blocks. You may only
  merge blocks with consecutive numbers (N and N+1). Never merge across a heading
  or a verse block, and never propose a merge whose numbers skip over one.
- Each block number appears in AT MOST ONE operation.
- For each "after" substring: copy a verbatim slice from the block that ends exactly
  at the split point and is UNIQUE within that block (10–20 characters is usually enough).
- If nothing needs to change in this window, output: []
- Output ONLY the JSON array. No explanation, no commentary, no code fences.
"""

USER_PROMPT_TEMPLATE = """\
Review the following blocks from a Tibetan commentary and output the merge/split \
operations needed to make each block a single citable thought unit. Block numbers \
are global (file-level).

--- BEGIN BLOCKS ---
{blocks_text}
--- END BLOCKS ---
"""

# ── block parsing ─────────────────────────────────────────────────────────────

FRONTMATTER_RE = re.compile(r'^---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n', re.DOTALL)


def parse_file(path: Path):
    """
    Return (frontmatter: str, blocks: list[str]).
    Frontmatter is the YAML block; blocks are split on double newlines.
    """
    text = path.read_text(encoding="utf-8")
    frontmatter = ""
    body = text
    m = FRONTMATTER_RE.match(text)
    if m:
        frontmatter = m.group(0)
        body = text[m.end():]
    raw = re.split(r'\n{2,}', body)
    blocks = [b.strip() for b in raw if b.strip()]
    return frontmatter, blocks


def is_heading(block: str) -> bool:
    return block.lstrip().startswith('#')


def squeeze(text: str) -> str:
    """Strip all whitespace — used for integrity comparison."""
    return re.sub(r'\s+', '', text)


_SHAD_END_RE = re.compile(r'[\u0f0d\u0f0e]\s*$')


def is_verse(block: str) -> bool:
    """A stanza block: 2+ lines, every line ending in a shad. Protected — no
    operation may merge it with prose or split it (pādas stay together and a
    quoted root verse stays its own block)."""
    lines = [l for l in block.strip().split('\n') if l.strip()]
    return (not block.lstrip().startswith('#') and len(lines) >= 2
            and all(_SHAD_END_RE.search(l) for l in lines))


def join_prose(texts):
    """Join merged prose blocks the way the source writes them: no space after
    a "། །" / "༎" cluster (the cluster carries its own space), one space after
    a single shad or anything else."""
    out = texts[0].strip()
    for t in texts[1:]:
        t = t.strip()
        if re.search(r'[\u0f0d\u0f0e]\s+[\u0f0d\u0f0e]\s*$|\u0f0e\s*$', out):
            out += t
        else:
            out += ' ' + t
    return out


# ── windowing ─────────────────────────────────────────────────────────────────

def make_windows(blocks, window_size, overlap):
    """
    Return a list of window dicts:
      {idx, start (0-based inclusive), end (0-based exclusive), blocks}
    Block numbers shown to the LLM are 1-based (start+1 .. end).
    """
    total = len(blocks)
    windows = []
    start = 0
    idx = 0
    while start < total:
        end = min(start + window_size, total)
        windows.append({
            "idx":    idx,
            "start":  start,
            "end":    end,
            "blocks": blocks[start:end],
        })
        idx += 1
        if end >= total:
            break
        start = end - overlap
    return windows


def format_window(window):
    """Format window blocks for the LLM, with 1-based global block numbers."""
    parts = []
    for i, block in enumerate(window["blocks"]):
        gn = window["start"] + i + 1  # 1-based global number
        tag = " [HEADING]" if is_heading(block) else (" [VERSE]" if is_verse(block) else "")
        parts.append(f"[Block {gn}{tag}]\n{block}")
    return "\n\n".join(parts)


# ── Gemini API ────────────────────────────────────────────────────────────────

def get_client():
    try:
        from google import genai  # noqa: PLC0415
    except ImportError:
        sys.exit(
            "Error: google-genai is not installed.\n"
            "  Run: pip install google-genai"
        )
    api_key = _gemini_api_key()
    if not api_key:
        sys.exit(
            "Error: no API key found.\n"
            "  Put GEMINI_API_KEY=your-key in the .env file at the vault root (next to 4-SYSTEM/),\n"
            "  or set GEMINI_API_KEY in the environment."
        )
    return genai.Client(api_key=api_key)


def _is_overloaded(err) -> bool:
    s = str(err).upper()
    return any(tok in s for tok in (
        "503", "UNAVAILABLE", "OVERLOADED", "HIGH DEMAND",
        "429", "RESOURCE_EXHAUSTED",
    ))


def _generate(client, model, user_prompt, fallback_model="", label="window"):
    try:
        from google.genai import types  # noqa: PLC0415
    except ImportError:
        sys.exit("Error: google-genai not installed.")

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        thinking_config=types.ThinkingConfig(thinking_level=GEMINI_THINKING),
        max_output_tokens=GEMINI_MAX_OUTPUT,
    )
    models_to_try = [model]
    if fallback_model and fallback_model != model:
        models_to_try.append(fallback_model)

    last_err = None
    for mi, mdl in enumerate(models_to_try):
        if mi > 0:
            print(f"    -> '{model}' still overloaded; falling back to '{mdl}'",
                  file=sys.stderr)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = client.models.generate_content(
                    model=mdl, contents=user_prompt, config=config,
                )
                _check_finish(resp)
                return (resp.text or "").strip()
            except Exception as e:  # noqa: BLE001
                last_err = e
                if attempt < MAX_RETRIES:
                    base = min(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)), MAX_BACKOFF)
                    wait = base + random.uniform(0, base * 0.25)
                    kind = "overloaded" if _is_overloaded(e) else "error"
                    print(f"    ! {label} attempt {attempt}/{MAX_RETRIES} {kind}: {e}; "
                          f"retrying in {wait:.0f}s...", file=sys.stderr)
                    time.sleep(wait)
        if not _is_overloaded(last_err):
            break
    raise RuntimeError(f"Gemini call failed after retries: {last_err}")


def call_llm_for_window(client, model, window, fallback_model=""):
    """Call the LLM for one window. Returns list of operation dicts."""
    blocks_text = format_window(window)
    user_prompt = USER_PROMPT_TEMPLATE.format(blocks_text=blocks_text)
    label = f"window-{window['idx'] + 1}"
    raw = _generate(client, model, user_prompt, fallback_model=fallback_model,
                    label=label)
    # strip code fences if the model wrapped the JSON
    raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
    raw = re.sub(r'\s*```$', '', raw.strip())
    try:
        ops = json.loads(raw)
        if not isinstance(ops, list):
            print(f"  ! {label}: LLM returned non-list JSON — treating as []",
                  file=sys.stderr)
            return []
        return ops
    except json.JSONDecodeError as e:
        print(f"  ! {label}: JSON parse error ({e}) — treating as []. Raw:\n{raw[:200]}",
              file=sys.stderr)
        return []


# ── staging ───────────────────────────────────────────────────────────────────

def staging_path(staging_dir: Path, window_idx: int) -> Path:
    return staging_dir / f"window-{window_idx:04d}.json"


def save_window_result(staging_dir: Path, window: dict, ops: list):
    staging_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "window_idx":  window["idx"],
        "start_block": window["start"] + 1,   # 1-based
        "end_block":   window["end"],           # 1-based inclusive
        "operations":  ops,
    }
    staging_path(staging_dir, window["idx"]).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_window_result(staging_dir: Path, window_idx: int):
    p = staging_path(staging_dir, window_idx)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# ── combine operations ────────────────────────────────────────────────────────

def _op_key(op):
    """Hashable identity for an operation."""
    if op["op"] == "merge":
        return ("merge", tuple(sorted(op["blocks"])))
    else:
        after = op.get("after", "")
        after_key = tuple(after) if isinstance(after, list) else after
        return ("split", op["block"], after_key)


def combine_operations(window_results, blocks):
    """
    Merge per-window operation lists into one deduplicated list.

    Merges are decided per join — "block b continues into block b+1". A join is
    applied only if every window that sees both blocks makes it; a window that
    leaves the two apart counts as a vote for the boundary. So two windows that
    see different slices of one unit still combine (one reports [34..37], the
    next, starting at 36, reports [36, 37]), but when they disagree the boundary
    stays: a window whose merge runs into its last block cannot see where that
    unit ends, and before this rule its merge won silently, swallowing the next
    window's boundary.

    Splits: if every window that proposes a split for a block proposes the same
    one → include it once; otherwise → conflict, excluded from ops_to_apply.

    Returns (ops_to_apply: list, conflicts: list). A conflict is either
    {"block", "operations", "windows"} (split, not applied) or
    {"join", "windows", "joined_by"} (merge join, boundary kept).
    """
    ranges = {wr["window_idx"]: (wr.get("start_block"), wr.get("end_block")) for wr in window_results}
    ops_to_apply = []
    conflicts = []

    # ── merges, per join (b, b+1) ──
    joins: dict = {}        # b -> set of window_idx that join b with b+1
    for wr in window_results:
        w_idx = wr["window_idx"]
        for op in wr["operations"]:
            if op["op"] != "merge":
                continue
            bns = op.get("blocks", [])
            if len(bns) < 2 or sorted(bns) != list(range(min(bns), max(bns) + 1)):
                ops_to_apply.append(op)        # malformed: let validation report it
                continue
            for b in sorted(bns)[:-1]:
                joins.setdefault(b, set()).add(w_idx)

    def sees(w, b):
        s, e = ranges.get(w, (None, None))
        return s is not None and s <= b and b + 1 <= e

    kept = set()
    for b, yes in joins.items():
        voters = {w for w in ranges if sees(w, b)} | yes
        if yes == voters:
            kept.add(b)
        else:
            conflicts.append({"join": (b, b + 1), "windows": sorted(voters),
                              "joined_by": sorted(yes)})
    for b in sorted(kept):
        if b - 1 in kept:
            continue
        run = [b]
        while run[-1] in kept:
            run.append(run[-1] + 1)
        ops_to_apply.append({"op": "merge", "blocks": run})

    # ── splits, per block ──
    block_claims: dict = {}
    for wr in window_results:
        for op in wr["operations"]:
            if op["op"] == "split":
                block_claims.setdefault(op["block"], []).append((wr["window_idx"], op))

    seen_keys: set = set()
    for bn, entries in block_claims.items():
        keys = [_op_key(e[1]) for e in entries]
        unique_keys = list(dict.fromkeys(keys))
        if len(unique_keys) == 1:
            key = unique_keys[0]
            if key not in seen_keys:
                seen_keys.add(key)
                ops_to_apply.append(entries[0][1])
        else:
            conflicts.append({
                "block":      bn,
                "operations": [e[1] for e in entries],
                "windows":    [e[0] for e in entries],
            })

    def first_block(op):
        return min(op["blocks"]) if op["op"] == "merge" and op.get("blocks") else op.get("block", 0)
    ops_to_apply.sort(key=first_block)
    return ops_to_apply, conflicts


# ── validate operations ───────────────────────────────────────────────────────

def validate_operations(ops, blocks):
    """
    Validate:
    - Merge blocks are consecutive and in ascending order.
    - Split has a non-empty 'after' substring.
    - No block appears in more than one operation.
    - No operation touches a heading block.

    Returns (valid_ops: list, errors: list[str])
    """
    total = len(blocks)
    claimed: dict = {}   # block_n -> op
    errors = []
    valid_ops = []

    for op in ops:
        if op["op"] == "merge":
            bns = op.get("blocks", [])
            if len(bns) < 2:
                errors.append(f"merge {bns}: need at least 2 blocks")
                continue
            # ascending + consecutive check
            sorted_bns = sorted(bns)
            if sorted_bns != bns:
                errors.append(f"merge {bns}: not in ascending order — auto-sorted")
                bns = sorted_bns
                op = {**op, "blocks": bns}
            ok = True
            for i in range(len(bns) - 1):
                if bns[i + 1] != bns[i] + 1:
                    errors.append(f"merge {bns}: blocks are not consecutive")
                    ok = False
                    break
            if not ok:
                continue
            # heading check
            heading_hit = [b for b in bns if 1 <= b <= total and is_heading(blocks[b - 1])]
            if heading_hit:
                errors.append(f"merge {bns}: includes heading block(s) {heading_hit} — skipped")
                continue
            verse_hit = [b for b in bns if 1 <= b <= total and is_verse(blocks[b - 1])]
            if verse_hit:
                errors.append(f"merge {bns}: includes protected verse block(s) {verse_hit} — skipped")
                continue
            # claim check
            conflict = [b for b in bns if b in claimed]
            if conflict:
                errors.append(f"merge {bns}: block(s) {conflict} already claimed — skipped")
                continue
            for b in bns:
                claimed[b] = op
            valid_ops.append(op)

        elif op["op"] == "split":
            bn = op.get("block")
            after = op.get("after", "")
            if not bn:
                errors.append(f"split: missing 'block' field — skipped")
                continue
            afters = after if isinstance(after, list) else [after]
            if not afters or any(not a for a in afters):
                errors.append(f"split block {bn}: missing/empty 'after' substring — skipped")
                continue
            if 1 <= bn <= total and is_heading(blocks[bn - 1]):
                errors.append(f"split block {bn}: is a heading — skipped")
                continue
            if 1 <= bn <= total and is_verse(blocks[bn - 1]):
                errors.append(f"split block {bn}: is a protected verse block — skipped")
                continue
            if bn in claimed:
                errors.append(f"split block {bn}: already claimed by another op — skipped")
                continue
            claimed[bn] = op
            valid_ops.append(op)

        else:
            errors.append(f"unknown op type: {op.get('op')} — skipped")

    return valid_ops, errors


# ── apply operations ──────────────────────────────────────────────────────────

def apply_operations(blocks, ops):
    """
    Apply validated merge and split operations to the block list.
    Returns a new block list. Original list is not modified.

    blocks: 0-based list of block strings
    ops:    operations with 1-based block numbers
    """
    # Build lookup: 1-based block_n -> op
    block_to_op: dict = {}
    for op in ops:
        if op["op"] == "merge":
            for bn in op["blocks"]:
                block_to_op[bn] = op
        elif op["op"] == "split":
            block_to_op[op["block"]] = op

    new_blocks = []
    i = 0  # 0-based index into blocks
    while i < len(blocks):
        bn = i + 1  # 1-based

        if bn not in block_to_op:
            new_blocks.append(blocks[i])
            i += 1
            continue

        op = block_to_op[bn]

        if op["op"] == "merge":
            if op["blocks"][0] == bn:
                # Start of merge group — consume all blocks in the group
                texts = [blocks[b - 1] for b in op["blocks"]]
                merged = join_prose(texts)
                new_blocks.append(merged)
                i += len(op["blocks"])
            else:
                # Middle/tail of merge group — already consumed; skip
                i += 1

        elif op["op"] == "split":
            block_text = blocks[i]
            after_val  = op["after"]
            cut_strs   = after_val if isinstance(after_val, list) else [after_val]
            cut_positions = []
            ok = True
            for after_str in cut_strs:
                occ = block_text.count(after_str)
                if occ == 0:
                    print(f"  ! split block {bn}: substring not found: {after_str!r}; "
                          f"keeping block whole", file=sys.stderr)
                    ok = False
                    break
                if occ > 1:
                    print(f"  ! split block {bn}: substring not unique "
                          f"({occ} occurrences): {after_str!r}; "
                          f"keeping block whole", file=sys.stderr)
                    ok = False
                    break
                cut_positions.append(block_text.find(after_str) + len(after_str))
            if not ok:
                new_blocks.append(block_text)
            else:
                parts = []
                prev = 0
                for pos in sorted(set(cut_positions)):
                    seg = block_text[prev:pos].strip()
                    if seg:
                        parts.append(seg)
                    prev = pos
                tail = block_text[prev:].strip()
                if tail:
                    parts.append(tail)
                new_blocks.extend(parts if parts else [block_text])
            i += 1

    return new_blocks


# ── integrity check ───────────────────────────────────────────────────────────

def check_integrity(input_path: Path, frontmatter: str, new_blocks: list):
    """
    Verify squeeze(original file) == squeeze(reconstructed output).
    Returns (ok: bool, detail: str)
    """
    original_text = input_path.read_text(encoding="utf-8")
    result_text   = frontmatter + "\n\n".join(new_blocks)

    orig_sq   = squeeze(original_text)
    result_sq = squeeze(result_text)

    if orig_sq == result_sq:
        return True, "OK"

    # find first difference for a helpful error message
    for i, (a, b) in enumerate(zip(orig_sq, result_sq)):
        if a != b:
            ctx_o = orig_sq[max(0, i - 30): i + 30]
            ctx_r = result_sq[max(0, i - 30): i + 30]
            return False, (
                f"First difference at squeezed char {i}:\n"
                f"  original: ...{ctx_o!r}...\n"
                f"  result:   ...{ctx_r!r}..."
            )

    return False, (
        f"Length mismatch: original {len(orig_sq)} chars, result {len(result_sq)} chars"
    )


# ── output writers ────────────────────────────────────────────────────────────

def write_output(output_path: Path, frontmatter: str, new_blocks: list):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = frontmatter + "\n\n".join(new_blocks) + "\n"
    output_path.write_text(text, encoding="utf-8")


def write_ops_log(log_path: Path, ops_applied, errors, conflicts,
                  orig_blocks, new_blocks, commentary_id):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def preview(text, n=80):
        t = text.replace("\n", " ")
        return t[:n] + ("…" if len(t) > n else "")

    lines = [
        f"# Block Resegmentation Log — {commentary_id}",
        "",
        f"Original blocks : {len(orig_blocks)}",
        f"Result blocks   : {len(new_blocks)}",
        f"Ops applied     : {len(ops_applied)}",
        f"Errors skipped  : {len(errors)}",
        f"Conflicts       : {len(conflicts)}",
        "",
    ]

    if ops_applied:
        lines += ["## Applied Operations", ""]
        for op in ops_applied:
            if op["op"] == "merge":
                bns = op["blocks"]
                lines.append(f"**MERGE** blocks {bns}")
                for bn in bns:
                    lines.append(f"  Block {bn}: {preview(orig_blocks[bn - 1])}")
                lines.append("")
            elif op["op"] == "split":
                bn = op["block"]
                af = op['after']
                af_disp = af if isinstance(af, str) else " | ".join(af)
                lines.append(f"**SPLIT** block {bn}  after: `{af_disp}`")
                lines.append(f"  Block {bn}: {preview(orig_blocks[bn - 1])}")
                lines.append("")

    if errors:
        lines += ["## Skipped (Validation Errors)", ""]
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    split_conf = [c for c in conflicts if "block" in c]
    join_conf = [c for c in conflicts if "join" in c]
    if join_conf:
        lines += ["## Overlap Disagreements — Boundary Kept", ""]
        lines += [
            "Overlapping windows disagreed whether these blocks belong together; the",
            "boundary was kept. To merge anyway, edit the relevant `window-NNNN.json`",
            "staging file and re-run with `--apply-only`.",
            "",
        ]
        for c in join_conf:
            a, b = c["join"]
            lines.append(f"Blocks {a} | {b} — windows {c['windows']}, joined by {c['joined_by']}:")
            lines.append(f"  Block {a}: {preview(orig_blocks[a - 1])}")
            lines.append(f"  Block {b}: {preview(orig_blocks[b - 1])}")
            lines.append("")
    if split_conf:
        lines += ["## Conflicts — Manual Review Required", ""]
        lines += [
            "These blocks appeared in two overlapping windows with different splits.",
            "Edit the relevant `window-NNNN.json` staging file and re-run with `--apply-only`.",
            "",
        ]
        for c in split_conf:
            lines.append(f"Block {c['block']} — windows {c['windows']}:")
            for cop in c["operations"]:
                lines.append(f"  {cop}")
            lines.append("")

    log_path.write_text("\n".join(lines), encoding="utf-8")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Meaningful block re-segmentation for Tibetan commentaries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_file",
                        help="Stage-1 segmented commentary with TOC headings embedded")
    parser.add_argument("--commentary-id", default="",
                        help="Short ID for output filenames (inferred from filename if omitted)")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE,
                        help=f"Blocks per LLM window (default: {DEFAULT_WINDOW_SIZE})")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP,
                        help=f"Overlap blocks between adjacent windows (default: {DEFAULT_OVERLAP})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--fallback-model", default=DEFAULT_FALLBACK_MODEL,
                        help=f"Fallback model if primary is overloaded (default: {DEFAULT_FALLBACK_MODEL})")
    parser.add_argument("--force", action="store_true",
                        help="Reprocess all windows even if staging files exist")
    parser.add_argument("--apply-only", action="store_true",
                        help="Skip LLM calls; apply already-staged operations")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run integrity check only; write no output files")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        sys.exit(f"Error: input file not found: {input_path}")

    # resolve commentary id
    cid = args.commentary_id or input_path.stem

    # resolve vault root (walk up looking for 4-SYSTEM/)
    vault_root = input_path.resolve().parent
    for _ in range(8):
        if (vault_root / "4-SYSTEM").exists():
            break
        vault_root = vault_root.parent
    else:
        vault_root = Path(".").resolve()

    staging_dir  = vault_root / TEMP_BASE    / f"RESEG-{cid}" / "windows"
    output_path  = vault_root / OUTPUT_BASE  / f"{cid}.reseg.md"
    log_path     = vault_root / OUTPUT_BASE  / f"{cid}.ops.md"

    print(f"Input:      {input_path}")
    print(f"ID:         {cid}")
    print(f"Vault root: {vault_root}")
    print(f"Staging:    {staging_dir}")
    print(f"Output:     {output_path}")
    print()

    # ── parse ──
    frontmatter, blocks = parse_file(input_path)
    total = len(blocks)
    heading_count = sum(1 for b in blocks if is_heading(b))
    print(f"Blocks: {total}  (headings: {heading_count}, content: {total - heading_count})")

    windows = make_windows(blocks, args.window_size, args.overlap)
    print(f"Windows: {len(windows)}  (size={args.window_size}, overlap={args.overlap})")
    print()

    # ── LLM phase ──
    if not args.apply_only:
        client = get_client()
        for win in windows:
            label = (f"Window {win['idx'] + 1}/{len(windows)} "
                     f"(blocks {win['start'] + 1}–{win['end']})")
            already = load_window_result(staging_dir, win["idx"])
            if already and not args.force:
                n_ops = len(already.get("operations", []))
                print(f"  {label}: already staged ({n_ops} op(s)) — skipping")
                continue
            print(f"  {label}: calling LLM...")
            ops = call_llm_for_window(client, args.model, win, args.fallback_model)
            save_window_result(staging_dir, win, ops)
            print(f"    → {len(ops)} operation(s) flagged")
    else:
        print("--apply-only: skipping LLM calls, loading staged results.")

    # ── load staged results ──
    window_results = []
    missing = []
    for win in windows:
        result = load_window_result(staging_dir, win["idx"])
        if result is None:
            missing.append(win["idx"] + 1)
            window_results.append({"window_idx": win["idx"], "operations": []})
        else:
            window_results.append(result)
    if missing:
        print(f"\nWarning: missing staging files for window(s): {missing}")
        print("Re-run without --apply-only to process missing windows.\n")

    # ── combine ──
    ops_raw, conflicts = combine_operations(window_results, blocks)

    # ── validate ──
    ops_valid, validation_errors = validate_operations(ops_raw, blocks)

    # ── report ──
    print(f"\nOperations to apply: {len(ops_valid)}")
    for op in ops_valid:
        if op["op"] == "merge":
            print(f"  MERGE {op['blocks']}")
        else:
            af = op['after']
            af_disp = af if isinstance(af, str) else " | ".join(af)
            print(f"  SPLIT block {op['block']} after: {af_disp[:50]!r}")

    if validation_errors:
        print(f"\nValidation errors ({len(validation_errors)}) — skipped:")
        for e in validation_errors:
            print(f"  - {e}")

    split_conf = [c for c in conflicts if "block" in c]
    join_conf = [c for c in conflicts if "join" in c]
    if join_conf:
        print(f"\nOverlap disagreements ({len(join_conf)}) — boundary kept:")
        for c in join_conf:
            print(f"  - Blocks {c['join'][0]} | {c['join'][1]}: windows {c['windows']}, "
                  f"joined by {c['joined_by']}")
    if split_conf:
        print(f"\nSplit conflicts in overlap zone ({len(split_conf)}) — not applied:")
        for c in split_conf:
            print(f"  - Block {c['block']}: windows {c['windows']}")

    # ── apply ──
    new_blocks = apply_operations(blocks, ops_valid)
    print(f"\nBlocks: {total} → {len(new_blocks)}")

    # ── integrity check ──
    ok, detail = check_integrity(input_path, frontmatter, new_blocks)
    if not ok:
        print(f"\n✗ INTEGRITY CHECK FAILED")
        print(f"  {detail}")
        print("\nOutput NOT written. Investigate the error above.")
        sys.exit(1)
    print("✓ Integrity check passed")

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return

    # ── write output ──
    write_output(output_path, frontmatter, new_blocks)
    write_ops_log(log_path, ops_valid, validation_errors, conflicts,
                  blocks, new_blocks, cid)

    print(f"\nOutput:  {output_path}")
    print(f"Ops log: {log_path}")

    if split_conf:
        print(f"\n⚑ {len(split_conf)} split conflict(s) require manual review — see ops log.")
        print("  Edit the relevant staging file(s) and re-run with --apply-only.")
    if join_conf:
        print(f"\n{len(join_conf)} overlap disagreement(s) resolved by keeping the boundary — see ops log.")


if __name__ == "__main__":
    main()
