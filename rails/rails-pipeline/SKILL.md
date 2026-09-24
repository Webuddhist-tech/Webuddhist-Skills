---
name: rails-pipeline
description: >
  Orchestrate the rails skills end to end: pick the right pipeline for a goal,
  detect what a text already has, then run each rails skill in order with its
  own completion checks and the human gates between them. This skill does no
  text work itself; it sequences the others and keeps a resumable run log.

  Trigger this skill whenever the user says things like: "run the rails on this
  text", "what's next for this commentary", "take this raw file all the way to
  a translation", "resume the pipeline", "which skills do I need for X", or
  "plan the work for a new text".
profile: any
supersedes: []
---

# rails-pipeline — orchestrator for the rails skills

This skill does no text work itself. It decides **which** rails skill runs next,
**in what order**, and **whether the previous one actually finished**, then hands
off to that skill's own SKILL.md. Every real rule (block IDs, file formats,
completion checks) lives in the individual skills and in `rails/CONVENTIONS.md`.
When this file and a skill disagree, the skill wins; when a skill and
`CONVENTIONS.md` disagree, `CONVENTIONS.md` wins.

---

## Step 0 — Load the ground rules (every run)

1. Read `rails/CONVENTIONS.md` (block IDs, heading `-0` anchors, commentary
   labels, `^toc-` namespace, inline sa bcad links).
2. Read `rails/PROFILES.md` and resolve the logical names (`$WORK`,
   `$SOURCE_TEXTS`, `$COMMENTARIES`, `$GLOSSARIES_RAW`, `$CLAIMS`, `$SECTIONS`,
   `$VERSES`, `$TRANSFORMATIONS`, `$SYSTEM` ...) for the repo you are in.
   A `.claude/skill-profile.yml` in the repo overrides the table.
   - `rails-vault` profile: 21-taras-rails, tara-sadhana-rails,
     bodhisattvacharyavatara-rails, abhidhamma-rails, Liturgy-rails.
   - `library-pipeline` profile: webuddhist-library-data-pipeline (`texts/<text-id>/`).
3. If a folder a skill needs does not exist in this vault (e.g. no
   `Commentaries/` in Liturgy-rails, no `Claims/` outside 21-Taras), say so and
   stop that branch. Never invent a location.
4. Where to load each skill from: the canonical copy is
   `rails/<skill>/SKILL.md` in this repo. Vaults also carry copies under
   `4-SYSTEM/Skills/`, often under **legacy names** (table at the end). Prefer the
   canonical copy; if the vault copy differs, note it for `vault-audit`.

**Permission floor (never break):** `1-SOURCES/` may only receive structural edits
(block boundaries, block IDs, navigation links, factual `[Ed: ...]` notes).
Rewording or glossing source text is forbidden — that belongs in `2-RAILS/` or
`3-TRANSFORMATIONS/`. Material flows left to right: a later stage never writes
back into an earlier one.

---

## Step 1 — Pin down the goal and the inputs

Ask (only for what is missing):

- **Goal** — which end product? (formatted source, sa bcad/TOC, verse packages,
  glossary, translation track, Wikipedia article, audience adaptation, audit).
- **Text** — the text-id / file(s), and whether each file is a **root text** or a
  **commentary** (never infer this from content).
- **Language(s)** — source language (bo, sa, pi, zh) and target language + track
  / audience / grade if translating.
- **Scope** — whole text, chapter range, one verse, one TOC node, one topic.

Then pick the pipeline(s) from Step 2. Most goals need an earlier pipeline to be
complete first; walk backwards from the goal to the first missing artifact.

---

## Step 2 — The pipelines

Each pipeline lists skills in run order. `→` means "must finish first". For a
skill with phases/modes, run only the phase the job needs, as named.

### P1 — Intake: get the file into the vault

Pick the entry that matches the arrival format:

| Arrives as | Run |
|---|---|
| EPUB | `epub-to-markdown` |
| JSON dump (tipitaka.org, SuttaCentral, GRETIL, BDRC) — root text | `json-to-source-text` |
| tipitaka.org Atthakatha / Tika JSON — commentary | `json-to-commentary` |
| Raw OCR / segmentation `.txt` / `.docx.txt` | `tibetan-ocr-quality` (optional, Tibetan OCR only — perplexity check before investing work) → `raw-to-sources` (`--type root` or `--type commentary`) |

Then:

`clean-raw-text` (Mode 1 raw text / Mode 2 commentary) → one formatter:

| File | Formatter |
|---|---|
| Tibetan root text | `format-tibetan-root-text` |
| Sanskrit root text (four-zone IDs) | `format-sanskrit-root-text` |
| Any other root text | `format-root-text` |
| Commentary (Tibetan / Chinese / full pipeline) | `format-commentary` (Mode 1 / 2 / 3). **OCR repair happens here and nowhere else.** |

→ metadata: `frontmatter` (Variant 1 root / 2 commentary / 3 translation) and
`extract-source-metadata` (colophon / first-last page). `property-creator` is the
lightweight title+colophon property pass when full frontmatter is not needed.

**Done when:** the file sits in `$SOURCE_TEXTS/` or `$COMMENTARIES/` with complete
frontmatter (`registered_id` on commentaries) and passes the formatter's check.

### P2 — Structure: sa bcad, segmentation, block IDs, transclusion

Root text:

- `structural-outline-ingest` (optional — only if the author/edition provides
  divisions beyond chapter/verse) and/or `tag-inline-toc` (only for texts that
  announce their own sections inline; run after a `format-*-root-text`).
- `add-toc` when a flat draft TOC list must become a nested `^toc-X-Y-Z` block.

Commentary (order matters):

1. `segment-commentary` — Phase 1 (continuous prose) or Phase 2 (one clause per
   line) into citable blocks.
2. `toc-generate` — full run Phase 0 → E builds the verified sa bcad tree and
   ingests it as headings. **Build the tree after segmentation**: its `[[N]]`
   pointers are computed against exact file bytes. Shorter entries: Phase 0 → A
   (candidate scan only — never citable), Phase E only (tree already exists),
   Simple mode (quick two-level TOC).
3. If headings shifted block boundaries, re-run `segment-commentary` (its
   re-draw case) **before anything cites the file**.
4. `add-block-ids` — every `##` must already carry its hand-written `^label-0`
   (Mode 1). Never generate or edit `##` labels.
5. `transclusion` — insert `![[root#^N-V]]` for root verses (Mode 1 verbatim
   quotes / Mode 2 sa bcad-introduced; Stages 1 → 2 → 3).

Standalone outline for readers: `outline-extract` (writes the flat and nested
ས་བཅད files to `$TRANSFORMATIONS/Adaptations/<id>-sa-bcad/`).

**Done when:** block IDs present and valid, TOC tree QC-clean
(`status: complete`), transclusions placed. From here on, **block IDs are
citations** — re-segmenting breaks every downstream rail silently.

### P3 — Commentary rails: meaning per section and per verse

Requires P2 on every commentary involved.

- `section-summary` — Phase 1 once per commentary per TOC node (original
  language, **never translate in Phase 1**), then Phase 2 combined across
  commentaries with an English translation → `$SECTIONS/<node-id>.md`.
- `verse-context` — per-verse package (root verse + commentary passages +
  disambiguated restatement) → `$VERSES/<verse-id>.md`. Needs the verse to exist
  in a `$SOURCE_TEXTS/` file first.
- `commentary-claims` — one claims file per commentary (Strategy 1 tree-guided,
  needs the `toc-generate` tree) → `$CLAIMS/raw/tree-guided/<registered-id>.md`.

### P4 — Terminology: glossary, keywords, definitions

Two routes produce locked terminology; they have different blind spots, so use
both when the vocabulary matters.

**Route A — glossary (block-aligned tally).** Needs a block-aligned translation
(a human translation, or a zero-shot baseline from P5 step 1).

1. `interlinear-gloss` — one gloss file per (root text, translation) at
   `$GLOSSARIES_RAW/<src>-<tgt>-gloss.md`. Validate clean
   (`scaffold_gloss.py --validate`) before moving on.
2. `bilingual-glossary` Phase 1 (extract raw per-source glossary) → Phase 2
   (combine per language pair) → Phase 3 (contest: rank terms whose renderings
   disagree) → **human decision** → Phase 4 (select the per-track working
   glossary). Phase 4 output is a **hard constraint** for `zeroshot-translate`
   Mode 2 and `translate-commentary`.
3. Pāli texts: `pali-biterm-extraction` for full morphological families.

Blind spot: keeps only terms attested in several blocks — a rare but important
term (a name or technical term that appears once or twice) is dropped.

**Route B — keywords (statistical ranking).**

1. `keyword-extract` — Mode 1 (Tibetan text's English translation: YAKE per
   verse, optional corpus TF-IDF, then enrich each keyword with the Tibetan term
   it renders in that verse) or Mode 2 (Pāli).
2. Feeds `graded-translate` Phase 1 (per-grade termbase) and the article
   pipeline (P6).

Blind spot: reads one language, so two different source terms rendered by the
same target word can be merged; the Tibetan mapping step is where errors enter.

When both routes run, reconcile: Route A wins on attested consistency; Route B
adds rare-but-salient terms Route A dropped — send those to Phase 3 as
contested, not straight into the locked glossary.

Definitions and localisation (BCA-style term tables):

- `term-definition` — verbatim commentary definitions into the Meaning column of
  `$LOCAL_WIKI/BCA-Term-Localization.md` → `term-localization` renders each term
  into En / Zh / Hin / Nep / Rus / Mon **from that Meaning column**.
- `local-wiki-article` — reference of last resort for a term the glossary does
  not capture; original language, cited.

### P5 — Translation

1. **Baseline (first look, never a release candidate):** `machine-translate`
   (Engine 1 Gemini / Engine 2 DharmaMitra) or `zeroshot-translate` Mode 3
   (unconstrained, audience-guided). Block IDs must match the source exactly.
2. **Lock the vocabulary before anything that will be published** — P4 Route A
   Phase 4 glossary and/or Route B → `graded-translate` Phase 1 termbase.
3. **Controlled translation** — choose one:

   | Job | Skill |
   |---|---|
   | Graded tracks (beginner / general / intermediate / advanced) | `graded-translate` Phase 1 → 2 (locked) → 3 (drift check) |
   | One pass with a locked glossary | `zeroshot-translate` Mode 2 |
   | Triangulated against human translations + second source language | `zeroshot-translate` Mode 1 |
   | Metrical / rhymed verse from verse packages | `verse-translate` (needs P3 `verse-context`) |
   | A whole commentary | `translate-commentary` (needs termbase + P3 section summaries) |

4. **QA loop (both mandatory before upload):** `translation-qa` (MQM scorecard,
   pass/fail gate) and `commentary-fact-check` Phase 1 (grade against the
   commentaries) → Phase 2 (apply mechanical fixes only, log the rest) →
   **re-run `translation-qa`** (a stale QA report is worse than none).
5. If a fix forces a term to change, change it in `bilingual-glossary` Phase 4
   (or the termbase) and re-translate — never let glossary and translation drift.

**Never** set `status: complete` on your own output — report, and let a human
promote it.

### P6 — Wikipedia article pipeline (21-Taras layout)

Requires P2 + P3 `commentary-claims` for every commentary, and a literal English
translation of the root text. Follow `4-SYSTEM/Guidelines/keyword-extraction-methodology.md`.

1. `keyword-extract` Mode 1 → methodology Steps 2–6 (locate occurrences, map to
   Tibetan terms / term registry, count, composite score, viability gate) →
   `article_queue.json`.
2. `article-subject-filter` → `article_subjects.json` (standalone / section of X /
   glossary-only, with reasons).
3. `wiki-article-inventory` → `wiki-inventory.yaml` + snapshots (does bo.wikipedia
   already have it?). Needs network to bo.wikipedia.org and wikidata.org.
4. `author-metadata-sync` — push human-curated author names into the raw claims
   files; fix any mismatches it reports first.
5. `spine-map` — per commentary, route TOC nodes and claim IDs onto the root
   text's spine slots.
6. `claims-consolidate` Phase 1 (topic page) → Phase 2 (adversarial attribution
   audit). **Never draft from an unaudited page.**
7. `wiki-article-from-claims` → `article.md`, `citations.md`, `article-preview.md`.
8. `gemini-article-polish` — pilot mode by default; `in-place` only on explicit
   human instruction after domain-expert review.

### P7 — Audience adaptations

- `multilevel-summary` — kids / general / academic summary of a verse or chapter
  (BCA; needs P3 rails).
- `outline-extract` — reader-facing sa bcad files (see P2).

### P8 — Maintenance and tooling

- `vault-audit` — read-only integrity report (skills sync, frontmatter,
  citation chain, status, stale inbox, dead links). Run weekly and after any
  pipeline run that touched many files.
- `tibetan-ocr-quality` — OCR perplexity before intake.
- `create-skill` — scaffold and register a new skill in all four places.

---

## Step 3 — Detect what already exists

Before planning, check artifacts (resolve paths via the profile). An artifact
that exists **and** passes its skill's completion check means that step is done.

| Check | If present |
|---|---|
| File in `$SOURCE_TEXTS/` / `$COMMENTARIES/` with frontmatter | P1 done |
| Every content block ends in ` ^id`; `##` carry `^label-0` | block IDs done |
| `$SECTIONS_RAW/toc-tree/<id>.md` with `status: complete` | TOC tree done |
| `![[...#^N-V]]` lines in the commentary | transclusion done |
| `$SECTIONS_RAW/<commentary>/<node>.md`, `$SECTIONS/<node>.md` | section summaries |
| `$VERSES/<verse-id>.md` | verse packages |
| `$CLAIMS/raw/tree-guided/<id>.md` | claims extracted |
| `$GLOSSARIES_RAW/<src>-<tgt>-gloss.md` (validates) | interlinear gloss done |
| `$GLOSSARIES_RAW/<src>-<tgt>.md` / `$GLOSSARIES/<src>-<tgt>.md` | glossary Phase 1 / 2 |
| `*-keywords.md`, `*_verse_keywords.json`, `*_termbase.json` in `$WORK` | keyword-extract ran |
| `$TRANSFORMATIONS/Translations/<track>/` with `termbase.md` + chapters | translation track |
| `qa-report.md` newer than the translation file | QA current |
| `$WORK/rails-run-<text-id>.md` | a previous orchestrated run — resume from it |

Also flag hazards you find: `^TOC-N` anchors (deprecated — must become `^N-0`
before use), zero-padded IDs, a TOC tree older than the last segmentation, a QA
report older than the translation.

---

## Step 4 — Plan, confirm, then run one skill at a time

1. Write the plan as a numbered run list: skill, phase/mode, input, expected
   output, and which human gates it hits. Show it to the user and confirm before
   running anything that edits files.
2. For each step:
   - Load that skill's SKILL.md and follow it exactly; run only the phase named.
   - Run the skill's own **Completion check**. If it fails, stop, report, and do
     not start the next step.
   - Append a line to the run log (below).
3. Stop at every human gate and wait:
   - `raw-to-sources` / `clean-raw-text`: root vs commentary, missing text-id.
   - `add-block-ids` Mode 1: `##` labels are hand-written by a contributor.
   - `toc-generate` Phase D: QC failures or repair decisions.
   - `bilingual-glossary` Phase 3 → 4: which rendering wins for contested terms.
   - Article queue / subject list review (P6 steps 1–2) when the methodology
     calls for it; never auto-seed a ledger from keyword output.
   - `claims-consolidate` Phase 2 findings.
   - `commentary-fact-check` Phase 2 items skipped for human judgment.
   - `gemini-article-polish` pilot → in-place.
   - Any promotion to `status: complete`.
4. Long, per-unit skills (per commentary, per TOC node, per verse, per topic):
   batch them, checkpoint after each unit in the run log so a later session can
   resume, and use isolated subagents where the skill says so (`toc-generate`,
   `commentary-claims`).

### Run log

Write `$WORK/rails-run-<text-id>.md` (create if missing, append otherwise):

```markdown
# rails run — <text-id>
goal: <goal>  profile: <rails-vault|library-pipeline>

| # | date | skill | phase/mode | input | output | check | notes |
|---|---|---|---|---|---|---|---|
| 1 | 2026-09-23 | clean-raw-text | Mode 2 | raw.md | cleaned.md | pass | |
| 2 | ... | toc-generate | 0→E | ... | ... | FAIL | QC: 3 orphan nodes — waiting on human |

next: <the next step, or the gate being waited on>
```

---

## Ordering rules that actually bite

- Segment **before** building the TOC tree; re-segmenting after the tree (or
  after anything cites the file) invalidates `[[N]]` pointers and block-ID
  citations — rebuild every downstream rail that cites it.
- OCR repair only in `format-commentary`; segmentation and ID skills cannot fix
  a character (no-loss assertion).
- `section-summary` Phase 1 stays in the original language — it is the evidence
  `bilingual-glossary` and `term-definition` read.
- Lock vocabulary before any translation meant for publication; a
  `machine-translate` / `zeroshot-translate` Mode 3 output is a first look only.
- `translation-qa` and `commentary-fact-check` both run before upload, and QA is
  re-run after every fix round.
- An unaudited claims page never feeds `wiki-article-from-claims`.

---

## Legacy skill names in the vaults

Vault `4-SYSTEM/Skills/` folders still use pre-consolidation names. Map them to
the canonical rails skill (and phase) before loading:

| Vault name | Canonical rails skill |
|---|---|
| `glossary-extract-raw` | `bilingual-glossary` Phase 1 |
| `glossary-combine` | `bilingual-glossary` Phase 2 |
| `glossary-select` | `bilingual-glossary` Phase 4 (Phase 3 = contest, `find_contested.py`) |
| `english-keyword-extraction` | `keyword-extract` Mode 1 |
| `gemini-translate` / `dharmamitra-translate` | `machine-translate` Engine 1 / Engine 2 |
| `section-summary-raw` / `section-summary-combined` | `section-summary` Phase 1 / 2 |
| `claims-consolidation` / `claims-consolidation-audit` | `claims-consolidate` Phase 1 / 2 |
| `commentary-fact-check-apply-fixes` | `commentary-fact-check` Phase 2 |
| `toc-candidate-extraction` | `toc-generate` Phase 0 → A |
| `toc-tree-extraction` + `toc-tree-ingest` / `TOC-to-HEADING` | `toc-generate` full run / Phase E |
| `commentary-segmentation` / `commentary-resegment` / `block-resegmentation` | `segment-commentary` |
| `Obsidian-Block-ID-to-Commentary` / `commentary-verse-id` / `add-block-id-root-text` | `add-block-ids` |
| `Transclude-Rootexto-Commentary` | `transclusion` |
| `Outline-Extractor` | `outline-extract` |
| `root-text-frontmatter` / `commentary-frontmatter` / `reference-frontmatter` | `frontmatter` Variants |
| `colophon-metadata-extractor` / `source-property-extractor` | `extract-source-metadata` |
| `term-definition-from-commentaries` | `term-definition` |
| `clean-commentary-text` | `clean-raw-text` Mode 2 |

Any name not in this table: check `PROVENANCE.md` at the repo root, the vault's
`4-SYSTEM/Skills/SKILLS-CATALOG.md`, and `rails/README.md` before guessing.

## Out of scope

Upload to the WeBuddhist library (`library/` skills: `annotate-root-text`,
`lint-annotations`, `upload-root-text`) runs after this pipeline under the
`library-pipeline` profile; hand off rather than orchestrating it here.
