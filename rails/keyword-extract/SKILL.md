---
name: keyword-extract
description: >
  Extract ranked, domain-specific keywords from a translation — per verse or
  per file — using statistical ranking against a general-language corpus, and enrich
  each keyword with the source-language term it actually renders.

  Trigger on "extract the keywords", "what are the key terms here", "rank the
  terminology", "pull the domain vocabulary out of this translation", "TF-IDF the
  translation".

  Feeds glossary and termbase work.
profile: any
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/english-keyword-extraction/SKILL.md
  - abhidhamma-rails/4-SYSTEM/Skills/pali-keyword-extraction/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Extract ranked keywords from a translation

| Mode | Source language | Method |
|---|---|---|
| 1 — English translation of a Tibetan text | Tibetan | YAKE + spaCy, optional TF-IDF against a general-English IDF corpus; each keyword enriched with its Tibetan term |
| 2 — English translation of a Pāli text | Pāli | TF-IDF against the Google-10k Zipf table; unigrams and compound phrases |

Both rank against a **general-language** corpus, which is the point: raw frequency
just returns "the", "is", "one". What matters is the term that is common *here* and
rare in ordinary English.

Mode 1's enrichment step — attaching the Tibetan term each English keyword actually
renders, in context — is what makes the output usable by `bilingual-glossary`. A
ranked list of English words with no source-side anchor is a reading aid, not a
glossary input.

---

## Mode 1 — English keywords from a Tibetan text's translation

Keyword statistics behave badly on classical Tibetan directly: tokenization is
contested, no standard reference corpus exists (open-questions.md Q7), and the
team's Tibetan-only prompt (forum topic 289) is documented to over-return
phrase fragments. This skill routes around all three problems by extracting
keywords from an **English translation** — where YAKE/TF-IDF are
well-conditioned — and then mapping each keyword back to the Tibetan term it
renders, verse by verse.

If the corpus has no English translation yet, produce one first with
`$SKILLS/zeroshot-translator/` (block-ID-preserving), or use any
existing published translation whose verses carry `^chapter-verse` IDs.

### Pipeline

#### Step 1 — extract keywords per verse (deterministic)

```bash
python3 scripts/keywords.py --input <en-translation>.md --output <out>/verse_keywords.json
```

`keywords.py` (YAKE + spaCy noun-phrase filtering) reads a block-ID'd English
translation and writes `{verse_id: {text, keywords: [{key, rank, score,
count}]}}`. Requires `pip install yake spacy` + the `en_core_web_sm` model
(see `scripts/requirements.txt`).

#### Step 2 (optional) — corpus-level TF-IDF report

```bash
python3 scripts/generate_en_translation_idf.py
```

Ranks terms across the whole translation against the bundled Reuters-21578
general-English IDF table (`scripts/idf_corpus.py`, regenerable with
`scripts/generate_idf_corpus.py`). Use this to pick the corpus-level top-N
key terms rather than per-verse ones.

#### Step 3 — enrich with Tibetan equivalents

Two routes; prefer (a) in a Claude session:

**(a) No API — Claude does it directly.** For each verse's keywords, add a
`"bo"` field with the Tibetan term that the English keyword *renders in that
verse* — the contextually correct term, not a dictionary lookup. Consult the
aligned Tibetan verse (same `^chapter-verse` ID in the root text) to see which
Tibetan word the translator was rendering. Write the enriched JSON alongside
the input with suffix `_en_bo_keyword_meaning_enriched.json`. Checkpoint
every 50 verses. Report totals and gaps when done.

**(b) Batch via Gemini** (reads `GEMINI_API_KEY` from the environment,
never hardcoded):

```bash
python3 scripts/enrich_en_bo_keyword_meaning.py --input <out>/verse_keywords.json
```

### Output contract

```json
{
  "1-1": {
    "text": "English verse text",
    "keywords": [
      {"key": "bodhisattva", "rank": 1, "score": 0.001, "count": 2, "bo": "བྱང་ཆུབ་སེམས་དཔའ།"}
    ]
  }
}
```

- Verse keys are the root text's `^chapter-verse` block IDs — the same IDs the
  aligner uses, so a keyword's commentary spans are one `spans_for_term` call
  away.
- Every `bo` value ends with a shad `།` (matching the team's term-list
  convention from forum topic 289).
- The Tibetan term must actually occur in the Tibetan verse (or be its
  standard citation form) — if uncertain, use the closest established term
  and note it in a `"note"` field rather than silently guessing.

### Feeding the article pipeline

The enriched list is a *candidate* term list. To use it for a corpus:

1. Aggregate `bo` terms across verses; rank by count and per-verse rank.
2. Intersect with the curated registry (`corpora/<id>/terms.yaml`) if one
   exists; otherwise propose the top terms for human review — the human
   approves the list before extraction runs (PLAN.md §3, stage 3).
3. Never auto-seed the ledger from this output without review.

### Provenance

Ported 2026-08-01 from
`bodhisattvacharyavatara-rails/$SYSTEM/scripts/english_keyword/`
(scripts verbatim: `keywords.py`, `generate_en_translation_idf.py`,
`generate_idf_corpus.py`, `enrich_en_bo_keyword_meaning.py`, `idf_corpus.py`,
`requirements.txt`; the BCA-specific `output/` runs and the redundant
`idf_corpus.pkl` were not carried over). Step 3(a) is the API-free
`bo-keyword-enrich-simple.skill` bundled in the same directory, inlined here.
The source pipeline is documented end-to-end in that repo's
`$SYSTEM/bca-translation-pipeline.md` and was run in production on the BCA
with the David Karma Choephel translation.

---

## Mode 2 — English keywords from a Pāli text's translation

Runs **Pass 1 only** of the bilingual extraction pipeline: TF-IDF keyword selection on an English translation file, with n-gram compound phrase detection.

Use this skill when you want the keyword list independently — for tuning, debugging, or feeding into a separate co-occurrence step.

---

### Inputs

| Input | Description | Path pattern |
|---|---|---|
| Target file | English translation markdown with block IDs | `$TRANSFORMATIONS/Translations/<track>/<lang-tag>-<text>-<translator>.md` |
| Output path | Path for the keyword list | `$WORK/<name>-keywords.md` |

---

### Output

A ranked Markdown file — one keyword per line with its TF-IDF score — sorted descending:

```
## English keywords — <source filename>
## Method: block-level TF-IDF × Google-10k Zipf IDF; compound phrases via n-gram detection
## N blocks, K keywords selected

phenomena: 8.24
wholesome: 7.91
right concentration: 7.55
initial application: 7.43
contact: 6.88
feeling: 6.71
perception: 6.62
volition: 6.54
sustained application: 6.40
jhāna: 6.31
```

---

### Procedure

#### Step 1 — Run keyword extraction

```bash
python3 $SKILLS/pali-biterm-extraction/scripts/pali_biterm_extraction.py \
    <en_file> \
    $WORK/<name>-keywords.md \
    --keywords-only
```

Example:

```bash
python3 $SKILLS/pali-biterm-extraction/scripts/pali_biterm_extraction.py \
    $TRANSFORMATIONS/Translations/en-Contemporary-English-Abhidhamma/en-dhammasangani-ai.md \
    $WORK/dhammasangani-keywords.md \
    --keywords-only
```

Optional flags:

| Flag | Default | Effect |
|---|---|---|
| `--top N` | 600 | Maximum keywords to output |
| `--max-phrase N` | 4 | Maximum phrase length in words |

#### Step 2 — Review

Open the output file and check that:
- Core Abhidhamma terms appear near the top (e.g. `phenomena`, `wholesome`, `right concentration`)
- Compound phrases are correctly detected (e.g. `initial application`, `right mindfulness`)
- Common English words with low IDF are absent

---

### Completion check

- [ ] Script ran without errors
- [ ] Output written to `$WORK/`
- [ ] Core domain terms appear in top 20
- [ ] Compound phrases detected for major multi-word terms

---

## After this skill

`bilingual-glossary` Phase 1 turns ranked keywords plus their source terms into a raw
per-source glossary. For Pāli, `pali-biterm-extraction` goes further, building the
full morphological family for each term.
