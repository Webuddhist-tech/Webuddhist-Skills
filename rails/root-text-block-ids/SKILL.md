---
name: root-text-block-ids
description: >
  Step 6 of root-text-pipeline: build the final root-text file from the grouping (verse lines
  one per line inside a stanza, a prose paragraph on one line), refuse a grouping that mixes
  prose and verse, crosses a heading or a printed paragraph break, or misses a unit; stamp
  the block IDs (^0, ^I-n, ^N-n, ^a-n); verify the text is unchanged. Deterministic, no
  model. Use for "finish the root text", "stamp the block IDs on the root text".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-block-ids

---

## Inputs

| Input | Description |
|---|---|
| `workdir` | `$INBOX/<id>-root` with `prepared.md`, `state.json` and `groups-<free|prose>.json` |

## Output

`$INBOX/<id>-root/final-free.md` (verse) or `final-prose.md` (prose / mixed), with IDs.

## Output file format

As in `root-text-pipeline`: `# <title> ^0`; frame blocks `^I-1 …`, `^a-1 …`; body blocks
numbered by their top-level section (`^1-1, ^1-2 …` under `## … ^1-0`, running through its
sub-sections); footnote definitions take no ID.

---

## Rules

1. **The grouping is checked before anything is written:** every unit exactly once and in
   order; no block mixing prose sentences and verse lines; no block across a raw paragraph
   break (`¶`) or a heading.
2. **No character changes** — the built file is compared with `prepared.md`, the stamped
   file again by the ingest script ("Integrity: text unchanged"), and finally by the
   **strict gate** `$SKILLS/seg-toc-lib/verify_text.py` against the source:
   letters AND spacing. Only line/block breaks, headings and IDs may be added; inside a
   line the source's own spacing is kept (one space between the shads of `། །`, none after
   it: `…ནོ། །དེ་ནས`); a space where a break was added disappears into the break (no space
   at a line start or end). A spacing difference is restored from the source; a letter
   difference stops the step.
3. **IDs** follow the vault convention (`$SYSTEM/Guidelines/annotation-conventions.md`): the
   `-0` slot for headings, content from 1, numbered by the top-level section.
4. Never stamp IDs into a file that is cited elsewhere without re-running what cites it.

---

## Procedure

```bash
python $SKILLS/seg-toc-lib/root_text_build.py finish "$INBOX/<id>-root"
```

On a refusal, fix the groups JSON (or re-run `root-text-group` on that part) and run again.
Report the block sizes it prints.

---

## Completion check

- [ ] Final file written; all text checks passed, the last one printing "✓ … identical to <source> (letters and spacing …)"
- [ ] IDs stamped; no duplicate IDs
- [ ] Block sizes reported
