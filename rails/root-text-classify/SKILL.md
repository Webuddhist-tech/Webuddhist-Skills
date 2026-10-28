---
name: root-text-classify
description: >
  Step 1 of root-text-pipeline: decide whether a Tibetan text from the root folder is a
  VERSE text, a PROSE text, MIXED (prose with verse passages) — or actually a COMMENTARY
  (it glosses another text), which must go to commentary-pipeline instead. Content first,
  title second: a commentary word in the title does not make a verse text a commentary.
  Use for "is this root text verse or prose?", "classify this text", "is this a
  commentary?". Deterministic, no model.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-classify

Measures the text and picks the form the rest of the root-text workflow uses.

---

## Inputs

| Input | Description |
|---|---|
| `source` | the text, e.g. `$SOURCE_TEXTS/<id>.md` or `$INBOX/root/<id>.md` |

## Output

One line on the console, and the exit code: `0` for verse, mixed and prose (the form is
picked again, the same way, by `root-text-segment`); `1` for a commentary.

## Output file format

```
<file>: <verse|mixed|prose|commentary>  (title: … · gloss markers N/1000 syl · metrical share P%)
  → <what to do next>
```

---

## Rules

1. **Content first.** Gloss markers (`ཞེས་པ་ནི`, `ཞེས་པ་སྟེ`, `ཞེས་བྱ་བ་ནི` …) per 1000
   syllables, and the **metrical share**: syllables in clauses of 5+ syllables that have the
   same count as a neighbouring clause.
2. **Commentary** if gloss ≥ 1.0 with metrical share < 60%, or gloss ≥ 3.0, or a commentary
   word in the title (`འགྲེལ`, `རྣམ་བཤད`, `ཊཱི་ཀཱ`, `དཀའ་འགྲེལ` …) with metrical share < 60%.
   A verse text with a commentary title (`…ཚད་མ་རྣམ་འགྲེལ།`, `བྱང་ཆུབ་སེམས་ཀྱི་འགྲེལ་པ།`)
   stays verse; one `ཞེས་པ་` in a short prayer does not make it a commentary.
3. **Verse** if metrical share ≥ 60%; **prose** below 30%; **mixed** between. Mixed and prose
   both take the prose form (paragraphs, with verse passages as stanzas).
4. A text in the root folder that classifies as a commentary: stop and ask the editor —
   do not process it with the root-text skills.

---

## Procedure

```bash
python $SKILLS/seg-toc-lib/root_text_build.py classify "<source>"
```

Report the class and the two measures. On `commentary`, stop and ask.

---

## Completion check

- [ ] Class reported with gloss markers and metrical share
- [ ] `commentary` → stopped and asked; otherwise the form noted for `root-text-segment`
