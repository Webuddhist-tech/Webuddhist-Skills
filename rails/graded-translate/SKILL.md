---
name: graded-translate
description: >
  Produce an audience-graded, term-consistent translation of a block-ID'd verse
  text into any target language: first build a per-grade keyword termbase for
  that language on top of the keyword-extract output or the rails' own concept
  lists (beginner / general / intermediate / advanced, rank-cut and
  register-adapted, optionally seeded from an attested human translation), then
  translate chapter by chapter with every termbase rendering locked, then run
  the mechanical drift check.

  Trigger on "translate to <language> by audience level", "beginner Hindi version",
  "scholarly English translation", "term-consistent Vietnamese", "grade-level
  keywords", "build the <language> termbase", "standardise the vocabulary before
  translating", "check the translation for termbase drift".

  This is the vocabulary-standardised path. Use `machine-translate` or
  `zeroshot-translate` Mode 2 for a rough first look; use this skill for anything
  that will be published or fact-checked.
profile: rails-vault
supersedes:
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/english-translation/bo-en-translate-skill.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/hindi-translation/bo-hi-keyword-grade-skill.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/hindi-translation/bo-hi-translate-skill.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/vietnamese-translation/bo-vi-keyword-grade-skill.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/vietnamese-translation/bo-vi-translate-skill.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/scripts/termbase-consistency-check/check_termbase_consistency.py
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.
>
> One extra location this skill leans on: **`$KEYWORDS`** (`2-RAILS/Keywords/`,
> laid out per `rails/CONVENTIONS.md` §9) — `keyword-extract` writes its output to
> `$KEYWORDS/shared/`, and this skill keeps each target language's termbase and
> grade files in `$KEYWORDS/<tgt>/`. The track's `termbase.md` is exported from
> that JSON; it is what reviewers and `translation-qa` read.
>
> The bundled scripts read the source-language fields as `bo` / `bo_text`, so for a
> Tibetan source `<src>_text` below is `bo_text`. A non-Tibetan source needs the
> scripts extended first.

# Graded, term-locked translation

| Phase | Does | Input | Output |
|---|---|---|---|
| 1 — Keyword grade | Builds the target-language termbase, one file per audience grade, on top of the source-enriched keyword inventory | keyword source (see below) · base termbase · optional attested translation | `$KEYWORDS/<tgt>/<src>_<tgt>_keyword_<grade>.json` + the track's `termbase.md` (exported from it) |
| 2 — Translate | Translates chapter by chapter at the grade's register with every termbase rendering locked | one grade file from Phase 1 + the track contract | `$TRANSFORMATIONS/Translations/<tgt>-<grade>/<text-id>-<tgt>-<grade>.md` |
| 3 — Drift check | Mechanically verifies that every locked rendering actually appears in every verse that needs it | termbase + translation (+ verse rails) | pass / MISSING table |

Run the phase asked for. Phase 2 refuses to run without its Phase 1 file — it
must not improvise term choices. Phase 3 is the check that makes "term-consistent"
a claim rather than a hope; `commentary-fact-check` is the separate accuracy
backstop that runs after it.

**Why this exists.** A zero-shot translation renders each verse (or each API
batch) independently. The same source term can come out three different ways
across a long text and nothing flags it. Locking the vocabulary *before*
translating — at the register the audience needs — is what makes the output
publishable and checkable. One vault's end-to-end run of the chain is written
up in [`references/worked-example.md`](references/worked-example.md); it is a
history, not a contract.

**Language is a parameter, not a fork.** The original vault had one skill pair
per language that differed only in the target code and the register table. Here
`<src>` is the source-language tag and `<tgt>` the target ISO code (`en`, `hi`,
`vi`, `zh`, `ne`, `mn`, …), the JSON fields are `<tgt>` / `<tgt>_text`, and the
per-language register tables live in §Registers below. To add a language, add
its register table; do not copy the skill.

**The pivot is an input.** Phase 1 keys its termbase on a **pivot translation**:
any block-ID-aligned translation of the same text. That is normally a reviewed
human translation in `$TRANSLATIONS/`, but a `zeroshot-translate` **Mode 2**
unconstrained draft will do when no human translation exists — that is exactly
what Mode 2 is for. Name the pivot in the run and record it in the output
frontmatter. Nothing here requires the pivot to be English; English is simply
the most commonly available pivot.

---

## Inputs

| Input | Phase | Required | Description |
|---|---|---|---|
| **Target language** `<tgt>` | 1, 2, 3 | ✓ | ISO code. Determines file names and which register table applies. |
| **Grade(s)** | 1, 2 | ✓ | `beginner`, `general`, `intermediate`, `advanced`, or `all` (Phase 1 only). Ask if not given. |
| **Source root text** | 1 | ✓ | The root text this vault translates, **per `$SYSTEM/Guidelines/vault-annex.md`** — canonical verse text with `^verse-id` markers under `$SOURCE_TEXTS/`. |
| **Pivot translation** | 1 | ✓ | Any block-ID-aligned translation of the same text: a human translation in `$TRANSLATIONS/`, or a `zeroshot-translate` Mode 2 draft from `$WORK/zeroshot/`. Its keys are what the termbase is keyed on. |
| **Keyword source** | 1 | ✓ | **Either** `keyword-extract`'s enriched output in `$KEYWORDS/` (`{verse_id: {text, keywords:[…]}}` with a source-language meaning per keyword), **or** the rails: the `concepts_in_verse:` and `concepts_in_commentary:` lists in `$VERSES/<id>.md`. Use the rails when no keyword-extract run exists — they are the descriptive record of which terms each verse turns on, which is exactly what the cutoff is applied to. Say in the report which source was used. |
| **Base termbase** | 1 | ✓ (built if absent) | `$KEYWORDS/<tgt>/<pivot>-<src>-<tgt>-termbase-general.json`. If missing, build it from another language's base (same pivot key set), dropping that language's field and filling `<tgt>` per §Registers. |
| **Track contract** | 1, 2 | ✓ | `$TRANSFORMATIONS/Translations/<tgt>-<grade>/` must carry `requirements.md`, `audience.md` and `termbase.md`. If the folder or any contract file is missing, create the folder and the three files first (register/grade from §Registers, audience from the grade's row) — a track without its contract is not a track. |
| **Attested translation** | 1 | optional | An existing human or reviewed translation in `<tgt>`, block-ID aligned. Its renderings are authoritative and override the base termbase. Its frontmatter `track:` may name the grade it seeds (default: general/intermediate). |
| **Source text to translate** | 2 | ✓ | The `<src>_text` (source language) or the pivot `text` field of the grade file. Prefer the source language when the translator can read it; say which in the output frontmatter. |
| **Verse scope** | 2, 3 | optional | Chapter(s) or verse IDs. Default: all. |

---

## Phase 1 — Keyword grade: build the per-grade termbase

### Grade levels

| Grade | Audience | Keyword rank cutoff |
|---|---|---|
| `beginner` | General public, new to Buddhism | rank ≤ 200 |
| `general` | Educated general reader | rank ≤ 500 |
| `intermediate` | Students with basic Buddhist study | rank ≤ 500 |
| `advanced` | Scholars, monks, serious practitioners | all ranks |

Rank comes from the keyword source: `keyword-extract`'s corpus-level TF-IDF /
YAKE rank where that run exists, otherwise a rank derived from the rails —
count how many verses list each term in `concepts_in_verse:` /
`concepts_in_commentary:` and rank by descending frequency, ties broken by
first occurrence. The cutoff controls how much vocabulary the grade *exposes as
locked terms*; it does not change which verses are translated.

### Grade classification — keywords

**beginner** — terms a newcomer understands after one teaching:
> buddha, dharma, karma, compassion, virtue, mind, suffering, body, death, birth, joy, faith, peace

**intermediate** — terms requiring study of basic Buddhist philosophy:
> bodhichitta, bodhisattva, emptiness, samsara, nirvana, merit, refuge, precepts, mindfulness,
> attachment, afflictions, wisdom, samadhi, dedication, renunciation, patience, diligence

**advanced** — technical Abhidharma, Madhyamaka, or tantric terminology:
> dharmakaya, tathagatagarbha, alayavijnana, dependent origination (technical), two truths,
> trikaya, prajnaparamita, madhyamaka, shamatha, vipashyana, any transliterated Skt/Tib term

When a keyword sits on a boundary, assign the lower (more accessible) grade.

### Termbase structures

**The termbase is built as JSON and published as markdown.** The JSON files below,
under `$KEYWORDS/<tgt>/`, are what this skill and its scripts build, validate and
check against. The track's `termbase.md` is exported from them with
`termbase_to_md.py`; it is the contract the rest of the vault reads, the thing
`translation-qa` checks against, and the file a human reviews. Change a rendering
in the JSON (or in `keyword-standardize`'s decisions file) and re-export — never
edit only the markdown, or the two drift apart.

Track termbase — `$TRANSFORMATIONS/Translations/<tgt>-<grade>/termbase.md`:

```markdown
| Source lemma | Locked <tgt> rendering | Gloss | Verses |
|---|---|---|---|
| <lemma> | <rendering> | <short gloss> | 1-1, 2-3 |
```

Base termbase cache — `$KEYWORDS/<tgt>/<pivot>-<src>-<tgt>-termbase-general.json`:

```json
{
  "keyword_pivot": {
    "<src>": "source-language meaning",
    "<tgt>": "target-language meaning at general level",
    "rank": 0,
    "verse_ids": ["1-1", "2-3"]
  }
}
```

`verse_ids` is populated from the keyword source in Step 2 and lets every term
be traced back to the verses it occurs in.

Grade file cache — `$KEYWORDS/<tgt>/<src>_<tgt>_keyword_<grade>.json` (also Phase 2's
input and write-back target):

```json
{
  "verse_id": {
    "text": "Pivot translation — unchanged",
    "<src>_text": "Source-language lines — added",
    "<tgt>_text": "Translation at this grade — added (Phase 2 fills it)",
    "keywords": [
      {
        "key": "pivot_term",
        "rank": 0, "score": 0.0, "count": 0,
        "<src>": "source-language meaning — unchanged",
        "<tgt>": "target-language meaning at this grade — added",
        "grade": "beginner"
      }
    ]
  }
}
```

When the target language *is* the pivot language, the base `text` is the pivot
translation and `<tgt>_text` is the *graded* rewrite; the two are different
fields on purpose.

### Procedure

**Step 0 — Check the track contract.** Confirm
`$TRANSFORMATIONS/Translations/<tgt>-<grade>/` exists with `requirements.md`,
`audience.md` and `termbase.md`. Create any that are missing before going on:
the requirements from the grade's register row, the audience from the grade's
audience row, and an empty `termbase.md` with the table header above.

**Step 1 — Load the base termbase.** If
`$KEYWORDS/<tgt>/<pivot>-<src>-<tgt>-termbase-general.json` does not exist, build it:
take the key set of any existing base for another target language (same pivot
key set), drop that language's field, and fill `<tgt>` for each key using the
register table and — first — any attested translation supplied.

**Step 2 — Load the keyword source and populate `verse_ids`.** From
`keyword-extract`'s enriched JSON, or from the rails' `concepts_in_verse:` /
`concepts_in_commentary:` lists: for every keyword in every verse, add the verse
ID to the termbase entry; create a stub (`<src>` from the keyword, `<tgt>`
empty, `rank`, `verse_ids`) for any keyword not yet in the termbase.

**Step 3 — Parse the pivot and the attested translation (if given).** Build
`{verse_id → text}` for each. Two parse rules matter and are easy to get wrong:

- **Skip any line that starts with `![[` or `#`.** A transclusion line is
  structural, not content, and a heading is editorial. Folding either into a
  verse's text poisons every downstream match.
- Join the lines of a multi-line verse into one block; the verse ID is the
  trailing `^id` on the block's last line. Skip closing notes and colophon
  prose that carries no verse ID.

**Step 4 — Extend the termbase from the attested translation.** For each verse,
for each of its keywords: if the base rendering occurs in the attested text,
confirm it; if a different rendering is attested, replace the base value with
the attested form and log the change; if the base value is empty, read the
rendering off the attested text. Attested beats base beats invented.

**Ignore any keyword whose rendering is identical to its key.** An entry whose
`<tgt>` value is just the pivot key echoed back is not a translation — it is an
unfilled cell that looks filled. Treat it as empty, and report it among the
keywords still needing a rendering.

Save the updated base termbase (`termbase.md` is exported from it in Step 8).

**Step 4b — No attested translation.** Fill each `<tgt>` value from the
sources the language's register section lists, most trusted first, and record
where each came from (`<tgt>_source`) and why (`<tgt>_note`). Values chosen
where the sources disagree get `<tgt>_decision`. The machine draft is never the
only evidence for a value unless the note says no other source had the word. If
the target language needs distinctions the pivot termbase does not lock
(mantra syllables, a Tibetan word English merged), add target-only entries
with the same schema and say so in their note.

**Step 5 — Parse the source root text** into `{verse_id → <src>_text}`, joining
the lines of a multi-line verse and applying the same two parse rules as Step 3
(skip lines starting with `![[` or `#`).

**Step 6 — Derive grade variants** of every `<tgt>` value from the general base,
using the adaptation rules in §Registers (general → beginner strips jargon and
glosses; general → intermediate keeps the technical term, may add a precision
qualifier; general → advanced adds the Sanskrit/technical form in parentheses).
Keep values short (1–6 words); match the Buddhist sense, not the dictionary
sense; prefer an attested form over a new one.

**Step 7 — Build the grade files.** For each requested grade: every verse gets
`text`, `<src>_text`, `<tgt>_text` (attested text for the grade it seeds, otherwise
empty until Phase 2), and the keywords that survive the rank cutoff, each with
its grade-adapted `<tgt>` and `grade`.

**Step 8 — Save and verify.** Write each file to a temp path, then copy into
`$KEYWORDS/<tgt>/` and re-load it to confirm it parses. Export the termbase into
the track's `termbase.md` (`scripts/termbase_to_md.py <termbase>.json -o termbase.md`). Print per grade: verse count, keyword
count, and every keyword whose `<tgt>` is still empty (or equal to its key) —
those must be filled before Phase 2 uses the file.

**Step 9 — Validate.** Run the validator on the termbase and every grade file:

```bash
python3 $SKILL/scripts/validate_grade_file.py --lang <tgt> \
    --termbase   $KEYWORDS/<tgt>/<pivot>-<src>-<tgt>-termbase-<grade>.json \
    --grade-file $KEYWORDS/<tgt>/<src>_<tgt>_keyword_<grade>.json
```

`--lang` names the field that holds the locked rendering (default `en`). The
same flag exists on `check_termbase_consistency.py --grade-file` and on
`termbase_to_glossary.py`.

Fix every **E** line before Phase 2 (exit code 1 until they are gone); read every
**W** line. What it enforces, and why:

- **A keyword's Tibetan is copied from that verse's `bo_text`**, in the verse's own
  word order and spelling (E2). A form that is not literally in the verse can never
  be checked or glossed.
- **A keyword's Tibetan is one of its term's forms** (E3). On the Twenty-One Tārās,
  1-21's མཐུ was filed under `power` (locked to དབང) because the English draft said
  "power"; only the commentary fact-check caught it.
- **Context-dependent senses are separate entries with disjoint `verse_ids`** (E5).
  One Tibetan form may carry two renderings (དབང: "power" at 1-10, "empowerment" at
  2-3) only when each entry lists the verses it applies to.
- **No `...` in a Tibetan form** (W1). Write each contiguous part, or leave the phrase
  out; a gapped form matches nothing.
- **One English word for several locked Tibetan terms** (W2) is the signature of a
  base draft that merged distinctions ("power" for ནུས / དབང / མཐུ). Confirm each
  split is intended.
- **Nested terms** (W5 — "Tara" inside the Sanskrit title) are reported as COVERED
  by the Phase 3 check; make sure that is what you want.

Phase 1 writes only to `$KEYWORDS/<tgt>/` and the track's `termbase.md`. It never
modifies `$SOURCE_TEXTS/`, `$TRANSLATIONS/`, the keyword source, or the attested
translation.

### Completion check — Phase 1

- [ ] Track folder exists with `requirements.md`, `audience.md` and `termbase.md`.
- [ ] Base termbase loaded (or built and saved) for `<tgt>`.
- [ ] `verse_ids` populated from the keyword source; the report says which source was used.
- [ ] Pivot and attested translation parsed with lines starting `![[` or `#` skipped.
- [ ] Attested translation's renderings folded into the termbase; changes logged
      (or, with none, every value has a `<tgt>_source`, per Step 4b).
- [ ] `<src>_text` set for every verse.
- [ ] Every keyword in every grade file has a `<tgt>` that is non-empty **and not equal to its key**, plus a `grade`; rank cutoff applied.
- [ ] Track `termbase.md` exported from the termbase JSON (`termbase_to_md.py`).
- [ ] Files re-loaded after writing; nothing outside `$KEYWORDS/<tgt>/` and the track folder touched.
- [ ] `validate_grade_file.py` reports 0 errors; its warnings were read.

---

## Phase 2 — Translate with the termbase locked

**Step 1 — Load the grade file** `$KEYWORDS/<tgt>/<src>_<tgt>_keyword_<grade>.json`
and build a flat `key → <tgt>` dict (first occurrence wins), **skipping any
entry whose rendering equals its key** — that is an unfilled cell, not a
rendering. Check the dict against the track's `termbase.md`; if they disagree, one
was edited without the other — fix the JSON, re-export, and only then go on. This dict is the single source of truth for
terminology in this run. **If the grade file does not exist, stop and say Phase
1 must be run first** — do not choose renderings ad hoc.

**Step 2 — Group verses by chapter** (first segment of the verse ID) and process
chapters in the text's own order. Read the chapter set off the root text's
`^N-0` headings — never assume a chapter count or numbering. A text may have a
chapter `0`, roman-numeral front matter, and lettered back matter.

**Step 3 — Translate chapter by chapter.** For each chapter:

1. **Lock the terms** — scan the chapter's verses for termbase keys. Their
   `<tgt>` renderings are fixed; no synonyms, no register-driven substitutions.
2. **Translate each verse** from `<src>_text` (or regrade the pivot `text`),
   writing at the grade's register (§Registers) and within the track's
   `requirements.md`, with locked terms substituted.

Rules: locked terms override register · translate line by line · never add
content · inflection and natural target-language word order are allowed.

**Variant — enforce on a machine draft.** When the base is a `machine-translate`
draft (DharmaMitra), keep its wording and only substitute the locked terms verse by
verse. Give DharmaMitra the termbase as a hint first
(`scripts/termbase_to_glossary.py --lang <tgt> --scope-all` → `dm_translate.py
--glossary`; `--scope-all` hints each term only in the verses where it is locked, so
1-8's ཆུ་སྐྱེས་ཞལ "her lotus face" is not pushed onto 1-1, where the same Tibetan is
the Lord's face), but do not rely on it: on the Twenty-One Tārās the glossary-primed draft was ~88% identical to the
unprimed one and still used "zombies" and "yakṣas". The enforcement pass here is what
makes the terms stick (locked-term adherence 87% → 99%).

**Step 4 — Consistency pass.** Re-scan the whole output for every locked term;
fix any verse that used a non-termbase form. Write each verse's `<tgt>_text`
back into the grade file.

`<tgt>_text` is the **Phase 2 snapshot**. Later edits — `commentary-fact-check`
Phase 2 fixes, translator decisions — go into the translation `.md` only; do not
rewrite `<tgt>_text`. The file's `draft_history` property (rails/CONVENTIONS.md)
and git record which text is which draft.

**Step 5 — Write the markdown.** One block per verse, translated text followed
by its block ID, blank line between blocks; headings (`id` ends in `-0`) as
`## <text> ^<id>`:

```
<tgt_text> ^<verse_id>
```

Path: `$TRANSFORMATIONS/Translations/<tgt>-<grade>/<text-id>-<tgt>-<grade>.md`.
Body is target language only — no source, no metadata in the body. Provenance
goes in the frontmatter:

```yaml
---
title: "<work title> — <tgt> (<grade>)"
transformation_type: translation
track: <tgt>-<grade>
lang_tag: <tgt>
root_text: 1-SOURCES/Text/<lang>-root-text.md
pivot_translation: <path to the pivot used>
translated_from: <src>_text | text        # say which field was the base
grade_file: 2-RAILS/Keywords/<tgt>/<src>_<tgt>_keyword_<grade>.json
context_packages:
  - 3-TRANSFORMATIONS/Translations/<tgt>-<grade>/requirements.md
  - 3-TRANSFORMATIONS/Translations/<tgt>-<grade>/termbase.md
  - 3-TRANSFORMATIONS/Translations/<tgt>-<grade>/audience.md
  - 2-RAILS/Verses/<verse-id>.md            # every rail consulted
covers_verses: "<A>–<B>"
generation_date: <YYYY-MM-DD>
status: draft
---
```

If the vault's translation convention is the transclusion layout (root block
transcluded above each translated block — see `rails/CONVENTIONS.md` and the
vault's own linter), produce that layout instead; the block-ID contract is
identical.

### Adapting between grades

- **general → beginner**: strip parenthetical and untranslated technical terms;
  replace them with the beginner termbase's plain forms; gloss on first use if
  unavoidable.
- **general → advanced**: add the Sanskrit/technical term in parentheses; use
  the advanced termbase's more precise equivalents.
- Always switch to the **target grade's** file — never mix entries from two grades.

### Completion check — Phase 2

- [ ] Grade specified; the matching grade file loaded (or the run stopped because it is missing).
- [ ] Locked-term dict built from the whole file, first occurrence wins, key-equals-rendering entries skipped.
- [ ] Dict checked against the track's `termbase.md`; any disagreement fixed in the JSON and re-exported.
- [ ] Chapters read off the root's `^N-0` headings and processed in the text's own order; locked terms identified per chapter before translating.
- [ ] Register matches the grade table for `<tgt>` and the track's `requirements.md`.
- [ ] Consistency pass done; same rendering for the same term throughout.
- [ ] Markdown written, one verse per block, `^id` on the same line, headings as `## … ^N-0`.
- [ ] Output frontmatter carries `transformation_type: translation`, `track`, `context_packages`, `covers_verses`, `generation_date`, `status: draft`.
- [ ] No JSON modified except the grade file's own `<tgt>_text` write-back.

---

## Phase 3 — Mechanical drift check

**Without verse rails (grade-file mode)** — the usual case right after Phase 2:

```bash
python3 $SKILL/scripts/check_termbase_consistency.py \
    --grade-file  $KEYWORDS/<tgt>/<src>_<tgt>_keyword_<grade>.json \
    --translation $TRANSFORMATIONS/Translations/<tgt>-<grade>/<text>-<tgt>-<grade>.md \
    --strict-diacritics
```

Each verse's expected terms are its keyword list in the grade file. A term whose
Tibetan sits inside a longer locked phrase present in the same verse is
**COVERED**. Pass `--strict-diacritics` whenever the termbase locks IAST spellings:
without it accents are folded, and "Tārā" passes for "Tara" (on the Twenty-One Tārās
machine draft that hid 11 of 21 misses).

**With verse rails:**

```bash
python3 $SKILL/scripts/check_termbase_consistency.py \
    --termbase   $TRANSFORMATIONS/Translations/<track>/termbase.md \
    --translation $TRANSFORMATIONS/Translations/<track>/<file>.md \
    --rails-dir  $VERSES \
    --verses 1-1 1-2 1-3
```

`scripts/termbase_to_md.py <termbase>.json -o termbase.md` writes the JSON termbase
as that table (it is also the `termbase.md` that `translation-qa` reads).

The script parses a `termbase.md` table (`| source lemma | locked rendering |
note |`, several source variants per row separated by ` / `, parenthetical
glosses accepted as alternate surface forms), reads each verse rail's
`concepts_in_verse:` (fallback `concepts_in_commentary:`) to learn which lemmas
are load-bearing in that verse, splits the translation on trailing `^id`
markers (footnote bodies are folded into the verse that cites them), and
reports per (verse, lemma): **EXACT**, **LOOSE** (article-stripped,
de-pluralised), or **MISSING**. MISSING is a human-look item — a legitimate
paraphrase or real drift.

Two things to know:

- In rails mode it reads the **markdown termbase**, the `termbase.md` a track
  keeps under `$TRANSFORMATIONS/Translations/<track>/`, exported from the JSON
  by `termbase_to_md.py`. If the two have drifted, fix the JSON and re-export
  before checking.
- Rails mode needs verse rails (`$VERSES/<id>.md` with `concepts_in_verse:`) to
  know which lemmas to expect in which verse. Where no rails exist yet, use
  grade-file mode above: it takes each verse's expected terms from the grade
  file's own keyword lists.

Block IDs of every shape are read (`^0`, `^1-5`, `^I-1`, `^a-1`), multi-line
verses are joined, and transclusion lines (`![[…#^id]]`) are skipped, so the
check runs on transclusion-layout files as they are.

Every MISSING must be either fixed or explained in the translation's notes
before the file is handed to `commentary-fact-check`.

---

## Registers

Locked terms override register in every case. The tables give the *style* of
the surrounding prose and the *shape* of a grade-adapted term.

### English (`en`)

| Grade | Style |
|---|---|
| **beginner** | Plain modern English. No unglossed Sanskrit/Pali/Tibetan. Gloss any unavoidable technical term inline: "the wish to awaken for the sake of all beings (bodhichitta)". |
| **general** | Standard English prose. Common Buddhist loanwords used freely (bodhichitta, karma, nirvana) without gloss. |
| **intermediate** | English + untranslated Sanskrit/Pali terms for technical concepts (kleśas, prajñā) used without gloss. |
| **advanced** | Sanskrit/Pali-rich technical register. Full Abhidharma/Madhyamaka vocabulary; parenthetical Sanskrit/Tibetan for key terms. |

| Concept | beginner | general | advanced |
|---|---|---|---|
| bodhichitta | the wish to awaken for the sake of all beings | bodhichitta | bodhichitta (bodhicitta) |
| suffering | suffering | suffering | suffering (duḥkha; three types of duḥkhatā) |
| emptiness | the lack of any fixed, separate self in things | emptiness | emptiness (śūnyatā; niḥsvabhāvatā) |
| merit | good karma from virtuous action | merit | merit (puṇya) |
| liberation | freedom from suffering | liberation | liberation (mokṣa; vimokṣa) |

When `<tgt>` equals the pivot language, the base `text` is already in that
language, so Phase 2 is a *regrade* unless translating from `<src>_text`. The
pivot's keyword set is the one every target language's termbase is keyed on —
so a vault should pick one pivot and keep it.

### Hindi (`hi`)

| Grade | Style |
|---|---|
| **beginner** | Plain Hindustani, everyday words, no unglossed Sanskrit. Gloss Sanskrit on first use: बोधिचित्त (सबके भले की इच्छा). |
| **general** | Modern standard Hindi. Sanskrit Buddhist terms used freely. Flowing prose. |
| **intermediate** | Hindi + classical Sanskrit. Terms like क्लेश, प्रज्ञा used without glosses. Precise but readable. |
| **advanced** | Sanskrit-rich. Full Abhidharma/Madhyamaka vocabulary. Parenthetical expansions welcome. |

| English | beginner | general | intermediate | advanced |
|---|---|---|---|---|
| compassion | दया | करुणा | करुणा | करुणा / अनुकम्पा |
| emptiness | खालीपन | शून्यता | शून्यता | शून्यता (सर्वधर्मनिःस्वभावता) |
| merit | पुण्य | पुण्य | पुण्य / कुशल | कुशलकर्म |
| bodhichitta | सबके भले की इच्छा | बोधिचित्त | बोधिचित्त | बोधिचित्त (संवोधिचित्त) |
| suffering | दुःख | दुःख | दुःख | दुःख (सर्वसंस्कारदुःखता) |
| liberation | मुक्ति | मुक्ति | मुक्ति | विमोक्ष |

Adaptation: general → beginner replaces Sanskrit with plain Hindi
(`बोधिचित्त` → `सबके भले की इच्छा`, `करुणा` → `दया`, `शून्यता` → `खालीपन`);
general → intermediate keeps the Sanskrit and may add a qualifier
(`पुण्य` → `पुण्य / कुशल`); general → advanced adds the technical Sanskrit in
parentheses (`शून्यता` → `शून्यता (सर्वधर्मनिःस्वभावता)`). Keep values 1–5 words.

Liturgy (general): mantra syllables and Sanskrit title lines in Devanagari (ॐ तारे तुत्तारे तुरे स्वाहा);
avoid जिन / जिनपुत्र for a general reader (they read as Jain) — बुद्ध / बोधिसत्त्व. With no attested Hindi
translation, build the word list with `keyword-standardize` (§Hindi).

### Vietnamese (`vi`)

| Grade | Style |
|---|---|
| **beginner** | Plain modern Vietnamese, short sentences. Sino-Vietnamese/Sanskrit terms glossed in parentheses on first use: tâm bồ đề (lòng mong muốn giúp tất cả chúng sinh thoát khổ). |
| **general** | Modern standard Vietnamese. Common Sino-Vietnamese Buddhist terms used freely (Phật, Pháp, Bồ Tát, từ bi, hồi hướng). Flowing prose. |
| **intermediate** | Vietnamese + precise Sino-Vietnamese terms. Terms like phiền não, ba-la-mật used without glosses. Readable but exact. |
| **advanced** | Sino-Vietnamese/Sanskrit-rich. Full Abhidharma/Madhyamaka vocabulary, Sanskrit terms transliterated or parenthesised. |

| English | beginner | general | intermediate | advanced |
|---|---|---|---|---|
| compassion | lòng thương người | từ bi | từ bi | từ bi (đại bi tâm) |
| emptiness | sự trống rỗng của mọi thứ | tánh không | tánh không | tánh không (vô tự tính) |
| merit | việc tốt, phước đức | công đức | công đức / phước đức | phước đức, công đức |
| bodhichitta | tâm muốn giúp tất cả mọi người | tâm bồ đề | tâm bồ đề | tâm bồ đề (bồ đề tâm) |
| suffering | khổ, nỗi khổ | khổ đau | khổ đau | khổ đau (khổ đế) |
| bodhisattva | vị Bồ Tát, người phát nguyện cứu giúp chúng sinh | Bồ Tát | Bồ Tát | Bồ Tát (Bồ-đề-tát-đỏa) |
| samsara | vòng sinh tử luân hồi | luân hồi | luân hồi | luân hồi (sinh tử luân hồi) |
| nirvana | sự giải thoát hoàn toàn khỏi khổ đau | niết bàn | niết bàn | Niết-bàn (Nirvāṇa) |
| afflictions (kleshas) | cảm xúc xấu | phiền não | phiền não | phiền não (kleśa) |
| mindfulness | luôn để ý, tỉnh táo | chánh niệm | chánh niệm | chánh niệm (smṛti) |
| dedication | chia sẻ công đức cho người khác | hồi hướng | hồi hướng | hồi hướng công đức |
| patience | kiên nhẫn, nhịn nhục | nhẫn nhục | nhẫn nhục | nhẫn nhục ba-la-mật |
| diligence | cố gắng, chăm chỉ | tinh tấn | tinh tấn | tinh tấn ba-la-mật |
| refuge | nương tựa | quy y | quy y, nương tựa | quy y Tam Bảo |

Adaptation: general → beginner replaces Sino-Vietnamese/Sanskrit with plain
Vietnamese or a short gloss (`tâm bồ đề` → `tâm muốn giúp tất cả mọi người`);
general → intermediate keeps the Sino-Vietnamese term, may add a qualifier
(`công đức` → `công đức / phước đức`); general → advanced adds the Sanskrit/Pali
form in parentheses (`tánh không` → `tánh không (vô tự tính)`). Keep values 1–6
words; prefer a form attested in an existing Vietnamese translation over a new
one. Natural Vietnamese particles (rồi, thì, mà, vậy) are allowed in prose.

### Chinese (`zh`)

WeBuddhist writes **Traditional characters** (`zh-Hant`) unless a project says
otherwise. For Simplified, convert the finished termbase and text with a
character converter (e.g. OpenCC `t2s`); never re-choose terms by hand.

| Grade | Style |
|---|---|
| **beginner** | Plain modern written Chinese (白話), short sentences. A Buddhist term is glossed in parentheses on first use: 菩提心（為利益一切眾生而求覺悟的心）. |
| **general** | Standard modern written Chinese. Common Buddhist terms used freely (菩提心、涅槃、灌頂、功德). Clear sentences, with no classical grammar (之乎者也) and no lines forced to seven characters. |
| **intermediate** | Modern Chinese + exact Buddhist terms used without gloss (煩惱、般若、波羅蜜、三摩地). |
| **advanced** | Term-dense, may lean on classical canon wording. Sanskrit/Tibetan in parentheses for key terms. |

| English | beginner | general | intermediate | advanced |
|---|---|---|---|---|
| compassion | 慈悲心（希望眾生離苦） | 慈悲 | 悲心 | 悲心（karuṇā） |
| emptiness | 一切事物沒有固定不變的本質 | 空性 | 空性 | 空性（śūnyatā，無自性） |
| merit | 善行帶來的福報 | 福德 | 福德／功德 | 福德資糧（puṇya） |
| bodhichitta | 為利益一切眾生而求覺悟的心 | 菩提心 | 菩提心 | 菩提心（bodhicitta） |
| suffering | 痛苦 | 苦 | 苦 | 苦（duḥkha，三苦） |
| liberation | 從痛苦中解脫 | 解脫 | 解脫 | 解脫（mokṣa） |

Adaptation: general → beginner replaces a term with its plain gloss, or adds the
gloss once; general → intermediate keeps the term and may pick the narrower one
(慈悲 → 悲心); general → advanced adds the Sanskrit in parentheses. Keep values
1–6 characters where possible.

Conventions for every grade:

- **Mantra syllables are written in Chinese characters, never Latin.** Where the
  syllable belongs to a mantra that people commonly recite, use that recitation
  form (Tārā: 嗡 達咧 都達咧 都咧 梭哈; also 吽, 呸). Otherwise use the form of the
  classical canon translation (CBETA). Lock every syllable in the termbase, since
  the English termbase often leaves them unlocked.
- **Names use their established Chinese forms** (度母、阿彌陀佛、須彌山、帝釋、梵天、
  夜叉). A Sanskrit title line stays in IAST, as in English.
- **Classical vocabulary is evidence, not the target.** A classical translation
  (e.g. CBETA) shows which words Chinese readers already know. Keep a classical
  word a modern reader understands (敬禮、無餘、起屍). Replace a transliteration
  they cannot parse (部多 → 鬼神). Do not copy classical lines into the text.
- **Line count follows the Tibetan**, one Chinese line per Tibetan line, with
  full-width punctuation （，。；：！、）.

**No attested Chinese translation?** This is the usual case. Use the
[`keyword-standardize`](../keyword-standardize/SKILL.md) skill, which does
the steps below with scripts and one editable decisions file. It builds the base
termbase from, in order of trust: (1) a classical canon translation of the same
text (CBETA), aligned by block ID in a reference file; (2) the established
Buddhist term (Mahāvyutpatti pairs, 佛學大辭典); (3) the zero-shot machine draft,
which may suggest but never confirm. Record the source of every value in
`zh_source` and the reason for any choice between sources in `zh_note`. A value
decided without agreement between sources gets `zh_decision` saying who
decided, so the native reviewer can find it.

### Adding a language

Add a register table with the four grades, a short adaptation paragraph, and a
handful of anchor terms (compassion, emptiness, merit, bodhichitta, suffering at
least). Build the base termbase per Phase 1 Step 1. Nothing else changes.

---

## Provenance

Consolidated 2026-09-21 from one vault's per-language skill pairs (a
`keyword-grade` + `translate` pair per target language) and its
`termbase-consistency-check/` script, which were identical apart from the target
code and the register table. That vault's end-to-end production run is written
up in [`references/worked-example.md`](references/worked-example.md) as a
history, not a contract. Its two English-track glossary scripts hard-coded that
vault's track names and paths and were not carried over; `bilingual-glossary`
Phase 4 is the general form of that step.

## After this skill

`translation-qa` grades the output against the source and the verse packages;
`commentary-fact-check` checks that each verse says what the commentaries say it
means. Both should run before a graded translation is uploaded.
