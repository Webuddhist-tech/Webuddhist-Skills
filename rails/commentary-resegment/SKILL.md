---
name: commentary-resegment
description: >
  Step 5 of commentary-pipeline: re-draw block boundaries in a segmented Tibetan commentary
  (with its TOC headings in) to produce semantically coherent, citation-sized units: the
  model flags merge/split operations per window, a Python script applies them and verifies
  text integrity, then a QC pass checks and repairs. No character is added, removed, or
  reordered — only blank-line boundaries change. Gemini 3.8 Flash (high) by default, Claude
  (Opus) subagents on request. Use for "re-segment the commentary", "fix the block
  boundaries", "merge and split blocks semantically", "run meaningful segmentation".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/block-resegmentation/SKILL.md
  - Nalanda-texts-rails/4-SYSTEM/Skills/commentary-resegment/SKILL.md
---

# commentary-resegment

**Role:** Expert editor in classical Tibetan Buddhist commentary (འགྲེལ་པ་) structure.

**Task:** Identify which adjacent blocks should be merged into one thought unit and
which single blocks should be split at a topic boundary — then apply those operations
via script, preserving every character of the source.

---

## Pipeline position

```
commentary-segment --units    ← rule-based units (+ --root quotes)
         ↓
commentary-toc-extract (passes 1–5)    ← sa bcad tree + anchors
commentary-toc-ingest                     ← headings inserted into the segmented file
         ↓
commentary-resegment                ← THIS SKILL: meaning-based merge/split
         ↓
commentary-block-ids               ← derived body IDs (optional, after review)
```

**Input:** a Stage-1 segmented file with TOC headings embedded, in `$INBOX/segmented/`
or wherever the TOC step wrote its output.

**Do not run** on a file that has block IDs already. Do not run before TOC headings
are included (the headings give the LLM section context).

---

## What good output looks like — one block per functional unit

This is the layout of the vault's human-edited commentaries (measured in
`$SYSTEM/scripts/seg-toc-benchmark/`), the same one `commentary-segment --units`
produces deterministically. This skill finishes what rules cannot decide — mostly
**merging an explanation that the segmenter cut at a sentence end**.

- **Opener** — a division announcement together with the first-child opener that follows
  it (`… ལ་གསུམ། A། B། C་འོ། །དང་པོ་ནི།`); a sibling opener `གཉིས་པ་ … ནི།` alone.
- **Root quote** — the quoted root stanza, whole. Verse blocks are **protected**: the
  script rejects any operation that touches one, so an opener can never be glued onto a
  stanza and a stanza can never be cut.
- **Explanation** — `ཞེས་པ་སྟེ། …` up to the next opener, quote or heading is one block,
  even at 150–250 syllables, with its questions (`གང་ལ་ན།`), side remarks, variant
  readings and passing mantra citations. **Never split a block only because it is long.**
- **Frame** — the namo line alone, each of the author's verses, `སྨྲས་པ།` alone, the
  colophon one block.
- **Headings are untouched.** Markdown heading lines pass through unchanged and are never
  part of a merge or split operation.

Merged prose is joined the way the source writes it: no space after a `། །` cluster, one
space after a single shad.

---

## Architecture — LLM flags, script applies

```
[Phase 1]  Script chunks the file into overlapping block windows
[Phase 2]  LLM reads each window, outputs a JSON operation list
           {"op": "merge", "blocks": [3, 4]}
           {"op": "split", "block": 7, "after": "<unique substring>"}
[Phase 3]  Script combines windows (overlap zone: a merge is kept only where every
           window that sees both blocks makes it), applies ops
[Phase 4]  Script runs squeeze(input) == squeeze(output); aborts on mismatch
[Phase 5]  QC pass — deterministic checks + optional LLM correction
[Phase 6]  Human reviews ops log + QC report; approves output
```

The LLM **never retypes Tibetan**. It only points at block numbers and verbatim
substrings. All text manipulation is done by the script.

---

## Scripts

Two scripts bundled in `scripts/`:

| Script | Purpose |
|---|---|
| `resegment.py` | Main resegmentation: chunk → LLM flag → apply → integrity check |
| `qc_check.py` | QC pass: deterministic checks → optional LLM correction → integrity check |

---

### `resegment.py`

```
python3 $SKILL/scripts/resegment.py \
    "$INBOX/segmented/<file>.md" \
    --commentary-id <id>
```

**Setup:** `pip install google-genai`; the key is read from `GEMINI_API_KEY` in the environment
or the vault-root `.env` (never printed). The model step can also run on Claude — see
**Model** below.

**Key flags:**

| Flag | Default | Purpose |
|---|---|---|
| `--commentary-id` | inferred from filename | Short ID for output filenames and staging folder |
| `--window-size` | 40 | Blocks per LLM call |
| `--overlap` | 5 | Overlap blocks between adjacent windows |
| `--model` | `gemini-3.8-flash` (high thinking) | Gemini model to use |
| `--fallback-model` | none | Fallback if primary is overloaded (`gemini-2.0-flash` was retired) |
| `--force` | off | Reprocess all windows even if staging files exist |
| `--apply-only` | off | Skip LLM calls; apply already-staged operations |
| `--dry-run` | off | Run integrity check only; write nothing |

**Outputs:**

| File | Purpose |
|---|---|
| `$INBOX/resegmented/<id>.reseg.md` | Resegmented commentary |
| `$INBOX/resegmented/<id>.ops.md` | Human-readable operations log |
| `$WORK/RESEG-<id>/windows/window-NNNN.json` | Per-window staging (resumable) |

---

### `qc_check.py`

Mirrors the QC pattern in `toc_tree_extractor`: detect → repair → re-check → report.
By default all four steps run automatically. Run after `resegment.py`.

```
python3 $SKILL/scripts/qc_check.py \
    "$INBOX/resegmented/<id>.reseg.md"
```

Use `--no-fix` to run detection only (no LLM repair):

```
python3 $SKILL/scripts/qc_check.py \
    "$INBOX/resegmented/<id>.reseg.md" --no-fix
```

**Steps:**

1. **Deterministic check** — scans every block for known violations; no API call.
2. **LLM repair** — sends the issues list + flagged blocks with context to the model (Gemini by default),
   which outputs correction operations. Script applies them; integrity is verified.
3. **Re-check** — runs the deterministic checks again on the repaired output.
4. **Report** — written with `flags_before`, corrections applied, `flags_after`.

**What the deterministic checker flags:**

| Flag                    | Condition                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| `CONNECTOR_ENDING`      | Block ends with `དང་།` / `ཞིང་།` / `ཅིང་།` / `ནས།` / `ལས།` / `སྟེ།` / `ཏེ།` — sentence incomplete |
| `OBJECTION_REPLY_FUSED` | Block contains both `ཅེ་ན།`/`ཞེ་ན།` and `འོ་ན།` — should be two blocks                            |
| `OVER_LENGTH`           | Block exceeds 250 syllables — may contain a buried node opener (a whole explanation is legitimately long) |
| `SHORT_FRAGMENT`        | Block is under 4 syllables — may be a split artifact                                              |

**Outputs:**

| File | Purpose |
|---|---|
| `$INBOX/resegmented/<id>.qc.md` | QC report with `flags_before` / `flags_after` |
| `.reseg.md` updated in place | (only when real issues found and `--no-fix` not set) |

**Key flags:**

| Flag | Default | Purpose |
|---|---|---|
| `--no-fix` | off | Detection only; skip LLM repair |
| `--over-length` | 250 | Syllable threshold for OVER_LENGTH flag |
| `--dry-run` | off | Compute corrections but write nothing |
| `--model` | `gemini-3.8-flash` (high thinking) | Gemini model |
| `--fallback-model` | none | Fallback model |

---

## How the LLM decides

The full instruction text is `SYSTEM_PROMPT` in `scripts/resegment.py`; in short:

### MERGE

**M1 — Continued explanation** (the most common fix). A block that goes on explaining the
same quote/topic as the block before it — no new opener, quote or verse — belongs to it.
A sentence end alone is not a reason to keep a cut.
**M2 — Incomplete sentence.** A block ending in a connector (`དང་།` / `ཞིང་།` / `ཅིང་།` /
`ནས།` / `སྟེ།` / `ཏེ།`) that the next block completes.
**M3 — Opener chain.** An enumeration block followed by `དང་པོ་ནི།` / `དང་པོ་ལ་ N།`.
**M4 — Colophon.** The parts of the closing colophon and its final wishes.

### SPLIT

**S1** — a new node opener (ordinal + title + `ནི།` / `ལ་ N།`) buried mid-block.
**S2** — the treatment of a new verse/topic starting mid-block (e.g. `ཡང་ཕྱག་གང་ལ་འཚལ་ན`).
**S3** — an opener `… ནི།` fused to the explanation of the previous quote.

Blocks tagged `[HEADING]` or `[VERSE]` in the window are never part of an operation; the
script enforces this whatever the model returns.

---

## Procedure

**Step 1 — Resegment**

Confirm the input file has TOC headings embedded and no block IDs yet. Then run:

```
python3 $SKILL/scripts/resegment.py \
    "$INBOX/segmented/<file>.md" \
    --commentary-id <id>
```

The script processes all windows (resumable — re-run after interruption without
`--force` to pick up where it stopped). On completion it prints: block count
before → after, operations applied, any conflicts in the overlap zone, and the
integrity check result.

- If integrity check fails (`✗`): the output file is **not written**. Read the
  error, fix the staging JSON if needed, re-run with `--apply-only`.
- **Overlap disagreements** (`Blocks a | b: windows [4, 5], joined by [4]`): two windows
  disagree whether two blocks belong together; the boundary is **kept**. A window whose
  merge runs into its own last block cannot see where that unit ends — before v2.1 its
  merge won silently (the log said "not applied") and swallowed the next window's
  boundary (tāranātha: a chapter boundary lost in all six runs; boundary F1 +0.02–0.03
  with the fix). To merge anyway, edit the relevant `window-NNNN.json` and re-run with
  `--apply-only`.
- **Split conflicts** (two windows split one block differently) are not applied and are
  listed for manual review: edit the staging file, then re-run with `--apply-only`.

**Step 2 — QC**

```
python3 $SKILL/scripts/qc_check.py \
    "$INBOX/resegmented/<id>.reseg.md"
```

Runs all four steps automatically: detect → LLM repair → re-check → write report.
The `.reseg.md` file is updated in place if real issues are found.
Review `$INBOX/resegmented/<id>.qc.md` for the `flags_before` / `flags_after` summary.

To run detection only without repair: add `--no-fix`.

**Step 3 — Human review**

Review `$INBOX/resegmented/<id>.ops.md` (main operations) and
`$INBOX/resegmented/<id>.qc.md` (QC corrections). On approval the file is ready.

---

## Rules

- **No character changes.** The script enforces `squeeze(input) == squeeze(output)`.
  If this assertion fails, the output is not written.
- **Headings are never touched.** A block starting with `#` is always KEEP.
- **Output stays in `$INBOX/`** until a domain specialist approves.
- **Verse blocks are protected** like headings (rejected in validation).
- **When in doubt, keep the cut.** Merge only where the next block plainly continues the
  same unit.

## Model — Gemini 3.8 Flash by default, Claude agents on request

**Default: Gemini 3.8 Flash, high thinking** — both scripts call it directly
(`thinking_level="high"`, temperature at the API default, 65,536 output tokens because
thinking counts against them; a reply cut off at that limit is retried, never used).
Measured on the 8-file benchmark: Gemini 3.8 Flash high and Opus are equal on this step.

**On request — Claude agents (Opus, high effort).** When the user asks for Claude / Opus,
run the *same prompts* with isolated subagents, using the two adapters bundled in
`scripts/` (the scripts' windowing, staging, reconciliation and integrity checks stay the
same — only the model call is swapped). Run the session at high effort.

1. Windows: `python $SKILL/scripts/claude_reseg_shim.py dump "<input.md>" --commentary-id <id>`
   → one `$WORK/RESEG-<id>/claude/window-NNNN.prompt.md` per window.
2. One isolated subagent **per window** (`model: opus`), in parallel — the windows must not
   see each other, as with separate API calls:
   > Read `<…/window-NNNN.prompt.md>` in full. It contains a system prompt and a user prompt;
   > act exactly as the model receiving them and produce the JSON array it asks for. Write
   > ONLY that array to `<…/window-NNNN.response.json>`. Read no other file.
3. `python …/claude_reseg_shim.py stage "<input.md>" --commentary-id <id>`, then
   `python …/resegment.py "<input.md>" --commentary-id <id> --apply-only`.
4. QC repair: `python …/claude_generate_shim.py --dir $WORK/RESEG-<id>/qc-calls -- $SKILL/scripts/qc_check.py "$INBOX/resegmented/<id>.reseg.md"`.
   If it stops with exit code 3, it has written `call-NNN.prompt.md`: answer it with one
   isolated Opus subagent into `call-NNN.response.txt` (raw reply, no fence), then re-run
   the same command; repeat until it finishes.
