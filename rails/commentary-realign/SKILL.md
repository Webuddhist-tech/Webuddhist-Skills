---
name: commentary-realign
description: >
  Make a copy of a commentary that is aligned to one root text, re-aligned to a
  second root text that contains the same root passages (possibly several
  times), by carrying the existing alignment across: every transcluded root
  block is matched to all of its occurrences in the new root, the copy's
  transclusions are re-pointed there, its frontmatter is re-pointed and cleared
  of the old live ids and given a new unique title, the result is verified
  against the old alignment, and the old file is deleted. Translations of the
  commentary stay translations *of the commentary*: they are re-pointed at the
  re-aligned copy (block for block), never aligned to the root directly, and
  reach the root only through it. Dry-run by default.

  Trigger this skill when the user says: "align this commentary to the other
  root", "migrate the alignment to the ritual text", "re-align the commentary to
  a new root text", "the root passage appears three times — point the
  commentary at all of them", "re-upload the commentary as a commentary of
  another root", "re-point the English and Chinese translations of the
  commentary to the new copy".
profile: rails-vault
supersedes:
  - Dzongsar-dolma-bumtsok-rails/3-SKILLS/commentary-realign/SKILL.md
---

# commentary-realign

The library lets a commentary be aligned to **one** root text only. When the same root passage also lives inside a second root text — for example a praise recited three times inside a longer ritual text — the commentary has to be uploaded again as a new commentary of the second root. This skill builds that copy from the alignment the commentary already has, instead of re-aligning it by hand.

Correct output is a copy that differs from the original **only** in its transclusion lines and its frontmatter; whose alignment (as `parser-commentary` reads it) is exactly the old alignment carried through the block map; in which every commentary block that pointed at a repeated root passage now points at every occurrence of it; and that carries no live id of the original, so `commentary-upload` creates a new text instead of touching the old one.

---

## Inputs

| Input | Description | Required |
|---|---|---|
| **Commentary** | A `$COMMENTARIES/` file with `file_type: commentary`, `root_text:` set, and its root passages transcluded (`![[<root>#^ref]]`) | yes |
| **New root** | The root text to align to, in `$SOURCE_TEXTS/`, with block IDs; it should carry `text_id` (uploaded) so `commentary_of` can be set | yes |
| **New title** | A title for the copy that is not already a title or alt title of any text in the same language on the library (titles are unique per language; the original keeps its titles) | yes, for `--write` |
| **Translations** | Optional: translations of the commentary (`file_type: translation`, `root_text:` = the commentary) with the same block IDs, each block transcluding its source block (`![[<commentary>#^X]]`), e.g. machine translations in `$TRANSFORMATIONS/Translations/`. Each needs its own new unique title | no |
| **parser-commentary** | The scripts import the commentary parser to read alignments. It ships with `commentary-upload` (`$SKILLS/commentary-upload/scripts/parser-commentary/`), so install that skill too; a vault copy under `$SYSTEM/scripts/` is used first if present | yes |
| **Overrides** | Optional JSON `{"<old ref>": ["<new ref>", …]}` replacing the automatic matches for those refs (`[]` = leave unaligned) | no |

If the new title is not given, stop and ask for it. Do not invent one without the human's approval.

## Output

| Path | What |
|---|---|
| `$COMMENTARIES/<old stem>-<new root name>.md` (or `--out`) | The re-aligned copy |
| `$WORK/commentary-realign/<old stem>.mapping.json` | The block map with scores, for review and for building overrides |
| the old commentary file | Deleted after verification passes (`--delete-old`) |
| `<translation folder>/<new commentary stem>-<lang>.md` | For each translation: a copy re-pointed at the re-aligned commentary; the old translation file is deleted after the checks pass |

---

## Output file format

Body: identical to the original except each transclusion of the old root:

```markdown
![[$SOURCE_TEXTS/<old-root>.md#^1-1]]
```

becomes one line per occurrence in the new root, written as one group so the parser aligns the commentary blocks beneath it to all of them:

```markdown
![[$SOURCE_TEXTS/<new-root>.md#^1-64]]

![[$SOURCE_TEXTS/<new-root>.md#^1-98]]

![[$SOURCE_TEXTS/<new-root>.md#^1-132]]
```

A root block with **no** counterpart in the new root keeps its transclusion of the old root. `parser-commentary` reads a transclusion of any file other than `root_text` as a scope break with no target, so the commentary on it is left unaligned rather than paired with a same-numbered block of the new root.

Frontmatter, changes only:

```yaml
title: <new unique title>
root_text: $SOURCE_TEXTS/<new-root>.md
commentary_of: <new root text_id>
covers_verses: <first target>–<last target>
source_description: "<original> Re-aligned copy for <new root>: … The original remains live as a commentary of <old root> (text <old text_id>)."
realigned_from: $COMMENTARIES/<old file>.md
realigned_from_text_id: <old text_id>
realigned_from_edition_id: <old edition_id>
realigned_from_root_text: $SOURCE_TEXTS/<old-root>.md
# removed: text_id, edition_id, toc_id, aligned_to_edition_id, alt_titles
```

A **translation** copy stays a translation of the commentary. Its body keeps one transclusion per block, re-pointed from the old commentary to the re-aligned copy (`![[<old commentary>#^X]]` → `![[<re-aligned commentary>#^X]]`); it gets **no** root transclusions. `translation-upload` aligns it to the re-aligned commentary by identity (block `^X` ↔ block `^X`), so it reaches the new root only through the commentary. Frontmatter, changes only:

```yaml
title: <new unique title>
root_text: $COMMENTARIES/<re-aligned commentary>.md   # the commentary, not the root
title_original: <the re-aligned commentary's title>              # only if the key exists
realigned_from: <old translation path>
realigned_from_text_id: <old text_id>
realigned_from_edition_id: <old edition_id>
realigned_from_translation_of: <old commentary text_id>
# removed: text_id, edition_id, toc_id, aligned_to_edition_id, translation_of, translation_of_text_id, translation_of_edition_id, alt_titles
```

`file_type` stays `translation`. `translation_of` is not set by hand: the translation linter fills it from the re-aligned commentary's `text_id`, so **the commentary must be uploaded before its translations**.

`alt_titles` are dropped because the original already claims them on the library (titles and alt titles are unique per language, and a claimed alt title cannot be removed); pass `--keep-alt-titles` only for alt titles that are new.

---

## Rules

1. **Dry run first, always.** Read the block map before writing. Every ref must have the expected number of targets (a passage the new root repeats N times has N targets; one it contains once has 1). A `⚠ close call` (accepted score within 0.15 of the best rejected block) or an unexpected count must be settled with an `--map` override, never by lowering the threshold blindly.
2. **Only transclusion lines and frontmatter change.** The script verifies this and refuses to delete the old file if anything else differs. Never hand-edit the commentary text in this skill.
3. **The copy's alignment must equal the old alignment mapped through the block map.** Verified with `parser-commentary` on both files; a mismatch stops the run.
4. **Never carry live ids over.** `text_id`, `edition_id`, `toc_id`, `aligned_to_edition_id` belong to the original's live text; the copy gets its own from `commentary-upload`.
5. **Never reuse a title.** The new title must differ from the original's title and alt titles.
6. **The original on the library is untouched.** This skill deletes the old *file* only; the live text stays a commentary of the old root. Deleting anything on the library is not part of this skill.
7. **Uploading is a separate step.** Run `commentary-upload` on the copy (dry run, then `--execute` only after explicit human confirmation).
8. **Translations are translations of the commentary, never commentaries of the root.** `repoint_translation.py` keeps `file_type: translation`, points `root_text` at the re-aligned commentary, and adds no root transclusions. The translation's block IDs must equal the commentary's content block IDs one for one (identity alignment), or it stops.
9. **Upload order: root → commentary → translations.** The translations' `translation_of` and their identity check against the live commentary segmentation need the commentary's `text_id` and `edition_id`; `upload_translation.py` refuses to run before they exist.
10. **Report stale links.** After `--delete-old` each script lists the files that still link to the deleted file; re-point them or tell the human.

---

## Procedure

1. **Dry run** from the vault root:
   ```bash
   python3 $SKILL/scripts/realign_commentary.py "<commentary.md>" --new-root "<new-root.md>" --title "<new title>"
   ```
   Read the table: old ref, number of targets, targets with scores, best rejected block. Check the counts against the structure of the new root.
2. **Settle any doubt** by writing overrides to a JSON file (start from `$WORK/commentary-realign/<stem>.mapping.json`) and re-running with `--map <file>`.
3. **Confirm the new title** with the human if they have not given it.
4. **Write and verify**:
   ```bash
   python3 $SKILL/scripts/realign_commentary.py "<commentary.md>" --new-root "<new-root.md>" --title "<new title>" --write --delete-old
   ```
   The script writes the copy, checks that only transclusion lines changed and that the alignment is the mapped old alignment, and only then deletes the old file. It prints the files that still name the old file.
5. **Re-point each translation** of the commentary (dry run, then write):
   ```bash
   python3 $SKILL/scripts/repoint_translation.py "<translation.md>" --source "<re-aligned commentary.md>" --title "<new title>"
   python3 $SKILL/scripts/repoint_translation.py "<translation.md>" --source "<re-aligned commentary.md>" --title "<new title>" --write --delete-old
   ```
   The dry run must print `OK`: block IDs identical to the commentary, every block transcluding its commentary block, only transclusion lines changing.
6. **Prepare the payloads.** Commentary: `commentary-upload` dry run (lint clean, `commentary_of` = the new root's `text_id`, the expected pair count, no duplicate). Translations: until the commentary is live, run the `translation-upload` linter and parser directly (`$SKILLS/translation-upload/scripts/linter-root-text/lint_text_input.py`, then `parser-root-text/parser.py <file> <lint.json>`) and check the edition's references equal the commentary edition's references and the alignment is identity; `translation_of` is empty until the commentary has a `text_id`. After the commentary is uploaded, run the full `translation-upload` dry run for each translation.
7. **Report** to the human: the block map summary, pair counts old → new, commentary blocks left unaligned, the files that still name the old file, and the upload dry run. Upload only on an explicit yes.

---

## Completion check

- [ ] Dry run read: every old ref has the expected number of targets; no unexplained close call or unmapped ref
- [ ] New title confirmed and distinct from the original's title and alt titles
- [ ] Copy written; verification `OK` (only transclusion lines changed; alignment = mapped old alignment)
- [ ] Copy frontmatter: new `root_text`, `commentary_of`, `covers_verses`; no `text_id`/`edition_id`/`toc_id`/`aligned_to_edition_id`; `realigned_from*` recorded
- [ ] Old file deleted only after verification passed
- [ ] Files still naming the old file reported to the human
- [ ] Each translation re-pointed with `repoint_translation.py`: checks `OK`, still `file_type: translation`, `root_text` = the re-aligned commentary, new unique title, old file deleted
- [ ] Commentary payload: `commentary-upload` dry run passes
- [ ] Translation payloads: references equal the commentary edition's, identity alignment; full `translation-upload` dry run after the commentary is live
