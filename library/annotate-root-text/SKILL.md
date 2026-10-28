---
name: annotate-root-text
description: >
  Pipeline 1 orchestrator. Invoked via /annotate [path-to-raw-text] [text-id]
  [language] — with no path, picks the next pending file from input/ per the
  repo-root ledger.json. Sequences the intake/annotation/metadata skills
  end-to-end against one texts/<text-id>/ directory, tracking progress in
  status.json and ledger.json and stopping at human-review checkpoints, to
  produce annotated.md. Performs no text transformation itself; every edit is
  delegated to a sub-skill.

  Trigger this skill whenever the user wants a raw text taken through the
  whole annotation pipeline — "annotate this text", "process the file(s) in
  input/", "run the pipeline on this file", "continue/resume the annotation",
  "what's in the queue" — not just when they type /annotate.
profile: library-pipeline
supersedes:
  - webuddhist-library-data-pipeline/skills/annotate-root-text/SKILL.md
  - data-pipeline/skills/annotate-root-text/SKILL.md
---

# annotate-root-text

Pipeline 1 orchestrator for a single root text. This skill **sequences**
sub-skills and **tracks state** — it never edits verse text, headings, block
IDs, or frontmatter itself. Every transformation is delegated to the
sub-skill named in the step table below; this skill's own job is: figure out
which step comes next, invoke the right sub-skill with the right input/output
paths, record the result in `status.json`, and stop for human review at the
two mandated checkpoints.

Invocation: `/annotate [path-to-raw-text] [text-id] [language]`

- `[path-to-raw-text]` — optional. Path to the raw source file (anywhere on
  disk, not necessarily already under `texts/`). **If omitted, use the
  `input/` queue**: list every file in `input/` (skip `README.md` and
  dotfiles), look each up in `ledger.json` (repo root), and report the queue
  to the human — which files are already `"annotated"`/`"uploaded"` (never
  re-process these unless the human explicitly says to), which are
  `"in_progress"` (resumable — see Resumability), and which have no entry
  yet (pending). Then take the first resumable-or-pending file as this run's
  input and proceed. Process one text end-to-end (through both checkpoints)
  before touching the next pending file.
- `[text-id]` — optional. If omitted, derive from the filename (see Intake).
- `[language]` — optional. One of `bo` (Tibetan), `sa` (Sanskrit), or `other`
  (every other language — Pāli, Chinese, English, etc.). If omitted, detect
  from content/frontmatter (see Intake). Accepts full names too (`tibetan`,
  `sanskrit`) and normalises them.

End state on success: `texts/<text-id>/annotated.md`, ready for
`/upload texts/<text-id>/` (Pipeline 2 — see `skills/upload-root-text/SKILL.md`).

---

## Per-text contract

All work happens under `texts/<text-id>/`:

| Path | Role |
|---|---|
| `raw.md` | Original ingest, verbatim, never modified after intake |
| `work/` | Intermediates — every step but `frontmatter` writes here |
| `annotated.md` | Final output, promoted from `work/segmented.md` at the end of `validate` |
| `status.json` | Step tracker for resumability (this skill's state) |

This skill only ever writes inside `texts/<text-id>/`. It never touches
`docs/`, `tools/`, `README.md`, or `CLAUDE.md`.

---

## Intake

Run once, before Step 1, only if `texts/<text-id>/status.json` does not
already exist (see Resumability).

1. **Resolve `text-id`.**
   - If given, use it as-is (it is assumed to already be lowercase-hyphenated;
     re-slugify it anyway using the rule below as a safety net).
   - If not given, derive it from `<path-to-raw-text>`'s filename: take the
     stem (drop the extension), Unicode-normalise (NFKD) and drop combining
     marks so diacritics fall away (é → e, ā → a, ṅ → n), lowercase,
     replace every run of characters that are not `a-z0-9` with a single
     hyphen, and trim leading/trailing hyphens. Non-Latin-script filenames
     (e.g. a Tibetan or Sanskrit title used as the filename) will not
     survive this transliteration meaningfully — in that case, or if the
     result is empty or under 3 characters, stop and ask the human for an
     explicit `text-id`.
2. **Resolve `language`.**
   - If given, normalise: `tibetan`/`bo` → `bo`; `sanskrit`/`sa`/`skt` → `sa`;
     anything else (including the literal `other`) → `other`.
   - If not given, detect:
     a. If the raw file already has YAML frontmatter with `language:` or
        `lang_tag:`, normalise that value the same way.
     b. Otherwise, sample the file content (first ~2000 characters is
        enough) and count characters by Unicode block: Tibetan
        (U+0F00–U+0FFF) vs. Devanagari (U+0900–U+097F). Whichever block
        dominates decides `bo` or `sa`; if neither is clearly dominant
        (mixed script, or neither block present — e.g. Latin-script Pāli or
        English), use `other`.
     c. Report the detected language to the human as part of the intake
        summary — do not silently proceed on a guess without saying so.
3. **Create the working directory.** `texts/<text-id>/` and
   `$WORK/`.
4. **Copy the input verbatim to `raw.md`.** Byte-for-byte copy of
   `<path-to-raw-text>` to `texts/<text-id>/raw.md`. Never edit this copy in
   any later step.
5. **Initialise `status.json`:**
   ```json
   {
     "text_id": "<text-id>",
     "language": "<bo|sa|other>",
     "steps": {
       "clean": "pending",
       "segment": "pending",
       "verse_ids": "pending",
       "toc": "pending",
       "frontmatter": "pending",
       "validate": "pending"
     },
     "updated": "<ISO date>"
   }
   ```
   Note for later: `tools/run_upload.py` (Pipeline 2) writes to this **same**
   file when it runs, under its own `steps.lint` / `steps.parse` /
   `steps.upload` keys (each a `{"state": ..., ...}` object) and its own
   `updated_at` field. The two pipelines' step names never collide, so this
   is safe — Pipeline 1's steps stay flat strings, Pipeline 2's stay nested
   objects, in the same `steps` map. Don't "clean up" the other pipeline's
   keys when writing this file.
6. **Record the text in `ledger.json`** (repo root — the pipeline's
   done-tracking queue). Append one entry to its `entries` array:
   ```json
   {
     "file": "input/<filename>  (or the explicit path the run was given)",
     "text_id": "<text-id>",
     "language": "<bo|sa|other>",
     "status": "in_progress",
     "started": "<ISO date>",
     "annotated": null,
     "uploaded": null
   }
   ```
   Exactly one entry per input file — on resume, update the existing entry
   in place; never append a duplicate. The ledger is what lets a no-arg
   `/annotate` skip files that are already done, so keep it truthful:
   `"in_progress"` until checkpoint 2 is human-confirmed, flipped to
   `"annotated"` at Completion (below), and to `"uploaded"` only by
   `skills/upload-root-text/SKILL.md` after a confirmed execute run.
7. Report the intake summary to the human: resolved `text-id`, resolved
   `language` (and how it was determined), the created paths, and the new
   ledger entry. Then proceed to Step 1.

---

## Step order

Each step reads the prior step's output from `work/`, writes its own output,
and — only once its output exists and looks right — sets its `status.json`
entry to `"done"`. Steps are always run in this order; do not skip ahead.

| # | Step key | Sub-skill(s) | Reads | Writes |
|---|---|---|---|---|
| 1 | `clean` | `skills/clean-raw-text/SKILL.md` | `raw.md` | `work/cleaned.md` |
| 2 | `segment` | `skills/format-tibetan-root-text/SKILL.md` (bo) / `skills/format-sanskrit-root-text/SKILL.md` (sa) / `skills/format-root-text/SKILL.md` (other) | `work/cleaned.md` | `work/segmented.md` |
| 3 | `verse_ids` | same skill as `segment`, its block-ID phase | `work/segmented.md` | `work/segmented.md` (in place) |
| 4 | `toc` | `skills/add-toc/SKILL.md` / `skills/tag-inline-toc/SKILL.md` — each conditional, see below | `work/segmented.md` | `work/segmented.md` (in place, after reconciliation) |
| 5 | `frontmatter` | `skills/root-text-frontmatter/SKILL.md` (+ `skills/colophon-metadata-extractor/SKILL.md`, `skills/source-property-extractor/SKILL.md` conditionally) | `work/segmented.md` | `work/segmented.md` (in place) |
| 6 | `validate` | checklist + `skills/format-sanskrit-root-text/scripts/apply.py` (sa only) | `work/segmented.md` | `annotated.md` (on pass) |

### Step 1 — `clean`

Invoke `skills/clean-raw-text/SKILL.md` in full, exactly as written, with
`text-id` = this text's id. It reads `raw.md` and writes
`work/cleaned.md`. Follow its own procedure completely, including printing
the profile JSON before running any script (its Rule 4) and the first-100-line
review (its Step 5) — these are that skill's own built-in checks, not
optional. Once `work/cleaned.md` exists and the review found no remaining
issues, set `clean` → `"done"`.

If the skill's own rules ask you to stop and ask the human about an ambiguous
repeated line (its Rule 6), do so — this is a normal pause, not a pipeline
failure; resume once answered.

### Step 2 — `segment`

Route by `language`:

- **bo** → `skills/format-tibetan-root-text/SKILL.md`. Follow its "Applying
  to a New Text" procedure to choose between
  `skills/format-tibetan-root-text/scripts/format_bca.py` (colophon-driven)
  and `skills/format-tibetan-root-text/scripts/format_bo_root.py`
  (table-driven), then run
  the chosen script with `--input $WORK/cleaned.md --output
  $WORK/segmented.md`. This single pass already assigns
  `^chapter-verse` block IDs and `^N-0` chapter headings — Tibetan has no
  separate segmentation-vs-ID split at the tool level (see the note on Step 3
  below).
- **sa** → `skills/format-sanskrit-root-text/SKILL.md`. For this step, copy
  `work/cleaned.md` to `work/segmented.md` (establishing the file at the
  path every other language step uses), then work through the skill's Step 0
  (OCR cleanup check) and Step 1 (read and identify structure semantically —
  zones, headings) on `work/segmented.md`, applying heading IDs (its Step 2)
  as you go. Leave content-block IDs (its Step 3) for Step 3 of this
  orchestrator, below — that is exactly the skill's own `apply.py`
  audit/apply/LLM-resolve workflow.
- **other** → `skills/format-root-text/SKILL.md`. Copy `work/cleaned.md` to
  `work/segmented.md`, then apply the skill's Step 2.1–2.2 (frontmatter
  placeholder + heading standardisation, including the `## 0. Introduction
  ^0-0` rule) on `work/segmented.md`. Leave block-ID assignment (its Step
  2.3) for Step 3 of this orchestrator — `format-root-text` has no separate
  script either, so this split is enforced by this orchestrator, not the
  sub-skill.

Set `segment` → `"done"` once `work/segmented.md` exists with headings in
place (chapter/section structure visible, `^N-0` anchors present or
pending only final numbering).

### Step 3 — `verse_ids`

> **Where this step's actual work differs by language** — noted here because
> the plan describes one uniform "audit → apply → LLM resolves flagged
> blocks" phase, but only Sanskrit has a script that implements that
> workflow:

- **sa**: run the real two/four-phase cycle described in
  `skills/format-sanskrit-root-text/SKILL.md`'s "Workflow" section:
  1. `python skills/format-sanskrit-root-text/scripts/apply.py audit $WORK/segmented.md`
  2. Read the audit output; for every `[needs LLM judgment]` block, decide
     its zone per the skill's Step 1b.
  3. `python skills/format-sanskrit-root-text/scripts/apply.py apply $WORK/segmented.md`
  4. Apply any still-flagged blocks by hand with the Edit tool, per the
     skill's Step 4.
- **bo**: block IDs were already assigned in Step 2 by `format_bca.py` /
  `format_bo_root.py` (there is no separate audit script for Tibetan). This
  step becomes a **verification pass**: read `work/segmented.md` end to end
  and check it against `format-tibetan-root-text/SKILL.md`'s "Common
  Pitfalls" table (missing `^`, unsplit stanzas, colophon text leaking into
  output, double blanks, off-by-one chapter boundaries, stray `^TOC-N`
  anchors). Also run the mechanical line-structure check:
  `python3 skills/lint-annotations/scripts/fix_midverse.py --input
  $WORK/segmented.md --check` (merged verse half-lines —
  see `skills/lint-annotations/SKILL.md`). Fix anything found directly
  with the Edit tool (or, for merged lines the human confirms, re-run
  `fix_midverse.py` without `--check`).
- **other**: same situation as bo — `format-root-text` assigns IDs inline
  with no separate script. Verify against `format-root-text/SKILL.md`'s
  "Dos and Don'ts" list (no renumbering by own interpretation, no block IDs
  on non-`^N-0` heading lines, no `####`, no `^TOC-N`) and fix directly.

Set `verse_ids` → `"awaiting_review"` (not `"done"` yet) once this step's
work is complete — see **Human review checkpoint 1**, below, before it can
become `"done"`.

### Step 4 — `toc`

By the end of Step 3, `^N-0` / `^N-N-0` chapter and section heading anchors
already exist in `work/segmented.md` (every `segment` path produces them).
This step covers only the **optional enrichments** on top of that — run each
only if its precondition holds; skip the rest:

- **`skills/add-toc/SKILL.md`** — only if `raw.md` (or `work/cleaned.md`)
  contains a flat, unindented draft TOC list at the top of the document
  (that skill's own Step 1 precondition). It writes a new file,
  `work/toc-segmented.md`. If produced, review it, then copy its content
  back over `work/segmented.md` so the file stays canonical for later steps
  — `add-toc` does not do this reconciliation itself, since its own contract
  is scoped to producing the `toc-`-prefixed file.
- **`skills/tag-inline-toc/SKILL.md`** — only if the text has inline
  *sa bcad*-style structural announcements (per
  `docs/reference/conventions.md`). It writes `work/tagged-segmented.md`.
  If produced, review the render report (prose-integrity check must pass),
  then copy its content back over `work/segmented.md` the same way.
If neither precondition holds, this step is a no-op: record it
`"done"` with a note (`toc: "done — no flat TOC draft, no inline sa
bcad"` alongside the `status.json` entry, or in the conversation
if you'd rather keep `status.json` to bare strings) and move on.

### Step 5 — `frontmatter`

Three sub-skills can touch frontmatter; they overlap in scope and use
different field names for the same concepts, so run them in this fixed order
and let earlier, more-specific extractions survive later, more-general ones
— never let a later pass blindly clobber a field an earlier pass already
filled with a real (non-placeholder) value:

1. **`skills/colophon-metadata-extractor/SKILL.md`** — only if `language ==
   bo` **and** the original input filename matches the Derge convention
   (starts with `D` followed by digits, e.g. `D3872.txt` — this is a hard
   precondition in that skill's own "Inputs" table, not a suggestion). If it
   doesn't match, skip this sub-skill entirely; `frontmatter` (Variant 1)
   alone covers Tibetan colophon extraction for non-Derge sources. When it
   does run, treat its output as a seed, not a final answer — its own field
   names (`title_in_english`, `author_in_english`, `derge_catalog_id`) are
   not exactly `docs/reference/frontmatter-schema.md`'s schema; carry
   `derge_catalog_id` through as a harmless extra property (the schema
   defines required/recommended/optional fields, not a closed set), and let
   Step 5.2 reconcile the rest into schema-correct field names.
2. **`skills/root-text-frontmatter/SKILL.md`** — always run, on
   `work/segmented.md`. This is the authoritative extractor for this
   repo's schema. If Step 5.1 ran first and left a partial frontmatter
   block, **merge** rather than following its Step 7 ("insert or replace")
   literally as a full overwrite — preserve any field Step 5.1 already
   populated with a real value (including `derge_catalog_id`), and fill in
   everything else per `docs/reference/frontmatter-schema.md` (required:
   `file_type`, `title`, `language`/`lang_tag`, `category_id`, `license`,
   `author`, `source`, `edition_type`).
   **Override its own inline example when they disagree with the schema
   doc**: `docs/reference/frontmatter-schema.md` and the golden fixture
   (`tests/fixtures/bcav08-sh-sk/annotated.md`) both use `lang_tag: sa` for
   Sanskrit; `root-text-frontmatter/SKILL.md`'s own "lang_tag defaults" table
   and `colophon-metadata-extractor/SKILL.md`'s template both say `sk`. Use
   `sa` (and `bo` for Tibetan) — `docs/reference/frontmatter-schema.md` is
   the authoritative schema per this repo's own provenance notes; treat any
   skill's inline example that disagrees with it as the error, not the
   schema.
3. **`skills/source-property-extractor/SKILL.md`** — only if, after Step
   5.2, `source` or `source_description` is still empty or still holds
   `frontmatter` (Variant 1)'s own placeholder fallback text ("Source unknown
   — to be verified"). Run it to make one more targeted pass at the title
   and colophon specifically for provenance fields, and fill just those two
   fields if it finds something real. Do not re-run it if Step 5.2 already
   produced a confident `source_description`.

Set `frontmatter` → `"done"` once the YAML block at the top of
`work/segmented.md` has every required field from
`docs/reference/frontmatter-schema.md`.

### Step 6 — `validate`

1. **Sanskrit only** — run
   `python skills/format-sanskrit-root-text/scripts/apply.py audit $WORK/segmented.md`
   one more time and confirm it reports no remaining `[needs LLM judgment]`
   blocks and no gaps. (This script's zone scheme is Sanskrit-specific;
   running it against a bo/other file would misreport, so skip it for those
   — the checklist below is the only check for them.)
2. **Mechanical lint, all languages** — run `skills/lint-annotations/SKILL.md`
   against `work/segmented.md` (it wraps this step's Sanskrit audit, the
   Tibetan merged-line check, the footnote-digit flagger, and — since
   frontmatter now exists — the Pipeline 2 field/reference lint). Treat any
   issue it reports as a checklist failure below.
3. **Checklist, all languages** — read `work/segmented.md` in full and
   confirm:
   - [ ] Every stanza/content block ends with a block ID.
   - [ ] Heading levels don't skip (`#` → `##` → `###`, never `#` → `###`).
   - [ ] Every heading block ID ends in `-0`.
   - [ ] Frontmatter has every required field from
     `docs/reference/frontmatter-schema.md`.
   - [ ] No null bytes or leftover page markers remain (these should have
     been removed in Step 1, but confirm — a page marker surviving into
     `annotated.md` is a lint-time failure in Pipeline 2, not just cosmetic).
4. **On pass**: copy `work/segmented.md` to `texts/<text-id>/annotated.md`
   (copy, don't move — keep `work/` as the audit trail). Set `validate` →
   `"awaiting_review"` — see **Human review checkpoint 2**, below.
5. **On fail**: do not promote. Report exactly which checklist item(s)
   failed and which earlier step is responsible (missing block ID →
   revisit `verse_ids`; skipped heading level or missing `-0` → revisit
   `segment`/`toc`; missing frontmatter field → revisit `frontmatter`;
   leftover page marker → revisit `clean`). Leave `validate` as `"pending"`
   and stop — this is not a `"blocked"` state (nothing failed to run; the
   output just isn't ready yet), so don't mark it that way. Await
   instruction on whether to loop back automatically or let the human fix it
   directly.

---

## Human review checkpoints

Two points in the pipeline **stop and ask** — do not proceed automatically
past them, even if everything mechanically succeeded:

1. **After Step 3 (`verse_ids`)** — segmentation and block IDs are the
   backbone every later step (headings, frontmatter, and all of Pipeline 2)
   depends on. Present a summary (chapter count, verse count per chapter,
   any blocks that needed LLM judgment) and the file itself for review.
   `status.json`: `"verse_ids": "awaiting_review"`. Only flip to `"done"`
   once the human confirms; then continue to Step 4.
2. **After Step 6 (`validate`)**, before declaring the text done — even
   though the checklist passed mechanically, a human confirms before
   `annotated.md` is treated as final and handed to Pipeline 2. Present the
   checklist results and the promoted `annotated.md`. `status.json`:
   `"validate": "awaiting_review"`. Only flip to `"done"` once confirmed.

At both checkpoints, if the human requests changes, make them, then re-run
just that step's own checks before asking again — do not silently
re-approve.

---

## Resumability

On invocation, if `texts/<text-id>/status.json` already exists, **skip
Intake** and resume:

1. Load `status.json`. Find the first step (in table order) whose value is
   not `"done"`.
2. If that step is `"awaiting_review"` — do not silently continue. Re-present
   the pending review (per the checkpoint it belongs to) and wait for
   confirmation before resuming.
3. If that step is `"blocked"` — report the blocking note already recorded
   for it (see Failure handling) and stop; do not retry automatically.
4. If that step is `"pending"` — start it normally, using whatever `work/`
   files the prior `"done"` steps already produced.
5. If every step is `"done"`, the text is already annotated — report the
   existing `annotated.md` path and point at Pipeline 2; do not redo work.

The text's `ledger.json` entry already exists from the original intake —
leave its `status` as `"in_progress"` while resuming; never append a
duplicate entry. If `status.json` exists but the ledger entry is missing
(pre-ledger text, or hand-deleted), recreate the entry with what
`status.json` knows before resuming.

---

## Failure handling

If a sub-skill cannot complete (e.g. `clean-raw-text` can't produce a usable
`cleaned.md`, `format-sanskrit-root-text`'s `apply.py` errors out, a required
script is missing) do not skip ahead or paper over it:

1. Set that step's `status.json` entry to `"blocked"`.
2. Add a short note explaining why, alongside it — e.g.
   `"steps": {"segment": "blocked"}` plus a `"segment_note": "format_bca.py
   found no colophon marker; text needs format_bo_root.py with a manual
   CHAPTER_STARTS table, which requires a human to read the source and build
   it"`.
3. Stop. Report the block clearly: which step, which sub-skill, why, and
   what a human needs to supply or decide to unblock it.

Do not mark a step `"done"` on partial or uncertain output. When in doubt,
`"blocked"` with a clear note is always the safer state than a false
`"done"`.

---

## Completion

Once `validate` is `"done"` (human-confirmed):

1. **Update the text's `ledger.json` entry**: `status` → `"annotated"`,
   `annotated` → today's ISO date. (Only `skills/upload-root-text/SKILL.md`
   may later flip it to `"uploaded"`, after a confirmed execute run.)
2. Report:
   - `texts/<text-id>/annotated.md` — the final path.
   - A one-line summary: language, chapter/verse counts, which optional
     Step 4 enrichments ran.
   - Next step: **Pipeline 2** — `/upload texts/<text-id>/` (see
     `skills/upload-root-text/SKILL.md`).
   - If this run came from the `input/` queue and the ledger still lists
     pending files, say which — the human decides whether to start the next
     one now.

---

## Provenance

New to this repo — Pipeline 1 has no direct one-to-one predecessor skill in
`bodhisattvacharyavatara-rails`; that vault's equivalent workflow was manual
(a human invoking each `4-SYSTEM/Skills/` skill in sequence via its own
slash command, tracking progress by memory rather than a `status.json`).
This skill formalises that same sequence — clean → format → block IDs →
headings/TOC → frontmatter → validate — as one resumable orchestrator against
this repo's `texts/<text-id>/` per-text contract, per the implementation
plan's "Pipeline 1" section.
