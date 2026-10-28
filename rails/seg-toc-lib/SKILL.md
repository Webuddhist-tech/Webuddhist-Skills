---
name: seg-toc-lib
description: >
  Support library — not run on its own. The shared scripts and TOC prompts of the
  segmentation + TOC workflows, used by the root-text-* and commentary-* skills (and their
  pipelines root-text-pipeline / commentary-pipeline): the root-text build library, TOC
  tree ingest, chunking, the two tree checkers, the Gemini TOC pipeline, the shared pass
  prompts, and the strict text gate verify_text.py. Read it to learn which file a step uses,
  the model rule (Gemini API by default, agents only when asked) and each step's text check.
profile: rails-vault
---

# seg-toc-lib — shared scripts and prompts of the segmentation + TOC workflows

One copy of everything that both the root-text and the commentary workflows use, so the two
cannot drift apart. The skills that call it:

- Root texts: `root-text-pipeline` → `root-text-classify`, `root-text-segment`,
  `root-text-toc-extract`, `root-text-toc-ingest`, `root-text-group`, `root-text-block-ids`
- Commentaries: `commentary-pipeline` → `commentary-preclean`, `commentary-segment`,
  `commentary-toc-extract`, `commentary-toc-ingest`, `commentary-resegment`,
  `commentary-block-ids`

| File | Used by | What |
|---|---|---|
| `root_text_build.py` | all `root-text-*` skills | the root-text library: `classify`, `segment`, `toc-ingest`, `group-split`, `group-join`, `finish` |
| `toc_tree_ingest.py` | `commentary-toc-ingest`, `commentary-block-ids`, `root_text_build.py` | parse an anchored tree, insert headings, stamp body IDs; `--verify-against <source>` runs the strict gate after writing |
| `chunk_file.py` | both `*-toc-extract` | chunk index (line ranges) for passes 1–2 |
| `qc_check_tree.py` | both `*-toc-extract` | deterministic tree QC against the model's own candidates + enumerations (pass 4 gate) |
| `qc_tree_vs_source.py` | both `*-toc-extract` | deterministic tree QC **against the text itself** (pass 6 gate): anchors found in order, each title attested near its anchor, no repeated-pointer collisions, announced counts vs children. Resolves the pass-5 `[[text]]` anchors to line numbers first. (From the former `toc-generate`.) |
| `verify_text.py` | `root-text-block-ids`, `commentary-block-ids` | the strict text gate: letters **and** spacing vs the source; `--fix` restores the source spacing |
| `toc_tree_extractor/` | `commentary-toc-extract` (Gemini path) | Gemini 3.8 Flash pipeline: `extract_toc_tree.py` (passes 1–4, embedded v1 prompts), `find_toc_contexts.py` (anchors), `ingest_toc_commentary.py`, Windows launcher |
| `prompts/pass1-candidates-root.md` | `root-text-toc-extract`, `commentary-toc-extract` mode `labels` | pass 1 with Type D (topic headers without an ordinal) |
| `prompts/pass2-enumerations.md` · `pass3-tree.md` · `pass4-qc-repair.md` · `pass5-anchors.md` | both `*-toc-extract` | passes 2–5 |

## Models — Gemini API by default, other models only when asked

Every model step runs on **Gemini API calls by default — Gemini 3.8 Flash, thinking `high`**
(temperature at the API default, 65,536 output tokens; a reply cut off at the limit is
retried, never used). The key is read by the scripts from the vault-root `.env` (or the
environment) and never printed; nobody opens that file.

**Another model runs only when the prompt explicitly asks for it** ("run it with Claude /
Opus", "use agents"). The same prompts then go to isolated subagents (`model: opus`, high
effort) — one subagent per call, reading only its prompt file and input, as separate API
calls would — through the adapters `commentary-resegment/scripts/claude_reseg_shim.py` and
`claude_generate_shim.py`, or the subagent procedures written in each skill. The scripts'
windowing, staging, reconciliation and text checks stay the same; only the model call
changes.

| Model step | Default (Gemini API) | On request (agents) |
|---|---|---|
| `commentary-toc-extract` | `toc_tree_extractor/extract_toc_tree.py` + `find_toc_contexts.py` (mode `sabcad`; embedded v1 prompts) | passes 1–5 from the prompt files, all four modes |
| `commentary-resegment` | `resegment.py`, `qc_check.py` | the two shims |
| `root-text-toc-extract` | — **not built yet**: the Gemini script has no root mode / Type D | passes 1–5 from the prompt files (the only path today) |
| `root-text-group` | — **not built yet** | `root-text-group/prompts/*.md` (the only path today) |

The two root-text model steps therefore run as agents until a Gemini runner exists for
them; say so in the report when you run them.

## Text checks — each step, and the strict gate at the end

Every step that writes text refuses to write if the text changed. The per-step checks
compare the text **with all whitespace removed** — they catch any letter deleted, added or
changed, but they cannot see spaces. So both workflows end with **`verify_text.py`**, which
compares letters **and** spacing with the source:

| Step | Its own check | What it compares |
|---|---|---|
| `root-text-classify` | — (reads only) | |
| `root-text-segment` | assertion before writing | source vs `prepared.md`, headings and whitespace ignored |
| `root-text-toc-ingest` | "Integrity: text unchanged" (`toc_tree_ingest.py`) | before vs after the headings, whitespace ignored |
| `root-text-group` | — (writes only JSON); its grouping is checked by the next step | |
| `root-text-block-ids` | grouping checks (every unit once, no prose/verse mix, no block across `¶` or a heading); assertion vs `prepared.md`; ingest integrity; **`verify_text.py --fix` vs the source** | letters **and** spacing |
| `commentary-preclean` | no-loss assertion | source vs output minus the removed scaffolding, whitespace ignored |
| `commentary-segment` | no-loss assertion | input vs output, whitespace ignored |
| `commentary-toc-extract` | `qc_check_tree.py` (the tree, not the text) | titles / ordinals attested in the text |
| `commentary-toc-ingest` | "Integrity: text unchanged" | whitespace ignored |
| `commentary-resegment` | integrity check after applying, again after QC repair | whitespace ignored |
| `commentary-block-ids` | ingest integrity; **`verify_text.py --fix` vs the pre-segmentation text**, run by the stamping command itself (`--verify-against`, exit 4 on a letter difference) | letters **and** spacing |

`verify_text.py` allows only what the workflow adds: line and block breaks, heading lines,
trailing block IDs. Inside a line the source's own spacing is kept — one space between the
shads of `། །` and none after it (`…ནོ། །དེ་ནས`); where a break was added, the space it
replaces disappears into the break (no space at a line start or end). A spacing difference
is restored from the source with `--fix`; a letter difference is never "fixed" — the step
that caused it is wrong. Measured 2026-10-09: the root prose build had added a space after
`། །` 1–467 times per file, the commentary re-segmentation changed 1–12 spaces per file; all
restored, letters were identical everywhere.

## Where the rest lives

Commentary-only prompts and scripts live in their own skills: `commentary-toc-extract/prompts/`
(`pass1-candidates.md`, `verse-headings.md`), `commentary-preclean/scripts/`,
`commentary-segment/scripts/`, `commentary-resegment/scripts/`. The root-text grouping
prompts live in `root-text-group/prompts/`.

Change a file here only with both workflows in mind, and re-run the checks of both
(root: re-build the processed root texts byte-for-byte; commentary: the 8-file benchmark in
`$SYSTEM/scripts/seg-toc-benchmark/`).
