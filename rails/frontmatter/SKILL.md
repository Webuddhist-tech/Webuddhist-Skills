---
name: frontmatter
description: >
  Populate the complete YAML frontmatter for any text file in the collection —
  root text, commentary, translation, or reference — by extracting the metadata from
  the file's own title, colophon, and opening lines and writing the block that matches
  that file type's schema.

  Trigger on "add the frontmatter", "fill in the properties", "write the YAML for this
  file", "set the file_type", "this file is missing its metadata", or whenever a newly
  ingested file has no frontmatter block.

  Four file types, four schemas, one procedure. Never invent an external ID.
profile: any
supersedes:
  - webuddhist-library-data-pipeline/skills/root-text-frontmatter/SKILL.md
  - data-pipeline/skills/root-text-frontmatter/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/root-text-frontmatter/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/root-text-frontmatter/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/commentary-frontmatter/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/commentary-frontmatter/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/translation-frontmatter/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/translation-frontmatter/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/reference-frontmatter/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/reference-frontmatter/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Write a file's YAML frontmatter

Pick the variant by the file's `file_type`:

| `file_type` | Lives in | Variant |
|---|---|---|
| `root-text` | `$SOURCE_TEXTS/` | 1 |
| `commentary` | `$COMMENTARIES/` | 2 |
| `translation` | `$TRANSLATIONS/` | 3 |
| `reference` | `$REFERENCES/` | 4 |

**Rules that hold for all four.**

1. **Read the ends, not the middle.** Title and opening lines at the top; publication,
   author, and translator details in the colophon at the very end. Reading the body
   wastes context and does not improve the result.
2. **Never invent an external ID.** `bdrc_work_id`, `dsbc_url` and friends go in only
   when the value is visible in the file itself. A plausible-looking ID that is wrong
   is worse than an absent one, because nothing downstream will question it.
3. **Edit only the YAML block.** Insert or replace the frontmatter at the top of the
   file. Never rewrite the document to add metadata.
4. **Omit what you do not know.** An empty or absent field is a truthful signal that
   someone still needs to supply it; a guess is not.

Where a field's controlled vocabulary lives (language tags, `verse_id_format` values,
the full schema per type) depends on the repo — see `rails/PROFILES.md`. In a Rails
vault it is `$SOURCES/About Sources.md`; in the library pipeline it is
`docs/reference/frontmatter-schema.md`.

---

## Variant 1 — Root text

The fullest schema — verse ID format, chapter and verse counts, source description, external IDs.

This skill populates the standard YAML frontmatter for a root text file
(`file_type: root-text`) under `texts/<text-id>/`. It extracts all available
metadata from the file's title, colophon, and opening lines, then writes the
complete frontmatter block according to the spec in
`docs/reference/frontmatter-schema.md`.

### Instructions

When asked to add or generate frontmatter for a root text file:

1. **Read the file.** Use the Read tool on the target file. Focus on the title line, the opening verse or prose, and the colophon (publication information found at the beginning or end).
2. **Determine the language and script.** Identify the primary language (Sanskrit, Tibetan, Chinese, Pāli, etc.) and the script in use (Devanāgarī, Unicode Tibetan, etc.). Assign the correct `lang_tag`.
3. **Extract all available fields** (see template below). Only include external ID fields (`bdrc_work_id`, `dsbc_url`, etc.) when the values are known from the file itself — never invent them.
4. **Determine `verse_id_format`.** Inspect the file structure:
   - If verses are numbered by chapter and verse → `chapter-verse`
   - If verses carry a single sequential number → `verse`
   - If the text has books, chapters, and verses → `book-chapter-verse`
5. **Count or estimate** `chapters` and `total_verses` if the file makes them clear. Leave empty if uncertain.
6. **Populate `related_commentaries` and `related_translations`** only if corresponding files already exist in this repo. Out of scope for most runs — this pipeline currently handles root texts in isolation; leave these fields out unless a related file genuinely exists under `texts/`.
7. **Write the frontmatter** using the Edit tool to insert or replace the YAML block at the top of the file.

### Frontmatter Template

See `docs/reference/frontmatter-schema.md` for the authoritative, required-vs-optional
breakdown (this template is a superset useful during extraction; not every
field is required — check the schema doc before treating a missing field as
an error):

```yaml
---
title:                        # exact title as it appears in the file (diacritics OK)
author:                       # original author name (diacritics OK)
date:                         # date or century of composition, e.g. "8th century CE"
language:                     # full language name, e.g. Sanskrit / Tibetan / Chinese
script:                       # script name, e.g. Devanāgarī / Unicode Tibetan
file_type: root-text
lang_tag:                     # e.g. sa / bo / zh / pi
chapters:                     # integer — omit if unknown
total_verses:                 # integer — omit if unknown
verse_id_format:              # chapter-verse | verse | book-chapter-verse
source_description:           # REQUIRED — e.g. "Transcribed from Vaidya 1960 critical edition"
source_url:                   # URL if sourced digitally — leave blank if none
dsbc_url:                     # DSBC entry URL — omit if not applicable
bdrc_work_id:                 # e.g. WA1KG13126 — omit if unknown
bdrc_instance_id:             # omit if unknown
gretil_url:                   # GRETIL URL — omit if not applicable
cbeta_id:                     # Chinese Buddhist canon — omit if not applicable
suttacentral_id:              # Pāli texts — omit if not applicable
acip_id:                      # Tibetan ACIP — omit if not applicable
other_ids:                    # VIAF, Wikidata, etc. — omit if none
related_commentaries:         # list of paths — omit if none yet
related_translations:         # list of paths — omit if none yet
---
```

### Example Output

```yaml
---
title: Bodhicaryāvatāra
author: Śāntideva
date: 8th century CE
language: Sanskrit
script: Devanāgarī
file_type: root-text
lang_tag: sa
chapters: 10
total_verses: 913
verse_id_format: chapter-verse
source_description: "Transcribed from Vaidya 1960 critical edition"
source_url: https://www.dsbcproject.org/canon-text/content/71
dsbc_url: https://www.dsbcproject.org/canon-text/content/71
bdrc_work_id: WA1KG13126
---
```

### Rules & Edge Cases

- **`source_description` is required.** Every root text file must have it. If no publication data is visible, use a minimal description such as `"Source unknown — to be verified"`.
- **Do not hallucinate external IDs.** If a BDRC, GRETIL, DSBC, or other ID is not visible in the file, omit that field entirely.
- **One script per file.** If the file contains an alternative script (e.g., IAST alongside Devanāgarī), note the discrepancy with `[Ed: ...]` — do not add a second script tag.
- **`lang_tag` defaults**: Sanskrit → `sa`, Tibetan → `bo`, Chinese → `zh`, Pāli → `pi`. For editions in alternative scripts append the suffix (e.g., `sa-iast`). Confirm against `docs/reference/frontmatter-schema.md`.
- **Omit empty optional fields.** Do not leave placeholder values like `null` or `""` for optional fields. Either populate them or remove the key entirely.
- **`related_commentaries` / `related_translations`** — list only files that already exist. Do not pre-populate with anticipated future files.

---

### Provenance

Adapted from `bodhisattvacharyavatara-rails/4-SYSTEM/Skills/root-text-frontmatter/SKILL.md`.
The reference to `$SYSTEM/docs/source-formatting.md § 4` is replaced with
`docs/reference/frontmatter-schema.md`, this repo's authoritative frontmatter
spec.

---

## Variant 2 — Commentary

Adds the commentary's relationship to its root text — which work it comments on, and in which tradition.

This skill populates the standard YAML frontmatter for a commentary file (`file_type: commentary`) in `$COMMENTARIES/`. It extracts all available metadata from the file's title, colophon, and opening content, then writes the complete frontmatter block according to the spec in `$SOURCES/About Sources.md` §4.

### Instructions

When asked to add or generate frontmatter for a commentary file:

1. **Read the file.** Read the target file, focusing on the title line, author credits, colophon, and opening lines. Do not read the entire body.
2. **Identify the language and script.** Determine the primary language of the commentary (which may differ from the root text) and its script. Assign the correct `lang_tag` from §12 of `$SOURCES/About Sources.md`.
3. **Assign a `registered_id`.** This is the short, stable identifier used in `$RAILS/` to attribute claims to this commentary. Derive it from the author's surname in lowercase, romanised without diacritics. Once set it must never change. Check the vault annex (`$SYSTEM/Guidelines/vault-annex.md` §Commentaries) to confirm the ID is not already taken.
4. **Identify the root text.** Record the vault path of the root text this commentary addresses under `root_text`.
5. **Determine `verse_id_format`.** This field declares the commentary's *own* internal numbering system — not the root text's. Inspect how the commentary structures its own divisions:
   - Chapter + verse → `chapter-verse`
   - Section + paragraph → `section-paragraph`
   - Single sequential verse/passage number → `verse`
   - Folio + line → `folio-line`
   - Book + chapter + verse → `book-chapter-verse`
   If the commentary has no internal numbering, use `verse` and apply sequential numbering.
6. **Record `covers_verses`** — the range of root text verses this commentary addresses, in block-ID format (e.g., `1-1–10-58`). Omit if the range is unclear.
7. **Add external IDs** (BDRC, GRETIL, etc.) only when they are visible in the file itself.
8. **Write the frontmatter** by inserting or replacing the YAML block at the top of the file.

### Frontmatter Template

```yaml
---
title:                        # exact title of the commentary (diacritics OK)
author:                       # commentary author (diacritics OK)
author_in_use:                # name form used for this author inside article prose (respectful/honorific, e.g. རྒྱལ་བ་དགེ་འདུན་གྲུབ་) — HUMAN-supplied only; omit, never invent
date:                         # date or century of composition, e.g. "11th century CE"
language:                     # language of the commentary, e.g. Sanskrit / Tibetan / English
script:                       # script name — omit for roman-script languages
file_type: commentary
lang_tag:                     # ISO tag from §12, e.g. sk / bo / en
verse_id_format:              # the commentary's own ID system (see §9 of About Sources.md)
registered_id:                # short stable ID used in $RAILS/ — lowercase, no diacritics
root_text:                    # vault path to the root text, e.g. $SOURCE_TEXTS/[lang]-root-text.md
covers_verses:                # root text verse range, e.g. 1-1–10-58 — omit if unknown
source_description:           # REQUIRED — e.g. "Transcribed from [editor year] edition"
source_url:                   # URL if sourced digitally — leave blank if none
bdrc_work_id:                 # omit if unknown
bdrc_instance_id:             # omit if unknown
gretil_url:                   # GRETIL URL — omit if not applicable
dsbc_url:                     # DSBC URL — omit if not applicable
cbeta_id:                     # Chinese Buddhist canon — omit if not applicable
acip_id:                      # Tibetan ACIP — omit if not applicable
other_ids:                    # VIAF, Wikidata, etc. — omit if none
---
```

### Example Output

```yaml
---
title: [Commentary title]
author: [Commentator]
date: [century or year]
language: [language]
script: [script — omit for roman-script languages]
file_type: commentary
lang_tag: [tag]
verse_id_format: chapter-verse
registered_id: [short-id]
root_text: $SOURCE_TEXTS/[lang]-root-text.md
covers_verses: 1-1–10-58
source_description: "Transcribed from [editor year] edition"
---
```

### Rules & Edge Cases

- **`source_description` is required.** Every commentary file must have it. If publication data is not visible, use `"Source unknown — to be verified"`.
- **`registered_id` must be unique and stable.** Check the vault annex (`$SYSTEM/Guidelines/vault-annex.md` §Commentaries) before assigning. Once a commentary is used in any `$RAILS/` file, the `registered_id` must never change. After writing the frontmatter, remind the user to register the new ID in the vault annex.
- **`verse_id_format` is the commentary's own system, not the root text's.** A Tibetan commentary may use `folio-line` even though a Sanskrit root text uses `chapter-verse`. Both coexist — root text transclusions in the commentary body carry the root text's block IDs, while the commentary's own passages carry its own IDs.
- **`script` field** — include for non-roman scripts (Devanāgarī, Unicode Tibetan, etc.). Omit for languages written in the Latin alphabet.
- **`author_in_use` is human-authored — the LLM never writes its value.** (Added 2026-08-18.) This key holds the respectful name form that downstream article prose uses when citing the author's view (`wiki-article-from-claims` Rule 17, "in-prose author names"; carried into claims files by `commentary-claims` (Strategy 1)). Which honorific to use is an editorial judgment: a human contributor adds and reviews the value. When generating frontmatter, omit the key entirely and note in your report that it awaits human entry. Never derive it from the colophon, tradition, or general knowledge.
- **Do not hallucinate external IDs.** If a BDRC, GRETIL, or other ID is not visible in the file, omit that field entirely.
- **Omit empty optional fields.** Either populate a field or remove the key entirely — no `null` or `""` placeholders.

---

## Variant 3 — Translation

Adds translator, target language, and the source edition the translation was made from.

This skill populates the standard YAML frontmatter for a translation file (`file_type: translation`) in `$TRANSLATIONS/`. It extracts all available metadata from the file's title, colophon, and opening content, then writes the complete frontmatter block according to the spec in `$SOURCES/About Sources.md` §4.

### Instructions

When asked to add or generate frontmatter for a translation file:

1. **Read the file.** Read the target file, focusing on the title page, translator credits, colophon, and opening lines. Do not read the entire body text.
2. **Identify the translator(s).** Record names in `Surname, Firstname` format, separated by semicolons if multiple. Use the name as it appears in the source.
3. **Identify the target language.** This is the language the text was translated *into*. Assign the correct `lang_tag` from §12 of `$SOURCES/About Sources.md`.
4. **Identify the root text.** Determine which root text this is a translation of and record its vault path under `root_text`. If the corresponding file does not yet exist, leave a descriptive placeholder string (e.g., `"$SOURCE_TEXTS/[lang]-root-text.md — to be created"`).
5. **Determine `verse_id_format`.** Block IDs in a translation correspond to the *source* verse numbering, not the translator's own numbering. Inspect the root text or notes to confirm the format (`chapter-verse`, `verse`, or `book-chapter-verse`).
6. **Record `translation_basis`.** Note the edition or manuscript the translator worked from, as stated in the preface or colophon.
7. **Record `covers_verses`** if the translation covers a known range (e.g., `1-1–10-58`). Omit if unclear.
8. **Write the frontmatter** by inserting or replacing the YAML block at the top of the file.

### Frontmatter Template

```yaml
---
title:                        # title of the translation as it appears in the file
translator:                   # Surname, Firstname; Surname, Firstname (semicolon-separated)
date:                         # publication year or decade, e.g. 1995
language:                     # target language, e.g. English / French / German
file_type: translation
lang_tag:                     # ISO tag from §12, e.g. en / fr / de
verse_id_format:              # chapter-verse | verse | book-chapter-verse
root_text:                    # vault path to the root text, e.g. $SOURCE_TEXTS/[lang]-root-text.md
translation_basis:            # edition the translator worked from, e.g. "[editor year] edition"
covers_verses:                # verse range in block-ID format, e.g. 1-1–10-58 — omit if unknown
source_description:           # REQUIRED — e.g. "[publisher year] first edition"
source_url:                   # URL if sourced digitally — leave blank if none
---
```

### Example Output

```yaml
---
title: [Translation title]
translator: [Surname, Firstname; Surname, Firstname]
date: [year]
language: [target language]
file_type: translation
lang_tag: [tag]
verse_id_format: chapter-verse
root_text: $SOURCE_TEXTS/[lang]-root-text.md
translation_basis: [editor year] edition
covers_verses: 1-1–10-58
source_description: "[publisher year] first edition"
source_url:
---
```

### Rules & Edge Cases

- **`source_description` is required.** Every translation file must have it. If publication data is not visible, use `"Source unknown — to be verified"`.
- **Block IDs follow the source verse, not the translator's numbering.** If the translator uses a different verse numbering system, note this with `[Ed: ...]` in the file body — the `verse_id_format` field always refers to the root text's structure.
- **`translator` not `author`.** Translations use the `translator` field. The original author is identified via the `root_text` link.
- **`lang_tag` is the *target* language.** For an English translation, `lang_tag: en`. The source language is implicit in the `root_text` link.
- **Do not hallucinate fields.** If `translation_basis`, `covers_verses`, or `source_url` cannot be confirmed from the file, omit those fields rather than guessing.
- **Omit empty optional fields.** Either populate a field or remove the key entirely.
- **Multiple translators** — list all on a single line, semicolon-separated, as they appear in the publication.

---

## Variant 4 — Reference

Secondary literature — modern scholarship, dictionaries, study aids.

This skill populates the standard YAML frontmatter for a secondary literature or reference file (`file_type: secondary-literature`) in `$REFERENCES/`. It extracts all available metadata from the file's title page, colophon, and opening content, then writes the complete frontmatter block according to the spec in `$SOURCES/About Sources.md` §4.

### Instructions

When asked to add or generate frontmatter for a reference or secondary literature file:

1. **Read the file.** Read the target file, focusing on the title page, author credits, colophon, table of contents, and any abstract or introduction. Do not read the entire body.
2. **Identify the author(s).** Record names in `Surname, Firstname` format. Use the name as it appears in the publication. If multiple authors, separate them with semicolons.
3. **Identify the language.** This is the language the work is written *in* (usually English for modern scholarship). Assign the correct `lang_tag` from §12 of `$SOURCES/About Sources.md`.
4. **Identify the primary root text** the work relates to, if applicable, and record its vault path under `root_text`. If the work spans multiple texts or is not focused on a specific text, omit this field.
5. **Extract `topics`.** List the main subjects the work addresses — chapter references, doctrinal topics, textual traditions — as a YAML list. Draw from the table of contents or abstract.
6. **Record the `source_description`.** Include publisher, year, and edition as they appear in the colophon or title page.
7. **Record `source_url`** if the work was sourced digitally (DOI, stable URL, etc.).
8. **Write the frontmatter** by inserting or replacing the YAML block at the top of the file.

### Frontmatter Template

```yaml
---
title:                        # exact title of the work (diacritics OK, use quotes if needed)
author:                       # Surname, Firstname; Surname, Firstname (semicolon-separated)
date:                         # publication year, e.g. 2017
language:                     # language the work is written in, e.g. English
file_type: secondary-literature
lang_tag:                     # ISO tag from §12, e.g. en / fr / de
root_text:                    # vault path to the primary root text — omit if not applicable
topics:                       # list of subjects covered, e.g. [chapter 6, patience]
source_description:           # REQUIRED — e.g. "[publisher year]"
source_url:                   # URL or DOI if sourced digitally — leave blank if none
---
```

### Example Output

```yaml
---
title: "[Work title]"
author: [Surname, Firstname]
date: [year]
language: English
file_type: secondary-literature
lang_tag: en
root_text: $SOURCE_TEXTS/[lang]-root-text.md
topics: [chapter 6, patience]
source_description: "[publisher year]"
source_url: [doi or url — omit if none]
---
```

### Rules & Edge Cases

- **`source_description` is required.** Every reference file must have it. If publication data is not visible, use `"Source unknown — to be verified"`.
- **Titles with special characters** — wrap the `title` value in double quotes if it contains colons, non-roman script, or other YAML-special characters.
- **`root_text` is optional.** Reference works that cover broad topics or multiple texts need not link to a single root text. Omit the field rather than leaving it blank.
- **`topics` should be concise and useful.** Draw entries from the work's own table of contents, chapter titles, or keywords. Use lowercase, natural-language terms. Aim for 3–8 entries.
- **`author` not `translator`.** Secondary literature always uses `author`. If a work is both an edition and a study, still use `author`.
- **`lang_tag` is the language the secondary work is *written in***, not the language of the primary source it studies. A French article on Sanskrit texts gets `lang_tag: fr`.
- **Do not hallucinate DOIs or URLs.** If a stable URL or DOI is not visible in the file, leave `source_url` blank.
- **Omit empty optional fields.** Either populate a field or remove the key entirely.
- **Dictionaries and reference tools** also use `file_type: secondary-literature`. For these, `topics` may list the languages or domains covered (e.g., `[Sanskrit lexicon, Tibetan lexicon]`).

---

## After this skill

`vault-audit` checks frontmatter completeness across the collection and will report
files still missing required fields. In the library pipeline, the linter patches
`language` / `lang_tag` / `author` / `bdrc_work_id` in place on every run — expect
the source file to show as modified afterwards (`rails/PROFILES.md`).
