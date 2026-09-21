---
name: verse-context
description: >
  Build the context package for a verse: transclude the root verse and the
  relevant commentary passages, paraphrase or synthesise how each commentator reads it,
  and write a disambiguated restatement of the verse in the original language — the
  package a translator works from instead of the bare verse line.

  Trigger on "build the verse context", "make the verse package", "what do the
  commentaries say about this verse", "build the context for chapter N", "verse
  context for the whole chapter", "contextual summary for these verses".

  One verse, a whole chapter in bulk, or a group of verses under one outline node.
profile: rails-vault
supersedes:
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/verse-context/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/verse-context/SKILL.md
  - abhidhamma-rails/4-SYSTEM/Skills/verse-context/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/verse-context-batch/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/root-verse-context-creator/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Build a verse's context package

| Mode | Scope | Use |
|---|---|---|
| 1 — Single verse | One verse | Default; also the one to use while the format is still being tuned |
| 2 — Chapter batch | Every verse in a chapter | After mode 1 has been validated on a few verses of that text |
| 3 — Verse group | A group of verses under one sa-bcad node | When the commentary treats several verses as one unit |

**Run mode 1 on two or three verses before starting a batch.** Mode 2 builds a
complete block-ID mapping across every commentary and then generates one file per
verse — an error in the package format is an error in every file, and finding it
after 90 verses is expensive.

Mode 3 exists because commentaries frequently do not comment verse by verse: they
take a group of verses under one outline node and treat it as a single topic. Forcing
that into per-verse packages invents distinctions the commentary did not make. When
the sa-bcad groups verses, follow it.

Every mode's output cites block IDs — into the root text for the verse, into each
commentary for its reading.

---

## Mode 1 — Single verse

Transcludes the root verse (both source languages where they exist), paraphrases each commentary's reading, then compiles the descriptive layers.

Produces the **verse-level descriptive context** that every downstream transformation (translation, adaptation, study plan) works from. The translator never sees the bare verse: it sees the disambiguated restatement plus the chendrel, the concepts, the stories, and the cited synthesis. This is the rail that defuses hallucination — every interpretive decision is made and cited here, once, before any output is generated.

Authoritative schema: [`$RAILS/About Rails.md`](../../../$RAILS/About%20Rails.md) §5. Vault conventions (commentary IDs, language tracks, addressing): [`$SYSTEM/Docs/vault-annex.md`](../../Docs/vault-annex.md). When this skill and `About Rails.md` disagree, **About Rails wins**.

---

### Language rule

- **Traditional Interpretation** — English paraphrase, one subsection per commentary.
- **Every other section is in Tibetan**: AI Overview, Chendrel, Word-by-word Disambiguation, Key Concepts, Stories, Metaphors, Quotations, and the Disambiguated Restatement.
- Quotations are verbatim Tibetan. Never translate scripture in the rail — that is a transformation's job.

This follows the vault-annex convention: the primary analysis language for `$RAILS/` is Tibetan; only the cross-tradition paraphrase is held in English so coverage is legible at a glance.

---

### Inputs

- **Verse ID** — block ID of the verse, no caret (e.g. `1-1`, `6-33`). Per-chapter numbering.
- **Sanskrit root** — `$SOURCE_TEXTS/BCAV08_SH_sk.md#^<verse-id>`.
- **Tibetan root** — `$SOURCE_TEXTS/<bo-root-text>.md#^<verse-id>` (transclude; if the Tibetan root-text file does not yet carry this block, the Tibetan verse must be added to a root-text file under `$SOURCE_TEXTS/` first — do not paste the verse into the rail).
- **Commentary files** — every relevant file under `$COMMENTARIES/Transcluded/`. For this verse, prefer:
  - a **word-commentary / annotation** (*mchan-'grel*) source for the Chendrel and disambiguation (e.g. `BCAC19_KS_bo`);
  - **story commentaries** (*gtam-rgyud* / *sgrung-'grel*) for the Stories (e.g. `BCACXX_WR_bo`, `BCAC13_KTB_bo`);
  - scholarly commentaries for the paraphrase and concepts.
  Use the `registered_id` from the vault annex to attribute every claim.

### Output

One file at `$VERSES/<verse-id>.md`. Update in place if it exists; never overwrite a hand-edited Tibetan section without confirming the edit is still supported by the cited blocks.

---

### Output file format

```markdown
---
ref: <e.g. 1-1-ref>
unit_type: single | group | template | instance
unit_verses: [<verse-id>]
commentary_coverage: [<id>, <id>, …]
tradition_coverage: [<tradition>, …]
concepts_in_verse: [<བོད་སྐད་ term> (gloss), …]
concepts_in_commentary: [<བོད་སྐད་ term> (gloss), …]
stories: [<story name>, …]
layer_order: [traditional, ai-overview, chendrel, word-disambiguation, concepts, stories, metaphors, quotations]
status: draft
---

### Source Text

#### Sanskrit
![[$SOURCE_TEXTS/BCAV08_SH_sk.md#^<verse-id>]]

#### Tibetan
![[$SOURCE_TEXTS/<bo-root-text>.md#^<verse-id>]]

**Variants**
[Ed: …]

### Traditional Interpretation

#### <id> — <Commentary full name> (<language>)
<English paraphrase; every claim cited.>
($COMMENTARIES/<id>.md#^<block>)

#### Divergences
<only where commentaries genuinely disagree; each position attributed, ⚑.>

### AI Overview (བསྡུས་དོན།)

**ངོ་སྤྲོད་མདོར་བསྡུས།** <one–two Tibetan sentences: what the verse says.>
($COMMENTARIES/<id>.md#^<block>)

**གནད་དོན་གཙོ་བོ།**
- <key point, Tibetan> ($COMMENTARIES/<id>.md#^<block>)
- <key point, Tibetan> ($COMMENTARIES/<id>.md#^<block>)

### Chendrel — ཚིག་འགྲེལ

<running Tibetan word-commentary: each phrase of the root verse with its gloss
woven inline, mchan-'grel style.>
($COMMENTARIES/<mchan-grel-id>.md#^<block>)

### Word-by-word Disambiguation (ཚིག་དོན་གསལ་བཤད།)

- **<root word/phrase>** — <Tibetan disambiguating gloss.>
  ($COMMENTARIES/<id>.md#^<block>)

### Key Concepts (ཆོས་ཀྱི་གནད་ཚིག)

#### ཚིགས་བཅད་ནང་གི་གནད་ཚིག
- **<term>** (<gloss>) — <Tibetan note.>
  ($COMMENTARIES/<id>.md#^<block>) · [[$LOCAL_WIKI/<term>_(<disambiguator>).md]]

#### འགྲེལ་པ་ནས་འབྱུང་བའི་གནད་ཚིག
- **<term>** (<gloss>) — <Tibetan note.>
  ($COMMENTARIES/<id>.md#^<block>) · [[$LOCAL_WIKI/<term>_(<disambiguator>).md]]

### Stories (སྒྲུང་།)

- **<story name>** — <Tibetan précis; which phrase it illustrates.>
  ($COMMENTARIES/<story-id>.md#^<block>)

### Metaphors (དཔེ།)

- **<image>** → <tenor.> <how the commentary develops it.>
  ($COMMENTARIES/<id>.md#^<block>)

### Quotations (ལུང་།)

> <verbatim Tibetan scripture>
> — <scripture as named by the commentary>
> ($COMMENTARIES/<id>.md#^<block>)

### Disambiguated Restatement (Tibetan)

<short Tibetan rewrite of the verse with every ambiguity the synthesis
resolved made explicit. Cite the blocks that authorise each choice.>
($COMMENTARIES/<id>.md#^<block>)

### Concept Links
- [[$LOCAL_WIKI/<term>_(<disambiguator>).md]]
```

---

### Rules

1. **Required sections always present:** Source Text, Traditional Interpretation, AI Overview, Disambiguated Restatement. The rest are populated where the commentaries supply material and **omitted otherwise** (a verse with no attached story drops the Stories section — do not write an empty heading).
2. **Both languages in Source Text.** Transclude the Sanskrit and the Tibetan root blocks; never copy them. If a block ID is missing in a root-text file, fix the root text first.
3. **Traditional Interpretation is the cited anchor.** The AI Overview is its Tibetan compression — every claim in the Overview must trace to a paraphrase that is itself cited. Do not introduce a claim in the Overview that is not in Traditional Interpretation.
4. **Chendrel uses a word-commentary source.** It is not your own gloss — it re-presents an attested *mchan-'grel* / annotation reading as running word-commentary, cited to its blocks.
5. **Word-by-word disambiguation only for non-obvious choices** — sense selection, compound parsing, referent. Skip obvious tokens.
6. **Stories are précis, not invention.** Only narratives a commentary actually attaches to the verse; name the story and cite the block.
7. **Quotations are verbatim and attributed.** Reproduce the Tibetan as the commentary gives it; name the scripture the commentary names; cite the commentary block that adduces it.
8. **Every claim cites a `$SOURCES/` block.** No parametric knowledge. Uncited field → leave blank, `status: draft`.
9. **Divergences are never flattened.** ⚑ each position; the Disambiguated Restatement follows the best-attested reading and footnotes the alternatives.
10. **`status: draft` always.** The LLM never sets `complete`; a domain specialist does.

---

### Procedure

1. Read the Sanskrit and Tibetan root blocks. Confirm both block IDs exist; if the Tibetan root file lacks the block, stop and fix the root text.
2. **Locate verse commentary in each Transcluded file** — do not read the whole file. Root text verses are transcluded into the commentary files with the Obsidian syntax `![[...#^<verse-id>]]`. Search each file in `$COMMENTARIES/Transcluded/` for the transclusion of the target verse's block ID. All text from that transclusion up to (but not including) the next transclusion is commentary on that verse. Read only that span and record the block IDs and `registered_id`.
3. Write **Traditional Interpretation** — one English subsection per commentary, each claim cited. Add **Divergences** if any.
4. Write the **AI Overview** in Tibetan from the paraphrases (see prompt below).
5. Build the **Chendrel** from the annotation source; **Word-by-word Disambiguation** for non-obvious tokens.
6. Fill **Key Concepts** (in-verse / from-commentary), **Stories**, **Metaphors**, **Quotations** — each from a cited block; omit any section with no material.
7. Write the **Disambiguated Restatement** in Tibetan.
8. Fill frontmatter; set `status: draft`. Add **Concept Links**.
9. Write to `$VERSES/<verse-id>.md`.

---

### AI Overview — generation prompt

The AI Overview reproduces the experience of a Google "AI Overview" answer box, in Tibetan, over the commentary corpus. Generate it with this prompt:

> You are compiling the **AI Overview** block for one verse package. Your only
> sources are the per-commentary paraphrases already written in this file's
> **Traditional Interpretation** section, each of which is cited to a
> `$SOURCES/` block. Do not use any knowledge outside those paraphrases.
>
> Write in **Tibetan**. Produce, in this order:
>
> 1. **ངོ་སྤྲོད་མདོར་བསྡུས། (the direct answer)** — one or two sentences that
>    answer "what does this verse say?" as the commentaries collectively read
>    it. Lead with the conclusion, the way an AI Overview opens with the
>    answer before the detail. Neutral, synthetic voice — not "commentary X
>    says," but the settled reading. End the sentence(s) with the source
>    citation(s) they rest on.
>
> 2. **གནད་དོན་གཙོ་བོ། (key points)** — three to six short bullets, each a
>    single scannable idea (a referent fixed, a term's sense chosen, the
>    verse's function in the chapter, a concept introduced). Each bullet ends
>    with the `($COMMENTARIES/<id>.md#^<block>)` source(s) it draws
>    on — the inline-citation feel of an AI Overview's linked snippets. Where
>    a point aggregates several commentaries, cite all of them.
>
> Constraints matching the AI-Overview style:
> - **Synthesise, attribute by citation.** The prose reads as one voice;
>   attribution lives in the trailing source links, not in the sentence.
> - **Lead with the answer, keep it skimmable.** Short sentences, short
>   bullets, no throat-clearing.
> - **Surface disagreement, don't hide it.** If the commentaries split on a
>   point, say so in that bullet and mark it ⚑, citing each side — an AI
>   Overview flags "it depends," it does not fabricate consensus.
> - **Every claim is grounded.** If a statement cannot be traced to a cited
>   paraphrase above, cut it.

---

### Completion check

- [ ] Frontmatter complete; `status: draft`.
- [ ] Source Text transcludes both Sanskrit and Tibetan (not copied).
- [ ] Traditional Interpretation: one English subsection per commentary, every sentence cited; Divergences ⚑ where they exist.
- [ ] AI Overview in Tibetan: direct answer + key points, every line cited, ⚑ on splits, nothing beyond the paraphrases above.
- [ ] Chendrel drawn from a cited word-commentary source (or section omitted).
- [ ] Word-by-word disambiguation only for non-obvious tokens, each cited.
- [ ] Key Concepts: in-verse and from-commentary, cited and Local-Wiki-linked.
- [ ] Stories / Metaphors / Quotations populated from cited blocks, omitted where absent; quotations verbatim Tibetan.
- [ ] Disambiguated Restatement in Tibetan, each choice cited.
- [ ] Concept Links present for every key term.

---

## Mode 2 — Chapter batch

Scans every commentary once to produce a complete block-ID mapping, then generates one file per verse in the chapter.

This skill produces a complete set of verse-level context packages for an entire chapter, using a Python script to generate all files in one pass after the source-scanning phase is complete. It exists because building 30+ verse packages one at a time with `verse-context` is slow and prone to mapping inconsistencies between files — this skill enforces a single mapping table that every package in the chapter is generated from.

The output of this skill is identical in format to what `verse-context` produces for individual verses: each file has a verse transclusion, commentary passage transclusions, Tibetan synthesis prose per commentary, a Consensus section, and a disambiguated verse with block citations. Status is always `draft` on generation; a domain specialist marks files `complete` after review.

---

### Inputs

- **Chapter number** — e.g. `1` for Chapter 1.
- **Verse range** — first and last verse number in the chapter (e.g. `1-4` through `1-36`; verses that already have manually authored files may be skipped).
- **Commentary files** — all relevant `$COMMENTARIES/*.md` files for this vault:
  - `bo-མཁན་པོ་ཀུན་དཔལ།.md` (Kunpal)
  - `bo-དངུལ་ཆུ་ཐོགས་མེད།.md` (Ngülchu Thogmé)
  - `bo-ས་བཟང་མ་ཏི་པཎ་ཆེན་བློ་གྲོས་རྒྱལ་མཚན།.md` (Sabzang Mati)
  - `bo-ཤེས་རབ་འབྱུང་གནས་བློ་གྲོས། Prajñākaramati.md` (Prajñākaramati)
- **Translation file** — `$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md` (for verse transclusions).
- **All commentary files must already have block IDs.** Run `format-commentary` on any commentary that lacks them before proceeding.

---

### Output

One file per verse at:

```
$VERSES/<chapter>-<verse>.md
```

e.g. `$VERSES/1-4.md` through `$VERSES/1-36.md`.

Files that already exist are skipped (not overwritten).

A Python generation script is saved to `$WORK/verse-context-batch-ch<N>.py` for audit and re-use.

---

### Output file format

Each generated file matches the `verse-context` schema exactly:

```markdown
---
verse_id: <chapter>-<verse>
root_text: $TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md
root_block: ^<chapter>-<verse>
language: bo
commentaries: [kunpal, ngulchu-thogmed, sabzang, prajnakaramati]
status: draft
---

### Verse

![[$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md#^<chapter>-<verse>]]

### Commentary passages

#### kunpal

![[$COMMENTARIES/bo-མཁན་པོ་ཀུན་དཔལ།.md#^<block-id>]]
...

#### ngulchu-thogmed

![[$COMMENTARIES/bo-དངུལ་ཆུ་ཐོགས་མེད།.md#^<block-id>]]
...

#### sabzang

![[$COMMENTARIES/bo-ས་བཟང་མ་ཏི་པཎ་ཆེན་བློ་གྲོས་རྒྱལ་མཚན།.md#^<block-id>]]
...

#### prajnakaramati

![[$COMMENTARIES/bo-ཤེས་རབ་འབྱུང་གནས་བློ་གྲོས། Prajñākaramati.md#^<chapter>-<verse>-1]]

### Synthesis (original language)

#### kunpal

<Tibetan prose summarising Kunpal's reading, with inline block citations>

#### ngulchu-thogmed

<Tibetan prose summarising Ngülchu's reading, with inline block citations>

#### sabzang

<Tibetan prose summarising Sabzang's reading, with inline block citations>

#### prajnakaramati

<Tibetan prose summarising Prajñākaramati's reading, with inline block citation>

#### Consensus

<Tibetan prose stating what all commentaries agree on>

### Disambiguated verse (original language)

![[$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md#^<chapter>-<verse>]]

($COMMENTARIES/bo-མཁན་པོ་ཀུན་དཔལ།.md#^<block-id>)
($COMMENTARIES/bo-དངུལ་ཆུ་ཐོགས་མེད།.md#^<block-id>)
($COMMENTARIES/bo-ས་བཟང་མ་ཏི་པཎ་ཆེན་བློ་གྲོས་རྒྱལ་མཚན།.md#^<block-id>)
($COMMENTARIES/bo-ཤེས་རབ་འབྱུང་གནས་བློ་གྲོས། Prajñākaramati.md#^<chapter>-<verse>-1)
```

---

### Rules

1. **Read before mapping.** Never guess block ranges. Read each commentary section in full before assigning block IDs to verses. Commentary structure frequently does not align one-to-one with root-text verses.
2. **Ngülchu's section numbers are his own, not root-text verse numbers.** `### 1.7` in Ngülchu means his structural section 7 of Chapter 1 — it covers multiple root-text verses. Map his sections to root-text verses by reading the content.
3. **Sabzang's Chapter 1 body has two large prose sections.** Section 1.1 (blocks `^1-1-1` to `^1-1-46`) covers root-text verses 1-4 through 1-17; Section 1.2 (blocks `^1-2-1` to `^1-2-38`) covers verses 1-18 through 1-36. Blocks may straddle verse boundaries — include the block in both verse packages where this occurs.
4. **Kunpal's blocks are sequential.** His Chapter 1 body runs from approximately `^0-127` onward. Map ranges by scanning for verse-heading markers.
5. **Prajñākaramati has one block per root-text verse.** Block ID format is `^<chapter>-<verse>-1` (e.g. `^1-4-1`, `^1-36-1`). Verify all blocks exist before generating.
6. **Do not overwrite existing files.** If `$VERSES/<verse-id>.md` already exists, skip it silently.
7. **Status is always `draft` on generation.** Never set `status: complete` — that is a human domain-specialist decision.
8. **Synthesis prose must be in Tibetan only.** No English in any synthesis subsection.
9. **Every synthesis claim must cite a source block.** Format: `($COMMENTARIES/<file>.md#^<block-id>)` inline at the end of the claim.
10. **Save the generation script to `$WORK/`.** This preserves the mapping table for audit and re-runs.

---

### Procedure

#### Phase 1 — Verify prerequisites

1. Confirm all four commentary files have block IDs throughout. If any lacks block IDs, run `format-commentary` on it first and do not proceed until that is complete.
2. Confirm `$TRANSLATIONS/bo-བློ་ལྡན་ཤེས་རབ།.md` has block IDs for every verse in the target chapter (format `^<chapter>-<verse>`).
3. Note which verse files in `$VERSES/` already exist and will be skipped.

#### Phase 2 — Build the block mapping table

For each commentary, read the relevant chapter section(s) and record the block ID range that covers each root-text verse. Produce a mapping table of this shape:

| Verse | Kunpal blocks | Ngülchu blocks | Sabzang blocks | Prajñākaramati |
|-------|--------------|----------------|----------------|----------------|
| 1-4   | ^0-176 to ^0-187 | ^1-3-1 to ^1-3-16 | ^1-1-1 to ^1-1-3 | ^1-4-1 |
| ...   | ...          | ...            | ...            | ...    |

**Kunpal:** Scan Chapter 1 body sequentially. Identify verse heading markers (e.g. `ཚིགས་སུ་བཅད་པ་བཞི་པ།`) to delimit block ranges per verse.

**Ngülchu:** Read each structural section heading (`### 1.X`). Read the section body to determine which root-text verses it covers. Note that multiple verses may fall within one section, and multiple sections may be needed for one verse.

**Sabzang:** Read Section 1.1 (blocks `^1-1-1` to `^1-1-46`) and Section 1.2 (blocks `^1-2-1` to `^1-2-38`) in full. Map each block to the root-text verse whose content it discusses. Where a block straddles two verses, include it in both.

**Prajñākaramati:** Grep for `^<chapter>-<verse>-1` blocks across the chapter range to confirm all exist.

#### Phase 3 — Draft synthesis descriptions

For each verse, note (in one sentence per commentary) the structural context and main interpretive point. These become the synthesis prose in the generated files. Cite the first key block per commentary.

#### Phase 4 — Write the generation script

Write a Python script to `$WORK/verse-context-batch-ch<N>.py` that:

1. Defines the block mapping table as a Python dict keyed by verse number.
2. For each verse in the range:
   a. Skips if the output file already exists.
   b. Generates the markdown content using the mapping and synthesis descriptions.
   c. Writes to `$VERSES/<chapter>-<verse>.md`.
3. Prints a summary of files created vs. skipped.

The script must be self-contained (no external dependencies beyond the Python standard library) and use absolute paths.

#### Phase 5 — Run the script

Execute the script via bash. Verify the printed summary matches the expected count of new files.

#### Phase 6 — Spot-check output

Read three generated files — one from the beginning, middle, and end of the chapter — and verify:
- Frontmatter fields are correct.
- All four commentary sections are present and non-empty.
- Block IDs in transclusion links match the mapping table.
- Synthesis prose is in Tibetan and has at least one inline citation.
- Disambiguated verse section has citations from all four commentaries.

#### Phase 7 — Save and report

Confirm the generation script is saved to `$WORK/`. Report: total files generated, any files skipped (already existed), and any anomalies found in spot-check.

---

### Commentary block-ID reference (Chapter 1, BCA vault)

This section records the mapping used for Chapter 1 of the Bodhisattvacaryāvatāra so subsequent runs can verify or extend it without re-reading all sources.

#### Kunpal (`bo-མཁན་པོ་ཀུན་དཔལ།.md`)

Chapter 0 (introduction) runs through approximately `^0-175`. Chapter 1 body begins at `^0-127` (verse 1-1 material) and the verse-specific ranges are:

| Verse | Block range |
|-------|------------|
| 1-1 | ^0-127 to ^0-175 |
| 1-2 | ^0-156 to ^0-163 |
| 1-3 | ^0-164 to ^0-168 |
| 1-4 | ^0-176 to ^0-187 |
| 1-5 | ^0-188 to ^0-199 |
| 1-6 | ^0-200 |
| 1-7 | ^0-201 to ^0-203 |
| 1-8 | ^0-204 to ^0-205 |
| 1-9 | ^0-206 to ^0-211 |
| 1-10 | ^0-212 |
| 1-11 | ^0-213 to ^0-214 |
| 1-12 | ^0-215 to ^0-217 |
| 1-13 | ^0-218 to ^0-220 |
| 1-14 | ^0-221 |
| 1-15 | ^0-222 to ^0-239 |
| 1-16 | ^0-240 to ^0-243 |
| 1-17 | ^0-244 |
| 1-18 | ^0-245 to ^0-256 |
| 1-19 | ^0-257 to ^0-258 |
| 1-20 | ^0-259 to ^0-265 |
| 1-21 | ^0-266 to ^0-268 |
| 1-22 | ^0-269 to ^0-270 |
| 1-23 | ^0-271 |
| 1-24 | ^0-272 |
| 1-25 | ^0-273 to ^0-276 |
| 1-26 | ^0-277 to ^0-279 |
| 1-27 | ^0-280 to ^0-281 |
| 1-28 | ^0-282 to ^0-285 |
| 1-29 | ^0-286 to ^0-288 |
| 1-30 | ^0-289 to ^0-291 |
| 1-31 | ^0-292 to ^0-293 |
| 1-32 | ^0-294 to ^0-296 |
| 1-33 | ^0-297 to ^0-299 |
| 1-34 | ^0-300 to ^0-306 |
| 1-35 | ^0-307 to ^0-313 |
| 1-36 | ^0-314 to ^0-315 |

#### Ngülchu (`bo-དངུལ་ཆུ་ཐོགས་མེད།.md`)

Ngülchu's Chapter 1 is divided into structural sections 1.3 through 1.11. His section numbers are his own — not root-text verse numbers.

| Verse | Ngülchu blocks | Ngülchu section |
|-------|---------------|-----------------|
| 1-1 | ^0-3-12 to ^1-1-7 | 0.3, 1.1 |
| 1-2 | ^1-2-1 | 1.2 |
| 1-3 | ^1-3-1 to ^1-3-16 | 1.3 (partial) |
| 1-4 | ^1-3-1 to ^1-3-16 | 1.3 |
| 1-5 | ^1-4-1, ^1-5-1, ^1-6-1 | 1.4, 1.5, 1.6 |
| 1-6 | ^1-7-1 to ^1-7-4 | 1.7 part 1 |
| 1-7 | ^1-7-5 to ^1-7-6 | 1.7 part 2 |
| 1-8 | ^1-7-6 to ^1-7-7 | 1.7 part 3 |
| 1-9 | ^1-7-7 to ^1-7-8 | 1.7 part 4 |
| 1-10 | ^1-7-8 to ^1-7-12 | 1.7 part 5, example 1 (gold) |
| 1-11 | ^1-7-13 to ^1-7-15 | 1.7 part 5, example 2 (jewel) |
| 1-12 | ^1-7-16 to ^1-7-21 | 1.7 part 5, example 3 (tree) |
| 1-13 | ^1-7-22 to ^1-7-26 | 1.7 part 5, example 4 (escort) |
| 1-14 | ^1-7-27 to ^1-7-52 | 1.7 part 5, examples 5–6 (fire + Gaṇḍavyūha) |
| 1-15 | ^1-8-1 to ^1-8-16 | 1.8 |
| 1-16 | ^1-8-1 to ^1-8-16 | 1.8 |
| 1-17 | ^1-8-1 to ^1-8-16 | 1.8 |
| 1-18 | ^1-9-1, ^1-10-1 to ^1-10-17 | 1.9, 1.10 |
| 1-19 | ^1-9-1, ^1-10-1 to ^1-10-17 | 1.9, 1.10 |
| 1-20 | ^1-9-1, ^1-10-1 to ^1-10-17 | 1.9, 1.10 |
| 1-21 | ^1-9-1, ^1-10-1 to ^1-10-17 | 1.9, 1.10 |
| 1-22 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-23 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-24 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-25 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-26 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-27 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-28 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-29 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-30 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-31 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-32 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-33 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-34 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-35 | ^1-11-1 to ^1-11-30 | 1.11 |
| 1-36 | ^1-11-1 to ^1-11-30 | 1.11 |

#### Sabzang (`bo-ས་བཟང་མ་ཏི་པཎ་ཆེན་བློ་གྲོས་རྒྱལ་མཚན།.md`)

Chapter 1 body has two large prose sections. Introduction runs through `^0-2-11`.

| Verse | Sabzang blocks |
|-------|---------------|
| 1-1 | ^0-2-11 |
| 1-2 | ^0-1-28 to ^0-1-30 |
| 1-3 | ^0-1-31, ^0-1-32 |
| 1-4 | ^1-1-1 to ^1-1-3 |
| 1-5 | ^1-1-4, ^1-1-5 |
| 1-6 | ^1-1-6 |
| 1-7 | ^1-1-6 |
| 1-8 | ^1-1-6 |
| 1-9 | ^1-1-7 |
| 1-10 | ^1-1-8 to ^1-1-13 |
| 1-11 | ^1-1-14, ^1-1-15 |
| 1-12 | ^1-1-16 to ^1-1-19 |
| 1-13 | ^1-1-19 to ^1-1-23 |
| 1-14 | ^1-1-24 to ^1-1-36 |
| 1-15 | ^1-1-37 |
| 1-16 | ^1-1-37 to ^1-1-41 |
| 1-17 | ^1-1-41 to ^1-1-46 |
| 1-18 | ^1-2-1, ^1-2-2 |
| 1-19 | ^1-2-3 to ^1-2-6 |
| 1-20 | ^1-2-7 to ^1-2-14 |
| 1-21 | ^1-2-15 to ^1-2-18 |
| 1-22 | ^1-2-19, ^1-2-20 |
| 1-23 | ^1-2-21, ^1-2-22 |
| 1-24 | ^1-2-23 to ^1-2-27 |
| 1-25 | ^1-2-28, ^1-2-29 |
| 1-26 | ^1-2-30 to ^1-2-32 |
| 1-27 | ^1-2-33 to ^1-2-35 |
| 1-28 | ^1-2-36 |
| 1-29 | ^1-2-37 |
| 1-30 | ^1-2-38 |
| 1-31 | ^1-2-38 |
| 1-32 | ^1-2-38 |
| 1-33 | ^1-2-38 |
| 1-34 | ^1-2-38 |
| 1-35 | ^1-2-38 |
| 1-36 | ^1-2-38 |

#### Prajñākaramati (`bo-ཤེས་རབ་འབྱུང་གནས་བློ་གྲོས། Prajñākaramati.md`)

One block per verse throughout. Block format: `^<chapter>-<verse>-1`.
Verified present for all Chapter 1 verses (1-1 through 1-36).

---

### Completion check

- [ ] All four commentary files confirmed to have block IDs before mapping begins
- [ ] Block mapping table built by reading source files (not guessed)
- [ ] Ngülchu section numbers confirmed not conflated with root-text verse numbers
- [ ] Generation script saved to `$WORK/verse-context-batch-ch<N>.py`
- [ ] Script run successfully; printed summary matches expected file count
- [ ] Three spot-checked files pass format verification
- [ ] No existing `$VERSES/` files were overwritten
- [ ] All generated files have `status: draft`
- [ ] Synthesis prose is Tibetan only, with at least one inline block citation per commentary subsection

---

## Mode 3 — Verse group under one outline node

For root texts with a nested sa-bcad outline: one contextual summary paragraph per verse group, tracing the commentary's own division.

### What This Skill Produces

For every group of root-text verses that appears under a section heading in a sa-bcad+root-text (ས་བཅད་རྩ་སྦྱར།) file, produce a contextual summary paragraph in Tibetan that:

1. Quotes the verses exactly as they appear in the source file.
2. Appends a Tibetan prose paragraph that traces the full nested outline path — from the outermost relevant container all the way down to the specific leaf section — and closes with `གཞུང་ཚིག་ཡིན་ནོ།།`.

Save the output as a Markdown file in the `$VERSES/` folder of the workspace, named `bo-[chapter]-ས་བཅད་གཞིར་བཟུང་རྩ་ཚིག་ངོས་འཛིན།.md`.

---

### Step 1 — Read and Parse the Source File

The source file is large; read it in chunks using `offset` and `limit`. Because the file interleaves outline headings with verse blocks, pay attention to:

- **Outline headings**: Lines starting with `-` and containing a `^TOC-…` anchor. The indentation level (number of tabs) encodes nesting depth.
- **Verse blocks**: Lines indented under an outline heading that contain Tibetan syllables but **no** `^TOC-…` anchor. Verse lines usually start with a tab and end with `། །` or `།`.
- **Chapter colophon** (`མཚན།` heading): Marks the end of a chapter's verse content.

Group the verses: every consecutive set of verse lines that falls under the same leaf-level outline heading is one verse group. Note the full ancestor chain of that heading — that chain is the outline path you will trace in the summary.

---

### Step 2 — Build the Outline Path in Tibetan

The summary paragraph must state the position of the verse group in the outline. Reconstruct this path in natural Tibetan prose by working **outward to inward**: start from the outermost relevant container (usually the chapter group), state how many sub-sections it contains, name them, pick the one that leads to the target, and repeat at each level until you reach the leaf section.

#### Core Sentence Frame

```
ཞེས་པའི་[VERSE-COUNT-PHRASE]་འདི་[ནི/དག་ནི]་[PATH-CHAIN]་གཞུང་ཚིག་ཡིན་ནོ།།
```

- Use `འདི་ནི་` for a single-verse group.
- Use `འདི་དག་ནི་` for a multi-verse group.

#### Path Chain Construction

Each level of the chain follows one of two patterns:

**A. Branching level** — when the parent contains multiple named sub-sections and you must say "from the N sub-sections, the Kth one is…":

```
[PARENT-NAME]-ལ་ [CHILD-1] དང་ [CHILD-2] གཉིས་ལས། [ORDINAL]-པ་ [CHILD-K]-…
```

When there are three named children:
```
[PARENT-NAME]-ལ་ [CHILD-1]། [CHILD-2]། [CHILD-3]-བཅས་གསུམ་ལས། [ORDINAL]-པ་ [CHILD-K]-…
```

When there are more children, list them with `།` separators and close with `-བཅས་[N]-ལས།`.

**B. Direct level** — when a container has exactly one named part that is the target:
```
[CONTAINER-NAME]-ཡི་ [PART-NAME]-བཤད་པ་ལ་…
```

**Ordinals in Tibetan:**

| Position | Tibetan |
|----------|---------|
| 1st | དང་པོ་ |
| 2nd | གཉིས་པ་ |
| 3rd | གསུམ་པ་ |
| 4th | བཞི་པ་ |
| 5th | ལྔ་པ་ |
| 6th | དྲུག་པ་ |
| 7th | བདུན་པ་ |

**Count words for sub-sections:**

| Count | Tibetan |
|-------|---------|
| 2 | གཉིས་ལས། |
| 3 | གསུམ་ལས། |
| 4 | བཞི་ལས། |
| 5 | ལྔ་ལས། |
| 6 | དྲུག་ལས། |

#### Closing the Path

The final clause names the leaf section and ends:

- `[LEAF-SECTION]-སྟོན་པའི་གཞུང་ཚིག་ཡིན་ནོ།།`  — when the section "shows/demonstrates" something.
- `[LEAF-SECTION]-བཤད་པའི་གཞུང་ཚིག་ཡིན་ནོ།།`  — when the section "explains" something.
- `[LEAF-SECTION]-བསྒྲུབ་པའི་གཞུང་ཚིག་ཡིན་ནོ།།`  — when the section "establishes" something through scripture or reasoning.
- `[LEAF-SECTION]-བསྟན་པའི་གཞུང་ཚིག་ཡིན་ནོ།།`  — when the section "teaches/presents" through an example.
- For a cross-reference section (ཞལ་འཕང་བ།): `འདིར་མ་བཤད་པ་གཞུང་གཞན་དུ་ཞལ་འཕང་བའི་གཞུང་ཚིག་ཡིན་ནོ།།`

Choose the closing verb that matches the sa-bcad label of the leaf section.

---

### Step 3 — Count the Verses Correctly

| Lines in group | Phrase to use |
|---------------|---------------|
| 2 (half-verse) | `ཚིགས་སུ་བཅད་པ་འདི་ནི་` |
| 4 (1 full verse / shloka) | `ཤློཀ་གཅིག་པོ་འདི་ནི་` |
| 8 (2 shlokas) | `ཤློཀ་གཉིས་པོ་འདི་དག་ནི་` |
| 12 (3 shlokas) | `ཤློཀ་གསུམ་པོ་འདི་དག་ནི་` |
| 16 (4 shlokas) | `ཤློཀ་བཞི་པོ་འདི་དག་ནི་` |
| 20 (5 shlokas) | `ཤློཀ་ལྔ་པོ་འདི་དག་ནི་` |
| 28 (7 shlokas) | `ཤློཀ་བདུན་པོ་འདི་དག་ནི་` |

For edge cases (e.g., a verse that runs 6 lines because it contains one 4-line shloka plus a 2-line fragment), treat the 4-line block as one shloka and the 2-line block as a separate group if they appear under different headings. If they appear under the same heading, count the combined line count and use the nearest shloka count plus note the fragment.

---

### Step 4 — Assemble the Output

Produce a Markdown file using this repeating unit for each verse group:

```markdown
### [SECTION-NUMBER-IN-TIBETAN]། [LEAF-SECTION-HEADING]

[VERSE LINE 1]
[VERSE LINE 2]
[VERSE LINE 3]
[VERSE LINE 4]

[…additional verse stanzas if present…]

ཞེས་པའི་[VERSE-COUNT-PHRASE]་འདི་[ནི/དག་ནི]་[FULL PATH CHAIN]་གཞུང་ཚིག་ཡིན་ནོ།།

---
```

Number the sections consecutively in Tibetan numerals (༡། ༢། ༣། …).

Title the file:
```
bo-[chapter-name-in-Tibetan]-ས་བཅད་གཞིར་བཟུང་རྩ་ཚིག་ངོས་འཛིན་བསྡུས་དོན།.md
```

Add a closing colophon at the very end:
```
*[Text name]་ལས། [Chapter title]་ཞེས་བྱ་བ་སྟེ་ལེའུ་[ordinal]འི་རྩ་ཚིག་ས་བཅད་གཞིར་བཟུང་ངོས་འཛིན་བསྡུས་དོན་རྫོགས་སོ།། །།*
```

---

### Reference: Worked Example (Chapter 1)

The session that produced the Chapter 1 output demonstrates every grammar pattern this skill requires. Study these examples carefully:

#### Single verse (4 lines) — ལུས་རྟེན་བཤད་པ།

> ཞེས་པའི་ཤློཀ་གཅིག་པོ་འདི་ནི་བྱང་ཆུབ་ཀྱི་སེམས་རིན་པོ་ཆེ་མ་སྐྱེས་པ་བསྐྱེད་པར་བྱེད་པའི་ལེའུ་གསུམ་ལས། དང་པོ་བྲོད་པ་བསྐྱེད་པ་ཕན་ཡོན་གྱི་ལེའུ་ཡི་གཞུང་བཤད་པ་ལ་བྱང་ཆུབ་སེམས་ཀྱི་རྟེན་བཤད་པ་དང་བརྟེན་པ་སེམས་བསྐྱེད་ཀྱི་ཕན་ཡོན་བཤད་པ་བཅས་ས་བཅད་གཉིས་ལས། དང་པོ་བྱང་ཆུབ་སེམས་ཀྱི་རྟེན་བཤད་པ་ལ་ལུས་རྟེན་བཤད་པ་དང་སེམས་རྟེན་བཤད་པ་གཉིས་ལས། དང་པོ་ལུས་རྟེན་བཤད་པའི་གཞུང་ཚིག་ཡིན་ནོ།།

**Path decoded:**
- Outermost container → ལེའུ་གསུམ་ (3 chapters) → དང་པོ་ (1st chapter)
- Within 1st chapter's text → 2 outline sections (རྟེན། and ཕན་ཡོན།) → དང་པོ་ (1st: རྟེན།)
- Within རྟེན། → 2 parts (ལུས་རྟེན། and སེམས་རྟེན།) → དང་པོ་ (1st: ལུས་རྟེན།)
- Closes: ལུས་རྟེན་བཤད་པའི་གཞུང་ཚིག་ཡིན་ནོ།།

#### Three verses (12 lines) — དགེ་བ་གཞན་ལས་ཁྱད་འཕགས་ཕན་ཡོན། (the example given by user)

> ཞེས་པའི་ཤློཀ་གསུམ་པོ་འདི་དག་ནི་བྱང་ཆུབ་ཀྱི་སེམས་རིན་པོ་ཆེ་མ་སྐྱེས་པ་བསྐྱེད་པར་བྱེད་པའི་ལེའུ་གསུམ་ལས། དང་པོ་བྲོད་པ་བསྐྱེད་པ་ཕན་ཡོན་གྱི་ལེའུ་ཡི་གཞུང་བཤད་པ་ལ་བྱང་ཆུབ་སེམས་ཀྱི་རྟེན་དང་བརྟེན་པ་སེམས་བསྐྱེད་ཀྱི་ཕན་ཡོན་བཤད་པ་བཅས་ས་བཅད་གཉིས་ལས། གཉིས་པ་བརྟེན་པ་སེམས་བསྐྱེད་ཀྱི་ཕན་ཡོན་བཤད་པ་ལ་སེམས་བསྐྱེད་སྤྱིའི་ཕན་ཡོན་བཤད་པ་དང་སྨོན་འཇུག་སོ་སོའི་ཕན་ཡོན་བཤད་པ་གཉིས་ལས། དང་པོ་སེམས་བསྐྱེད་སྤྱིའི་ཕན་ཡོན་བཤད་པ་ལ་དགེ་བ་གཞན་ལས་ཁྱད་པར་དུ་འཕགས་པའི་ཕན་ཡོན། མིང་དོན་གནས་འགྱུར་བའི་ཕན་ཡོན། ཕན་ཡོན་དཔེའི་སྒོ་ནས་བསྟན་པ་བཅས་གསུམ་ལས། དང་པོ་དགེ་བ་གཞན་ལས་ཁྱད་པར་དུ་འཕགས་པའི་ཕན་ཡོན་སྟོན་པའི་གཞུང་ཚིག་ཡིན་ནོ།།

**Path decoded:**
- 3 chapters → 1st chapter's text → 2 sections → 2nd (benefits) → 2 sub-sections (སྤྱི། and སོ་སོ།) → 1st (སྤྱི།) → 3 sub-sub-sections → 1st (དགེ་འཕགས།)
- Closes: དགེ་བ་གཞན་ལས་ཁྱད་པར་དུ་འཕགས་པའི་ཕན་ཡོན་སྟོན་པའི་གཞུང་ཚིག་ཡིན་ནོ།།

#### Six example sub-sections — list all six when descending into them

When the parent has 6 named children (as in ཕན་ཡོན་དཔེའི་སྒོ་ནས་བསྟན་པ།), name all six each time, then pick the target ordinal:

> …གསུམ་པ་ཕན་ཡོན་དཔེའི་སྒོ་ནས་བསྟན་པ་ལ་གསེར་འགྱུར་གྱི་དཔེས་སངས་རྒྱས་ཐོབ་པར་བསྟན་པ། རིན་པོ་ཆེའི་དཔེས་དོན་ཆེ་བར་བསྟན་པ། འབྲས་བུ་ཅན་གྱི་ལྗོན་ཤིང་གི་དཔེས་དགེ་རྩ་མི་ཟད་ཅིང་གོང་དུ་འཕེལ་བར་བསྟན་པ། སྐྱེལ་མ་དཔའ་བོའི་དཔེས་ངེས་པའི་སྡིག་པ་ཟིལ་གྱིས་གནོན་པར་བསྟན་པ། དུས་མཐའི་མེའི་དཔེས་མ་ངེས་པའི་སྡིག་པ་དྲུང་ནས་འབྱིན་པར་བསྟན་པ། འདིར་མ་བཤད་པ་གཞུང་གཞན་དུ་ཞལ་འཕང་བ་བཅས་དྲུག་ལས། [ORDINAL]-པ་ [TARGET-NAME]-གཞུང་ཚིག་ཡིན་ནོ།།

#### Five verses — ལྔ་པོ་

> ཞེས་པའི་ཤློཀ་ལྔ་པོ་འདི་དག་ནི་…

#### Seven verses — བདུན་པོ་

> ཞེས་པའི་ཤློཀ་བདུན་པོ་འདི་དག་ནི་…

#### Half-verse (2 lines) — ཚིགས་སུ་བཅད་པ་

> ཞེས་པའི་ཚིགས་སུ་བཅད་པ་འདི་ནི་…

---

### Key Principles

**Trace every ancestor.** Every node in the hierarchy from the outermost container to the leaf must appear in the summary paragraph. Do not skip levels.

**Name all siblings when branching.** Whenever you state "from N sub-sections," list every sibling by name before naming the target. This is what gives the reader a complete picture of the outline branch.

**Use the sa-bcad heading names verbatim.** Do not paraphrase outline headings; quote them exactly as they appear in the source file. The names carry precise doctrinal meaning.

**Match the closing verb to the sa-bcad label.** Choose སྟོན་པ།, བཤད་པ།, བསྒྲུབ་པ།, or བསྟན་པ། based on the actual heading used in the source. If the heading contains དཔེ་ it usually closes with བསྟན་པ།; if it contains རིགས་པ། it closes with བསྒྲུབ་པ།.

**Copy verses exactly.** Do not alter spacing, punctuation, or the `། །` line-ending markers.

**Chapter scope.** If the user specifies a chapter (e.g., "Chapter 1 only"), process only the verse groups between that chapter's first outline heading and its closing `མཚན།` colophon.

---

### Output Location

Save the final Markdown file to:
```
[workspace-root]/$VERSES/
```

Present the file to the user with a `computer://` link when done.

---

## After this skill

Verse packages are what `verse-translate` and the translation tracks read instead of
the bare root line, and what `multilevel-summary` calibrates for an audience.
