---
name: raw-to-sources
description: Bring one raw OCR/segmentation text file into 1-SOURCES/ as a cleaned, frontmattered root-text or commentary file — the first step of the ingest chain, before any segmentation, TOC, or block IDs.
profile: rails-vault
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/raw-to-sources/SKILL.md
---

# raw-to-sources

This is the missing first rung of the ingest chain: a raw `.txt`/`.docx.txt` export (OCR output, or a human transcriber's rough line-numbered segmentation) has no home in `$SOURCES/` until it is cleaned and frontmattered. This skill is a thin orchestrator — it does not reimplement cleaning or frontmatter extraction, both of which already exist as skills; it sequences them and places the result. What "correct output" looks like: a file at `$SOURCE_TEXTS/<title>.md` or `$COMMENTARIES/<title>.md`, OCR debris stripped, frontmatter complete for every field that is mechanically derivable or already known — but **still unsegmented and un-block-ID'd**. Segmentation, TOC extraction, transclusion, and block IDs are later, separate skills; conflating them here would make failures in this skill hard to isolate from failures in those.

---

## Inputs

| Input | Description | Format |
|---|---|---|
| **Raw file** | One raw text export. | Path under `$WORK/raw-data/…` or similar — a `.txt` or `.docx.txt` file. |
| **`--type`** | `root` or `commentary`. Required — never inferred from content. If omitted, stop and ask. | `root` \| `commentary` |
| **Known metadata** *(optional)* | Title, author, tradition/school already resolved from a curated catalog (e.g. a `.xlsx` དཀར་ཆག shipped alongside the raw files). When present, this is authoritative — prefer it over a colophon guess. | title / author / tradition strings |
| **Root text path** *(commentary only, optional)* | The vault-relative path to the already-ingested root text, for the `root_text:` frontmatter field. If the root has not been ingested yet, leave blank — do not block on it. | `$SOURCE_TEXTS/<file>.md` |

## Output

One file:

```
$SOURCE_TEXTS/<title>.md            if --type root
$COMMENTARIES/<title>.md    if --type commentary
```

`<title>` is the raw file's own Tibetan title, with the raw file's ID prefix (e.g. `R1B1817B6`) and transcription-process suffix (`Segmentation`, `- corrected`, `.docx`) stripped — those belong in frontmatter (`book_id`), not the filename.

---

## Output file format

```yaml
---
title: "<Tibetan title, verbatim>"
title_in_english: "<English gloss, if confidently known — else omit the field rather than guess>"
author: "<Tibetan author name, verbatim — from known metadata if supplied, else from colophon>"
file_type: root-text | commentary
language: Tibetan
script: Unicode Tibetan
lang_tag: bo
source_description: "Raw OCR/segmentation export received into <raw file's 0-INBOX path>; <catalog reference if one exists>."
book_id: "<raw filename's hex ID prefix, e.g. R1B1817B6 — omit the field if the raw filename has none>"
status: 0-raw
# commentary only, from commentary-frontmatter:
registered_id: <short id, assigned by commentary-frontmatter>
root_text: <path, if known — else omit>
covers_verses:        # left blank — manual review
# left blank on every file — manual review, not guessed here:
bdrc_work_id:
school:
copyright:
---

<cleaned body — OCR debris stripped, original line/verse numbering preserved as-is,
NOT yet resegmented into sense units, NOT yet block-ID'd>
```

---

## Rules

1. **Never overwrite an existing target file.** If `$SOURCE_TEXTS/<title>.md` or `$COMMENTARIES/<title>.md` already exists, stop and report the collision — do not silently pick a different filename or merge.
2. **Cleaning only, never interpretation.** The same no-loss invariant as `clean-raw-text`: strip page markers, running headers/footers, mid-word spaces, non-breaking tshegs — never reorder, reword, gloss, or "fix" the Tibetan.
3. **Frontmatter fields are either mechanically derivable or supplied — never guessed from parametric knowledge.** `book_id` comes from the raw filename's own hex prefix, when it has one. `title`/`author`/tradition come from supplied catalog metadata when given, otherwise from `frontmatter` (Variant 1)/`frontmatter` (Variant 2)'s own colophon-reading procedure — never from what the model "knows" about the text.
4. **`covers_verses`, `bdrc_work_id`, `school`, `copyright` stay blank.** These need judgment or an external lookup (`bdrc_fetch.py`) this skill does not perform. Leaving them blank is correct output, not incomplete output.
5. **`registered_id` is assigned by `frontmatter` (Variant 2), never invented here.** That skill already owns the uniqueness check against `vault-annex.md`.
6. **The body stays unsegmented and un-block-ID'd.** Do not run `segment-commentary` (Phase 2), `format-tibetan-root-text`, or any block-ID skill as part of this one — those are separate steps with their own verification.
7. **The raw source file is read-only.** Never edit or move anything under `$WORK/raw-data/`.
8. **`status: 0-raw` is this skill's exit marker.** Later steps update it; this skill only ever sets that one initial value.

---

## Procedure

1. **Resolve inputs.** Confirm the raw file path exists and `--type` is given. Stop and ask if either is missing.
2. **Clean.** Run `4-SYSTEM/Skills/clean-raw-text/SKILL.md`'s procedure on the raw file. Redirect its intermediate output to `$WORK/<slug>/cleaned.md` (a vault-appropriate scratch path — the skill's own documented `texts/<id>/work/cleaned.md` convention is generic and ported from a sibling repo; do not create a `texts/` tree in this vault).
3. **Derive the target filename.** Strip the raw filename's ID prefix and process-suffix (`Segmentation`, `- corrected`, `.docx`), keep the Tibetan title verbatim, append `.md`.
4. **Check for a collision** at `$SOURCE_TEXTS/<title>.md` or `$COMMENTARIES/<title>.md` per `--type`. Stop and report if the file already exists.
5. **Write the cleaned body** to that path — no frontmatter yet, just the cleaned text.
6. **Run the frontmatter skill** — `4-SYSTEM/Skills/root-text-frontmatter/SKILL.md` for `--type root`, `4-SYSTEM/Skills/commentary-frontmatter/SKILL.md` for `--type commentary` — on the newly placed file.
7. **Add the two fields those skills don't cover:** `book_id`/`openpecha_id` (raw filename's hex prefix, if present) and `status: 0-raw`.
8. **Reconcile with supplied catalog metadata, if any.** Where known-good title/author/tradition was given as an input, prefer it over what the frontmatter skill derived from the colophon, and note the catalog as the source in `source_description`.
9. **Report** the finished file's path and full frontmatter back to the human.

---

## Completion check

- [ ] Target file created at `$SOURCE_TEXTS/<title>.md` or `$COMMENTARIES/<title>.md`, no pre-existing collision
- [ ] Body is cleaned (OCR debris stripped) but **not** segmented and **not** block-ID'd
- [ ] Frontmatter populated via `frontmatter` (Variant 1)/`frontmatter` (Variant 2) (title, author, `file_type`, `language`, `lang_tag`, `source_description`, and `registered_id` for commentaries)
- [ ] `book_id`/`openpecha_id` (when derivable) and `status: 0-raw` added
- [ ] `covers_verses`, `bdrc_work_id`, `school`, `copyright` left blank, not fabricated
- [ ] Raw source file under `$WORK/raw-data/` unmodified
