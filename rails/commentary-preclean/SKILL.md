---
name: commentary-preclean
description: >
  Step 1 of commentary-pipeline (optional): strip earlier scaffolding from a Tibetan
  commentary — standalone OCR index numbers, outline numbers, block / verse IDs, heading
  markers, per-line breaks — back to continuous prose, so commentary-segment can re-derive
  the boundaries. The footnote apparatus and footnote markers [^n] are kept, the title line
  stays as `# title`, frontmatter is kept verbatim; no character of body text is removed
  (no-loss assertion). Use for "pre-clean this commentary", "strip the old IDs and line
  breaks". Skip for a file that is already plain running text.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/commentary-segmentation/SKILL.md
---

# commentary-preclean

Stage 0 of the commentary workflow, split out of the former `commentary-segmentation`.

---

## Inputs

| Input | Description |
|---|---|
| `source` | the commentary, `$COMMENTARIES/<file>.md` (OCR-clean — `format-commentary` first if not) |

## Output

| File | What |
|---|---|
| `$INBOX/<file>.preclean.md` | continuous prose, ready for `commentary-segment` |
| `$INBOX/<file>.preclean.tsv` | report (`--report`): what was removed, `heading-suspect` flags |

## Output file format

The source text as continuous runs: frontmatter verbatim, `# <title>`, body paragraphs
joined, footnote definitions `[^n]: …` unchanged at the end.

---

## Rules

1. Editorial scaffolding only — never a character of body text (no-loss assertion: output
   minus whitespace = input minus whitespace, or nothing is written).
2. Footnote references `[^n]` and definitions keep their digits (they are protected before
   the number pass).
3. Output to `$INBOX/` — never overwrite the source.

---

## Procedure

**Stage 0 — pre-clean already-formatted files (optional, run first when needed)**

Some commentary files arrive already carrying scaffolding from an earlier pass: standalone OCR index numbers (a line that is just `1`, `2`, `3`…), Obsidian block / verse IDs (`^0-1`, `^1-2`, `^1-2-0`), markdown heading markers (`##`, `###`), and line breaks that wrap verses and split sentences across lines. Segmentation re-derives boundaries from continuous prose, so this scaffolding must be removed **before** Stage 1. If a file is already plain, under-segmented running text, skip this stage.

```
python3 $SKILL/scripts/preclean_commentary.py \
    "$COMMENTARIES/<file>.md" \
    "$INBOX/<file>.preclean.md" \
    --report "$INBOX/<file>.preclean.tsv"
```

What it removes (editorial scaffolding only — never a character of body text):

- **Index / outline numbers** — any whitespace-bounded token consisting solely of digits (ASCII `0-9` or Tibetan `༠-༩`) with optional internal dots (hierarchical numbers such as `4.11`, `1.2.3`) and an optional trailing `.` or `)`, removed unconditionally. Covers simple counters (`1`, `2`, `3`), terminated counters (`1.`, `2.`), and hierarchical section labels (`4.11`, `1.2.3.`). Catches both an OCR line counter on its own line *and* an inline outline number sitting before a sa-bcad opener (e.g. `…ཏོ། །19. དང་པོ་ནི།…`). Numbers fused to body text (e.g. `ལོ16`) are left untouched — Tibetan never delimits a real syllable with a bare space.
- **Block / verse IDs** — `^N`, `^N-N`, `^N-N-N` … wherever they appear.
- **Heading markers** — all `#` characters are stripped from the body. Heading text is preserved as plain prose and acts as a natural separator between prose runs; a heading whose text is a bare number (likely OCR noise) is flagged `heading-suspect` in the report.
- **Intra-section line breaks** — consecutive content lines are joined into one continuous run, so Stage 1 starts from raw prose. Heading-text lines (now plain prose) still act as run separators, so a section title never fuses onto neighbouring content.

Frontmatter (the leading `--- … ---` block) is preserved verbatim and excluded from the no-loss comparison.


---

## Completion check

- [ ] No-loss assertion passed; `.preclean.md` written to `$INBOX/`
- [ ] Footnote markers and definitions intact
- [ ] `heading-suspect` rows (if any) looked at
