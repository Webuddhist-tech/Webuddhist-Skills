---
name: translation-segment-check
description: Report-only, segment-by-segment check that every block of a translation is (a) aligned to the right root segment and (b) a correct translation of it, line by line, with every interpretive verdict grounded in the verse-aligned commentaries. Use after a translation has been given block IDs and transclusions, and before it is trusted as a reference or uploaded.
profile: rails-vault
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/translation-segment-check/SKILL.md
---

# translation-segment-check

> **Locations.** `$SKILL` is this skill's own directory. `$SOURCE_TEXTS`,
> `$COMMENTARIES`, `$TRANSLATIONS`, `$TRANSFORMATIONS` and `$INBOX` resolve per
> repo — see `rails/PROFILES.md`.

`translation-alignment-check` proves a translation has the root's *shape* — same ids, same line counts, a transclusion above every block. It cannot tell whether the words under `^1-11` actually translate Tibetan `^1-11`. This skill does that: it pairs every translated block with the root segment its transclusion names, compares them line by line, and grades each segment. It catches the three failures the structural check is blind to — a block transcluding its neighbour (misalignment), a line that says something the Tibetan does not (mistranslation), and a clause dropped or invented (omission / addition).

Correct output is a report in which every segment has one verdict, every non-✅ verdict names the line and what differs, and every verdict that turns on *how the Tibetan is read* cites the commentary that reads it that way. Authority comes from the commentaries, never from the checker's own sense of the Tibetan: where the commentaries split, a translation that follows either side is not wrong.

---

## Inputs

| Input | Description | Required |
|---|---|---|
| Translation | A block-ID'd, transcluded translation note, e.g. `$TRANSLATIONS/<file>.md` or a `$TRANSFORMATIONS/Translations/<track>/…md` render | yes |
| Root text | `--root`, default the translation's `root_text:` frontmatter (a file in `$SOURCE_TEXTS/`) | no |
| Commentaries | Derived: every file under `$COMMENTARIES/` (recursively; `--commentary-dir` to narrow it) that transcludes the root. A commentary with no root transclusions carries no anchors and contributes nothing | derived |
| Reference translations | Derived: every other file in `$TRANSLATIONS/` (`--translation-dir` to change it), shown beside each pair as a meaning cross-check only | derived |

If the translation has no transclusions, stop and run `transclusion` (Type 1) first — this skill pairs on transclusions, not on guessed positions.

## Output

`$INBOX/segment-checks/<translation-file-stem>-segment-check.md` — one report per translation, overwritten on a re-run. The translation itself is never modified.

---

## Output file format

Keep it brief: one table, one row per non-✅/◇ segment, one short phrase per cell.

```markdown
---
title: "Segment check — <translation title>"
translation: <vault path of the translation>
root_text: <vault path of the root>
checked: <YYYY-MM-DD>
skill: translation-segment-check
verdicts: {ok: N, free: N, minor: N, major: N, misaligned: N}
---

# Segment check — <translation title>

**Alignment:** <one line: misaligned ids, or "all blocks transclude their own id">. Untranslated: <ids>.

**Verdict:** <one line>.

| Seg | Verdict | Line | Issue | Evidence |
|---|---|---|---|---|
| ^1-11 | ✗ | 1 | 守護眾地母 makes Tara the protector; Tibetan = the earth-protectors she summons | bo-ཀརྨ་མཻ་ཏྲི། "<snippet>" |

<one line: the remaining segments are ✅/◇, plus any notable ⚑>
```

Segments graded ✅ or ◇ are counted in `verdicts:` and not listed. Evidence is a commentary file stem, with a short snippet only for ✗ findings; "—" when no commentary glosses the point.

Verdict scale — one per segment, the worst of its lines:

| Mark | Name | Meaning |
|---|---|---|
| ✅ | ok | every line renders its Tibetan line |
| ◇ | free | meaning kept; wording compressed, reordered or poeticised across lines — normal in verse |
| ⚑ | attested | follows one side of a reading the commentaries (or the root's recorded witnesses) split on — not an error |
| ⚠ | minor | a small omission, addition or shift that does not change what the line asserts |
| ✗ | major | the line asserts something the Tibetan does not: wrong subject or object, wrong referent, a clause dropped or invented |
| ⇄ | misaligned | the block translates a different root segment than the one it transcludes |

---

## Rules

1. **Report-only.** Never edit the translation, the root or a commentary. Fixes are a separate, human-approved step.
2. **Pair on the transclusion.** A block is compared with the root segment its transclusion names. A block whose own id and transclusion differ is reported as structure, before any meaning check.
3. **No verdict from memory.** Any ⚑, ⚠ or ✗ that depends on how a Tibetan word or clause is read must cite at least one commentary by file stem (a ✗ also with a short verbatim snippet). If no commentary addresses the point, write "—" and cap the verdict at ⚠.
4. **Divergence is not error.** If any commentary supports the translation's reading, the verdict is at best ⚑, never ✗. Also check the root's frontmatter `source_description` for recorded witness variants (e.g. སྒྲོན་མ / སྒྲོལ་མ) — a translation following another witness is ⚑.
5. **Reference translations never decide.** The other `$TRANSLATIONS/` files are shown to spot misalignment and gross misreadings; a finding may not rest on them.
6. **Transliterated mantra syllables and bracketed romanisations** (`都哩(TURE)`) are checked only for being the right syllables in the right line, never for spelling convention.
7. **Line-level, not gist.** Every Tibetan line must be accounted for somewhere in the segment. A line whose content moved to a neighbouring line of the same segment is ◇, not an omission.
8. **Untranslated root segments** (listed by the script as "no translated block") are listed on the Alignment line, not graded.

---

## Procedure

1. Run the pairing worksheet:
   ```bash
   python3 $SKILL/scripts/pair_segments.py "<translation>"            # add --ids 1-3,1-4 to limit, --out <file> to save
   ```
   It prints, per block, the root lines and translation lines interleaved (`bo 1` / `tr 1` …), a line-count note when they differ, and each reference translation's rendering. Header `!!` lines report blocks with no transclusion, transclusions pointing at another id, and root segments with no translated block.
2. Summarise the header in the **Alignment** line. If any `!!` names a wrong transclusion, confirm by reading both segments and grade it ⇄.
3. Read every pair line by line. For each Tibetan line decide whether its content is present, where, and whether anything is added. Grade provisionally.
4. List every provisional ⚑ / ⚠ / ✗ that turns on interpretation. For those segment ids, pull the commentary passages:
   ```bash
   python3 $SKILL/scripts/pair_segments.py "<translation>" --ids none --commentary 1-11,1-14 --no-reference
   ```
   (`--ids none` suppresses the pairs so only the commentary passages print.) Each commentary's text between that verse's transclusion and the next is printed under its file stem. Search it for the disputed word.
5. Re-grade against the evidence under Rules 3–4. Record the file stem (and, for ✗, a snippet) in the table.
6. Write the report to `$INBOX/segment-checks/<stem>-segment-check.md` in the format above, with the verdict counts in frontmatter.
7. Read the ✗ and ⇄ findings back to the user with their ids; mention the ⚠ count and any systematic pattern.

---

## Completion check

- [ ] `pair_segments.py` run on the translation; alignment summarised in one line
- [ ] Every translated segment graded; counts in `verdicts:`; every non-✅/◇ segment has a table row
- [ ] Every ⚑, ⚠ and ✗ that depends on a reading cites a commentary file stem (✗ also a snippet), or shows "—" and is capped at ⚠
- [ ] No ✗ where any commentary supports the translation's reading
- [ ] Root witness variants checked before grading ⚑ vs ✗
- [ ] Report written to `$INBOX/segment-checks/`; translation and sources unmodified
