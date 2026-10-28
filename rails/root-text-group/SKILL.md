---
name: root-text-group
description: >
  Step 5 of root-text-pipeline — the model step: group the units of a segmented root text
  into blocks by sense: verse lines into stanzas (no fixed length), prose sentences into
  paragraphs of one point or one ritual step, verse passages inside prose into stanzas.
  Never across a heading or a printed paragraph break (¶). Isolated subagents follow
  prompts/stanza-grouping.md (verse) or prompts/prose-grouping.md (prose); a long text is
  split into parts that run in parallel. Use for "group the pādas into stanzas", "make the
  paragraphs of this root text".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-group

---

## Inputs

| Input | Description |
|---|---|
| `workdir` | `$INBOX/<id>-root` with `group-in.md` and `state.json` (from `root-text-segment` / `root-text-toc-ingest`) |

The form in `state.json` picks the version: `free` (verse) or `prose`.

## Output

`$INBOX/<id>-root/groups-free.json` or `groups-prose.json` (and, for a split input,
`groups-<v>-partN.json`).

## Output file format

```json
{"stanzas": [[1, 4], [5, 10], …],
 "notes": {"<first unit of a block>": "one short English reason"}}
```

`[a, b]` = units a..b inclusive, all blocks in order, covering every unit exactly once.

---

## Rules

The full rules are in the two prompts; in short:

1. **Verse (`prompts/stanza-grouping.md`) — by sense, no default length.** A block ends where
   a sentence or petition ends (a connective — `…སྟེ།` `…ནས།` `…ལ།` `…དང་།` — means it goes
   on); one block holds one point; lead lines (`ན་མོ།`, `ཨེ་མ་ཧོ།`, `ཧཱུཾ།`) attach forward;
   prose rubrics and chapter closing lines stand alone; a mantra stays with the line that
   introduces or labels it.
2. **Prose (`prompts/prose-grouping.md`).** One paragraph per point (treatise) or step
   (ritual); an objection (`…ཞེ་ན།`) apart from its answer, a teaching question
   (`…གང་ཞེ་ན།`) with its answer; a mantra with its step; a quotation's lead-in and close
   stay prose — with no prose to join (a `¶` or heading on the other side) they stand as
   their own block, never inside the stanza; whether a list of full-sentence items is one
   paragraph or one per item follows each text (editors, 2026-10-09).
3. **Never** a block across a heading or a `¶`, never prose and verse in one block — the
   build step refuses it.
4. **Isolation.** Each subagent sees only its prompt and its input part; parts never see
   each other.
5. **Model:** isolated subagents, `model: opus`, high effort. No Gemini runner yet.

---

## Procedure

1. Split a long input (cuts only before a heading or after a `¶`, so no block is cut):
   ```bash
   python $SKILLS/seg-toc-lib/root_text_build.py group-split "$INBOX/<id>-root"
   ```
2. One isolated subagent per part (or one for `group-in.md` when there is no split), in
   parallel:
   > Read `$SKILL/prompts/<stanza|prose>-grouping.md` and follow it
   > exactly (for prose, also `stanza-grouping.md` for its verse lines). The input is
   > `$INBOX/<id>-root/group-in[-partN].md` (read all of it; use the unit numbers as given).
   > Write the JSON to `$INBOX/<id>-root/groups-<free|prose>[-partN].json`. Read only these
   > files. Decide by reading the text, not with a script. Reply with the path and the
   > block sizes.

   Several short texts may share one subagent, each grouped separately.
3. Join the parts:
   ```bash
   python $SKILLS/seg-toc-lib/root_text_build.py group-join "$INBOX/<id>-root"
   ```
4. Read the subagents' notes: blocks of 1–2 or 7+ lines, uncertain boundaries, input lines
   tagged with the wrong form (a verse line tagged `S`) — carry them into the report.

---

## Completion check

- [ ] `groups-<v>.json` written (joined, for a split input)
- [ ] Every block of 1–2 or 7+ lines has a note
- [ ] Mis-tagged units reported, not forced
