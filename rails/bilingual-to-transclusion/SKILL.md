---
name: bilingual-to-transclusion
description: >
  Convert a translation that carries the root text inline — root lines, a
  separator such as <br>, then the translation, block by block — into the
  vault's translation form: a transclusion of the root block above each
  translated block, the inline root copy removed. Every inline root block is
  checked against the root file first; one mismatch and nothing is written.

  Trigger this skill when a translation "has the Tibetan in it instead of
  transclusions", "convert this bilingual file to transclusions", "replace the
  root text with transclusions", "align this translation to the root", "the
  translator pasted the root text into the file".
profile: rails-vault
supersedes:
  - Dzongsar-dolma-bumtsok-rails/3-SKILLS/bilingual-to-transclusion/SKILL.md
---

# bilingual-to-transclusion

Translators often deliver a translation interleaved with its root: each block holds the root text, a separator, then the translation, ending in the root's block id. That shape duplicates the root, lets the copy drift from it unnoticed, and is not what the uploader or `translation-alignment-check` expect. This skill rewrites it into the form every translation in the vault uses — `![[<root>#^<id>]]`, a blank line, the translated block ending in the same id — so the translation is aligned to the root by block id and the root lives in one place only.

Correct output: the same block ids in the root's order; above each block a transclusion of the root block with that id; headings keep their level with only the translated title; the translated text unchanged apart from trailing whitespace; no root text left in the file.

---

## Inputs

| Input | Description | Required |
|---|---|---|
| **Root file** | The root text in `$SOURCE_TEXTS/` whose block ids the translation uses | yes |
| **Interleaved translation** | The translation file, each block `root part` + separator + `translation part` + ` ^<id>`. Headings take the same shape on one line: `## <root title><br><translated title> ^<id>` | yes |
| **Separator** | The string between the root and the translation in each block. Default `<br>` | if not `<br>` |

If the file's block ids are not the root's ids in the root's order, stop and report — that is a segmentation problem, not a conversion.

## Output

The translation file rewritten in place (`$TRANSLATIONS/<file>.md`), or the path given with `--out`. Existing frontmatter is kept unchanged. Frontmatter is not added here — use `frontmatter` for that.

---

## Output file format

```markdown
---
(frontmatter, unchanged)
---
![[$SOURCE_TEXTS/<root>.md#^0]]

# <translated title> ^0

![[$SOURCE_TEXTS/<root>.md#^I-0]]

## <translated heading> ^I-0

![[$SOURCE_TEXTS/<root>.md#^I-1]]

<translated line 1>
<translated line 2> ^I-1
```

The transclusion link uses the root's full vault path (a wiki link needs the resolved literal path — see `rails/PROFILES.md`). Pass `--link <stem>` only to match an existing sibling translation that uses the short form.

---

## Rules

1. **The root is the truth.** The inline root part of every block must equal the root file's block with the same id, compared without whitespace, `<small>` tags, heading marks and the id. Any mismatch aborts the whole run; fix the file, never the check.
2. **Ids are never changed.** The output has exactly the root's block ids in the root's order — no renumbering, no merging, no splitting.
3. **The translation text is not edited.** Only trailing whitespace (markdown hard-break spaces) and the leading space after the separator are removed. Wording, punctuation and line breaks stay as delivered.
4. **One separator per block.** A block with none or several is reported, not guessed at.
5. **Dry run first**, then `--write`. The dry run writes nothing.
6. **A transclusion line never takes a block id** (`rails/CONVENTIONS.md` §3: transclusion lines never consume a block ID).

---

## Procedure

1. Dry run:
   ```bash
   python3 $SKILL/scripts/bilingual_to_transclusion.py \
     --root "<root file>" --src "<interleaved file>"
   ```
   It must report every inline root block matching the root. If it lists errors, read them back with their ids and stop.
2. Preview: re-run with `--write --out <scratch path>` and read the first blocks and one heading.
3. Write in place:
   ```bash
   python3 $SKILL/scripts/bilingual_to_transclusion.py \
     --root "<root file>" --src "<interleaved file>" --write
   ```
4. Add frontmatter with the `frontmatter` skill (variant 3, translation) if the file has none — at least `file_type: translation`, `language`, `lang_tag`, and `root_text:` pointing at the root.
5. Verify with `translation-alignment-check`:
   ```bash
   python3 $SKILLS/translation-alignment-check/scripts/check_translation_alignment.py \
     --root "<root file>" "<translation file>"
   ```
   It must end `RESULT: OK`.
6. If the root carries `<small>` marks, run `yigchung-transfer` next.

---

## Completion check

- [ ] Dry run: every inline root block matched the root, no errors
- [ ] File written; no root-language text left outside transclusions
- [ ] Every block has a transclusion above it pointing at its own id
- [ ] Headings keep their level, translated title only
- [ ] Frontmatter present with `root_text:`
- [ ] `translation-alignment-check` reports `RESULT: OK` for this file
