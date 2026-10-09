---
name: commentary-toc-ingest
description: >
  Step 4 of commentary-pipeline: ingest an anchored TOC tree (written by
  commentary-toc-extract's pass 5) into a segmented commentary by inserting markdown
  headings with block IDs, the way the vault's human-edited commentaries carry them: each
  heading at the start of the block where its section begins, parent and first-child
  headings stacked, front/back-matter frame headings (^I-0, ^a-0, ^b-1-0), siblings in the
  order of the text. The [[...]] contexts only locate positions — they are never copied into
  the output, and the text is verified unchanged. Use for "ingest the TOC tree", "insert
  headings from the toc-tree file", "add section headings to the commentary".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/toc-tree-ingest/SKILL.md
---

# commentary-toc-ingest

Inserts the section headings of a pre-extracted TOC tree into a Tibetan commentary, all
nodes in one pass, in document order.

---

## Inputs

| Field | Description |
|---|---|
| `toc_file` | The **anchored** tree: `$WORK/TOC-<id>/toc-tree-<id>.md`, written by `commentary-toc-extract` pass 5. Every node line carries `[[context]]`. A tree without contexts (passes 3–4 only) cannot be ingested — run pass 5 first. |
| `commentary_file` | The segmented commentary the anchors were copied from (output of `commentary-segment --units`), as a working copy in `$INBOX/` or `$COMMENTARIES/commentaries_with_toc/<id>.toc.md`. |

Tree line forms:

```
* 2.2.1 དང་པོ་ལོངས་སྐུའི་རྣམ་པའི་སྒོ་ནས་བསྟོད་པ་ [[དང་པོ་ལ་གཉིས། ཞི་བའི་…]]   sa bcad node
* I. མཆོད་བརྗོད། [[ན་མོ་གུ་རུ་…]]                                           front matter
* a. བསྔོ་བ། [[སྨྲས་པ།]]                                                     back matter
* b.1 མཛད་བྱང། [[ཅེས་སྒྲོལ་མར་ཕྱག་འཚལ་…]]                                    back matter child
```

---

## Placement — the convention of the human-edited files

The commentary is read as **blocks** (paragraphs separated by a blank line). For each node,
in tree order, the script finds its `[[context]]` at or after the previous node's position
(canonical match: whitespace and shads are ignored, so `པའོ།།` still finds `པའོ། །`; a
context that does not match whole is retried on its first half), and inserts the heading
**at the start of the block that contains it**.

That one rule reproduces the human layout:

- **Stacked headings.** A first child's opener (`དང་པོ་ནི།`) sits in the same block as its
  parent's division announcement, so the parent's heading and the first child's heading
  both land before that block — with the announcement under the deepest heading.
- **Node 1** is anchored on the work's top-level announcement, so `## 1` precedes it.
- **Frame headings** go before the homage, the dedication and the colophon.

When the context of a node that is **not** a first child falls in the middle of a block,
that block is cut at the context — a new node always starts a new block (reported as
"Blocks split at a node"; `--no-split-mid-block` only reports it).

Frame nodes (`I`, `II`, `a`, `b.1` …) are not cut out of a block by default — their heading
goes before the block that contains the context. **`--split-frame-nodes`** (recommended)
cuts for them too, so `## II.` gets its own block after a short homage line and `## མཇུག་བྱང།`
starts exactly at the colophon even when the segmenter left it on the end of the last
explanation.

### Siblings in the order of the text (default)

A commentary may announce its parts as A, B, C, D and then treat them as B, D, C, A. The
headings follow the **text**: before placing anything, the ingest checks every parent's
children inside the parent's section —

1. in the tree's order, each child searched after the one before it; if that works and the
   commentary's own ordinals agree (`དང་པོ་ནི།`, `གཉིས་པ་ …`, `གསུམ་པ་ …` rising), nothing
   changes;
2. otherwise the children are put in the text's order — by their opener ordinals when
   every child has one, else by where each context first occurs in the parent's section.
   Each node's children move with it. Frame nodes never move.

**Titles** are kept exactly as the commentary words them (a `གཉིས་པ་…` title that now
comes first still reads `གཉིས་པ་…`).

**Block IDs keep the announced order** (default): `གཉིས་པ་…` announced second keeps
`^1-2-0` even when it comes first in the text; the next one does **not** take `^1-2-0`.
So after a reorder the heading IDs in the file run out of numeric sequence
(`^1-2-0, ^1-4-0, ^1-3-0, ^1-1-0`) — expected, and the ingest prints a NOTE saying so. The
child that comes first in the text (whatever its number) is the one whose heading stacks
with its parent's. `--renumber-reordered` instead renumbers the moved siblings in text
order (`1.1 B, 1.2 D …`, descendants renumbered with them). Body IDs (`--stamp-body-ids`)
follow the `##` labels as always, so they are unaffected except that, after a reorder of
top-level parts, e.g. the `^2-n` blocks come before the `^1-n` blocks.

> **Tell the user** whenever the ingest reports `REORDERED`: which parent, the announced
> vs. text order, and that the IDs keep the announced numbering. Anything downstream that
> assumes heading IDs increase down the file needs to know.

Every change is printed (`REORDERED … under 1: tree 1.1 1.2 1.3 1.4 → text 1.2 1.4 1.3 1.1`).
`--keep-tree-order` turns reordering off. To get the reordered dkar chag itself:

```bash
python3 $SKILLS/seg-toc-lib/toc_tree_ingest.py reorder \
    --tree /tmp/toc-tree-<id>.json --commentary <commentary_file> \
    --out-md $WORK/TOC-<id>/toc-tree-<id>.reordered.md
```

Tested by `$SYSTEM/scripts/seg-toc-benchmark/test_reorder.py`, which shuffles the sibling
order of real anchored trees and checks that the headings land exactly where the
correctly ordered tree puts them, with the announced IDs kept (and, with
`--renumber-reordered`, identical to the original): 112/112 runs on 7 commentaries. On the
8 benchmark trees, which are already in text order, it changes nothing.

A context that runs across a block boundary (a short lead-in line, then the quoted verse in
the next block) is found on the joined text and placed at the block where it starts.

### Heading format

| Depth | Markdown | Example |
|---|---|---|
| 1 (and frame I, a, b) | `##` | `## གཉིས་པ་རྒྱས་པར་བཤད་པ། ^2-0` |
| 2 … 5 | `###` … `######` | `###### དང་པོ་ཞལ་མདངས་…བསྟོད་པ། ^2-2-1-1-1-0` |
| 6+ | `######` + bold | `###### **…** ^2-2-2-1-1-1-0` |

Block ID = full decimal path + `-0`, no cap (`b.1` → `^b-1-0`, `I` → `^I-0`).

`parse` repairs a `[[context]]` in which a model wrote a verse's line break as a literal
`\n` (Tibetan never contains a backslash), and prints a **WARNING** when two sibling
headings carry the same title — almost always a miscounted ordinal (`ཕྱག་འཚལ་བཅོ་ལྔ་པ།` twice).
Fix the tree before ingesting; the scorer and every downstream ID depend on it.
`--title-style shad` (default) ends each title with `།` as the vault writes headings
(`…བསྟན་པ་` → `…བསྟན་པ།`); `--title-style raw` keeps the tree's title as is.

### Body IDs

Stamping the derived body IDs is its own step, `commentary-block-ids`, run after
`commentary-resegment` and after the `##` labels have been confirmed.

---

## Procedure

```bash
# Step 1 — parse the anchored tree
python3 $SKILLS/seg-toc-lib/toc_tree_ingest.py parse \
    --input $WORK/TOC-<id>/toc-tree-<id>.md --out /tmp/toc-tree-<id>.json

# Step 2 — ingest (all nodes, one pass, text verified unchanged)
python3 $SKILLS/seg-toc-lib/toc_tree_ingest.py ingest \
    --tree /tmp/toc-tree-<id>.json --commentary <commentary_file> --split-frame-nodes

# Next: commentary-resegment, then commentary-block-ids (derived body IDs)
```

The JSON cache goes to `/tmp/` (avoids NTFS ghost-file issues). Re-running `ingest` is safe:
headings whose block ID is already in the file are skipped.

**Not-found nodes** (exit code 2) — the context was not found after the cursor: either the
context has a copying error, or the node is out of document order. Read the commentary
around the expected place and insert the heading by hand (`{hashes} {title} ^{id}` on its
own paragraph, before the section's first block), then re-run to confirm.

---

## Rules

1. **No context content in the output.** Only the title and block ID are written.
2. **No prose is altered.** The script aborts and writes nothing if the commentary's text
   (whitespace and IDs aside) would change; the only edit to a block is a cut at a node.
3. **Block IDs follow the tree.** Full decimal path, no segment cap.
4. **Single pass, document order**, all depths together.
5. **Idempotent.** Existing heading IDs are skipped.

---

## Completion checklist

- [ ] Tree carries `[[context]]` on every node (pass 5 done)
- [ ] `ingest` summary shows 0 not-found (or every not-found resolved by hand)
- [ ] "Integrity: text unchanged ✓" printed
- [ ] Stacked parent/first-child headings and frame headings look right at a glance
- [ ] Next steps: `commentary-resegment`, then `commentary-block-ids`
