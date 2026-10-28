---
name: commentary-toc-extract
description: >
  Step 3 of commentary-pipeline: build the full nested, decimal-numbered ས་བཅད (sa bcad)
  TOC TREE of a Tibetan Buddhist commentary — candidates, verbatim enumerations, nested
  tree, deterministic QC + repair, anchors — each pass an ISOLATED subagent with only its
  own prompt, plus the front/back-matter frame nodes. Four modes, chosen per commentary:
  sabcad (full sa bcad), verses (headings per root verse), top (large parts only), labels
  (sections opened by name, no ordinals). Use for "build the sa bcad tree", "extract the TOC
  tree", "make the dkar chag", "reconstruct the outline hierarchy" of a commentary. Root
  texts use root-text-toc-extract. For candidates only, run passes 0–2 and stop.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/toc-tree-extraction/SKILL.md
  - Nalanda-texts-rails/4-SYSTEM/Skills/toc-candidate-extraction/SKILL.md
  - Webuddhist-Skills/rails/toc-generate/SKILL.md
---

# commentary-toc-extract — ས་བཅད TOC tree extraction (Claude-native)

This skill reconstructs the **full hierarchical table of contents** (དཀར་ཆག / *dkar chag*)
of a Tibetan commentary as a single nested, decimal-numbered tree. It is the Claude-native
port of `$SKILLS/seg-toc-lib/toc_tree_extractor/extract_toc_tree.py`.

## Why this is an orchestrator, not one big prompt — READ THIS FIRST

The Gemini script's precision comes from **task isolation**: each pass is a *separate API
call* with only that one task's system prompt and only the relevant input. The
candidate-extraction call never sees the tree-building instructions, so it cannot drift into
tree-building; the verbatim-copy call never sees the "interpret and reconcile" instructions,
so it stays literal. Merging the four jobs into one prompt/one context collapses that
isolation and precision drops.

**Therefore you (the orchestrating agent) must NOT perform the four passes yourself in this
context.** Each pass runs as its own **isolated subagent** (via the `Task` tool) whose entire
instruction set is one prompt file (in `commentary-toc-extract/prompts/` or `$SKILLS/seg-toc-lib/prompts/`) plus its specific input.

**Each subagent reads its input by path and writes its own output file.** Do not paste chunk
text into the subagent prompt and do not funnel results back through your context to write
them yourself — that serialises the writes and bloats your context with every chunk's Tibetan.
Instead, hand each subagent the *paths* of its prompt file and its input, and the *path* it
must write. Distinct output filenames mean parallel subagents never collide. You only: chunk,
dispatch subagents, do the deterministic merge, run the checker, and dispatch the repair
subagent. Do not read the pass prompt files into your own context and do the work inline —
that re-merges what this design deliberately separates.

The isolated prompts live in two places — the commentary-only ones in this skill, the passes shared with `root-text-toc-extract` in the library:

| File | Pass |
|---|---|
| `$SKILL/prompts/pass1-candidates.md` | section candidates (one subagent per chunk) |
| `$SKILLS/seg-toc-lib/prompts/pass2-enumerations.md` | verbatim enumeration blocks (one subagent per chunk) |
| `$SKILLS/seg-toc-lib/prompts/pass3-tree.md` | build nested decimal tree (one subagent) |
| `$SKILLS/seg-toc-lib/prompts/pass4-qc-repair.md` | repair flagged issues (one subagent per repair round) |
| `$SKILLS/seg-toc-lib/prompts/pass5-anchors.md` | anchor every node in the text + add frame nodes (one subagent) |
| `$SKILL/prompts/verse-headings.md` | **instead of passes 1–4**, for commentaries declared `headings: verses` / `top` (see below) |
| `$SKILLS/seg-toc-lib/prompts/pass1-candidates-root.md` | pass 1 for mode `labels` — adds Type D, topic headers without an ordinal |

---

## Inputs

| Input | Description |
|---|---|
| `input-file` | Path to the commentary/root-text `.md`, normally under `$COMMENTARIES/` |
| `commentary-id` | Short id for output filenames (inferred from the filename if obvious) |

If the file path is missing, or the `commentary-id` is not obvious from the filename, **stop
and ask** before doing anything else.

## Outputs (all under `$INBOX/`)

| File | Stage |
|---|---|
| `$WORK/TOC-<id>/chunk-index.tsv` | chunk line-range index (no text duplicated) |
| `$WORK/TOC-<id>/candidates/chunk_NNN.md` | per-chunk section candidates (resumable) |
| `$WORK/TOC-<id>/enumerations/chunk_NNN.md` | per-chunk verbatim enumeration blocks |
| `$INBOX/toc-candidates-<id>.md` | merged candidates |
| `$INBOX/toc-enumerations-<id>.md` | merged verbatim enumerations |
| `$INBOX/toc-tree-<id>.md` | the final nested decimal TOC tree |
| `$INBOX/toc-tree-qc-<id>.md` | QC report (issues before / after repair) |
| `$WORK/TOC-<id>/toc-tree-<id>.md` | the anchored tree (`[[context]]` on every node + frame nodes) — the input of `commentary-toc-ingest` |
| `$WORK/TOC-<id>/toc-tree-qc-source-<id>.md` | pass 6: QC against the commentary itself |
| `$SECTIONS_RAW/toc-tree/<registered-id>.md` | **published** finished tree, once both checkers are clean (+ evidence in `toc-candidates/`, `toc-enumerations/`, `toc-qc/`) |

Drafts in `$INBOX/` — scratch, never cited from `$RAILS/`. The tree has **no `^toc` block
IDs**; the decimal numbering alone identifies each entry. (Inserting the tree into a
source/rails file with block IDs is a separate step — use `add-toc`.)

---

## Step 0 — Plan the chunks (deterministic helper, index-only)

Do NOT copy the text into per-chunk files. Just plan the line windows — subagents read their
range straight from the source:

```bash
python $SKILLS/seg-toc-lib/chunk_file.py \
  "<input-file>" --chunk-size 150 --overlap 25 --index-only \
  --output-dir $WORK/TOC-<id>
```

This writes one tiny file, `$WORK/TOC-<id>/chunk-index.tsv`, with a row per chunk:
`chunk_id <TAB> start_line <TAB> end_line` (1-based, inclusive). The 25-line overlap
guarantees every candidate appears in full in at least one window; no source text is
duplicated on disk. Read this small index into your context — it's just numbers — and drive
the passes from it.

**Resumability:** before dispatching a pass-1/pass-2 subagent for a chunk, check whether its
output file already exists and skip if so, so an interrupted run resumes from the first
missing chunk.

---

## Pass 1 — Section candidates · ISOLATED subagent per chunk

For each chunk row whose result file does not already exist, dispatch a **separate `Task`
subagent**. Pass it the prompt path, the source path, and that chunk's line range from the
index — never chunk text:

> Read `$SKILL/prompts/pass1-candidates.md` and follow it
> exactly. Read ONLY lines START–END of the source file `<input-file>` (use
> `sed -n 'START,ENDp' "<input-file>"`, or the Read tool with offset=START / limit=END−START+1).
> Write your output to `$WORK/TOC-<id>/candidates/chunk_NNN.md`, starting with the
> line `<!-- chunk NNN | lines START–END | source: <id> -->`, a blank line, then the
> candidate blocks — or `<!-- no candidates -->` if the prompt yields `NO CANDIDATES`. Do no
> other task; reply only with the path you wrote.

(Substitute the actual `START`, `END`, `NNN`, and `<input-file>` from the index row.)

Independent chunks have no dependencies, so dispatch several pass-1 subagents **in parallel**
— multiple `Task` calls in one message. (The harness runs a bounded number at once and queues
the rest.) Because each writes a distinct `chunk_NNN.md`, parallel writes never collide.

---

## Pass 2 — Verbatim enumerations · ISOLATED subagent per chunk

Run **separately** over the same chunks — a different isolated subagent, because verbatim
copying must not be contaminated by the interpretive instructions of the other passes. Same
read-by-path / write-own-file pattern:

> Read `$SKILLS/seg-toc-lib/prompts/pass2-enumerations.md` and follow it
> exactly. Read ONLY lines START–END of the source file `<input-file>` (use
> `sed -n 'START,ENDp' "<input-file>"`). Write your output to
> `$WORK/TOC-<id>/enumerations/chunk_NNN.md` — the enumeration blocks, or
> `NO ENUMERATIONS`. Isolate ONLY the division-announcement clauses (start at the topic being
> divided, stop at the closing count/list marker); do NOT copy the commentary body that
> explains each part. Copy verbatim; add no interpretation. Reply only with the path you wrote.

These run in parallel too (one message, multiple `Task` calls), each writing a distinct file.

---

## Merge (deterministic — concatenate on disk, don't read into context)

Merging is mechanical text assembly, not inference. Do it with the shell so the chunk text
never enters your context. Concatenate the per-chunk candidate files (keeping their
`<!-- chunk NNN -->` headers) into `$INBOX/toc-candidates-<id>.md`, e.g.:

```bash
cd $WORK/TOC-<id>/candidates && cat chunk_*.md > /tmp/cand-body.md
# then prepend frontmatter and move into place
```

Frontmatter:

```yaml
---
source: <id>
skill: commentary-toc-extract
stage: candidates
date: <YYYY-MM-DD>
total_candidates: <N>
---
```

Likewise concatenate the enumeration files (skipping `NO ENUMERATIONS` ones, in document
order) into `$INBOX/toc-enumerations-<id>.md`. Pass 3 reads both merged files by path.

---

## Pass 3 — Build the nested decimal tree · ISOLATED subagent

Dispatch ONE subagent with only the pass-3 prompt and the paths of the two merged inputs:

> Read `$SKILLS/seg-toc-lib/prompts/pass3-tree.md` and follow it exactly.
> Build the full nested decimal TOC for commentary "<id>" from the candidates in
> `$INBOX/toc-candidates-<id>.md`, reconciled against the enumerations in
> `$INBOX/toc-enumerations-<id>.md`. Write only the tree block (starting with
> `## དཀར་ཆག / Table of Contents`) to `$INBOX/toc-tree-<id>.md`. Reply only with the path
> you wrote.

After it returns, prepend `stage: toc-tree` frontmatter to `$INBOX/toc-tree-<id>.md` if the
subagent did not.

---

## Pass 4 — Deterministic QC, then ISOLATED repair subagent

First run the bundled checker yourself (NOT by hand — it encodes the exact
numbering/attestation logic and must be identical every run):

```bash
python $SKILLS/seg-toc-lib/qc_check_tree.py \
  $INBOX/toc-tree-<id>.md \
  --corpus $INBOX/toc-candidates-<id>.md $INBOX/toc-enumerations-<id>.md \
  --out $INBOX/toc-tree-qc-<id>.md
```

It flags indentation errors, Tibetan-ordinal vs decimal mismatch, duplicate decimals, sibling
gaps/dups, titles not attested (possible hallucination), ordinals not attested for a
title, and an **announced count** that the children do not match (a node titled
`… རྣམ་པ་བཅུ་གཅིག` with 10 children: a part the text treats without a topic label was
missed — Gu_3CFQ, 2026-10-08). Exit code = issue count.

If issues remain, dispatch ONE **isolated repair subagent** with only the pass-4 prompt and
the paths of the issue report, tree, both sources and the source text:

> Read `$SKILLS/seg-toc-lib/prompts/pass4-qc-repair.md` and follow it exactly.
> Correct the tree for commentary "<id>", fixing every issue in `$INBOX/toc-tree-qc-<id>.md`
> against BOTH the enumerations (`$INBOX/toc-enumerations-<id>.md`) and the candidates
> (`$INBOX/toc-candidates-<id>.md`); for an announced-count issue only, you may read the
> source text `<input-file>`. The tree to fix is `$INBOX/toc-tree-<id>.md`. Overwrite
> that same file with the corrected tree block and reply only with its path.

When a repair inserted a part found only in the source text, re-run the checker with the
source text added to `--corpus`, so the new title is checked against the text it was copied
from.

After it returns, **re-run the checker** and record issues-before / issues-after in
`$INBOX/toc-tree-qc-<id>.md`. Iterate (a fresh isolated repair subagent per round) until the
count is 0 or only genuinely-ambiguous issues remain (note those for the human). Keep the
deterministic checker as the gate — never declare the tree clean on a subagent's say-so.

---

## Pass 5 — Anchors · ISOLATED subagent

`commentary-toc-ingest` places each heading by its `[[context]]` — the verbatim words where that
node's section begins. The tree from passes 3–4 has none, so this pass adds them, together
with the editorial **frame** nodes for the front and back matter (`* I. མཆོད་བརྗོད།`,
`* a. བསྔོ་བ།`, `* b. མཇུག་བྱང།` / `* b.1 མཛད་བྱང།`):

> Read `$SKILLS/seg-toc-lib/prompts/pass5-anchors.md` and follow it exactly.
> The TOC tree is `$INBOX/toc-tree-<id>.md`; the commentary is `<input-file>` (read all of
> it). Write the anchored tree to `$WORK/TOC-<id>/toc-tree-<id>.md`. Reply only with
> the path you wrote.

The anchoring rules encode where the vault's human editors put headings: a divided node at
its own division announcement, node 1 at the work's top-level announcement, every other node
at its own opener (`གཉིས་པ་ … ནི།`) — never at the parent's listing of its title. A first
child's opener sits in the same block as its parent's announcement, so the two headings
stack. For a long commentary, give the subagent one top-level subtree (and the matching
line range) at a time.

Run `commentary-segment --units` on the commentary **before**
extracting the tree, so that the file the anchors are copied from is the file the headings
are ingested into.

---

## Pass 6 — QC against the text itself, then ISOLATED repair subagent

`qc_check_tree.py` checks the tree against the candidates and enumerations — which are model
output too, so **a tree can pass it cleanly while still being wrong about the commentary**
(a top-level misattachment, an unresolved anchor, a cursor that lost its place). The second
checker reads the commentary itself:

```bash
python $SKILLS/seg-toc-lib/qc_tree_vs_source.py \
  $WORK/TOC-<id>/toc-tree-<id>.md --source <input-file> \
  --out $WORK/TOC-<id>/toc-tree-qc-source-<id>.md
```

It resolves each `[[context]]` to the source line where it is found (in tree order; `[[?]]`
when not found) and checks: every anchor found and in document order, no value repeating
three or more times across different subsections, each title attested **near** its own
anchor (not just somewhere in the file), and division counts named in a node's own text vs
its children. `--source` must be the exact file the anchors were copied from. Exit code =
issue count. Some flags are legitimately not errors (a sibling-count mismatch, a title that
the commentary words differently where the section opens) — list those for the human
rather than forcing a fix.

If it reports issues, dispatch ONE isolated repair subagent:

> Read `$SKILLS/seg-toc-lib/prompts/pass4-qc-repair.md` and follow it exactly. Fix
> every issue in `$WORK/TOC-<id>/toc-tree-qc-source-<id>.md` in the anchored tree
> `$WORK/TOC-<id>/toc-tree-<id>.md`, against the commentary `<input-file>` — the
> commentary is the final authority. Keep every anchor verbatim from the commentary.
> Overwrite that same file and reply only with its path.

Re-run **both** checkers after each repair (fresh subagent per round) until both are 0 or
only human-accepted issues remain. Never declare the tree clean on a subagent's say-so, and
never report zero issues for a checker that was not run.

---

## Publish — the finished tree to the rails, once both checkers are clean

`commentary-claims`, `spine-map` and `section-summary` read the finished tree from
`$SECTIONS_RAW/toc-tree/<registered-id>.md` (vault rule: CLAUDE.md §7). Once both
checkers are clean (or the remaining issues are human-accepted):

1. Copy the anchored tree to `$SECTIONS_RAW/toc-tree/<registered-id>.md` with this
   frontmatter (the `registered_id` from the commentary's frontmatter — run `frontmatter`
   first if it has none):

   ```yaml
   ---
   registered_id: <registered-id>
   source_file: <input-file>
   mode: <sabcad|verses|top|labels>
   qc_reports: [$SECTIONS_RAW/toc-qc/toc-tree-qc-<id>.md, $SECTIONS_RAW/toc-qc/toc-tree-qc-source-<id>.md]
   status: complete
   ---
   ```

2. Move the evidence next to it — a `status: complete` rail must not depend on scratch:
   `$INBOX/toc-candidates-<id>.md` → `$SECTIONS_RAW/toc-candidates/<registered-id>.md`;
   `$INBOX/toc-enumerations-<id>.md` → `$SECTIONS_RAW/toc-enumerations/<registered-id>.md`;
   both QC reports → `$SECTIONS_RAW/toc-qc/`.

The candidates and enumerations are extraction evidence, not attested structure (the
candidate scan contains false positives by design) — never cite them from a rail. A tree is
tied to one exact version of its commentary: after a re-segmentation or edit it is stale —
rebuild and re-publish over all four files; never leave a stale rail next to a fresh one.

---

## Heading mode — decide before pass 1

Not every commentary's editors use its sa bcad as headings, and not every commentary has
one. Declare one of four modes (root texts have their own skill, `root-text-toc-extract`):

| Mode | When | Route |
|---|---|---|
| `sabcad` | the commentary has a full sa bcad and the editors ingest it | passes 1–5 as below |
| `verses` | the commentary explains the root verse by verse (no sa bcad, or one the editors ignore) | `commentary-toc-extract/prompts/verse-headings.md` (mode `verses`) in one isolated subagent, then pass 5 for the frame nodes only |
| `top` | only the large parts of the body get headings | `commentary-toc-extract/prompts/verse-headings.md` (mode `top`), then pass 5 for the frame nodes only |
| `labels` | a **commentary without an ordinal sa bcad** that opens its sections by name — `<topic>་གྱི་དོན་གྱི་མདོ་ནི།`, `<topic>་ཞེས་བྱ་བ་ནི།` (Gu_3CFQ; check the first pages for `དང་པོ་ … ནི།` openers: none → this mode) | pass 1 with `$SKILLS/seg-toc-lib/prompts/pass1-candidates-root.md` (its Type D catches unnumbered topic headers, which the standard pass 1 ignores), passes 2–5 as for `sabcad`, **with** frame nodes |


In `verses` mode the headings are editorial: `1. བསྟོད་པ་དངོས།` (or the commentary's own
name), `1.n ཕྱག་འཚལ་<ordinal>།` per root stanza, children only where the commentary itself
divides a stanza (or splits every stanza the same way, e.g. `ཚིག་འགྲེལ།` / `གསལ་འདེབས་ཚུལ།`),
then the later parts (`ཕན་ཡོན།` …). On the 8-file benchmark this took the five non-sa-bcad
files from heading F1 0.10 to 0.83 (`$SYSTEM/scripts/seg-toc-benchmark/`, variant v1.4).

Subagent prompt:

> Read `$SKILL/prompts/verse-headings.md` and follow it
> exactly. Mode: `<verses|top>`. The commentary is `<segmented file>` (read all of it); the
> root text is `<root text>`. Write the tree to `$WORK/TOC-<id>/verse-tree-<id>.md`.
> Check every `[[context]]` occurs in the commentary (whitespace removed). Reply with the path.

Then run pass 5 on that tree with the instruction "keep every numbered line verbatim; add
the frame nodes only", or combine an existing frame tree with
`python3 $SYSTEM/scripts/seg-toc-benchmark/merge_trees.py <numbered> <frame> <out>`.

---

## Execution summary

1. Confirm `input-file` and `commentary-id` (ask if not obvious).
2. `chunk_file.py --index-only` → `chunk-index.tsv` (line ranges only, no text copied).
3. Pass 1: isolated subagent per chunk, reads its line range from the source + writes its own `candidates/chunk_NNN.md` (resumable, parallel).
4. Pass 2: isolated subagent per chunk, writes its own `enumerations/chunk_NNN.md` (parallel).
5. Merge on disk (shell `cat`) → `$INBOX/toc-candidates-<id>.md` and `$INBOX/toc-enumerations-<id>.md`.
6. Pass 3: one isolated subagent reads both merged files → writes `$INBOX/toc-tree-<id>.md`.
7. Pass 4: `qc_check_tree.py` → isolated repair subagent (reads/overwrites by path) → re-check → `$INBOX/toc-tree-qc-<id>.md`.
8. Pass 5: one isolated subagent anchors every node and adds frame nodes → `$WORK/TOC-<id>/toc-tree-<id>.md`.
9. Pass 6: `qc_tree_vs_source.py` on the anchored tree against `<input-file>` → repair → re-run **both** checkers until clean.
10. Publish to `$SECTIONS_RAW/toc-tree/<registered-id>.md` with its evidence.
11. Report totals (candidates, enumeration blocks, issues before/after for both checkers) and the output paths; hand the anchored tree to `commentary-toc-ingest`.

**Isolation is the whole point.** If you ever find yourself doing a pass's reasoning in this
orchestrating context instead of in its own subagent, stop and dispatch the subagent — that is
what preserves the per-task precision the Gemini pipeline was built around.

For candidate extraction only (no tree), run passes 0–2 of this skill and stop after the merge.

## Models — Gemini script vs Claude subagents

| Path | Model | What it runs |
|---|---|---|
| Gemini script (batch / headless) | `gemini-3.8-flash`, thinking `high`, 65 536 output tokens, no fallback; a reply cut off at the limit is retried, never used | `scripts/toc_tree_extractor/extract_toc_tree.py` = passes 1–4; `find_toc_contexts.py` (same folder) = pass 5 anchoring. `GEMINI_API_KEY` is loaded by the scripts from the vault `.env` — never open that file. |
| Claude subagents (this procedure) | isolated subagents with `model: opus` (Opus 5.5), session effort high | passes 1–5 above, prompts from `commentary-toc-extract/prompts/` and `$SKILLS/seg-toc-lib/prompts/` |

⚠ **The two paths are not equivalent yet.** The Gemini script carries its own *embedded*
v1 prompts (`SYSTEM_PROMPT`, `ENUM_SYSTEM_PROMPT`, `TREE_SYSTEM_PROMPT`,
`QC_SYSTEM_PROMPT`); passes 2 and 3 differ substantially from the prompt files (no line-number
`[[N]]` contract on this path, stricter enumeration rules), and the script has no modes
`verses` / `top` / `root`, no Type D, and no frame nodes (add those by hand). The benchmark
numbers in this skill were measured on the Claude path. Use the Gemini script for a quick
sa bcad pass over many commentaries; use the Claude path for the non-`sabcad`
modes, and anything that will be ingested.
