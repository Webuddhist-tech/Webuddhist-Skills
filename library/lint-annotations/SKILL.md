---
name: lint-annotations
description: >
  Annotation-convention linter. Invoked via /lint <text-id> (or a file
  path) — verifies verse structure, lines-per-verse, block IDs, verse IDs,
  heading anchors, and stray footnote digits against
  docs/reference/conventions.md, using the repo's tested checkers per
  language. Report-only by default; never fixes anything without explicit
  human confirmation.

  Trigger this skill whenever annotation conventions need checking —
  "lint the annotations", "verify the block IDs", "check the verse
  structure", "are the headings right", "validate the conventions" — at
  /annotate checkpoints, and as a pre-flight before /upload.
profile: library-pipeline
supersedes:
  - webuddhist-library-data-pipeline/skills/lint-annotations/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/lint-annotations/SKILL.md
---

# lint-annotations

Annotation-convention linter for a formatted root-text file. This skill
**sequences existing, tested checkers** and reads the result back in plain
language — it contains no detection logic of its own. Every mechanical check
lives in a script that predates this skill (see Provenance); the only
LLM-judgment part is the read-through checklist, which is the same checklist
the `annotate-root-text` orchestrator's Step 6 already mandates.

Invocation: `/lint <text-id>` or `/lint <path-to-md>`

- `<text-id>` — lints `$WORK/segmented.md` if it exists,
  else `texts/<text-id>/annotated.md`.
- `<path-to-md>` — lints that file directly.

Read `language` from `texts/<text-id>/status.json` (or the file's
frontmatter, or detect by Unicode block as in `annotate-root-text`'s
Intake) — it decides which language-specific checks run.

**This skill never modifies the target file.** Every check below runs in
report-only mode. Fix actions (last section) require the human to see the
report first and explicitly confirm.

---

## Checks

Run every check whose precondition holds, collect all results, then report
once at the end — do not stop at the first failure.

### 1. Block IDs, verse IDs, headings — all languages

Mechanical scan (Grep/Read, patterns from `docs/reference/conventions.md`):

- [ ] Every content block (stanza/paragraph) ends with a `^…` block ID.
- [ ] Every heading line's block ID ends in `-0` (`^1-0`, `^1-2-0`).
- [ ] No `^TOC-N` anchors anywhere (deprecated — parses with no usable TOC).
- [ ] Heading levels never skip (`#` → `##` → `###`, never `#` → `###`);
      no `####`.
- [ ] Within each chapter, verse IDs (`^chapter-verse`) are sequential —
      no gaps, no duplicates. (For Sanskrit, skip this — check 2 owns it.)
- [ ] No null bytes, page markers, or leftover OCR artifacts.

### 2. Sanskrit zone/ID audit — `sa` only

```bash
python3 skills/format-sanskrit-root-text/scripts/apply.py audit <file>
```

The existing tested auditor: reports zone assignment
(`^T-n`/`^I-n`/`^N-V`/back-matter), gaps, and `[needs LLM judgment]`
blocks. A clean file reports none of either.

### 3. Verse-line structure (merged half-lines) — `bo` only

```bash
python3 skills/lint-annotations/scripts/fix_midverse.py --input <file> --check
```

Detects the two tested patterns of wrongly-merged verse lines (mid-verse
single-shad break; embedded shad-pair mid-line) — i.e. stanzas whose
line-per-verse structure is wrong. `--check` prints every offending line
and writes nothing; exit 1 means findings.

**Known benign candidates** (observed on the vault's own final Tibetan
text — report them, but recommend dismissal rather than fixing):
opening-ornament lines (`༄༅། །` + title on one line) and chapter-colophon
terminals ending `…པའོ།། །` — both match the patterns but are legitimate
single lines. Genuine findings are *verse* lines with a shad break
mid-stanza. This is exactly why findings go to the human before any fix.

### 4. Stray footnote digits — any language, OCR/print-derived sources

```bash
python3 skills/lint-annotations/scripts/flag_footnote_numbers.py <file> \
    --outdir $WORK/
```

Flags digit runs glued to preceding text (flattened footnote markers like
`bliss,25 the`), deliberately ignoring block IDs, YAML frontmatter, heading
numbers, and space-preceded numbers. Writes a review TSV + human-readable
report to `work/`, and prints a sequence sanity-check (genuine footnotes
are contiguous). Writes nothing into the target file itself.

### 5. Frontmatter + segmentation refs — only if frontmatter exists

Only when the file already has YAML frontmatter (i.e. Step 5 of
`/annotate` is done — skip silently otherwise):

```bash
python3 tools/linter/lint_text_input.py <file> --offline --output-dir texts/<text-id>/payloads/
```

The Pipeline 2 linter, run early: required frontmatter fields, `lang_tag`
validity, and body block-reference integrity (`missing reference` errors).
Read `docs/06-lint.md` for interpreting its output. Note its one side
effect: it may patch `language`/`lang_tag`/`author` in the file's
frontmatter (documented "expected dirty state" in `CLAUDE.md`) — report
any patch it prints.

---

## Report

One summary at the end, per check: **pass** / **N issue(s)** with the
offending lines (line numbers + content), or **skipped** (with the reason —
wrong language, no frontmatter yet). If any check found issues, end with
which pipeline step owns each fix (`verse_ids` for ID problems, `segment`
for structure, `clean` for artifacts, `frontmatter` for YAML) — same
mapping as `annotate-root-text` Step 6.

---

## Fixes — only after the human reviews the report

Nothing in this skill auto-fixes. On explicit confirmation only:

- **Merged verse lines (bo):** re-run `fix_midverse.py` without `--check`
  (in place; block IDs preserved by the script).
- **Approved footnote digits:** the human edits the `approve` column in the
  flags TSV first, then:
  ```bash
  # preview
  python3 skills/lint-annotations/scripts/remove_footnote_numbers.py <file> <flags.tsv> --dry-run
  # apply (writes <file>.bak)
  python3 skills/lint-annotations/scripts/remove_footnote_numbers.py <file> <flags.tsv>
  ```
  Never run the remover on an unreviewed TSV — the flag → human review →
  remove sequence is the tested workflow, in that order.
- **ID/heading/frontmatter issues:** route back to the owning
  `annotate-root-text` step rather than patching ad hoc.

---

## Where this runs in the pipeline

- Standalone, any time, via `/lint`.
- Inside `/annotate`: Step 3's verification pass (bo/other) and Step 6's
  validate checklist reference the same checks — running `/lint` at
  checkpoint 1 or before checkpoint 2 is the mechanical version of those
  read-throughs.
- Before `/upload`: a clean `/lint` pass is a cheap pre-flight for
  Pipeline 2's own lint stage.

---

## Provenance

- `scripts/flag_footnote_numbers.py` and `scripts/remove_footnote_numbers.py`
  — **verbatim** from `bodhisattvacharyavatara-rails/4-SYSTEM/scripts/`
  (already argparse-based and path-clean; report-only / TSV-driven by
  design there too).
- `scripts/fix_midverse.py` — from the same vault dir; detection and
  splitting logic unchanged, hardcoded vault paths replaced with
  `--input`/`--output` and a `--check` (report-only) flag added.
- Check 2 wraps `skills/format-sanskrit-root-text/scripts/apply.py` (vault:
  `add-block-id-root-text/apply.py`, ported at ~97% identity).
- Check 5 wraps `tools/linter/` (vault: `4-SYSTEM/scripts/linter-root-text/`).
- Check 1's checklist is `annotate-root-text` Step 6's checklist +
  `docs/reference/conventions.md` — not new rules.

This SKILL.md itself is new (the vault had no single lint entry point —
these checkers were invoked by hand), but like the two pipeline
orchestrators it only sequences tested tools.
