---
name: toc-generate
description: >
  Build a Tibetan Buddhist text's ས་བཅད (sa bcad) table of contents end to end —
  scan the text for structural-outline candidates, copy the division-announcement
  passages verbatim, reconcile them into one nested decimal tree, verify that tree
  against the source with two deterministic checkers, and ingest it back into the
  text as markdown headings with block IDs.

  Trigger this skill whenever the user wants any part of a text's structural outline:
  "extract the sa bcad", "build the TOC tree", "make the dkar chag / dkar-chag",
  "find the divisions", "reconstruct the outline hierarchy", "add section headings
  to the commentary", "ingest the toc tree", "add a clickable TOC", "make this text
  navigable", or "insert headings at the structural markers". Also triggers on
  ས་བཅད, sa bcad, dkar chag, Type A announcements, Type B node headers, and Type C
  closing counts.

  Runs the whole pipeline by default; individual phases are separately addressable
  (see Entry points) when a tree already exists or only candidates are wanted.
profile: any
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/toc-tree-extraction/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/toc-tree-extraction/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/toc-candidate-extraction/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/toc-candidate-extraction/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/toc-tree-ingest/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/toc-tree-ingest/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/TOC-to-HEADING/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/TOC-GENERATOR/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. `$COMMENTARIES`, `$WORK`,
> `$SECTIONS_RAW` and `$RAILS` resolve per repo — see `rails/PROFILES.md`. Block ID
> and heading rules are in `rails/CONVENTIONS.md`; this skill implements them.



## Entry points

The full run is Phase 0 → A → B → C → D → E. Three shorter entries are supported,
because these used to be separate skills and are still individually useful:

| The user wants | Run | Was |
|---|---|---|
| The whole TOC, from raw text to headings in the file | Phase 0 → E | `toc-tree-extraction` + `toc-tree-ingest` |
| Just the candidate scan — "find the divisions", no tree | Phase 0 → A, then stop and report | `toc-candidate-extraction` |
| A tree already exists; put it into the text | Phase E only | `toc-tree-ingest` / `TOC-to-HEADING` |
| A quick two-level clickable TOC, no tree file, no vault | Simple mode (end of this file) | `TOC-GENERATOR` |

Phase A alone is the old candidate-only skill: it is deliberately
**recall-over-precision**, so its output contains false positives by design and is
never citable as attested structure. Say so when reporting it.

# ས་བཅད Table of Contents — extract, verify, ingest

## Why this is an orchestrator, not one big prompt — READ THIS FIRST

The Gemini script's precision comes from **task isolation**: each pass is a *separate API
call* with only that one task's system prompt and only the relevant input. The
candidate-extraction call never sees the tree-building instructions, so it cannot drift into
tree-building; the verbatim-copy call never sees the "interpret and reconcile" instructions,
so it stays literal. Merging the four jobs into one prompt/one context collapses that
isolation and precision drops.

**Therefore you (the orchestrating agent) must NOT perform the four passes yourself in this
context.** Each pass runs as its own **isolated subagent** (via the `Task` tool) whose entire
instruction set is one prompt file under `prompts/` plus its specific input.

**Each subagent reads its input by path and writes its own output file.** Do not paste chunk
text into the subagent prompt and do not funnel results back through your context to write
them yourself — that serialises the writes and bloats your context with every chunk's Tibetan.
Instead, hand each subagent the *paths* of its prompt file and its input, and the *path* it
must write. Distinct output filenames mean parallel subagents never collide. You only: chunk,
dispatch subagents, do the deterministic merge, run the checker, and dispatch the repair
subagent. Do not read the pass prompt files into your own context and do the work inline —
that re-merges what this design deliberately separates.

The four isolated prompts live in:

| File | Pass |
|---|---|
| `prompts/pass1-candidates.md` | section candidates (one subagent per chunk) |
| `prompts/pass2-enumerations.md` | verbatim enumeration blocks (one subagent per chunk) |
| `prompts/pass3-tree.md` | build nested decimal tree (one subagent) |
| `prompts/pass4-qc-repair.md` | repair flagged issues (one subagent per repair round) |

---

## Inputs

| Input | Description |
|---|---|
| `input-file` | Path to the commentary/root-text `.md`, normally under `$COMMENTARIES/` |
| `commentary-id` | Short id for output filenames (inferred from the filename if obvious) |

If the file path is missing, or the `commentary-id` is not obvious from the filename, **stop
and ask** before doing anything else.

## Outputs

Working intermediates, all scratch, never cited from `$RAILS/`:

| File | Stage |
|---|---|
| `$WORK/TOC-<id>/chunk-index.tsv` | chunk line-range index (no text duplicated) |
| `$WORK/TOC-<id>/candidates/chunk_NNN.md` | per-chunk section candidates (resumable) |
| `$WORK/TOC-<id>/enumerations/chunk_NNN.md` | per-chunk verbatim enumeration blocks |
| `$WORK/toc-candidates-<id>.md` | merged candidates |
| `$WORK/toc-enumerations-<id>.md` | merged verbatim enumerations |
| `$WORK/toc-tree-<id>.md` | the tree, in progress through QC/repair rounds |
| `$WORK/toc-tree-qc-<id>.md` | QC report vs. the candidates+enumerations corpus (issues before / after repair) |
| `$WORK/toc-tree-qc-source-<id>.md` | QC report vs. the source commentary itself — pointer validity, near-pointer attestation, monotonicity/collisions, sibling-count congruence |

The rail and its evidence trail — written only once both checkers are clean (Pass 4's Promotion step, below):

| File | Content |
|---|---|
| `$SECTIONS_RAW/toc-tree/<id>.md` | the finished tree, frontmatter naming both QC reports |
| `$SECTIONS_RAW/toc-candidates/<id>.md` | the merged candidate scan (evidence only — recall-over-precision, never citable) |
| `$SECTIONS_RAW/toc-enumerations/<id>.md` | the merged verbatim enumerations (evidence only, never citable) |
| `$SECTIONS_RAW/toc-qc/toc-tree-qc-<id>.md`, `…/toc-tree-qc-source-<id>.md` | both QC reports |

The tree has **no `^toc` block IDs**; the decimal numbering alone identifies each entry.
(Inserting the tree's headings into the source file itself is a separate step — this
vault uses `toc-tree-ingest`, not `add-toc`, for commentaries with a tree from this skill.)

---

## Phase 0 — Plan the chunks (deterministic helper, index-only)

Do NOT copy the text into per-chunk files. Just plan the line windows — subagents read their
range straight from the source:

```bash
python $SKILL/scripts/chunk_file.py \
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

## Phase A — Section candidates · ISOLATED subagent per chunk

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

## Phase B — Verbatim enumerations · ISOLATED subagent per chunk

Run **separately** over the same chunks — a different isolated subagent, because verbatim
copying must not be contaminated by the interpretive instructions of the other passes. Same
read-by-path / write-own-file pattern:

> Read `$SKILL/prompts/pass2-enumerations.md` and follow it
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
`<!-- chunk NNN -->` headers) into `$WORK/toc-candidates-<id>.md`, e.g.:

```bash
cd $WORK/TOC-<id>/candidates && cat chunk_*.md > /tmp/cand-body.md
# then prepend frontmatter and move into place
```

Frontmatter:

```yaml
---
source: <id>
skill: toc-tree-extraction
stage: candidates
date: <YYYY-MM-DD>
total_candidates: <N>
---
```

Likewise concatenate the enumeration files (skipping `NO ENUMERATIONS` ones, in document
order) into `$WORK/toc-enumerations-<id>.md`. Pass 3 reads both merged files by path.

---

## Phase C — Build the nested decimal tree · ISOLATED subagent

Dispatch ONE subagent with only the pass-3 prompt and the paths of the two merged inputs:

> Read `$SKILL/prompts/pass3-tree.md` and follow it exactly.
> Build the full nested decimal TOC for commentary "<id>" from the candidates in
> `$WORK/toc-candidates-<id>.md`, reconciled against the enumerations in
> `$WORK/toc-enumerations-<id>.md`. Write only the tree block (starting with
> `## དཀར་ཆག / Table of Contents`) to `$WORK/toc-tree-<id>.md`. Reply only with the path
> you wrote.

After it returns, prepend `stage: toc-tree` frontmatter to `$WORK/toc-tree-<id>.md` if the
subagent did not.

---

## Phase D — Deterministic QC, then ISOLATED repair subagent

Run **both** bundled checkers yourself (NOT by hand — each encodes exact
numbering/attestation logic and must be identical every run). They check different things
and neither substitutes for the other:

```bash
python $SKILL/scripts/qc_check_tree.py \
  $WORK/toc-tree-<id>.md \
  --corpus $WORK/toc-candidates-<id>.md $WORK/toc-enumerations-<id>.md \
  --out $WORK/toc-tree-qc-<id>.md

python $SKILL/scripts/qc_tree_vs_source.py \
  $WORK/toc-tree-<id>.md --source <input-file> \
  --out $WORK/toc-tree-qc-source-<id>.md
```

`qc_check_tree.py` flags indentation errors, Tibetan-ordinal vs decimal mismatch, duplicate
decimals, sibling gaps/dups, titles not attested *in the candidates+enumerations the model
itself extracted* (possible hallucination), and ordinals not attested for a title. That
corpus is LLM output too, so a tree can pass this check cleanly while still being
inconsistent with the actual commentary — which is exactly what happened on all three
trees shipped in this vault (all reported `issues_before: 0, issues_after: 0` while
carrying real defects; see `qc_tree_vs_source.py`'s module docstring for the specifics).

`qc_tree_vs_source.py` is the check against the commentary itself: pointer bounds, title
attestation *near* each node's own `[[N]]`/`[[?]]` pointer (not just somewhere in the
file), document-order monotonicity, repeated-pointer collisions (the "extractor lost its
cursor" signature — a value repeating three or more times across different titled
subsections), and a heuristic sibling-count check (does a node's own announcing text name
a division count that matches how many children the tree actually gives it). **Pass the
exact file version the tree's line numbers were computed against** — `--source` must be
the same bytes `chunk_file.py` chunked, not a later resegmentation of the same
commentary, or every pointer will look wrong for a reason that has nothing to do with the
tree.

Both exit codes = issue count. If either reports issues, dispatch ONE **isolated repair
subagent** with only the pass-4 prompt and the paths of both issue reports, tree, and both
sources:

> Read `$SKILL/prompts/pass4-qc-repair.md` and follow it exactly.
> Correct the tree for commentary "<id>", fixing every issue in `$WORK/toc-tree-qc-<id>.md`
> AND `$WORK/toc-tree-qc-source-<id>.md` against the enumerations
> (`$WORK/toc-enumerations-<id>.md`), the candidates (`$WORK/toc-candidates-<id>.md`),
> and the source commentary itself (`<input-file>`) — the source is the final authority
> when it and the candidates disagree. The tree to fix is `$WORK/toc-tree-<id>.md`.
> Overwrite that same file with the corrected tree block and reply only with its path.

After it returns, **re-run both checkers** and record issues-before / issues-after in both
QC report files. Iterate (a fresh isolated repair subagent per round) until both counts are
0 or only genuinely-ambiguous issues remain (note those for the human — a sibling-count
mismatch or a same-line collision across nested levels is often legitimate, not wrong;
`qc_tree_vs_source.py` says so explicitly rather than treating every flag as proven error).
Keep both deterministic checkers as the gate — never declare the tree clean on a
subagent's say-so, and never report zero issues when a checker was not actually run.

---

## Promotion — write the rail and its evidence, once clean

Once both checkers report 0 issues (or only human-reviewed-and-accepted ones):

1. Copy the tree from `$WORK/toc-tree-<id>.md` to `$SECTIONS_RAW/toc-tree/<id>.md`,
   normalizing its frontmatter to:

```yaml
---
registered_id: <id>
source_file: $COMMENTARIES/<filename>.md
qc_reports: [$SECTIONS_RAW/toc-qc/toc-tree-qc-<id>.md, $SECTIONS_RAW/toc-qc/toc-tree-qc-source-<id>.md]
status: complete
---
```

2. Move the evidence trail out of scratch, next to the tree — a `status: complete` rail
   must not depend on files in `$WORK/`:
   - `$WORK/toc-candidates-<id>.md` → `$SECTIONS_RAW/toc-candidates/<id>.md`
   - `$WORK/toc-enumerations-<id>.md` → `$SECTIONS_RAW/toc-enumerations/<id>.md`
   - `$WORK/toc-tree-qc-<id>.md`, `$WORK/toc-tree-qc-source-<id>.md` → `$SECTIONS_RAW/toc-qc/` (filenames unchanged)

The per-chunk staging under `$WORK/TOC-<id>/` stays in scratch. The promoted
candidate/enumeration files are extraction evidence, not attested structure — extraction is
deliberately recall-over-precision, so they contain false positives by design; never cite
them from any rail or transformation. If a later resegmentation invalidates this tree,
rebuilding it overwrites `$WORK/toc-tree-<id>.md` and re-promotes over all four promoted
files; do not leave a stale rail file next to a fresh one.

---

## Phase E — Ingest the tree into the text as headings

The tree is only useful once its nodes are headings in the text itself. This phase
inserts one markdown heading line per node, **in place**, into the canonical file.
Prose is never deleted, reordered, or retyped.

Which anchor the ingest uses depends on what the tree's `[[N]]` pointers mean —
this is the one decision to get right:

| Pointer meaning | Use | Why |
|---|---|---|
| Source **line numbers**, validated by `qc_tree_vs_source.py` (trees this skill built) | **E1 — scripted ingest** | The pointer already is the resolved position; no searching needed |
| Source **PDF page numbers**, or unvalidated (hand-made trees, external trees) | **E2 — read-and-place ingest** | A page pointer used as a line number silently puts headings in the wrong place |

If you are unsure which you have, run `qc_tree_vs_source.py` (Phase D) first. A
tree whose pointers are page numbers will fail its bounds check immediately.

### Step 0 — Back up (both paths)

This phase edits the canonical source file directly. Take an undo copy first. It is
a safety net, never a second source of truth:

```bash
mkdir -p "$WORK/TOC-<id>"
cp "$COMMENTARIES/<id>.md" "$WORK/TOC-<id>/pre-toc-ingest-backup.md"
```

### E1 — Scripted ingest (line-number pointers)

Parse once, then ingest in a single pass:

```bash
python3 $SKILL/scripts/toc_tree_ingest.py parse \
  --input "$SECTIONS_RAW/toc-tree/<id>.md" \
  --out "/tmp/toc-tree-<id>.json"

python3 $SKILL/scripts/toc_tree_ingest.py ingest \
  --tree "/tmp/toc-tree-<id>.json" \
  --commentary "$COMMENTARIES/<id>.md"
```

Write the JSON to `/tmp/` to avoid NTFS ghost-file issues. Skip `parse` if the JSON
exists and the tree has not changed; it reports how many nodes carry no pointer
(`[[?]]`) — those will come back not-found.

**Nodes are inserted in reverse document order** (highest line number first), so
each insertion never shifts the line numbers of nodes not yet processed. The script
prints inserted / already-present / not-found counts and exits non-zero if anything
is not-found.

> **Retired anchor scheme — do not reintroduce.** An earlier version searched for a
> `[[context text]]` snippet with document-order cursor disambiguation. That never
> matched what `qc_tree_vs_source.py` validates (a `\d+|\?`-only pointer), so a tree
> could QC clean and still be ingested wrongly. Line-number pointers are the one
> format both tools agree on.

### E2 — Read-and-place ingest (page pointers or unvalidated trees)

Do not trust the pointer as a position. For each TOC entry, read the prose and find
the sentence that actually **announces** that section — the sa bcad — and insert the
heading immediately before it. Use the pointer only as a hint about roughly where to
look.

If a human contributor has already hand-ingested the first several entries as a
worked example, read that portion first and match its formatting exactly before
touching the rest.

The failure this avoids: headings landing at a plausible-looking but wrong spot, or
splitting a sentence badly, because a page number was treated as a line number.

`$SKILL/references/sachad-recognition.md` describes what a sa bcad announcement
looks like, and `$SKILL/scripts/insert_toc_headings.py` will apply a reviewed
annotation JSON (`$SKILL/references/example-annotation.json` shows the shape) so the
insertion itself stays deterministic once you have decided the positions.

### Heading level and block ID

| Depth | Heading | Decimal ID | Block ID |
|---|---|---|---|
| 1 | `##` | `1` | `^1-0` |
| 2 | `###` | `1.3` | `^1-3-0` |
| 3 | `####` | `1.3.2` | `^1-3-2-0` |
| 4 | `#####` | `1.3.2.2` | `^1-3-2-2-0` |
| 5+ | `######` | … | … |

Decimal path segments joined with `-`, then `-0` appended. No zero-padding.

> **Known conflict — decide per text and say which you chose.** `rails/CONVENTIONS.md`
> §2 caps heading IDs at four segments and says to flatten anything deeper. The
> ingest script follows the tree to full depth with no cap, which is what the
> 21-Taras commentaries actually contain. Both behaviours are in use. Deep trees are
> real, so the cap is the rule that gives: ingest at full depth, and note in the
> report that the file carries IDs deeper than the documented cap. Do not silently
> flatten a tree — that destroys the structure the previous four phases recovered.

### Step 3 — Resolve not-found nodes

**`[[?]]` pointer** — the tree could not resolve this node to a line. Read the
surrounding prose, locate the section, insert the heading manually:

```
###### Label text ^block-id

```
(blank line after; immediately before the section's opening prose)

**Out-of-range `[[N]]`** — N exceeds the file's line count. The tree was built
against a *different version* of this file, almost certainly a resegmentation since.
Do not patch the pointer by hand: rebuild the tree (Phase 0–D) against the current
file.

After manual insertions, re-run E1 — the already-present check skips them and should
confirm zero not-found.

### Rules

1. **No pointer content in the output.** Only the label and block ID are written.
2. **No prose is altered.** Never delete, reorder, or retype an existing line.
3. **Transclusion lines are structural** — they never take a block ID and never
   advance a body counter (`rails/CONVENTIONS.md` §3).
4. **Single pass, reverse document order**, all depths at once.

---

## Simple mode — two-level TOC, no tree file

When the user just wants a commentary made navigable and does not need a citable
tree rail, skip Phases 0–D entirely: detect the sa bcad directly and insert a
two-level set of headings (main topic / sub-topic) with block IDs at the point where
each topic's text begins, writing the result to a **new file**. The original prose is
never altered.

Use `$SKILL/references/sachad-recognition.md` for detection and
`$SKILL/scripts/insert_toc_headings.py` to apply the positions deterministically.
Once headings are in, Obsidian's Outline panel, `[[file#Heading]]` links, and any
static-site TOC generator render a clickable TOC for free.

This mode is vault-independent — it needs no `$RAILS`, no promotion step, and no QC
corpus. It is the right choice for a one-off or an unfamiliar text, and the wrong
choice when the tree itself has to be cited, compared across commentaries, or fed to
`section-summary` / `commentary-claims`.


---

## Execution summary

1. Confirm `input-file` and `commentary-id` (ask if not obvious).
2. `chunk_file.py --index-only` → `chunk-index.tsv` (line ranges only, no text copied).
3. Pass 1: isolated subagent per chunk, reads its line range from the source + writes its own `candidates/chunk_NNN.md` (resumable, parallel).
4. Pass 2: isolated subagent per chunk, writes its own `enumerations/chunk_NNN.md` (parallel).
5. Merge on disk (shell `cat`) → `$WORK/toc-candidates-<id>.md` and `$WORK/toc-enumerations-<id>.md`.
6. Pass 3: one isolated subagent reads both merged files → writes `$WORK/toc-tree-<id>.md`.
7. Pass 4: `qc_check_tree.py` → isolated repair subagent (reads/overwrites by path) → re-check → `$WORK/toc-tree-qc-<id>.md`.
8. Promote: once clean, copy to `$SECTIONS_RAW/toc-tree/<id>.md` with normalized frontmatter (above).
8b. Phase E: back up the commentary, then ingest the tree as headings — `toc_tree_ingest.py parse` + `ingest` for line-number pointers, read-and-place for page pointers. Resolve any not-found nodes and re-run until zero.
9. Report totals (candidates, enumeration blocks, issues before/after) and the output paths — both the `$WORK/` working files and the promoted `$SECTIONS_RAW/toc-tree/<id>.md`.

**Isolation is the whole point.** If you ever find yourself doing a pass's reasoning in this
orchestrating context instead of in its own subagent, stop and dispatch the subagent — that is
what preserves the per-task precision the Gemini pipeline was built around.

