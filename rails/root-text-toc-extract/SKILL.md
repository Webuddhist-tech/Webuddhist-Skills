---
name: root-text-toc-extract
description: >
  Step 3 of root-text-pipeline: build the heading tree of a Tibetan ROOT TEXT that announces
  its own parts — chapters closed by …ལེའུ་དང་པོའོ།, rites announced as <topic> ཆོ་ག་ནི།,
  <topic> བཤད་བྱ་སྟེ།, parts opened by དང་པོ་ … ནི། — in isolated passes: (1) section
  candidates incl. topic headers without an ordinal, (2) verbatim enumerations, (3) nested
  decimal tree, (4) deterministic QC + repair, (5) anchors. No frame nodes (the root-text
  frame comes from root-text-segment). Do not force a tree: a text that announces nothing
  gets none. Use for "build the TOC of this root text", "find the chapters of this root
  text". Commentaries use commentary-toc-extract.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/toc-tree-extraction/SKILL.md
---

# root-text-toc-extract

Root texts announce their parts without the commentarial sa bcad formula — often no ordinal
and no count. This step finds them and writes an anchored tree for `root-text-toc-ingest`.

**Isolation is the whole point.** Each pass runs as its own isolated subagent whose entire
instruction set is one prompt file plus its input; you only chunk, dispatch, merge on disk,
run the checker and dispatch the repair subagent. Subagents read their input by path and
write their own output file; never paste chunk text into a prompt or do a pass's reasoning
in your own context.

Prompts (shared with `commentary-toc-extract`): `$SKILLS/seg-toc-lib/prompts/` —
`pass1-candidates-root.md`, `pass2-enumerations.md`, `pass3-tree.md`, `pass4-qc-repair.md`,
`pass5-anchors.md`. Scripts: `$SKILLS/seg-toc-lib/chunk_file.py`,
`qc_check_tree.py`.

---

## Inputs

| Input | Description |
|---|---|
| `input-file` | the segmented text: `$INBOX/<id>-root/prepared.md` from `root-text-segment` (so the anchors are copied from the text they are ingested into) |
| `id` | short id for the folder `$WORK/TOC-<id>/` |

## Output

| File | Stage |
|---|---|
| `$WORK/TOC-<id>/chunk-index.tsv` | chunk line ranges |
| `$WORK/TOC-<id>/candidates/chunk_NNN.md` · `enumerations/chunk_NNN.md` | per chunk |
| `$WORK/TOC-<id>/toc-candidates-<id>.md` · `toc-enumerations-<id>.md` | merged |
| `$WORK/TOC-<id>/toc-tree-qc-<id>.md` | pass 4 QC report (issues before / after) |
| `$WORK/TOC-<id>/toc-tree-qc-source-<id>.md` | pass 6 QC report, against the text itself |
| `$WORK/TOC-<id>/toc-tree-anchored-<id>.md` | **the anchored tree** — input of `root-text-toc-ingest` |

## Output file format

```
## དཀར་ཆག / Table of Contents

* 1. <title> [[<verbatim words where part 1 begins>]]
   * 1.1 <title> [[…]]
* 2. <title> [[…]]
```

No `^toc` block IDs; no frame nodes `I.` / `a.` / `b.`. A preamble before part 1 may be
`II.` (`root-text-toc-ingest` decides how it is headed).

---

## Rules

1. **Do not force a tree.** If pass 1 returns no candidates for every chunk, stop: the text
   announces no parts (most prayers and chants). Report it — it is the correct result.
2. **Type D candidates.** `pass1-candidates-root.md` adds topic headers without an ordinal
   (`<topic> བཤད་བྱ་སྟེ།`, `<topic> ཆོ་ག་ནི།`, `<topic> སྦྱོར་བ་ལ།`), which the commentary
   pass 1 ignores.
3. **Chapters named only in their closing line** (`…ལེའུ་དང་པོའོ།`, `…ཆོ་ག་སྟེ་གཉིས་པའོ།`): the
   node is the chapter; its anchor is where the chapter **begins** (after the previous
   closing line), its title comes from the closing line.
4. **The deterministic checker is the gate** — never declare the tree clean on a
   subagent's say-so.
5. **Only the top-level nodes become headings** (`root-text-toc-ingest`); keep the full tree
   anyway — it is the record of the text's structure.

---

## Procedure

1. **Chunk** (line ranges only, no text copied):
   ```bash
   python $SKILLS/seg-toc-lib/chunk_file.py "<input-file>" --chunk-size 150 \
       --overlap 25 --index-only --output-dir $WORK/TOC-<id>
   ```
2. **Pass 1 — candidates**, one isolated subagent per chunk, in parallel, skipping chunks
   whose file exists:
   > Read `$SKILLS/seg-toc-lib/prompts/pass1-candidates-root.md` and follow it
   > exactly. Read ONLY lines START–END of `<input-file>`. Write your output to
   > `$WORK/TOC-<id>/candidates/chunk_NNN.md`, starting with
   > `<!-- chunk NNN | lines START–END | source: <id> -->`, then the candidate blocks — or
   > `<!-- no candidates -->`. Reply only with the path.

   No candidates in any chunk → stop (Rule 1).
3. **Pass 2 — enumerations**, one isolated subagent per chunk, in parallel:
   > Read `$SKILLS/seg-toc-lib/prompts/pass2-enumerations.md` and follow it exactly.
   > Read ONLY lines START–END of `<input-file>`. Write the enumeration blocks (or
   > `NO ENUMERATIONS`) to `$WORK/TOC-<id>/enumerations/chunk_NNN.md`. Copy verbatim.
   > Reply only with the path.
4. **Merge on disk** (shell `cat`, chunk order) → `toc-candidates-<id>.md`,
   `toc-enumerations-<id>.md` (skip `NO ENUMERATIONS` files).
5. **Pass 3 — tree**, one isolated subagent:
   > Read `$SKILLS/seg-toc-lib/prompts/pass3-tree.md` and follow it exactly. Build
   > the tree for "<id>" from `…/toc-candidates-<id>.md`, reconciled against
   > `…/toc-enumerations-<id>.md`. Write only the tree block to
   > `$WORK/TOC-<id>/toc-tree-<id>.md`. Reply only with the path.
6. **Pass 4 — QC**, then repair while issues remain (fresh subagent each round):
   ```bash
   python $SKILLS/seg-toc-lib/qc_check_tree.py $WORK/TOC-<id>/toc-tree-<id>.md \
       --corpus $WORK/TOC-<id>/toc-candidates-<id>.md $WORK/TOC-<id>/toc-enumerations-<id>.md \
       --out $WORK/TOC-<id>/toc-tree-qc-<id>.md
   ```
   > Read `$SKILLS/seg-toc-lib/prompts/pass4-qc-repair.md` and follow it exactly.
   > Fix every issue in `…/toc-tree-qc-<id>.md` against the enumerations and candidates (for
   > an announced-count issue you may read `<input-file>`). Overwrite `…/toc-tree-<id>.md`.

   Re-run the checker after each repair (add `<input-file>` to `--corpus` when a part was
   taken from the text); record issues before / after.
7. **Pass 5 — anchors**, one isolated subagent:
   > Read `$SKILLS/seg-toc-lib/prompts/pass5-anchors.md` and follow it exactly. The
   > tree is `…/toc-tree-<id>.md`; the text is `<input-file>` (read all of it). **Numbered
   > nodes only — do not add the frame nodes I. / a. / b.; the front matter and colophons
   > are headed by root-text-segment.** A preamble before node 1 may be `II.`. Write the
   > anchored tree to `$WORK/TOC-<id>/toc-tree-anchored-<id>.md`.
8. **Pass 6 — QC against the text itself.** The pass-4 checker only compares the tree with
   the model's own candidates; this one reads the text:
   ```bash
   python $SKILLS/seg-toc-lib/qc_tree_vs_source.py \
       $WORK/TOC-<id>/toc-tree-anchored-<id>.md --source "<input-file>" \
       --out $WORK/TOC-<id>/toc-tree-qc-source-<id>.md
   ```
   Every anchor found, in document order; no anchor value repeating across different
   parts; each title attested near its anchor; announced counts vs children. In a root
   text a chapter **titled from its closing line** is anchored where it begins, so "title
   not near its anchor" is expected for those nodes — accept it, do not "fix" it. An
   unresolved anchor (`[[?]]`) or a node out of order is a real error: give the issues to a
   fresh repair subagent (`pass4-qc-repair.md`, the text is the final authority), re-run
   both checkers.

**Models.** Claude path (this procedure): isolated subagents, `model: opus`, high effort.
Gemini path: `$SKILLS/seg-toc-lib/toc_tree_extractor/extract_toc_tree.py`
(Gemini 3.8 Flash, thinking high; key from the vault `.env`, never opened) runs passes 1–4
with its own embedded v1 prompts — it has **no Type D and no root mode**, so use the Claude
path for root texts.

---

## Completion check

- [ ] Either "no parts announced" reported (no tree), or:
- [ ] Pass 4 QC issues after repair = 0 (or the remaining ones listed as genuinely ambiguous)
- [ ] Pass 6 QC against the text: no `[[?]]`, no order errors; accepted flags (closing-line titles) listed
- [ ] Anchored tree written, every node with `[[context]]`, no frame nodes I. / a. / b.
