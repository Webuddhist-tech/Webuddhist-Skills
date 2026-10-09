---
name: root-text-toc-ingest
description: >
  Step 4 of root-text-pipeline: put the top-level parts of a root text's anchored heading
  tree (from root-text-toc-extract) into the segmented text as ## headings with block IDs,
  in place of the generic གཞུང་དངོས།; the author's opening verses stay with the first part;
  the grouping input is rewritten. Deterministic, no model; the text is verified unchanged.
  Use for "insert the chapter headings into the root text", "ingest the root-text TOC".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-toc-ingest

---

## Inputs

| Input | Description |
|---|---|
| `workdir` | `$INBOX/<id>-root`, written by `root-text-segment` |
| `tree` | the anchored tree `$WORK/TOC-<id>/toc-tree-anchored-<id>.md` |

No tree (the text announces no parts) → skip this step; `## གཞུང་དངོས། ^1-0` stays.

## Output

`prepared.md`, `group-in.md` and `state.json` in the working folder, rewritten with the body
headings; `tree-top.md` / `tree-top.json` (the nodes used).

## Output file format

```markdown
## ཀླད་ཀྱི་དོན། ^I-0
…
## <part 1 title> ^1-0
<the author's opening verses, then part 1>
## <part 2 title> ^2-0
…
```

---

## Rules

1. **Top-level parts only** (`1.`, `2.` …, `II.`): sub-parts in a verse text are often
   shorter than a stanza and would split stanzas or stand empty. **Exception:** a tree with
   a single numbered top node (one rite section, one chapter) gives its children too
   (`###`, IDs `^1-1-0` …).
2. **The author's opening verses belong to the body:** when the first part's anchor falls
   after them, its heading moves up to meet the front matter.
3. **Headings may fall inside a raw paragraph** (about 30% do): the first part after the
   title and homage, a ritual stage opened by `དེ་ནས་…` / `དེའི་རྗེས་ལ་…` without a new
   paragraph. A heading always falls at a unit boundary.
4. **Titles as the text gives them** — the author's chapter name complete, short or long;
   never shortened or reworded.
5. `not placed` must be 0 — a node whose anchor is not found is inserted by hand
   (`## <title> ^N-0` before the part's first block) and the step re-run.

Heading standardisation agreed with the editors (2026-10-09), to be applied by this step:
one ordinal form per file, ordinal first (`དང་པོ་…`, `གཉིས་པ་…`, taken from the closing line
or the announcement — no `ལེའུ` added where the text does not use it); `II.` only for a
true preamble (the author's homage and promise to compose), titled `མཆོད་བརྗོད།`.

---

## Procedure

```bash
python $SKILLS/seg-toc-lib/root_text_build.py toc-ingest "$INBOX/<id>-root" \
    --tree "$WORK/TOC-<id>/toc-tree-anchored-<id>.md"
```

It re-derives the units from the source with the settings `root-text-segment` stored (so
the result is exactly what one run with the tree gives), ingests the top-level nodes with
`$SKILLS/seg-toc-lib/toc_tree_ingest.py`, and rewrites the grouping input. Read
the report: `body headings: N not placed` and the printed heading list.

---

## Completion check

- [ ] `not placed: 0`
- [ ] Printed headings = the tree's top-level parts, in text order
- [ ] `group-in.md` rewritten (the headings appear in it)
