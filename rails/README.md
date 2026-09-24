# rails/ — text-processing skills

Everything involved in turning raw source material into a structured, citable
text: intake, cleanup, formatting, structure, segmentation, metadata,
terminology, summaries, claims, translation, and validation.

These skills came from four Obsidian vaults — `21-taras-rails`,
`bodhisattvacharyavatara-rails`, `abhidhamma-rails`, `Liturgy-rails` — and two
pipeline repos, where the same job had been re-implemented up to five times. One
copy of each lives here now.

## Read these two first

- **[`CONVENTIONS.md`](CONVENTIONS.md)** — block IDs and tag schemes. Every skill
  here implements it. When a skill and that document disagree, the document wins.
- **[`PROFILES.md`](PROFILES.md)** — what `$COMMENTARIES`, `$WORK`, `$SECTIONS`
  and the rest resolve to in the repo you are working in.

Skills refer to locations by logical name (`$COMMENTARIES/<id>.md`) rather than
hard-coded path. That indirection is the reason one skill can serve every vault
and the library pipeline — it is what the five separate `add-toc`s were paying
for in duplication.

## The usual order

**Want this run for you?** [`rails-pipeline`](rails-pipeline/SKILL.md) is the
orchestrator: it picks the pipeline for a goal, checks what a text already has,
runs each skill below in order with its completion check, stops at the human
gates, and keeps a resumable run log in `$WORK/rails-run-<text-id>.md`.

```
epub-to-markdown ─┐
                  ├─→ clean-raw-text ─→ format-*-root-text ─→ frontmatter
raw-to-sources ───┘                     format-commentary     extract-source-metadata
                                              │
                                              ▼
                              toc-generate ──→ segment-commentary ──→ add-block-ids
                                   │                                       │
                                   ▼                                       ▼
                    outline-extract / structural-outline-ingest      transclusion
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   section-summary          commentary-claims         verse-context
          │                        │                        │
          ▼                        ▼                        ▼
  bilingual-glossary       claims-consolidate        machine-translate
  keyword-extract          wiki-article-from-claims  zeroshot-translate
  term-definition                                    graded-translate
                                                     translation-qa
                                                     commentary-fact-check
```

Not every text needs every step, and several skills have separately addressable
phases — run the phase asked for, not the whole pipeline. Each skill's own
`Phases` / `Modes` table says which parts are independently useful.

## Ordering constraints that actually bite

- **`toc-generate`'s `[[N]]` pointers are computed against exact file bytes.**
  Re-segmenting a commentary after building its tree invalidates every pointer.
  Build the tree after segmentation, not before.
- **Block IDs are citations.** Once anything cites a file, re-segmenting it
  breaks those citations silently. Re-run every downstream rail if you must.
- **OCR repair happens in `format-commentary`, and nowhere else.** The
  segmentation and ID skills are bound by a no-loss assertion and cannot fix a
  character.
- **Lock the vocabulary before translating anything that will be published.**
  `graded-translate` Phase 1 builds the per-grade termbase from `keyword-extract`'s
  output; Phase 2 translates with it locked; Phase 3 checks for drift. A
  `machine-translate` / `zeroshot-translate` Mode 3 output is a first look, not a
  release candidate — regenerate it through `graded-translate` and run
  `commentary-fact-check` before upload.
- **Never translate in `section-summary` Phase 1.** That phase's original-language
  terminology is the evidence `bilingual-glossary` and `term-definition` read.
