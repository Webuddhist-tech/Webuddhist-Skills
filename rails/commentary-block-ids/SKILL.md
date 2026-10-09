---
name: commentary-block-ids
description: >
  Step 6 of commentary-pipeline: stamp the derived body block IDs on a finished, headed and
  re-segmented Tibetan commentary: every content block numbered by its top-level section
  (^2-1, ^2-2 … under ## … ^2-0, through its sub-sections), front/back matter from their
  own labels (^I-1, ^a-1, ^b-1), the title ^0; transclusions and footnote definitions take
  none. The text is verified unchanged. Deterministic, no model. Use for "stamp the block
  IDs on the commentary", "add body IDs".
profile: rails-vault
---

# commentary-block-ids

---

## Inputs

| Input | Description |
|---|---|
| `file` | the finished commentary: `$INBOX/resegmented/<id>.reseg.md` (after `commentary-resegment` and its QC) |
| `tree` | the parsed tree JSON from `commentary-toc-ingest` (`/tmp/toc-tree-<id>.json`) — or re-parse the anchored tree |

## Output

The same file, every content block ending in its block ID.

## Output file format

```markdown
# <title> ^0

## <frame> ^I-0

<homage> ^I-1

## 1. <top-level node> ^1-0

<block> ^1-1

### 1.1 <node> ^1-1-0

<block> ^1-2
```

---

## Rules

1. **The `##` labels of a commentary are a human decision** — have them confirmed before
   stamping (`$SYSTEM/Guidelines/annotation-conventions.md`).
2. **Stamp only after `commentary-resegment`** — it refuses files that already carry IDs.
3. **No character changes** ("Integrity: text unchanged").
4. Footnote definitions (`[^n]: …`) and transclusions never take an ID; a block that starts
   with a footnote marker (`[^58] …`) does.
5. Never stamp IDs into a file that is cited elsewhere without re-running what cites it.

---

## Procedure

```bash
python3 $SKILLS/seg-toc-lib/toc_tree_ingest.py parse \
    --input $WORK/TOC-<id>/toc-tree-<id>.md --out /tmp/toc-tree-<id>.json   # if not cached
python3 $SKILLS/seg-toc-lib/toc_tree_ingest.py ingest \
    --tree /tmp/toc-tree-<id>.json --commentary "$INBOX/resegmented/<id>.reseg.md" \
    --stamp-body-ids --verify-against "$INBOX/<file>.preclean.md"
```

`--verify-against` is **required** in this step: after stamping, the script runs the
**strict text gate** (`verify_text.py --fix`) itself — letters and spacing against the text
that went into `commentary-segment` (the `.preclean.md`, or the source when pre-cleaning
was skipped). It prints ✓ when the text is identical; a spacing difference (a space added or
removed inside a line, e.g. by a merge) is restored from the source; a **letter difference
stops the step with exit code 4** — the output is wrong, find the step that changed it. The
other checks ignore whitespace, so only this gate sees spacing (the 8 benchmark finals had
1–12 such spots each). Also check "Integrity: text unchanged" and that no ID repeats.

---

## Completion check

- [ ] `##` labels confirmed by a person before stamping
- [ ] Integrity line printed; no duplicate IDs
- [ ] Run with `--verify-against`; it printed ✓ — letters and spacing identical to the pre-segmentation text (exit 0)
- [ ] Output stays in `$INBOX/` until a domain specialist approves it
