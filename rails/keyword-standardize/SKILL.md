---
name: keyword-standardize
description: >
  Standardise the target-language keywords of a block-ID'd Tibetan text before it is
  translated, when no human translation in that language exists to attest against
  (Chinese, Vietnamese, Hindi, …). Reuse the Tibetan side of an existing termbase. Gather
  evidence (a classical canon version, a related language's word list, standard
  Buddhist terms, a machine draft) and lay it out term by term. Then choose one
  rendering per locked Tibetan term, with its source and reason, in one editable
  decisions file, and build the termbase, grade file, glossary and review table from it.

  Trigger on "keyword standardisation", "standardise the <language> terms",
  "build the <language> termbase / word list", "lock the Vietnamese / Chinese
  vocabulary", "there's no human translation to attest against", "which <language>
  word should we use for …".

  This is graded-translate Phase 1 for a language without an attested translation;
  graded-translate Phase 2 then translates with the result locked. Formerly
  `zh-keyword-standardize` (Chinese only); that name still works.
profile: rails-vault
supersedes: []
---

> **Locations.** `$SKILL` is this skill's own directory; `$GT` is
> `rails/graded-translate/`. All other `$NAME` paths resolve per repo — see
> `rails/PROFILES.md`. `$KEYWORDS` is the keywords folder, with one subfolder per
> language (`rails/CONVENTIONS.md` §8; in 21-taras-rails,
> `0-INBOX/AI_translation/keyword-extraction-dharmamitra/`). `<tgt>` is the ISO code.

# Standardise keywords without an attested translation

In English, a human translation gave us the words to lock. Most other languages have
none that matches our Tibetan edition. This skill builds the word list from other
evidence and records where every word came from, so a reviewer can check it.

**Reused:** the *Tibetan side* of an existing termbase, usually the English one. That
is which Tibetan words are locked, in which verses, and what they mean there (the
notes and the commentary fact-check). It does not re-run `keyword-extract`.

**Added:** one rendering per term, plus target-only entries where the language needs
a lock English did not (mantra syllables; a Tibetan word that one English word covered
in several senses).

| Not this skill | Use instead |
|---|---|
| An attested translation exists, block-aligned | `graded-translate` Phase 1 Steps 3–4 (attested beats everything) |
| Fill a column of the BCA term-localization table | `term-localization` |
| Translate the text | `graded-translate` Phase 2 (after this skill), or `machine-translate` for a first look |

---

## Before you start — four choices only the project owner can make

Record them in the decisions file's `_meta.choices`:

1. **Script / spelling.** Chinese: Traditional or Simplified. Vietnamese: full
   diacritics (always). Mongolian: Cyrillic or traditional script.
2. **Grade / style.** `general` = clear modern prose (the usual choice). A
   chantable metrical version is a different track, not this grade.
3. **Mantra syllables.** Native script or Latin. See the language section for what
   readers expect.
4. **Who decides flagged picks** (sources disagree or have nothing): the owner one
   by one, or Claude with the reason written down ("go with your picks"). Record
   who in `_meta.decided_by`.

---

## Inputs

| Input | Required | Description |
|---|---|---|
| Base termbase | ✓ | `$KEYWORDS/en/en-bo-en-termbase-<grade>.json`: the locked Tibetan terms, verse scopes and notes |
| Base grade file | ✓ | `$KEYWORDS/en/bo_en_keyword_<grade>.json`: per-verse keywords and `bo_text` |
| Meaning text | ✓ | The fact-checked translation (e.g. English D3). It is the meaning reference, not a source of words |
| Reference | advised | Something block-aligned that shows words readers already know. Either a classical canon version aligned by block ID (Chinese), or the finished word list and translation of a related language (Chinese for Vietnamese) |
| Machine draft | optional | A zero-shot draft in `<tgt>` (`machine-translate`) |
| Commentary consensus | optional | `commentary-fact-check` Phase 1b output. It settles what a verse means when the English is not enough |

## Outputs

In `$KEYWORDS/<tgt>/`. The scripts take explicit paths, so a flat folder works too.

| File | What |
|---|---|
| `<tgt>-decisions-<grade>.json` | **The one file a person edits.** One entry per term: `<tgt>`, `source`, `note`, optional `decision`, `add_verses`, `new_entry` |
| `en-bo-<tgt>-termbase-<grade>.json` | Termbase: `bo`, `en`, `<tgt>`, `verse_ids`, `<tgt>_source`, `<tgt>_note`, `<tgt>_evidence`, (`<tgt>_decision`, `<tgt>_only`) |
| `bo_<tgt>_keyword_<grade>.json` | Grade file: `text` = meaning text, `bo_text`, `<tgt>_text` (empty until Phase 2; kept on rebuild), keywords with `<tgt>` |
| `termbase-<tgt>-<grade>.md` | Readable review table, flagged picks first |
| `glossary-<tgt>-<grade>.tsv` | Verse-scoped glossary for `machine-translate --glossary` |
| `<tgt>-worksheet-<grade>.md` | Evidence per term and verse (working file) |
| `references/…` | Aligned reference texts |
| `$KEYWORDS/standardised-keywords-<grade>.md` | All languages in one table (`multilingual_table.py`) |

Never writes to `$SOURCE_TEXTS/`, `$TRANSLATIONS/`, the base termbase or the base grade file.

---

## Procedure

### Step 1 — Record the choices

Write the four answers, plus `lang`, `grade`, `language_name`, `lang_tag` and (if a
reference is used) `reference_prefix`, into `_meta` of the decisions file. Step 3
creates the file.

### Step 2 — Get the reference

See the language section. For a classical canon version (CBETA), the rules are:

- **Retrieval.** If the fetch tool summarises instead of returning raw text, ask for
  stanzas a few at a time, "exactly as written". Check each against a second copy
  where there is one. A regular verse text checks itself: every stanza of a
  seven-character quatrain is 28 characters.
- **Align by content, not by number.** Classical versions reorder, merge or add
  material. Give each stanza our block ID with a prefix (`^zhc-1-5`). Keep
  unalignable material as one block with a note.
- **Frontmatter.** Record `source`, `source_url`, `related`, `license_note`,
  `retrieved`, `retrieval_note` (how it was read and what was spot-checked),
  `alignment`, and `use: vocabulary evidence only`.

A related-language translation made with this skill needs no alignment. It already
has our block IDs, so pass it with `--reference-prefix ""`.

### Step 3 — Lay out the evidence

```bash
python3 $SKILL/scripts/worksheet.py --lang <tgt> \
    --base-termbase $KEYWORDS/en/en-bo-en-termbase-general.json \
    --base-grade-file $KEYWORDS/en/bo_en_keyword_general.json \
    --meaning-text <fact-checked translation .md> \
    --reference <reference .md> [--reference-prefix zhc-|""] \
    --mt-draft <machine draft .md> \
    -o $KEYWORDS/<tgt>/<tgt>-worksheet-general.md \
    --template $KEYWORDS/<tgt>/<tgt>-decisions-general.json
```

For every term, the worksheet shows each verse's Tibetan, meaning, reference and
machine draft side by side. It also lists multi-syllable Tibetan forms that occur
where the term is *not* locked: on the Tārās, སྒྲོལ་མ in 1-11 is the verb "liberate",
and ཆུ་སྐྱེས་ཞལ in 1-1 is the Lord's face. `--template` writes an empty decisions file,
and never over an existing one.

### Step 4 — Decide, term by term

Fill `<tgt>`, `source` and `note` for every term. The source codes, most trusted first:

| Code | Meaning |
|---|---|
| `attested` | a human translation in `<tgt>` |
| `classical` | a classical canon version (CBETA) |
| `related` | the checked word list of a related language, e.g. Chinese for Vietnamese (Sino-Vietnamese readings) |
| `standard` | the standard Buddhist term in `<tgt>` (e.g. Mahāvyutpatti pairs) |
| `recitation` | the form people chant |
| `kept` | kept as in English (e.g. an IAST title line) |
| `mt` | the machine draft |
| `new` | none of the sources had it |

Name them for one text in `_meta.source_labels`, e.g. `{"mt": "Gemini vi draft"}`.

Rules for every language:

1. **Meaning first.** The English lock, its note and the commentary consensus say
   what the Tibetan means *in this verse*. Choose the word for that sense, not the
   dictionary's first sense.
2. **Keep an inherited word only if a modern reader understands it.** Classical or
   Sino-Vietnamese forms are evidence of what readers know. Replace a
   transliteration or Hán-Việt compound a general reader cannot parse with the
   plain word.
3. **Avoid a word that names a different Tibetan concept in `<tgt>`.** For example,
   Chinese 三界 is ཁམས་གསུམ, so འཇིག་རྟེན is 世界; 魔 is བདུད, so གདོན needs its own word.
4. **Keep every distinction English made, and add the ones `<tgt>` needs.** For a
   sense English merged, add a `new_entry` with `split_from` (ཆེ་བ "greater" at 2-3).
   To lock a term in a verse English left open, use `add_verses`.
5. **Lock every mantra syllable** (as a `new_entry` if English did not), in one form
   across all verses.
6. **Lock the shortest form that stays unambiguous** when compounds vary naturally
   (Chinese 喜, Vietnamese *hỷ*). Lock the whole phrase when the phrase is the term.
   In a language that writes syllables with spaces, check that a short lock is not
   also part of an unrelated word in its verses (Vietnamese *chân* "foot" is also in
   *chân ngôn* and *chân như*).
7. **Flag, don't hide.** When the sources disagree or have nothing, set `"decision": true`
   and say in `note` what each source had and why this one won. The machine draft is
   never the only evidence unless `note` says so.
8. **Record what was wrong in the machine draft** in `note` when you see it. Phase 2
   needs to know.

### Step 5 — Build

```bash
python3 $SKILL/scripts/build_termbase.py \
    --decisions $KEYWORDS/<tgt>/<tgt>-decisions-general.json \
    --base-termbase $KEYWORDS/en/en-bo-en-termbase-general.json \
    --base-grade-file $KEYWORDS/en/bo_en_keyword_general.json \
    --meaning-text <fact-checked translation .md> \
    [--reference <reference .md>] --mt-draft <machine draft .md> \
    --out-dir $KEYWORDS/<tgt>            # --force to rebuild after editing decisions
```

The build refuses to run when:

- a base term has no decision;
- a rendering or source is empty;
- a `new_entry`'s Tibetan is not in its verse;
- a keyword points at a missing term.

`<tgt>_evidence` counts, for each term, how many of its verses already contain the
rendering in the reference and in the machine draft. Only pass `--reference` when it
is in the same language (a classical Chinese version for Chinese); a related-language
reference gives meaningless counts.

A rebuild keeps any `<tgt>_text` that Phase 2 already wrote. After changing a
decision once a draft exists, re-run the Phase 3 drift check.

### Step 6 — Validate, baseline, glossary

```bash
python3 $GT/scripts/validate_grade_file.py --lang <tgt> \
    --termbase $KEYWORDS/<tgt>/en-bo-<tgt>-termbase-general.json \
    --grade-file $KEYWORDS/<tgt>/bo_<tgt>_keyword_general.json      # must be 0 errors
python3 $GT/scripts/check_termbase_consistency.py --lang <tgt> \
    --grade-file $KEYWORDS/<tgt>/bo_<tgt>_keyword_general.json \
    --translation <machine draft .md>                               # baseline
python3 $GT/scripts/termbase_to_glossary.py --lang <tgt> --scope-all \
    $KEYWORDS/<tgt>/en-bo-<tgt>-termbase-general.json -o $KEYWORDS/<tgt>/glossary-<tgt>-general.tsv
```

To give reviewers one table of every locked term across all languages, run:

```bash
python3 $SKILL/scripts/multilingual_table.py --base $KEYWORDS/en/en-bo-en-termbase-general.json \
    --lang zh=$KEYWORDS/zh/en-bo-zh-termbase-general.json --lang vi=$KEYWORDS/vi/en-bo-vi-termbase-general.json \
    --lang hi=$KEYWORDS/hi/en-bo-hi-termbase-general.json \
    -o $KEYWORDS/standardised-keywords-general.md
```

Rebuild it whenever a word list changes.

Write the baseline into `_meta.baseline` and rebuild (Step 5 `--force`).
`--scope-all` hints each term only in the verses where it is locked. It is always
needed.

### Step 7 — Log and hand off

Log the choices, sources, counts and checks in `STATE.md`, then commit. Next comes a
`machine-translate` run into a new track (`machine-drafts/primed/dharmamitra-<tgt>-general/` or
`machine-drafts/primed/gemini-<tgt>-general/`) with the glossary and a `style.md` like the ones in the
language sections. After that: `graded-translate` Phase 2 (enforce on the machine
draft) and Phase 3 (drift), then the back-translation meaning check, the commentary
light check, and a native reviewer, who starts with the flagged table.

---

## Language sections

### Chinese (`zh`)

- **Reference:** the classical canon version in CBETA (Taishō). Find it by title or a
  well-known line; the data API returns a fascicle:
  `https://cbdata.dila.edu.tw/stable/juans?work=<T-number>&juan=1`. A teacher's or
  centre's published version is a second copy to check against.
- **Script:** WeBuddhist's default is Traditional (`zh-Hant`). For Simplified, convert
  finished files (OpenCC `t2s`); never re-pick terms.
- **Mantras:** Chinese characters. Where the syllable belongs to a mantra people
  chant, use the recitation form (Tārā: 嗡 達咧 都達咧 都咧 梭哈; also 吽, 呸); otherwise
  use the classical form (特囉, 喝囉).
- **Keep / modernise / replace:** keep 敬禮, 無餘, 起屍, 灌頂; use the modern spelling
  of the same word (蓮華 → 蓮花, 藥叉 → 夜叉); replace 部多 with 鬼神.
- **Engine:** DharmaMitra `--lang "modern chinese"`. The glossary priming works well
  (the Tārās: 46% → 89% locked words before enforcement).
- **style.md:** "Translate this Tibetan verse of praise line by line into clear modern
  written Chinese in Traditional characters: render each Tibetan line as one line of
  Chinese, in the same order, and keep the same number of lines as the source. Use
  plain modern vocabulary and grammar, not classical Chinese, and do not force lines
  into seven characters. Use the established Chinese Buddhist terms where they exist.
  Devotional but clear register. Write mantra syllables in Chinese characters, never
  in Latin letters. Use full-width Chinese punctuation. Do not add commentary, notes,
  or explanation."

### Vietnamese (`vi`)

- **Reference:** the finished **Chinese** word list and translation, if there is one.
  Vietnamese Buddhist vocabulary is mostly Sino-Vietnamese (Hán-Việt), so the Chinese
  choices, read the Vietnamese way, are strong evidence (敬禮 *kính lễ*, 度母 *Độ Mẫu*,
  灌頂 *quán đảnh*, 攝伏 *nhiếp phục*, 威力 *uy lực*). Source code `related`. A
  published Vietnamese version, if the owner can supply one, is a second reference.
- **Keep / replace:** keep a Hán-Việt word Vietnamese Buddhists use in prayer (*kính lễ*,
  *quán đảnh*, *tịch tĩnh*). Replace one only scholars know with the plain word:
  無餘 *vô dư* → *không sót*; 起屍 *khởi thi* is kept but flagged for the reviewer.
  Use *Chánh* (not *Chính*) in *Chánh Đẳng Chánh Giác*, as in the register table
  (*chánh niệm*).
- **Mantras:** usually Latin, the way Vietnamese Vajrayana practitioners write them
  (Om Tare Tuttare Ture Soha; Hum, Phat), without diacritics. The Sino-Vietnamese
  temple forms (Án, Ta Bà Ha) are the alternative.
- **Checks:** run `check_termbase_consistency.py` with `--strict-diacritics`. Folding
  accents would make *chân* match *chăn* and *hỷ* match *hy*.
- **Engine:** DharmaMitra may not serve Vietnamese well. Test one or two verses
  (`--lang vietnamese --only 1-1,1-2 --out /tmp/…`) before a full run. Otherwise use
  Gemini (`gemini-translate`, `GEMINI_API_KEY`), whose track glossary (`glossary.tsv`)
  also pins names.
- **style.md:** "Translate this Tibetan verse of praise line by line into clear modern
  Vietnamese with full diacritics: render each Tibetan line as one line of
  Vietnamese, in the same order, and keep the same number of lines as the source.
  Use the Sino-Vietnamese Buddhist vocabulary standard in Vietnamese Buddhist
  literature and the established Vietnamese names of buddhas and bodhisattvas.
  Devotional but clear register, natural modern Vietnamese word order. Keep mantra
  syllables in romanized Sanskrit without diacritics (Om, Tare, Tuttare, Ture, Soha,
  Hum, Phat), never translated. Do not add commentary, notes, or explanation."

### Hindi (`hi`)

- **Reference:** none needed. Hindi takes its Buddhist vocabulary straight from Sanskrit, so the standard term
  *is* the Sanskrit word in Devanagari (नमस्कार, स्तुति, अभिषेक, सम्यक् सम्बुद्ध, वेताल, यक्ष). Source code
  `standard`; no classical canon or related-language list sits in between. Pass no `--reference`.
- **Script:** Devanagari. Use the Sanskrit spelling in the Sanskritized register (चन्द्रमा, not चंद्रमा; सत्त्व,
  not सत्व).
- **Mantras:** Devanagari, the Sanskrit as chanted: ॐ तारे तुत्तारे तुरे स्वाहा; हूँ, फट्, त्रट्, हर. A
  Sanskrit title line is written in Devanagari too, not kept in IAST.
- **Keep / replace:** keep the Sanskrit term where Hindi readers know it in that sense, even where English
  chose a plain word (ग्रह for གདོན, "demons" in English — flag it). Replace one that a general Hindi reader
  would take for something else: जिन / जिनपुत्र sound Jain, so write बुद्ध / बोधिसत्त्व. Keep distinct
  English locks distinct in Hindi: भगवती is བཅོམ་ལྡན་འདས་མ, so རྗེ་བཙུན་མ་འཕགས་མ is पूज्य आर्या; बीजाक्षर is
  the named seed-syllable, अक्षर the generic ཡི་གེ.
- **Lock stems (rule 6):** Sanskrit compounds hide the free word — lock the stem: महा (महान्, महाभयंकर,
  महानता), चन्द्र (चन्द्रमा, अर्धचन्द्र). Don't put `…` in a rendering; the checker searches it literally.
  A stem is for the checker, not for the model: give such a term a `"hint"` (a whole word, e.g. महान्,
  चन्द्रमा) in the decisions file, and the glossary sends the hint instead. Without one, the Nepali primed
  run wrote bare महा and परम into the text.
- **Engine:** Gemini (`gemini-translate`). A Gemini zero-shot already reached 90% of the locked words on the
  Tārās, because its `style.md` asks for the Sanskrit Buddhist vocabulary.
- **style.md:** "Translate this Tibetan liturgical text into Hindi, line by line: render each Tibetan line as
  exactly one Hindi line, in the same order, keeping the same number of lines as the source. Write in
  Devanagari. Use the established Hindi/Sanskrit Buddhist vocabulary rather than coining new terms or
  borrowing Hindu-devotional or Christian idiom. Devotional but clear register, in natural Hindi word order.
  Keep mantra syllables as Devanagari transliteration of the Sanskrit, never translated. Render buddhas,
  bodhisattvas and deities by their Sanskrit names in Devanagari. Do not add commentary, notes, or
  explanation."

### Adding a language

Add a section here with its reference, keep/replace rules, mantra convention, engine
and `style.md`, and a register section in `$GT/SKILL.md` §Registers. The scripts do
not change.

---

## Rules

1. **Translate from the Tibetan.** The English is only the meaning check, never the
   source text and never a source of words.
2. **Edit the decisions file, never the built files.** Re-run Step 5 with `--force`.
3. **A reference is evidence, not text.** Never copy its lines into the translation.
   Respect its licence (CBETA: CC BY-NC-SA).
4. **Every value has a source; every disagreement has a note and a `decision`.**
5. **Never overwrite a decisions file** (`--template` refuses) or outputs without `--force`.
6. **A script change is a conversion** (Traditional ↔ Simplified), done on finished
   files, not a second set of picks.

## Completion check

- [ ] The four choices are recorded in `_meta`.
- [ ] The reference is in place, with retrieval notes, or its absence is stated.
- [ ] Every base term has `<tgt>`, `source` and `note`; flagged picks have `decision`.
- [ ] Every mantra syllable is locked, one form each.
- [ ] `build_termbase.py` ran clean; `validate_grade_file.py --lang <tgt>` reports 0 errors.
- [ ] The baseline is measured and in `_meta.baseline`; the glossary is built with `--scope-all`.
- [ ] `STATE.md` updated; files committed.

## Worked examples — Praise to the Twenty-One Tārās (21-taras-rails, 2026-09-24)

- **Chinese (general, Traditional).**
  - Reference: CBETA T1108B, the same text the 17th Karmapa office publishes. All 21
    stanzas are 28 characters; 7 were checked against the Karmapa page.
  - Word list: 47 + 5 Chinese-only entries, 14 of them flagged.
  - Machine drafts: zero-shot 63/137 locked words; the primed DharmaMitra draft
    122/137; after enforcement 137/137.
  - Files: `zh/zh-decisions-general.json` is the source of truth. A rebuild from it
    is byte-identical.
- **Vietnamese (general):** the related-language reference is the Chinese list and
  translation; the machine draft is Gemini zero-shot. See `vi/` and `STATE.md`.
- **Hindi (general):** no reference; the Sanskrit terms are the standard. 47 + 4 Hindi-only
  entries (ॐ, स्वाहा, हर, तारे), 7 flagged. The Gemini zero-shot already had 123/136 locked words;
  after enforcement 136/136. The full commentary check then found no errors. See `hi/` and `STATE.md`.

## After this skill

`machine-translate` (glossary-primed draft) → `graded-translate` Phase 2 and 3 →
back-translation meaning check → `commentary-fact-check` light check against the
existing consensus → `translation-qa` → native review → `translation-upload`.
