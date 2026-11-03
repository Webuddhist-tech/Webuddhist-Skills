---
name: yigchung-transfer
description: >
  Carry the <small>…</small> yigchung (small-script rubric) marks of a root
  text over to a block-aligned translation, so the translation marks the same
  rubrics the root does. Whole-block marks are applied mechanically; a block
  where only part of the root is small goes to a worklist with root and
  translation side by side, to be decided by meaning.

  Trigger this skill when a translation "doesn't have the small annotations",
  "bring the <small> marks over from the Tibetan", "mark the yigchung in the
  translation", "the rubrics are small in the root but not in the translation",
  "copy the small text markup to the Chinese".
profile: rails-vault
supersedes:
  - Dzongsar-dolma-bumtsok-rails/3-SKILLS/yigchung-transfer/SKILL.md
---

# yigchung-transfer

A yigchung — an instruction, colophon or rubric set in small type — is marked `<small>…</small>` in the root. The same passage is a rubric in every translation, and `yigchung-upload` can only publish what the translation file marks. This skill finds each root block that carries `<small>`, and marks the rendering of that small text in the translation block with the same id.

The block is certain — block ids align the files. What needs deciding is *which part* of the translated block renders the small text:

| Root block | Action |
|---|---|
| Every line small, one tag per line, translation has the same number of lines | each translated line wrapped — **applied** |
| Every line small, any other shape (one tag over the block, or line counts differ) | the whole translated block wrapped once — **applied**, with a note when the line counts differ |
| Only part of the block small | **worklist**: root and translation side by side; the matching translated words are marked by hand, by meaning |

---

## Inputs

| Input | Description | Required |
|---|---|---|
| **Root file** | The root text in `$SOURCE_TEXTS/` carrying the `<small>` marks | yes |
| **Translation file** | A translation in transclusion form, block-aligned to the root (`translation-alignment-check` passes). Convert an interleaved file with `bilingual-to-transclusion` first | yes |

## Output

- The translation file in `$TRANSLATIONS/`, with `<small>` marks added to the applied blocks (`--write`).
- `$WORK/yigchung-transfer-<translation stem>.md` — the worklist, written only when some root block is partly small.

---

## Output file format

A translated block after transfer, from a root block small throughout:

```markdown
![[$SOURCE_TEXTS/<root>.md#^1-19]]

<small>清淨之</small> ^1-19
```

and from a root block wrapped line by line:

```markdown
<small>三時導師及佛子，</small>
<small>發心事業殊勝尊，</small>
<small>佛母度母恭禮已，</small>
<small>說符合事、行修法。</small> ^1-2
```

The worklist:

```markdown
# Yigchung transfer worklist — <translation file>

## ^<id>

**Root**

    <root lines, with their <small> marks>

**Translation**

    <translated lines>
```

---

## Rules

1. **Only where the root has it.** A translated block is marked only when the root block with the same id carries `<small>`. `<small>` in the translation with none in the root is reported, never added to or removed.
2. **Tags only.** The translated words are never edited — only `<small>` and `</small>` are inserted, and never inside the block id.
3. **Partial blocks are decided by meaning, not position.** Mark the translated words that render exactly the root's small text — no more, no less. When the translation cannot be split that way (the small part is interwoven into a sentence), mark the smallest span that contains it and note it in the report.
4. **Blocks already marked are left alone** and counted; the check still compares them with the root.
5. **Dry run first**, then `--write`; finish with `--check`, which must say `consistent`.

---

## Procedure

1. Confirm the translation aligns: `translation-alignment-check --root <root> <translation>` ends `RESULT: OK`.
2. Dry run:
   ```bash
   python3 $SKILL/scripts/yigchung_transfer.py \
     --root "<root file>" --translation "<translation file>"
   ```
   Read the counts: to apply (line by line / as one block), already marked, partial, orphans, missing.
3. Apply the mechanical cases:
   ```bash
   python3 $SKILL/scripts/yigchung_transfer.py \
     --root "<root file>" --translation "<translation file>" --write
   ```
4. If a worklist was written, work through it: for each id, compare the root's small text with the translation and wrap the translated words that render it, directly in the translation file (Rule 3).
5. Check:
   ```bash
   python3 $SKILL/scripts/yigchung_transfer.py \
     --root "<root file>" --translation "<translation file>" --check
   ```
   It must print `consistent`.
6. Review: run `yigchung-upload` as a dry run (`--no-live` before the translation is uploaded) and read its review file next to the root's — every span on the same segment, each one rendering the root's rubric.

---

## Completion check

- [ ] Translation aligned to the root before transfer
- [ ] Mechanical cases applied; notes on line-count differences read
- [ ] Every worklist block marked by meaning (or none were partial)
- [ ] `--check` prints `consistent`
- [ ] `yigchung-upload` dry-run review: same segments as the root, spans render the rubrics
- [ ] No translated word edited — only tags added
