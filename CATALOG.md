# Skill catalogue

Every skill in this repo. Generated from each skill's own frontmatter —
run `python3 tools/build-catalog.py` after adding or changing one.

- **56** text-processing skills in [`rails/`](rails/README.md)
- **4** library ingestion skills in [`library/`](library/README.md)
- **17** org & engineering skills at the repo root

The rails and library skills consolidate **194**
skill files that were duplicated across six repos. See [`PROVENANCE.md`](PROVENANCE.md)
for the full mapping.

---

## rails/ — text processing


### Intake & cleanup

| Skill | Does | Absorbs |
|---|---|---|
| [`epub-to-markdown`](rails/epub-to-markdown/SKILL.md) | Convert an EPUB into structured markdown, adaptively: inspect the epub's own internal structure first, then either reuse an existing publisher-specific… | 4 |
| [`raw-to-sources`](rails/raw-to-sources/SKILL.md) | Bring one raw, human-reviewed file from the inbox into `$SOURCES/` as a cleaned, frontmattered root-text or commentary file — the first step of the ingest… | 2 |
| [`clean-raw-text`](rails/clean-raw-text/SKILL.md) | Inspect a raw text for mechanical damage — page markers, running headers and footers, OCR index numbers, stray spacing, encoding artifacts — generate a… | 5 |
| [`tibetan-ocr-quality`](rails/tibetan-ocr-quality/SKILL.md) | Calculate perplexity of a Tibetan OCR output file using KenLM and Botok normalization to assess OCR quality | 2 |
| [`json-to-source-text`](rails/json-to-source-text/SKILL.md) | Convert JSON dumps of classical texts (tipitaka.org, SuttaCentral, GRETIL exports, BDRC, custom scraped JSON) into properly formatted Markdown source-text… | 4 |
| [`json-to-commentary`](rails/json-to-commentary/SKILL.md) | Convert tipitaka.org Atthakatha and Tiká JSON exports into properly formatted Markdown commentary files for $COMMENTARIES/. Handles heading hierarchy,… | 3 |

### Formatting

| Skill | Does | Absorbs |
|---|---|---|
| [`format-root-text`](rails/format-root-text/SKILL.md) | Format and normalise a root text, a translation, or a commentary in any language that does not have a dedicated format skill — Pāli, Chinese, English,… | 5 |
| [`format-tibetan-root-text`](rails/format-tibetan-root-text/SKILL.md) | Format a Tibetan root-text markdown file into clean, navigable verse with block IDs (^chapter-verse), chapter headings with ^N-0 anchors, and one stanza… | 5 |
| [`format-sanskrit-root-text`](rails/format-sanskrit-root-text/SKILL.md) | Format and re-index a Sanskrit root-text file using the four-zone block ID scheme (^T-n pre-title, ^I-n front matter, ^N-V verses, ^N-a colophons/back… | 2 |
| [`format-commentary`](rails/format-commentary/SKILL.md) | Format a commentary for the collection: repair OCR damage, structure the headings, normalise spacing and punctuation, and apply block IDs — producing a… | 5 |

### Structure & table of contents

| Skill | Does | Absorbs |
|---|---|---|
| [`toc-generate`](rails/toc-generate/SKILL.md) | Build a Tibetan Buddhist text's ས་བཅད (sa bcad) table of contents end to end — scan the text for structural-outline candidates, copy the… | 8 |
| [`add-toc`](rails/add-toc/SKILL.md) | Generate a nested, decimal-numbered Table of Contents (TOC / dkar-chag) from a flat draft list at the top of a markdown document | 5 |
| [`tag-inline-toc`](rails/tag-inline-toc/SKILL.md) | Identify inline structural announcement phrases (sa bcad) in a formatted text file, wrap the announced terms in wikilinks, and insert standalone markdown… | 4 |
| [`outline-extract`](rails/outline-extract/SKILL.md) | Extract the structural outline (ས་བཅད། / sa bcad) already embedded in a Tibetan commentary and emit it as a standalone nested file — YAML frontmatter,… | 3 |
| [`structural-outline-ingest`](rails/structural-outline-ingest/SKILL.md) | Extract the structural outline of one source (root text, commentary, translation or reference) and write it as a citable rail at… | 4 |
| [`spine-map`](rails/spine-map/SKILL.md) | Build one commentary's routing index from its own TOC nodes and claim IDs onto the canonical spine slots of the root text — the once-per-commentary… | 1 |

### Segmentation, block IDs & transclusion

| Skill | Does | Absorbs |
|---|---|---|
| [`segment-commentary`](rails/segment-commentary/SKILL.md) | Break a commentary into short, individually-referenceable blocks — prose paragraphs, verse stanzas, quotations — so every claim can later cite one | 6 |
| [`add-block-ids`](rails/add-block-ids/SKILL.md) | Add Obsidian block IDs to a text so every verse, prose block, and heading can be cited and transcluded | 7 |
| [`transclusion`](rails/transclusion/SKILL.md) | Insert Obsidian block-transclusion links (`![[root#^N-V]]`) for root-text verses into a commentary or a second version of the root text, placing each… | 5 |

### Metadata & frontmatter

| Skill | Does | Absorbs |
|---|---|---|
| [`frontmatter`](rails/frontmatter/SKILL.md) | Populate the complete YAML frontmatter for any text file in the collection — root text, commentary, translation, or reference — by extracting the metadata… | 10 |
| [`extract-source-metadata`](rails/extract-source-metadata/SKILL.md) | Pull a source text's own metadata — title, author or composer, translator, publication details, scribe, patron, place and date — out of its first and last… | 9 |
| [`property-creator`](rails/property-creator/SKILL.md) | Adds standard properties to a file by extracting details from its title and colophon | 4 |
| [`author-metadata-sync`](rails/author-metadata-sync/SKILL.md) | Propagate human-curated author metadata (author, author_in_use, author_in_english) from the 16 commentary frontmatters in 1-SOURCES/ into the raw… | 1 |

### Terminology & glossaries

| Skill | Does | Absorbs |
|---|---|---|
| [`bilingual-glossary`](rails/bilingual-glossary/SKILL.md) | Build and maintain a project's bilingual glossary end to end: extract every source-language keyword and its attested renderings from each (source,… | 10 |
| [`interlinear-gloss`](rails/interlinear-gloss/SKILL.md) | For one root text + one translation, build an interlinear gloss file at 2-RAILS/Bilingual-Glossaries/Raw/<source>-<target>-gloss.md | 3 |
| [`keyword-extract`](rails/keyword-extract/SKILL.md) | The vocabulary-standardization pipeline | 2 |
| [`pali-biterm-extraction`](rails/pali-biterm-extraction/SKILL.md) | For a block-aligned Pāli source file and an English translation file, extract every attested English rendering for each Pāli token's morphological family… | 1 |
| [`term-definition`](rails/term-definition/SKILL.md) | Extract verbatim definitions of key terms from the commentaries and fill them into the Meaning column of the term-localization table, formatted in the… | 2 |
| [`term-localization`](rails/term-localization/SKILL.md) | Translate a text's key terms in the term-localization table into the track's target languages, deriving each rendering from the commentary-based Meaning… | 1 |

### Summaries & context

| Skill | Does | Absorbs |
|---|---|---|
| [`section-summary`](rails/section-summary/SKILL.md) | Summarise one node of a text's structural outline: first once per commentary in that commentary's own language and terminology, then as a single combined… | 6 |
| [`verse-context`](rails/verse-context/SKILL.md) | Build the context package for a verse: transclude the root verse and the relevant commentary passages, paraphrase or synthesise how each commentator reads… | 8 |
| [`multilevel-summary`](rails/multilevel-summary/SKILL.md) | Generate an audience-targeted summary of a verse or chapter from the verse and section rails, calibrating language, length, and fidelity to the specified… | 1 |
| [`local-wiki-article`](rails/local-wiki-article/SKILL.md) | Create or update a Local-Wiki article in 2-RAILS/Local-Wiki/<term>.md for one key term explained in the commentaries | 3 |

### Claims

| Skill | Does | Absorbs |
|---|---|---|
| [`commentary-claims`](rails/commentary-claims/SKILL.md) | Extract every distinct claim or fact a single commentary makes into one claims file for that commentary — stated in the commentary's own language with a… | 3 |
| [`claims-consolidate`](rails/claims-consolidate/SKILL.md) | Consolidate one topic's claims across every commentary into a single question-driven topic page — mapping each commentary in isolation, then generating… | 3 |

### Translation

| Skill | Does | Absorbs |
|---|---|---|
| [`machine-translate`](rails/machine-translate/SKILL.md) | Produce a zero-shot machine-baseline translation of a block-ID'd source text by calling a translation API on small batches of adjacent blocks, threading… | 4 |
| [`zeroshot-translate`](rails/zeroshot-translate/SKILL.md) | Translate a block-ID'd source text into a target language in one pass, either as a full citable track triangulated against a second source language and… | 3 |
| [`graded-translate`](rails/graded-translate/SKILL.md) | Produce an audience-graded, term-consistent translation of a block-ID'd verse text into any target language: first build a per-grade keyword termbase for… | 6 |
| [`translate-commentary`](rails/translate-commentary/SKILL.md) | Translate a commentary into a target language against a translation track's requirements, termbase and section rails, preserving every block ID and… | 1 |
| [`verse-translate`](rails/verse-translate/SKILL.md) | Translate a batch of verses into metrical or rhymed verse in any target language, working from `2-RAILS/Verses/<id>.md` packages rather than the bare root… | 1 |
| [`translation-qa`](rails/translation-qa/SKILL.md) | MQM-based quality check of a translation file or track in any target language, against the source text, the 2-RAILS/ verse packages, and the track's… | 2 |

### Validation

| Skill | Does | Absorbs |
|---|---|---|
| [`vault-audit`](rails/vault-audit/SKILL.md) | Read-only weekly audit of vault integrity | 0 |
| [`commentary-fact-check`](rails/commentary-fact-check/SKILL.md) | Check a translation verse by verse against the commentary tradition that grounds it, producing a graded report of every place the translation departs from… | 4 |

### Wiki article production

| Skill | Does | Absorbs |
|---|---|---|
| [`article-subject-filter`](rails/article-subject-filter/SKILL.md) | Classify every article-queue term as a standalone encyclopedic subject, section material for a named target article, or a glossary-only term — merging… | 1 |
| [`wiki-article-inventory`](rails/wiki-article-inventory/SKILL.md) | Determine, for every standalone article subject, whether the target Wikipedia (bo.wikipedia in the worked example) already has the article — via… | 1 |
| [`wiki-article-from-claims`](rails/wiki-article-from-claims/SKILL.md) | Draft a cited, readable Tibetan Wikipedia article from one consolidated claims topic page — claims-only drafting, fixed claim-resolution chain, verbatim… | 1 |
| [`gemini-article-polish`](rails/gemini-article-polish/SKILL.md) | Re-compose an existing wiki article's Tibetan prose with the Gemini API — improving flow, register, and natural Tibetan style — while freezing every fact,… | 1 |

### Plans

| Skill | Does | Absorbs |
|---|---|---|
| [`plan-scaffold`](rails/plan-scaffold/SKILL.md) | Create a new calendar-driven plan track under `$TRANSFORMATIONS/Plans/` from a session-shape declaration and a verse-distribution rule | 0 |
| [`plan-schedule`](rails/plan-schedule/SKILL.md) | Build, audit and edit a plan stream's day → verse distribution table | 2 |
| [`plan-day-generate`](rails/plan-day-generate/SKILL.md) | Author one or more day files for a plan's **authoring stream** from the stream's schedule, the verse rails and the plan's fixed assets, section by… | 4 |
| [`plan-day-translate`](rails/plan-day-translate/SKILL.md) | Produce a translation stream's day file by translating the authoring stream's day file section by section — locating each section by normalised heading… | 1 |
| [`plan-day-qa`](rails/plan-day-qa/SKILL.md) | Grade one plan day file against the plan's own contracts — structure and fidelity against the section declaration in `About <plan-name>.md`, grounding… | 1 |
| [`plan-day-package`](rails/plan-day-package/SKILL.md) | Build the machine-anchored per-day dossier that an app or API consumes: a source-of-record package that copies the day's verse rails verbatim, plus its… | 3 |

### Publishing

| Skill | Does | Absorbs |
|---|---|---|
| [`translation-alignment-check`](rails/translation-alignment-check/SKILL.md) | Report-only structural check that every translation of a text mirrors its root exactly — same segment references in the same order, same line count per… | 1 |
| [`translation-upload`](rails/translation-upload/SKILL.md) | Lint, parse and upload one finished translation to the library backend as an edition of its own text — aligned segment-for-segment to the published root… | 1 |

### Authoring skills

| Skill | Does | Absorbs |
|---|---|---|
| [`create-skill`](rails/create-skill/SKILL.md) | Scaffold a new skill completely and correctly — creates the SKILL.md with the required structure, registers it in SKILLS-CATALOG.md, creates the slash… | 3 |

---

## library/ — WeBuddhist library ingestion

> These require a checkout of `webuddhist-library-data-pipeline` — see [`library/README.md`](library/README.md).

| Skill | Does | Absorbs |
|---|---|---|
| [`annotate-root-text`](library/annotate-root-text/SKILL.md) | Pipeline 1 orchestrator | 2 |
| [`headings-not-content`](library/headings-not-content/SKILL.md) | Keep markdown headings out of an edition's uploaded content and segmentation, and build the table of contents from them instead | 0 |
| [`lint-annotations`](library/lint-annotations/SKILL.md) | Annotation-convention linter | 2 |
| [`upload-root-text`](library/upload-root-text/SKILL.md) | Pipeline 2 agent wrapper around tools/run_upload.py (lint -> parse -> upload) for a completed texts/<text-id>/annotated.md | 2 |

---

## Org & engineering skills

Pre-existing skills at the repo root — GitHub workflow, API and docs work. Not part of the rails consolidation.

| Skill | Does |
|---|---|
| [`alternative_suggestions`](alternative_suggestions/SKILL.md) | Surfaces and compares alternative ways to implement the same thing (patterns, libraries, APIs, syntax) |
| [`article-summarizer`](article-summarizer/SKILL.md) | Summarize web articles, blog posts, and news pages from URLs into concise TL;DR summaries with key takeaways |
| [`conversion-validation`](conversion-validation/SKILL.md) | Validate XML etext files using bdrc-etext-sync, then zip and upload to Google Drive on success |
| [`create-sub-issues`](create-sub-issues/SKILL.md) | General-purpose agent to ANY GitHub Project, pick a project board, break down tasks |
| [`design-engineer`](design-engineer/SKILL.md) | This skill encodes philosophy on UI polish, component design, animation decisions, and the invisible details that make software feel great inspire and… |
| [`documentation_generator`](documentation_generator/SKILL.md) | OpenPecha Organization Mode **⚠ no frontmatter — not discoverable by Claude; needs `name:` + `description:`** |
| [`frontend-backend`](frontend-backend/SKILL.md) | Full stack developer for TypeScript/Next.js and backend APIs; follows folder structure, endpoint standards, and Be Sure change discipline |
| [`frontend_design`](frontend_design/SKILL.md) | Create distinctive, production-grade frontend interfaces with high design quality |
| [`github-card-cleaner`](github-card-cleaner/SKILL.md) | You are "Issue-Refiner", an expert Agile Project Manager and Developer Assistant |
| [`github-issue-writer`](github-issue-writer/SKILL.md) | Generate structured GitHub issue cards for the WeBuddhist team |
| [`glossary_extraction`](glossary_extraction/SKILL.md) | Fetches Tibetan edition spans from the Pecha API, pulls related commentary and translation segments, runs UCCA (Layer 3 syntactic) and semantic gloss… |
| [`openAPI-spec-generator`](openAPI-spec-generator/SKILL.md) | Generate complete OpenAPI 3.0 specification YAML files from brief natural-language API requirements or from a requirements file |
| [`openpecha-api-master`](openpecha-api-master/SKILL.md) | Master guide for the OpenPecha backend codebase — a Tibetan Buddhist digital library API. Use when working on any code in openpecha-backend: writing… |
| [`sanity-check-github-tracker`](sanity-check-github-tracker/SKILL.md) | Org Commit Monitor **⚠ no frontmatter — not discoverable by Claude; needs `name:` + `description:`** |
| [`sherab-assistant`](sherab-assistant/SKILL.md) | Answer Open edX questions by searching and summarizing relevant threads from discuss.openedx.org |
| [`userback-to-githb`](userback-to-githb/SKILL.md) | **Skill Name: Userback-to-GitHub Requirements Engineer** **⚠ no frontmatter — not discoverable by Claude; needs `name:` + `description:`** |
| [`sprint-release-notes`](skills/sprint-release-notes/SKILL.md) | Automatically generate sprint release notes from a GitHub Project Board and publish to their respective repositories |

---

## Not in this repo

Deliberately left in their home vaults, because they build a finished product
for one specific text rather than processing text in general:

| Skill | Vault |
|---|---|
| `Tara-Plan-Creator` | 21-taras-rails |
| `BCA-Daily-Practice-Plan-HHDL`, `DKR-Fellow-Plan-Generator`, `Himalayan-Plan-Transformer`, `Daily-Challenge-Creator`, `day-package-pipeline`, `english-plan-evaluator`, `practice-verse-alignment`, `BCA-Verse-Distribution-Updater`, `Verse-package-file-creator`, `AI-summary-generator`, `verse-commentary-summarizer`, `BCA-Verse-Context-Summary`, `generate-modern-chinese`, `dalai-lama-plan-translation`, `hashtag-insert` | bodhisattvacharyavatara-rails |
| `daily-tipitaka-day`, `atthakatha-summaries`, `practice-summaries` | abhidhamma-rails |
| `inbox-diff` | Liturgy-rails |
| the 17-step `cowork-pipeline/` (Wikipedia publication programme) | 21-taras-rails |
| Documentation & UX skills (`doc-audit`, `user-journey-map`, `figma-issue-handoff`, …) | webuddhist-knowledge |

If one of these turns out to generalise, bring it over and note it here.
