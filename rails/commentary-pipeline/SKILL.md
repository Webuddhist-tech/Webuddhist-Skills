---
name: commentary-pipeline
description: >
  Run the WHOLE commentary workflow on one Tibetan commentary: pre-clean → segment into
  functional units → sa bcad / heading tree extraction → TOC ingest → meaning-based
  re-segmentation (+ QC) → body block IDs, with the checks between steps. Produces the
  vault's human-edited commentary layout (openers, quoted root verses, explanations, frame
  lines; sa bcad or verse headings; block IDs). Use for "process this commentary",
  "segment and add the TOC to this commentary", "run the commentary workflow". Each step is
  also its own skill (commentary-preclean … commentary-block-ids). Root texts go to
  root-text-pipeline.
profile: rails-vault
---

# commentary-pipeline

This skill only **orchestrates**. Each step is its own skill, with its own rules:

| # | Step skill | Does | Model? |
|---|---|---|---|
| 1 | `commentary-preclean` | strip earlier scaffolding back to continuous prose (optional) | no |
| 2 | `commentary-segment` | functional units (`--units`), quoted root verses (`--root`), stanzas | no |
| 3 | `commentary-toc-extract` | heading tree — mode `sabcad` / `verses` / `top` / `labels` — with anchors and frame nodes | yes |
| 4 | `commentary-toc-ingest` | headings into the segmented file | no |
| 5 | `commentary-resegment` | meaning-based merge / split + QC | yes |
| 6 | `commentary-block-ids` | derived body IDs | no |

Shared scripts and prompts live in `$SKILLS/seg-toc-lib/` (also used by the
root-text workflow).

---

## Inputs

| Input | Description |
|---|---|
| `source` | the commentary, `$COMMENTARIES/<file>.md` — OCR-clean (`format-commentary` first if not) |
| `id` | short id for the working files |
| `root` *(recommended)* | the root text it comments on, `$SOURCE_TEXTS/<root>.md` (for `--root` and the `verses` / `top` modes) |
| `quotes` | `separate` (each quoted root stanza its own block) or `inline` (kept inside the explanation) — how this commentary's editors lay out quotes |
| `mode` | `sabcad` / `verses` / `top` / `labels` — see `commentary-toc-extract` |

Decide `quotes` and `mode` before starting (look at the vault's other commentaries on the
same root, or the editor's sample); if unclear, ask.

## Output

| File | Step |
|---|---|
| `$INBOX/<file>.preclean.md` | 1 |
| `$INBOX/<file>.units.md` + `.segreport.tsv` | 2 |
| `$WORK/TOC-<id>/…` → anchored tree `toc-tree-<id>.md` | 3 |
| the units file with headings | 4 |
| `$INBOX/resegmented/<id>.reseg.md` · `.ops.md` · `.qc.md` | 5 |
| the same file with block IDs | 6 |

Everything stays in `$INBOX/` until a domain specialist approves it.

## Output file format

```markdown
# <title> ^0

## <front matter, e.g. མཆོད་བརྗོད།> ^I-0

<namo / homage line> ^I-1

## 1. <top-level sa bcad node> ^1-0

### 1.1 <node> ^1-1-0

<division announcement + first-child opener> ^1-1

<quoted root stanza, one pāda per line> ^1-2

<explanation> ^1-3

## <back matter, e.g. མཇུག་བྱང།> ^b-0
```

---

## Rules (across all steps)

1. **No character changes.** Every script asserts the text (whitespace, headings and IDs
   aside) is unchanged and writes nothing otherwise.
2. **Order matters:** segment before extracting the tree (the anchors are copied from the
   file they are ingested into); ingest the headings before re-segmenting (they give the
   model the section context); stamp IDs last.
3. **Models.** Gemini API calls (Gemini 3.8 Flash, thinking high) by default; the same
   prompts run as isolated subagents (`model: opus`, high effort) only when the prompt
   explicitly asks for another model (`$SKILLS/seg-toc-lib/SKILL.md`). The Gemini
   TOC script covers mode `sabcad` only; the other modes need the agent path.
4. **Strict text gate.** Step 6 ends with `verify_text.py` against the pre-segmentation
   text: letters and spacing identical, only breaks, headings and IDs added.
5. **Recommended segmentation flags** (benchmark v2): `--units --root <root> --enum-chain
   broad --quotes <separate|inline> --colophon-guard` (+ `--stanza-breaks` for commentaries
   that gloss the root line by line).

---

## Procedure

1. **`commentary-preclean`** — only if the file carries index numbers, IDs, headings or
   per-line breaks.
2. **`commentary-segment`** with `--units --root …` and the recommended flags. Check the
   quote-balance line and the report.
3. **`commentary-toc-extract`** in the declared mode on the segmented file. Stop until the
   QC checker reports 0 issues (or only ones listed as genuinely ambiguous).
4. **`commentary-toc-ingest`** (`--split-frame-nodes`). Stop if not-found > 0; tell the user
   about any `REORDERED`.
5. **`commentary-resegment`** + its QC. Review the ops log.
6. Have the `##` labels confirmed, then **`commentary-block-ids`**.
7. **Report** each step's numbers: units, tree size and QC issues, headings placed,
   merges / splits, QC flags before / after.

---

## Completion check

- [ ] Every step's integrity check passed; `verify_text.py` ✓ at the end (letters and spacing)
- [ ] TOC QC clean; ingest 0 not-found
- [ ] Re-segmentation ops and QC reviewed
- [ ] IDs stamped only after the `##` labels were confirmed
- [ ] Output in `$INBOX/` until approved
