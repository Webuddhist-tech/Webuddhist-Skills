# deprecated/ — retired skills, kept for reference

Skills that have been replaced. They stay here so their procedures and history can
still be read and compared, but nothing installs them: `install-skills.py` reads
`rails/` only, and `tools/build-catalog.py` lists them under *Deprecated* in
[`CATALOG.md`](../CATALOG.md) and [`PROVENANCE.md`](../PROVENANCE.md). Each one's
`replaced_by:` frontmatter names its successors.

| Skill | Replaced by | Retired |
|---|---|---|
| [`toc-generate`](toc-generate/SKILL.md) | `commentary-toc-extract` (tree, QC against the text, publish to `$SECTIONS_RAW/toc-tree/`), `commentary-toc-ingest` (headings), `root-text-toc-extract` (root texts) | 2026-10-09 |
| [`segment-commentary`](segment-commentary/SKILL.md) | `commentary-pipeline` → `commentary-preclean`, `commentary-segment`, `commentary-resegment`, `commentary-block-ids` | 2026-10-09 |

**Not carried over from `toc-generate`:** Simple mode (a quick two-level TOC
written to a new file, `insert_toc_headings.py`), the `--recall` candidate prompt,
and the E2 read-and-place ingest for page-number pointers. If a text needs one of
these, read it here and bring it into the new skills rather than reviving this copy.

Do not fix a skill in this folder. Fix its replacement.
