---
name: zeroshot-translate
description: >
  Translate a block-ID'd source text into a target language in one pass, with
  the degree of terminology control the job needs: no termbase at all, a locked
  bilingual glossary as a hard constraint, or triangulation against existing human
  translations plus a second source language for disambiguation.

  Trigger on "translate this", "zero-shot translation", "translate these blocks into
  X", "translate using the termbase", "translate this chapter".

  Output block IDs always match the source exactly.
profile: any
supersedes:
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/translate-zero-shot/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/zeroshot-translator/SKILL.md
  - abhidhamma-rails/4-SYSTEM/Skills/zero-shot-translate/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Zero-shot translation with terminology control

| Mode | Terminology control | Use |
|---|---|---|
| 1 — Triangulated | Glossary + a second source language + existing human translations | A text with good scholarship around it; highest quality |
| 2 — Termbase-locked | The track's bilingual glossary as a hard constraint | The normal production path |
| 3 — Unconstrained | None — audience profile only | A first look, or a text with no glossary yet |

**Mode 2 is the default for production work.** It requires `bilingual-glossary` Phase
4 to have produced the track's working glossary; contested terms are locked and the
translation may not depart from a locked rendering without saying so explicitly in
its notes.

**Mode 1 when the material supports it.** Disambiguating the source against a second
source language (Sanskrit against Tibetan, say) and checking each verse against
block-aligned human translations catches misreadings that no amount of terminology
control will. It costs more and needs those translations to exist and be aligned.

**Mode 3 is explicitly termbase-free** — no keyword extraction, no sense-tagging, no
terminology locking. That makes it fast and makes its terminology inconsistent across
a long text. Use it to see what a text says, not to produce something anyone cites.

Whichever mode: block IDs match the source one-for-one, and `translation-qa` grades
the result against the source, the verse packages, and the track's requirements.

---

## Mode 1 — Triangulated — second source language plus human translations

Disambiguates each verse against a second source language and checks it against block-aligned human translations.

Produces a full *Bodhisattvacaryāvatāra* translation track directly from `$SOURCES/` when `$VERSES/<verse-id>-summary.md` packages are not yet `status: complete`.

**Method: evidence-based triangulation.** Every decision is backed by something checkable at the exact verse, never by a pre-built table or parametric knowledge:

- **Meaning** — the Tibetan translation is the primary source; the Sanskrit root text resolves ambiguity (homonyms, pāda breaks, philosophical terms); three block-aligned human translations are compared at the same block ID. Consensus among them confirms a reading; divergence among them marks genuine ambiguity — check the Sanskrit and flag.
- **Terminology** — the termbase is built empirically as translation proceeds: when a key term first appears, its attested renderings are read from the aligned translations *at that block ID*, one is chosen for the track register, and appended with the verse citation as rationale. No glossary seeding.
- **Register** — from the track's existing `requirements.md` / `audience.md`, which are read, never overwritten.

Output matches the vault's transformation conventions: `requirements.md` / `audience.md` / `termbase.md`, one `Chapter-NN.md` per chapter, then one merged full-text file.

**Reference examples (this vault):**
- Track contracts: `$TRANSFORMATIONS/Translations/en-plain-english/` (`requirements.md`, `audience.md`, `termbase.md`)
- Merged full-text outputs: `$TRANSFORMATIONS/Translations/en-translate/BCA-Full-Children-English.md`, `BCA-Full-Plain-English.md`, `BCA-Full-Scholar-English.md`

---

### Inputs

| Input | Required | Description |
|---|---|---|
| **Target language** | ✓ | ISO-style code or short name, e.g. `en`, `hi`. Determines track folder prefix. |
| **Audience level** | ✓ | `children`, `plain`, or `scholar`. Determines register and track suffix. |
| **Chapter scope** | optional | Single chapter (`3`), range (`1-3`), or `all` (default: `all` = chapters 1–10). |
| **Merge** | optional | `yes` (default) or `no`. When `yes`, run merge after all requested chapters exist. |

If target language or audience level is missing, ask before proceeding.

#### Fixed source files (this vault)

| Role | Path |
|---|---|
| Tibetan primary | `$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md` |
| Sanskrit reference | `$SOURCE_TEXTS/BCAV08_SH_sk.md` |

#### Triangulation set (block-aligned with the Tibetan source)

The default set — always loaded, all three, for every chapter:

| Witness | Path |
|---|---|
| W1 | `$TRANSLATIONS/en-Padmakara_2006.md` |
| W2 | `$TRANSLATIONS/en-Wallace.md` |
| W3 | `$TRANSLATIONS/en-David_Karma_Choephel.md` |

For non-English targets, additionally load block-aligned translations in the target language when they exist (e.g. `zh-隆蓮法師.md` and other `zh-*` files; `hi-बोधिचर्यावतारः.md`) — these take precedence for terminology evidence. Record the triangulation set in the track's `requirements.md`.

#### Consolidated glossaries (optional hint only)

`$GLOSSARIES/bo-en.md` (and `sk-en.md`, `sk-zh.md`, `sk-bo.md`) may be consulted for frequency data on a rendering, but they are draft, cover ~50 keywords, and are **never** used to seed or override the termbase. Terminology evidence comes from the triangulation set at the exact block ID.

#### Track folder (output root)

```
$TRANSFORMATIONS/Translations/<lang>-<audience>-audience/
```

Examples: `en-children-audience`, `en-plain-audience`, `hi-scholar-audience`.

---

### Output

| Artifact | Path |
|---|---|
| Localized requirements | `$TRANSFORMATIONS/Translations/<track>/requirements.md` |
| Localized audience profile | `$TRANSFORMATIONS/Translations/<track>/audience.md` |
| Track termbase (grows per chapter) | `$TRANSFORMATIONS/Translations/<track>/termbase.md` |
| Per-chapter translation | `$TRANSFORMATIONS/Translations/<track>/Chapter-NN.md` |
| Merged full text | `$TRANSFORMATIONS/Translations/<track>/BCA-Full-<Label>.md` |

---

### Output file format

#### Per-chapter file (`Chapter-NN.md`)

```markdown
---
ref: <N>
title: "Chapter <N> — <English chapter title>"
transformation_type: translation
track: <lang>-<audience>-audience
context_packages:
  - $TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md (^<N>-0–^<N>-a)
  - $SOURCE_TEXTS/BCAV08_SH_sk.md (^<N>-0–^<N>-a)
  - $TRANSLATIONS/en-Padmakara_2006.md (^<N>-0–^<N>-a)
  - $TRANSLATIONS/en-Wallace.md (^<N>-0–^<N>-a)
  - $TRANSLATIONS/en-David_Karma_Choephel.md (^<N>-0–^<N>-a)
generation_date: <YYYY-MM-DD>
status: draft
---

## A Guide to the Bodhisattva's Way of Life   ← Chapter 1 only
#### <Audience> <Language> Translation          ← Chapter 1 only
*Zero-shot translation from the Tibetan of Blo ldan shes rab, cross-checked against the Sanskrit of Śāntideva*   ← Chapter 1 only

---

### Chapter <N>: <Chapter title>

<One prose paragraph per verse-block, ending with block ID.> ^<N>-<V>

*Thus ends Chapter <N>: "<Chapter title>."*
```

Publishing metadata (`text_id`, `edition_id`, `category_id`, `license`, etc.) is added by human editors at publication time — do not invent it.

**Chapter titles (BCA):**

| Ch | Title |
|---|---|
| 1 | The Benefits of Bodhichitta |
| 2 | Confessing Wrongdoing |
| 3 | Taking Hold of Bodhichitta |
| 4 | Carefulness |
| 5 | Guarding Awareness |
| 6 | Patience |
| 7 | Diligence |
| 8 | Meditative Concentration |
| 9 | Wisdom |
| 10 | Dedication |

#### Verse block rule

- One flowing prose paragraph per source verse-block.
- End every paragraph with the source block ID: `^chapter-verse` (e.g. `^3-12`).
- Preserve every verse ID present in the Tibetan source for that chapter — no skips, no duplicate IDs.
- Do not include Tibetan or Sanskrit source text in the output (target language only).

---

### Rules

1. **Rails first, zero-shot second.** For each verse, check `$VERSES/<verse-id>-summary.md`. If `status: complete`, use its synthesis and disambiguated restatement (plus `$GLOSSARIES/` and Local-Wiki as needed). If not complete, translate zero-shot per the workflow below.
2. **Never modify `$SOURCES/`.** Read only.
3. **Never set `status: complete`.** All generated files stay `status: draft` until a domain specialist reviews them (run `translation-qa` before sign-off).
4. **Termbase is law, and evidence-built.** Every keyword rendering must match `termbase.md`. New terms are **appended** at first occurrence with the attested renderings observed in the triangulation set at that block ID, the chosen rendering, and the citation as rationale — never silently change an existing locked rendering once a chapter has shipped. Never re-seed or rewrite an existing termbase.
5. **One chapter per save.** Translate and write one `Chapter-NN.md` at a time. Long chapters (5, 8, 9) may be read in sections but must be written as one complete chapter file.
6. **Register fidelity.** Follow the localized `requirements.md` and `audience.md` strictly — sentence length, loanword policy, footnote ban, verse-as-prose rule.
7. **Sanskrit is reference only.** When Tibetan and Sanskrit diverge, prefer the Tibetan line as the meaning base; use Sanskrit to disambiguate, not to override. Flag real divergences with the editorial note format below.
8. **Triangulation is mandatory, copying is forbidden.** Compare every draft verse against all three witnesses for *meaning* (subject, object, negations, modality, imagery). If all witnesses agree and your draft disagrees, your parse is almost certainly wrong — re-examine the Tibetan. If the witnesses disagree *with each other*, the verse is genuinely ambiguous — resolve from the Sanskrit and flag. Never copy any witness's wording — each is under its own copyright and its register will not match the track.
9. **Divergence flag format.** When sources genuinely disagree or a reading is uncertain, append a bracketed editorial note after the block ID line: `[Ed: Skt reads "…"; Tibetan followed.]` or `[Ed: Padmakara and Wallace read this pāda as X; Choephel as Y; Sanskrit supports X.]` English, factual, one sentence.
10. **Sensitive verses.** Verses with outdated cultural assumptions (e.g. `^10-30`) get a brief bracketed editorial note in children/plain tracks; scholar track may use a footnote-style aside only if `requirements.md` allows it.
11. **Do not hallucinate.** Translate only what is in the source. No invented explanations, no dropped pādas, no merged verses.
12. **Merge is deterministic.** After all chapters exist, merge with the bundled script (`scripts/merge_chapters.py`) — do not hand-stitch the full text.

---

### Per-verse translation workflow

For each verse-block, in order:

1. **Rails check** — if `$VERSES/<id>-summary.md` is `status: complete`, translate from its disambiguated restatement and skip to step 6.
2. **Parse the Tibetan** — identify agent, object, verb, negations, and particles; note any homonym or ambiguous syntax.
3. **Read the witnesses** — read all three triangulation translations at this block ID. Classify: **consensus** (all agree on meaning) or **split** (they diverge — record who reads what).
4. **Consult the Sanskrit** — resolve each ambiguity from step 2 and each split from step 3 against the Sanskrit pāda. Note (do not resolve silently) any real Tibetan/Sanskrit divergence.
5. **Resolve terminology** — apply locked termbase renderings. For a key term not yet in the termbase: list its renderings across the witnesses at this block ID, choose the one fitting the track register, and queue it for append with the citation (e.g. `བདེ་གཤེགས། → "the Blissful Ones" — Padmakara "Blissful Ones", Wallace "Sugatas", Choephel "sugatas" at ^1-1; register avoids loanwords`).
6. **Draft** — one prose paragraph in the track register per `requirements.md`, in your own wording.
7. **Verify against consensus** — if the witnesses were in consensus and your draft's meaning differs, return to step 2. If the split persists after step 4, keep the Sanskrit-supported reading and add a divergence note (Rule 9).
8. **Finalise** — append the block ID; add editorial note if flagged.

---

### Procedure

#### Step 1 — Confirm inputs

Resolve:
- `track` = `<lang>-<audience>-audience`
- `track_dir` = `$TRANSFORMATIONS/Translations/<track>/`
- Chapter list from scope (`all` → 1..10)
- Triangulation set (see Inputs)

#### Step 2 — Track folder

**If the track folder already exists (the normal case):** read `requirements.md`, `audience.md`, and `termbase.md` and continue. Do not overwrite, re-localize, or re-seed any of them — an existing termbase grows append-only from this point, however thin it is.

**Only if `track_dir` does not exist:**

1. Create `track_dir`.
2. Write `track_dir/requirements.md`, using `$TRANSFORMATIONS/Translations/en-plain-english/requirements.md` as the structural model. Localize for the target language and audience level (register, reading level, loanword policy, sentence length). Include **§ Zero-shot sources**: Primary: `$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md`; Reference: `$SOURCE_TEXTS/BCAV08_SH_sk.md`; Triangulation set: the three witnesses (plus any target-language translations). Fallback rule: use zero-shot when verse rails are not `status: complete`.
3. Write `track_dir/audience.md` (model: `en-plain-english/audience.md`), localized for the audience level.
4. Create `track_dir/termbase.md` **empty** — header and table columns only (source lemma | chosen rendering | rationale with block-ID citation), modeled on `en-plain-english/termbase.md`. Do not seed it: entries are added at first occurrence during translation, from witness evidence (per-verse workflow step 5).

#### Step 3 — Translate each chapter

For each chapter `N` in scope:

**a. Load sources**

- Read Tibetan chapter: lines from `^N-0` through the line before `^(N+1)-0` (chapter 10 through `^a-0`).
- Read matching Sanskrit chapter from `BCAV08_SH_sk.md` for the same verse IDs.
- Read the same chapter from **all three** triangulation translations (and any target-language translations).
- Load `termbase.md` and scan for terms appearing in this chapter.

**b–c. Translate**

Apply the **per-verse translation workflow** above to every verse-block in the chapter.

**d. Write chapter file**

Save to `track_dir/Chapter-NN.md` using the format above. Set `generation_date` to today.

**e. Update termbase**

Append the terms queued during this chapter (source lemma, chosen rendering, rationale with witness renderings and block-ID citation). Never edit prior rows.

**f. Report progress**

After each chapter, state which chapter finished, which remain, and how many divergence notes were added.

#### Step 4 — Merge full text (when scope is complete)

When all chapters in scope exist and `merge` is not `no`:

```bash
python $SKILL/scripts/merge_chapters.py \
  "$TRANSFORMATIONS/Translations/<track>" \
  --track "<track>" \
  --title "Entering the Bodhisattva's Way of Life — Full Text (<Audience> <Language>)" \
  --output "BCA-Full-<Audience>-<Language>.md" \
  --chapters all
```

The script fails on missing chapters or duplicate block IDs — fix the chapter files and rerun; never hand-edit the merged output.

#### Step 5 — Self-check before handoff

Run all of these; fix and rerun until clean:

1. **Verse coverage** — for each chapter, extract the unique `^N-V` IDs from the Tibetan source chapter and from `Chapter-NN.md`; the sets must be identical (no skips, no extras, no duplicates).
2. **Termbase consistency** — for each locked rendering, grep the chapter files to confirm no competing rendering of the same lemma slipped through; every termbase row added this run cites at least one block ID.
3. **Divergence notes** — every `[Ed: …]` note names its source; no unresolved `⚑` or TODO markers remain.
4. **Frontmatter** — every chapter file has `status: draft` and complete `context_packages`.
5. **QA skill** — run `translation-qa` on the per-chapter files (it includes `mqm_mechanical_checks.py`). Iterate until no critical/major errors. This step is required, not optional.

---

### Completion check

- [ ] Target language, audience level, and triangulation set confirmed.
- [ ] Track folder exists; existing `requirements.md`, `audience.md`, `termbase.md` were read, not overwritten or re-seeded.
- [ ] Every requested chapter saved as `Chapter-NN.md` with correct frontmatter and `status: draft`.
- [ ] Every verse in scope has exactly one `^N-V` block ID in the output (verified against source, not just counted).
- [ ] Every verse triangulated against all three witnesses; splits resolved from the Sanskrit and flagged with `[Ed: …]` notes.
- [ ] `termbase.md` updated append-only, each new row citing witness renderings at a block ID.
- [ ] Merged full-text file written via `scripts/merge_chapters.py` when scope is complete (unless user opted out).
- [ ] `translation-qa` run with no remaining critical/major errors.
- [ ] User told which chapters remain if scope was partial.
- [ ] User reminded that only a domain specialist may promote files to `status: complete`.

---

## Mode 2 — Termbase-locked

The track's bilingual glossary is a hard constraint for contested terms.

This skill translates Pāli source text block-by-block, using the per-track bilingual glossary (output of `bilingual-glossary` (Phase 4)) as a hard constraint: every term that appears in the glossary must be rendered with its chosen rendering, not whatever the LLM would choose unprompted. Terms not in the glossary are translated freely.

The key design principle is a **minimal, high-signal termbase**: the glossary passed to the LLM contains only the ~20–60 contested terms identified by `bilingual-glossary` (Phase 3), not every term in the vocabulary. A bloated termbase creates noise and contradictions; a focused one enforces consistency where it matters.

Processes text in batches of 30–50 blocks to stay within context limits. Each output block carries the same `^block-id` as its source.

---

### Inputs

- **Track folder** — `$TRANSFORMATIONS/Translation/<track-name>/`. Must contain:
  - `bilingual glossary.md` — per-track glossary (output of `bilingual-glossary` (Phase 4))
  - `requirements.md` — translation style requirements
- **Source file** — Pāli root text with Obsidian block IDs, e.g. `$SOURCE_TEXTS/pi-dhammasangani.md`
- **Block range** — which blocks to translate. Accepts: `all`, a single block ID, or a range like `1-0 to 1-100`
- **Output path** — where to write the translation, e.g. `$TRANSFORMATIONS/Translations/<track-name>/en-dhammasangani-<track-name>.md`

### Output

```
$TRANSFORMATIONS/Translations/<track-name>/<lang-tag>-<text-name>-<track-name>.md
```

---

### Output file format

```markdown
---
track: <track-name>
source: $SOURCE_TEXTS/<pi-text>.md
target_language: <en | bn | sin | ...>
glossary: $TRANSFORMATIONS/Translation/<track-name>/bilingual glossary.md
blocks_translated: <N>
last_updated: <ISO date>
status: draft
---

## <Text title> — <track-name> translation

<translated text for block 1> ^<block-id>

<translated text for block 2> ^<block-id>
```

Each paragraph ends with the same `^block-id` as the corresponding Pāli source block. This preserves alignment with the source for downstream bilingual tools (`pali-biterm-extraction`, `interlinear-gloss`).

---

### Rules

1. **Termbase renderings are hard constraints.** If a Pāli token in the source appears as a keyword in the bilingual glossary, its English rendering in the output must match the glossary's chosen rendering exactly — no synonyms, no paraphrases.
2. **Block IDs must be preserved.** Every output block carries the same `^block-id` as its source block. Missing or mismatched IDs break all downstream alignment tools.
3. **Translate in batches of 30–50 blocks.** Larger batches risk exceeding context limits and cause the LLM to drift from the termbase constraints.
4. **Never translate more blocks than exist.** If the requested range includes block IDs not present in the source file, stop and report the missing IDs rather than skipping them silently.
5. **The glossary injected into the prompt must be filtered to terms actually present in the batch.** Injecting the full glossary for every batch adds noise; scan each batch's Pāli tokens against the glossary and include only the relevant entries.
6. **Mark output `status: draft`.** A human or QA skill reviews before promotion.
7. **Never modify source files.** Reads from `$SOURCES/` and `$TRANSFORMATIONS/Translation/<track>/`; writes only to `$TRANSFORMATIONS/Translations/<track>/`.

---

### Procedure

#### Step 1 — Load inputs

1. Read `$TRANSFORMATIONS/Translation/<track>/bilingual glossary.md`. Extract the table: build a dict `{pali_token: (rendering, rationale)}` for every row.
2. Read `$TRANSFORMATIONS/Translation/<track>/requirements.md`. Note: target register, style constraints, script, any explicit prohibitions.
3. Parse the source file blocks (same parser as `pali-biterm-extraction`): collect `{block_id: pali_text}` for all blocks in the requested range.

#### Step 2 — Build the termbase index

For efficient per-batch filtering, build a lookup from plain-ASCII Pāli root forms to glossary entries. A source block "matches" a glossary entry when the plain-ASCII form of any Pāli token in the block is a substring of the plain-ASCII glossary keyword (or vice-versa, for inflected forms).

#### Step 3 — Translate in batches

For each batch of 30–50 blocks:

1. **Filter the termbase** to entries relevant to this batch (Step 2 lookup).
2. **Construct the prompt:**

```
You are translating Pāli Buddhist text into <target language>.

TERMBASE — render these Pāli terms exactly as shown, without substitution:
<pali_token_1> → <rendering_1>  [<rationale>]
<pali_token_2> → <rendering_2>  [<rationale>]
...

REQUIREMENTS:
<paste relevant clauses from requirements.md>

INSTRUCTIONS:
- Translate each numbered verse below from Pāli to <target language>.
- Preserve the verse numbers exactly.
- Apply the termbase renderings wherever those Pāli forms appear.
- Do not transliterate Pāli terms unless the termbase says to.
- Keep translations concise and faithful to the source.

VERSES:
[1] <pali_text_1>
[2] <pali_text_2>
...
```

3. **Parse the response.** Match each `[N]` label to its source block ID. If any block is missing from the response, flag it and retry that block individually.
4. **Append to the output file** with `^block-id` suffixes.

#### Step 4 — Post-batch checks

After each batch:
- Confirm every source block ID has a corresponding output block.
- Spot-check 2–3 blocks for termbase compliance: search the output for the Pāli tokens from the glossary and confirm the correct rendering was used.
- If a termbase violation is found, re-run the batch with a stricter prompt (add the violation as a negative example).

#### Step 5 — Finalise output file

After all batches are complete:
1. Write the YAML frontmatter (`blocks_translated`, `last_updated`, `status: draft`).
2. Confirm block count matches the requested range.

---

### Completion check

- [ ] `bilingual glossary.md` and `requirements.md` confirmed present in track folder
- [ ] All source blocks in the requested range parsed successfully
- [ ] Every output block has a `^block-id` matching its source
- [ ] Spot-check confirms termbase renderings applied correctly
- [ ] Output written to `$TRANSFORMATIONS/Translations/<track>/`
- [ ] `status: draft` in frontmatter
- [ ] No source files modified

---

## Mode 3 — Unconstrained, audience-guided

No termbase at all; guided only by an audience profile.

Translates a source text directly into a target language named by the user, applying an existing audience profile for register and style. There is no termbase in this path at all — no keyword extraction, no sense-tagging, no locked terminology. This is the fast path — useful for a first draft, a quick comparison, or when full terminology-locking isn't warranted for the task at hand.

### When to use this instead of the rails pipeline

Reach for this when the user wants a translation now and hasn't asked for (or doesn't need) locked, consistent terminology across a long text — e.g. a single chapter, a draft to react to, or a translation where term consistency matters less than speed. If the user is building toward a long, terminology-critical translation, mention that the rails pipeline (`keyword-equivalence-mapper` -> `word-sense-grouper` -> `termbase-builder` -> `rails-verse-translator`) exists as the more rigorous alternative, but don't force it on a request that's just asking for a zero-shot pass.

### Inputs needed

1. **Source text** (or its split chapters — see `split-file-by-markers` if splitting first is useful for a long text).
2. **Target language** — stated by the user in their prompt. This skill doesn't assume or default to any particular language; confirm it if the prompt is ambiguous.
3. **Audience profile** — an existing profile describing the intended readership, register, and translation goals (e.g. `audience_profile/plain.md`). If none exists yet, that needs to be created first rather than guessed at.

### Workflow

1. Read the audience profile closely — tone, register, how much explanatory latitude is allowed, priority order between understanding/accuracy/readability/consistency, etc.
2. Translate the source into the target language, applying the audience profile's guidance directly. Since there's no termbase, use your own best judgment for terminology, staying consistent within the piece even without an external reference locking word choices in advance.
3. **Translate verse by verse, pada-aligned to the source — this is required, not optional, even without a termbase.** Each segment's translation must mirror its source's exact line count, with each target-language line corresponding to its source line's content, not collapsed into flowing prose or mechanically word-wrapped. Preserve every segment ID exactly, in the same position as the source (typically the end of the last line of its segment). Skipping the termbase step doesn't mean skipping structural fidelity — the two are independent; this one always applies whenever the source has a segment/pada structure.
4. If the source is long, it's still reasonable to work through it in natural chunks (e.g. chapter by chapter) with the user rather than producing the entire thing in one uninterrupted pass — apply the same one-unit-per-turn reasoning as `rails-verse-translator` if the text is large enough that a systemic issue would be expensive to discover late.
5. **Translate chapters one at a time, in sequence, never in parallel.** Finish and present one chapter, then wait for the user's go-ahead before starting the next — don't dispatch multiple chapters at once (e.g. via parallel subagents) even though there's no termbase step gating things here. The same reasoning as `rails-verse-translator` applies: a register or structural problem caught after one chapter is cheap to fix; the same problem discovered after several chapters have already been produced in parallel is not, and it also avoids burning a large amount of tokens translating material that hasn't been reviewed yet.

### Where the output goes

1. **Create a subfolder for the target language** if one doesn't already exist, named after the language (e.g. `hindi`, `english`, `chinese`) rather than its short tag.
2. **The required output is the per-chapter split**, in a subfolder named:
   ```
   <text-slug>-<target-language>-<audience-profile-slug>-zeroshot_split_chapters/
   ```
   Example: `AI_translation/hindi/bca-hindi-plain-zeroshot_split_chapters/`

   - `<text-slug>` is a short identifier for the source text (e.g. `bca` for Bodhicaryāvatāra in this project) — infer it from existing filenames/conventions in the project if there is one, or ask if it's genuinely unclear.
   - `<target-language>` is the full language name (e.g. `hindi`, `english`, `chinese`), not a short tag — matching the language subfolder's own name.
   - `<audience-profile-slug>` matches the audience profile's own name (e.g. `plain`).
   - The `-zeroshot` marker distinguishes it from a termbase-guided (rails) translation of the same text/audience/language combination.

   This is the natural output shape since the translation happens chapter by chapter to begin with — no separate merge step is needed to produce it.

3. **A merged single file (same name without `_split_chapters`) is optional**, not a required output of this skill — only produce one if the user actually asks for it.

### Notes

- Because there's no locked termbase, re-running a zero-shot translation (or translating the same text for a different audience profile) can legitimately produce different word choices each time — that's expected, not an inconsistency to chase down.
- If the user later wants to upgrade this into a rails-guided translation, this zero-shot file is a reasonable candidate to build the keyword extraction and glossary from — its terminology choices, even if not locked, reflect real translation decisions worth capturing rather than starting from nothing.

---

### Provenance

Ported verbatim 2026-08-01 from
`bodhisattvacharyavatara-rails/AI_translation/skills/zeroshot-translator.md`
(the deliberately language-agnostic variant; that vault's sibling
`$SKILLS/translate-zero-shot/` hardcodes BCA vault paths and rails).
In this repo its main job is producing the block-ID-preserving English
translation that `$SKILLS/english-keyword-extraction/` consumes. The
audience-profile input it expects can be a one-paragraph profile written for
the run; the full rails pipeline it mentions was deliberately not ported.
