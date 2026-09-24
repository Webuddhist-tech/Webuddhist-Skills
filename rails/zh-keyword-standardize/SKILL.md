---
name: zh-keyword-standardize
description: >
  Standardise the Chinese keywords of a block-ID'd Tibetan text before it is
  translated into Chinese, when no human Chinese translation of it exists: collect
  the classical canon version and other evidence, lay it out term by term, choose
  one Chinese rendering per locked Tibetan term with its source and reason written
  down, and build the Chinese termbase, grade file, glossary and a review table
  from one editable decisions file.

  Trigger on "Chinese keyword standardisation", "standardise the Chinese terms",
  "build the Chinese termbase / word list", "lock the Chinese vocabulary",
  "translate to Chinese but there's no human translation to attest against",
  "which Chinese word should we use for …".

  This is graded-translate Phase 1 for Chinese without an attested translation;
  graded-translate Phase 2 then translates with the result locked.
profile: rails-vault
supersedes: []
---

> **Locations.** `$SKILL` is this skill's own directory; `$GT` is
> `rails/graded-translate/`. All other `$NAME` paths resolve per repo — see
> `rails/PROFILES.md`. `$KEYWORDS` is the folder holding the base termbase and
> grade file (in 21-taras-rails, `0-INBOX/AI_translation/keyword-extraction-dharmamitra/`).
> Block ID rules are in `rails/CONVENTIONS.md`.

# Standardise Chinese keywords without an attested translation

In English, a human translation gave us the words to lock. Chinese usually has
none that matches our Tibetan edition, so this skill builds the word list from
other evidence, and records where every word came from, so a reviewer can check it.

**What it reuses.** The *Tibetan side* of an existing termbase (usually the English
one): which Tibetan words are locked, in which verses, and what they mean there
(the notes and the commentary fact-check). It does not re-run `keyword-extract`.

**What it adds.** One Chinese rendering per term. Also Chinese-only entries where
Chinese needs a lock English did not (mantra syllables; a Tibetan word that one
English word covered in several senses).

| Not this skill | Use instead |
|---|---|
| An attested Chinese translation exists, block-aligned | `graded-translate` Phase 1 Steps 3–4 (attested beats everything) |
| Fill the Zh column of the BCA term-localization table | `term-localization` |
| Translate the text | `graded-translate` Phase 2 (after this skill) or `machine-translate` for a first look |

---

## Before you start — four choices only the project owner can make

Ask these once and record the answers in the decisions file's `_meta.choices`:

1. **Traditional or Simplified characters.** WeBuddhist's default is Traditional
   (`zh-Hant`). For Simplified, convert the finished files with a converter
   (OpenCC `t2s`); never re-pick terms.
2. **Grade / style.** `general` = clear modern written Chinese (the usual choice).
   A chantable seven-character version is a different track, not this grade.
3. **Mantra syllables.** Chinese characters (recommended), or Latin letters.
4. **Who decides flagged picks** (sources disagree or have nothing): the owner one
   by one, or Claude with the reason written down ("go with your picks"). Record
   who in `_meta.decided_by`.

---

## Inputs

| Input | Required | Description |
|---|---|---|
| Base termbase | ✓ | `$KEYWORDS/en-bo-en-termbase-<grade>.json` — the locked Tibetan terms, verse scopes and notes |
| Base grade file | ✓ | `$KEYWORDS/bo_en_keyword_<grade>.json` — per-verse keywords and `bo_text` |
| Meaning text | ✓ | The fact-checked translation (e.g. English D3). It is the meaning reference, not a source of words |
| Classical reference | strongly advised | A classical Chinese version of the same text (CBETA), aligned by block ID (Step 2) |
| Machine draft | optional | A zero-shot Chinese draft (`machine-translate`, DharmaMitra `modern chinese`) |
| Commentary consensus | optional | `commentary-fact-check` Phase 1b output — settles what a verse means when the English is not enough |

## Outputs

All in `$KEYWORDS/` unless stated.

| File | What |
|---|---|
| `zh-decisions-<grade>.json` | **The one file a person edits.** One entry per term: `zh`, `source`, `note`, optional `decision`, `add_verses`, `new_entry` |
| `en-bo-zh-termbase-<grade>.json` | Termbase: `bo`, `en`, `zh`, `verse_ids`, `zh_source`, `zh_note`, `zh_evidence`, (`zh_decision`, `zh_only`) |
| `bo_zh_keyword_<grade>.json` | Grade file: `text` = meaning text, `bo_text`, `zh_text` (empty until Phase 2), keywords with `zh` |
| `termbase-zh-<grade>.md` | Readable review table, flagged picks first |
| `glossary-zh-<grade>.tsv` | Verse-scoped glossary for `machine-translate --glossary` |
| `zh-worksheet-<grade>.md` | Evidence per term and verse (working file) |
| `…/zh-references/zh-classical-<id>.md` | Classical reference aligned to our block IDs (outside `$KEYWORDS`) |

Never writes to `$SOURCE_TEXTS/`, `$TRANSLATIONS/`, the base termbase or the base grade file.

---

## Procedure

### Step 1 — Record the choices

Write the four answers into `_meta` of the decisions file (Step 3 creates it).

### Step 2 — Build the classical reference

Look for a classical Chinese translation of the same work in CBETA (Taishō).
Find it by title or by a well-known line. The CBETA data API returns a whole
fascicle: `https://cbdata.dila.edu.tw/stable/juans?work=<T-number>&juan=1`.
Other published versions (a teacher's or centre's site) are second copies to
check against.

- **Retrieval.** If the fetch tool summarises instead of returning raw text, ask for
  stanzas a few at a time, "exactly as written". Check each against a second
  copy where there is one. A regular verse text self-checks: every stanza of a
  seven-character quatrain is 28 characters.
- **Align by content, not by number.** Classical versions reorder, merge or add
  (framing, dhāraṇīs, a longer benefits section). Give each stanza our block ID with
  a prefix, `^zhc-1-5`. Keep unalignable material as one block (`^zhc-benefits`)
  with a note.
- **Frontmatter.** Record `source`, `source_url`, `related`, `license_note`, `retrieved`,
  `retrieval_note` (how it was read and what was spot-checked), `alignment`, and
  `use: vocabulary evidence only`.

No classical version? Skip this step. The standard Buddhist term becomes the top
source; say so in `_meta.sources_note`.

### Step 3 — Lay out the evidence

```bash
python3 $SKILL/scripts/zh_worksheet.py \
    --base-termbase $KEYWORDS/en-bo-en-termbase-general.json \
    --base-grade-file $KEYWORDS/bo_en_keyword_general.json \
    --meaning-text <fact-checked translation .md> \
    --reference <zh-references/zh-classical-*.md> \
    --mt-draft <Dharmamitra/zh/…-zh.md> \
    -o $KEYWORDS/zh-worksheet-general.md \
    --template $KEYWORDS/zh-decisions-general.json
```

For every term, it shows each verse's Tibetan, meaning, classical stanza and machine
draft side by side. It also lists multi-syllable Tibetan forms that occur in verses where
the term is *not* locked. On the Tārās, སྒྲོལ་མ in 1-11 is the verb "liberate", not
her name, and ཆུ་སྐྱེས་ཞལ in 1-1 is the Lord's face, not hers. `--template` writes an
empty decisions file (never over an existing one).

### Step 4 — Decide, term by term

Fill `zh`, `source` and `note` for every term. Source codes, most trusted first:
`attested`, `classical`, `standard` (the standard Buddhist pair, e.g. from the
Mahāvyutpatti), `recitation` (the form people chant), `kept` (as in English, e.g.
an IAST title line), `mt` (machine draft), `new`.

Rules:

1. **Meaning first.** The English lock, its note and the commentary consensus say
   what the Tibetan means *in this verse*. Choose the Chinese word for that sense,
   not the dictionary's first sense.
2. **Keep a classical word when a modern reader understands it** (敬禮, 無餘, 起屍,
   灌頂). **Use the modern spelling of the same word** (蓮華 → 蓮花, 藥叉 → 夜叉).
   **Replace transliterations a general reader cannot parse** (部多 → 鬼神).
3. **Avoid a word that names a different Tibetan concept in Chinese.** 三界 is ཁམས་གསུམ,
   so འཇིག་རྟེན is 世界; 魔 is བདུད, so གདོན is 邪魅.
4. **Keep every distinction English made, and add ones Chinese needs.** For a
   comparative or other sense English merged, add a `new_entry` with `split_from`
   (ཆེ་བ "greater" at 2-3, out of "great"). To lock a term in a verse English left
   open, use `add_verses` ({"1-5": "ནུས"}).
5. **Lock every mantra syllable** as a `new_entry` if English did not. With Chinese
   characters: use the common recitation form where the syllable belongs to a
   mantra people chant (Tārā: 嗡 達咧 都達咧 都咧 梭哈; also 吽, 呸), otherwise the
   classical form (特囉, 喝囉). Normalise one syllable to one form across verses, even
   where the classical version varies.
6. **Lock the shortest form that stays unambiguous** when the compound varies
   naturally (喜 for 歡喜/喜悅/極喜, 光, 踏). Lock the whole phrase when the phrase is
   the term (蓮花面容, 圓滿具足).
7. **Flag, don't hide.** When the sources disagree or have nothing, set `"decision": true`
   and say in `note` what each source had and why this one won. The machine draft
   is never the only evidence unless `note` says no other source had the word.
8. **Record what was wrong in the machine draft** in `note` when you see it (1-6: 羅剎
   for རོ་ལངས). Phase 2 needs to know.

Follow the `zh` register section in `$GT/SKILL.md` §Registers for style and
anchor terms.

### Step 5 — Build

```bash
python3 $SKILL/scripts/build_zh_termbase.py \
    --decisions $KEYWORDS/zh-decisions-general.json \
    --base-termbase $KEYWORDS/en-bo-en-termbase-general.json \
    --base-grade-file $KEYWORDS/bo_en_keyword_general.json \
    --meaning-text <fact-checked translation .md> \
    --reference <zh-references/zh-classical-*.md> --mt-draft <machine draft .md> \
    --out-dir $KEYWORDS            # --force to rebuild after editing decisions
```

It refuses to build when a base term has no decision, a rendering or source is
empty, a `new_entry`'s Tibetan is not in its verse, or a keyword points at a missing
term. `zh_evidence` counts, for each term, how many of its verses already contain
the rendering in the reference and in the machine draft.

### Step 6 — Validate, baseline, glossary

```bash
python3 $GT/scripts/validate_grade_file.py --lang zh \
    --termbase $KEYWORDS/en-bo-zh-termbase-general.json \
    --grade-file $KEYWORDS/bo_zh_keyword_general.json          # must be 0 errors
python3 $GT/scripts/check_termbase_consistency.py --lang zh \
    --grade-file $KEYWORDS/bo_zh_keyword_general.json \
    --translation <machine draft .md>                          # baseline
python3 $GT/scripts/termbase_to_glossary.py --lang zh --scope-all \
    $KEYWORDS/en-bo-zh-termbase-general.json -o $KEYWORDS/glossary-zh-general.tsv
```

Write the baseline ("the machine draft already uses N of M locked words") into
`_meta.baseline`, then re-run Step 5 with `--force` so the review table shows it.
Always use `--scope-all`: it hints each term only in the verses where it is locked.

### Step 7 — Log and hand off

Log the choices, sources, counts and checks in the project's `STATE.md`, and commit.
Next is `machine-translate` into a new track (e.g. `Dharmamitra/zh-general/`) with
the glossary and a `style.md` like:

> Translate this Tibetan verse of praise line by line into clear modern written
> Chinese in Traditional characters: render each Tibetan line as one line of
> Chinese, in the same order, and keep the same number of lines as the source. Use
> plain modern vocabulary and grammar, not classical Chinese, and do not force lines
> into seven characters. Use the established Chinese Buddhist terms where they
> exist. Devotional but clear register. Write mantra syllables in Chinese
> characters, never in Latin letters. Use full-width Chinese punctuation. Do not
> add commentary, notes, or explanation.

Then `graded-translate` Phase 2 (enforce on the machine draft), Phase 3 (drift),
the meaning check against the fact-checked translation, a back-translation, and a
native reviewer, who starts with the flagged table.

---

## Rules

1. **Translate from the Tibetan.** The English is the meaning check. It is never
   the source text, and never a source of Chinese words.
2. **Edit the decisions file, never the built files.** Re-run Step 5 with `--force`.
3. **The classical version is evidence, not text.** Never copy its lines into the
   translation. Respect its licence (CBETA: CC BY-NC-SA).
4. **Every value has a source; every disagreement has a note and a `decision`.**
5. **Never overwrite a decisions file** (`--template` refuses) or outputs without `--force`.
6. **Simplified is a conversion**, done on finished files, not a second set of picks.

## Completion check

- [ ] The four choices are recorded in `_meta`.
- [ ] Classical reference aligned, with retrieval and spot-check notes (or its absence stated).
- [ ] Every base term has `zh`, `source`, `note`; flagged picks have `decision`.
- [ ] Mantra syllables all locked in one form each.
- [ ] `build_zh_termbase.py` ran clean; `validate_grade_file.py --lang zh` reports 0 errors.
- [ ] Baseline measured and in `_meta.baseline`; glossary built with `--scope-all`.
- [ ] `STATE.md` updated; files committed.

## Worked example — Praise to the Twenty-One Tārās (21-taras-rails, 2026-09-24)

- **Choices:** Traditional, general grade, Chinese-character mantras, Claude
  decided the flagged picks.
- **Classical reference:** CBETA T1108B, the same text the 17th Karmapa office
  publishes. All 21 stanzas are 28 characters, and 7 of them were checked against the
  Karmapa page.
- **Word list:** 47 base terms plus 5 Chinese-only (`greater`, `om`, `svaha`, `hara`,
  `tara_syllable`), with 14 flagged picks.
- **Checks:** the validator reported 0 errors. The DharmaMitra zero-shot draft
  already used 63/137 locked words (46%).
- **Files:** `zh-decisions-general.json` is the source of truth. Rebuilding from it
  reproduces the committed termbase and grade file exactly.

## After this skill

`machine-translate` (glossary-primed draft) → `graded-translate` Phase 2 and 3 →
`commentary-fact-check` against the existing consensus → `translation-qa` → native
review → `translation-upload`.
