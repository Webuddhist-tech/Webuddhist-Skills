---
name: commentary-segment
description: >
  Step 2 of commentary-pipeline: segment an OCR-clean but under-segmented Tibetan commentary
  into short, individually-referenceable blocks (functional units: openers, quoted root
  verses, explanations, frame lines — or citation-sized blocks) based on the functional
  content of the text — quotation frames, objection/answer markers, sa-bcad enumerations,
  sentence-final particles, verse stanza detection. Use when a commentary's text is one
  continuous run (or has overly long paragraphs) and needs breaking into units before the
  TOC and block IDs. Runs after commentary-preclean, before commentary-toc-extract. Does not
  interpret, translate, or alter a single character of the source.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/commentary-segmentation/SKILL.md
  - Webuddhist-Skills/rails/segment-commentary/SKILL.md
---

**Role:** Expert editor in classical Tibetan Buddhist commentary (`འགྲེལ་པ་`) structure and Obsidian markdown.

**Task:** Insert block boundaries into a Tibetan commentary so each block is a citation-sized unit (a prose sentence or two, one verse stanza, or one quotation) — without adding, removing, reordering, or re-spelling any character of the source.

The boundaries follow the text's own functional signals: quotation frames, objection/answer markers, sa-bcad enumerations, sentence-final particles, and verse meter. Most of this is done deterministically by the scripts in `scripts/`; you only hand-finish what the rules cannot resolve.

**Scope and the citation chain.** This skill operates on files in `$COMMENTARIES/`. Per `$SYSTEM/CLAUDE.md` §6, the only permitted edits to a source file are structural (block boundaries, block IDs, navigation, factual `[Ed:...]` notes). Inserting a paragraph break is structural; rewording, glossing, or "fixing" the text is interpretation and is forbidden here. If the text needs OCR repair, that belongs to `format-commentary`, which runs first. Every script here enforces this with a no-loss assertion: the output minus whitespace must equal the input minus whitespace, or it aborts and writes nothing.

---

**What good output looks like — two layouts**

*Functional units (`--units`) — the layout of the vault's human-edited commentaries. Use this for any commentary going into `$SOURCES/`.* Benchmarked against eight hand-processed Tārā commentaries (`$SYSTEM/scripts/seg-toc-benchmark/`), the human editors cut a verse commentary into functional units, not sentences:

| Unit | Example | Block |
|---|---|---|
| Opener | `<topic> ལ་གསུམ། A། B། C་འོ། །དང་པོ་ནི།` (division announcement + first-child opener) · `གཉིས་པ་ <title> ནི།` | one block |
| Root quote | the quoted root stanza (or 2/5 pādas of it) | one block, pādas one per line |
| Explanation | `ཞེས་པ་སྟེ། …` up to the next opener — including `…ལོ། །གང་ལ་ན། …` questions, side remarks and variant readings | one block, even at 150–250 syllables |
| Frame | the `ན་མོ་ …` line · each of the author's verses · `སྨྲས་པ།` · the colophon | one block each |

Median block size in the human files is 32–108 syllables. A 40-syllable target splits the explanation units the editors keep whole.

*Citation-granular (`--max-syllables 40`)* — 1–2 sentences of prose per block, for review work where every long run should be surfaced. A prose block that exceeds ~40 tsheg-delimited syllables should be split unless it is a single indivisible clause, quotation, or stanza.

In both layouts:
- **Verses (ཚིགས་བཅད):** one independent stanza per block. Keep a stanza's pādas together; never merge two independent stanzas into one block.
- **Quotes (ལུང་འདྲེན):** the source attribution (e.g. `སྡུད་པ་ལས།`) on its own block above the quote, and the closing formula (e.g. `ཞེས་སོ། །`) on its own block below it (format-commentary §3).

---

**Pipeline position**

```
format-commentary  →  commentary-preclean  →  commentary-segment  →  commentary-toc-extract  →  …
(OCR clean, heading structure)   (this skill: boundaries)     (rails consume the blocks)
```

Do not run this skill on text that is not yet OCR-clean.

```
[Stage 0]                   [Stage 1]               [Stage 2]              [check]        [human]
preclean_commentary.py  →  segment_commentary.py  →  stage2_refine.py  →  no-loss vs  →  approval
(strip scaffolding,         (deterministic            (mechanical            source         + hand review
 optional)                  boundaries)               refinement)
```

---

**Spacing is source text.** The scripts only insert and remove *block* boundaries. Whitespace inside a block — `། །`, `ག །`, `དྲུག །` — is the source's own punctuation and is preserved exactly. (Earlier versions rewrote `། །` to `།།` in structural mode and normalised spacing inside pādas; the whitespace-blind no-loss check could not see it. The benchmark now measures spacing separately.)

---

**Scripts at a glance**

| Script | Stage | Role |
|---|---|---|
| `preclean_commentary.py` | 0 | **In `commentary-preclean`** — strip prior scaffolding back to continuous prose. Optional. |
| `segment_commentary.py`  | 1 | Deterministic boundary insertion. The core of the skill. |
| `units.py`               | 1 | The `--units` layout (imported by `segment_commentary.py`): root-quote detection and signal-based merging into functional units. |
| `stage2_refine.py`       | 2 | Mechanical refinement of the Stage-1 draft (newline expansion, citation/lead-in splits, optional connector splits). |
| `batch_segment.py`       | 0+1 | Run Stage 0 + Stage 1 over a whole directory in parallel; emits per-file reports plus a batch summary and a combined flagged-rows file. |

All scripts share `--dry-run` (validate, write nothing) and a `--report` TSV. Paths below are relative to the vault root.

---

**Stage 0 — pre-cleaning** is its own skill now: `commentary-preclean` (run it first when the file carries index numbers, IDs, headings or per-line breaks).

---

**Stage 1 — deterministic boundary detection (script)**

`$SKILL/scripts/segment_commentary.py` inserts a paragraph break at every high-confidence *functional* boundary, and only there:

- `terminal-particle` — a clause-final particle (`འོ`/`ནོ`/`དོ`/`སོ`/`ཏོ`/`གོ`/`ལོ`…) plus `།` ends a prose sentence. Broad catch-all; runs last so more specific markers claim a position first.
- `quote-close` — explicit closers (`ཞེས་སོ། །`, `ཅེས་སོ། །`, `ཞེས་གསུངས་སོ། །`, `ཞེས་པའོ། །`, `ཞེས་བྱ་བའོ། །`…) end a citation.
- `quote-open` — a source-attribution marker (`…ལས།`, `…གསུངས།`) gets its own block before the cited passage.
- `enumeration-head` — a sa-bcad head closing on a number-word + suffix (e.g. `…ལ་གསུམ་སྟེ།`, `…ལ་གཉིས་ལས།`) ends a node.
- `ordinal-open` — `དང་པོ་…`, `གཉིས་པ་…`, `གསུམ་པ་…` opens a new topical node.
- `objection-close` / `objection-open` — `…ཅེ་ན།` / `…ཞེ་ན།` / `…སྙམ་ན།` closes an objection; `འོ་ན་…` opens the reply. `objection-open` is a weak-context rule: it only auto-cuts when it sits just after a shad; otherwise it is reported as a `-candidate` for a human to judge rather than cut blindly.
- `verse-stanza` — a run of 2–4 consecutive clause units, each 6–11 syllables, uniform in length (max − min ≤ 1), each ending on a strong (double) shad, is peeled out as one protected stanza: emitted whole, never run through the rule engine or the syllable cap, never flagged `STAGE2_REVIEW`. Metre is measured in **syllables** (runs of Tibetan letters), never characters or words: a tsheg before the shad (`དང་།`), `ག །`, the non-breaking tsheg `༌` and footnote markers `[^n]` do not change the count. A single-shad unit sandwiched between two stanza pādas is bridged into the run (some sources mark pāda ends with a single shad), but a bridged unit is never a stanza's first or last line. An isolated pāda-length clause stays with the surrounding prose, so a medium prose sentence is never mistaken for a one-line verse. After ཀ / ག a pāda ends `ག །` (space + single shad, no tsheg) — that counts as a full pāda end. Not pādas: the `ན་མོ་ …` homage formula, and a unit opening with `ཞེས་ / ཅེས་` (it closes a quotation and glosses it). **Prose look-alikes are rejected:** a candidate whose lines *each* end on a sentence-final particle (`གོ ངོ དོ ནོ བོ མོ རོ ལོ སོ ཏོ`, `…འོ`) is a run of complete prose sentences (`X ནི་ Y འོ། །` glosses), not a stanza — in real verse only the last pāda closes the sentence. Metre alone cannot see quotation; for a commentary on a verse root text, pass `--root` so quoted root pādas are matched by content.

After the rule pass it enforces a syllable cap: any segment still longer than `--max-syllables` is split at shad (clause) boundaries; over-cap segments with no internal shad are flagged `STAGE2_REVIEW:NO_SHAD_FOUND`. Over-fragmented adjacent segments are merged back while they fit the cap (citation boundaries are never merged away). The run also prints a **quote-balance** check (count of `quote-open` vs `quote-close`); a `MISMATCH` points to an unclosed or stray citation marker worth a look.

Two ways to run it:

```
# (a) cap-based — finer control, every over-cap block flagged for review:
python3 $SKILL/scripts/segment_commentary.py \
    "$INBOX/<file>.preclean.md" \
    "$INBOX/<file>.segmented.md" \
    --report "$INBOX/<file>.segreport.tsv" \
    --max-syllables 40

# (b) structural — closest match to the canonical block layout:
python3 $SKILL/scripts/segment_commentary.py \
    "$INBOX/<file>.preclean.md" \
    "$INBOX/<file>.structural.md" \
    --report "$INBOX/<file>.segreport.tsv" \
    --structural
```

`--structural` breaks prose only at strong (double-shad) sentence ends, section heads, and citation frames; emits verses one pāda per line; splits citation markers and re-attaches short closing formulas to their block; and implies **no syllable cap**. Use the cap-based mode (a) when you want every long run surfaced for manual review instead.

```
# (c) functional units — the vault layout (recommended for 1-SOURCES commentaries):
python3 $SKILL/scripts/segment_commentary.py \
    "$INBOX/<file>.preclean.md" \
    "$INBOX/<file>.units.md" \
    --report "$INBOX/<file>.segreport.tsv" \
    --units --root "$SOURCE_TEXTS/<root-text>.md"
```

`--units` runs the structural pass, then **only merges** its blocks back into functional units, and only on a positive linguistic signal (every other structural cut is kept; meaning-based merges are `commentary-resegment`'s job):

- **opener chain** — a block starting `དང་པོ་ནི།` / `དང་པོ་ལ་ N།` joins the block before it when that block ends with a division announcement (`… ལ་གསུམ། …`), nested as deep as the chain goes;
- **question continuation** — `… ལོ། །` + `གང་ལ་ན། …` (a short `གང་/ཅི/ཇི … ན།` question asks about the sentence it follows);
- **quotative** — a prose block starting `ཞེས/ཅེས …` quotes the words just before it.

It always keeps apart: the `ན་མོ་ …` homage line, `སྨྲས་པ།`, verse blocks, headings.

`--root` (recommended whenever the vault has the root text) cuts **quoted root verses** out of prose even when the stanza detector misses them — a 2-pāda quote, a 5-pāda verse cut 4+1, the root's homage line. A quote is cut out only when it is a lemma: introduced (`… ནི།`, block start) and closed (`ཞེས/ཅེས …`, block end), and at least two consecutive root pādas or a whole root line. Glossators who quote pāda by pāda (`<pāda> ཞེས་པ་ནི། <gloss>`) keep lemma and gloss together, as their editors do. With `--root`, a ≤2-pāda "stanza" that matches no root pāda is treated as a false stanza detection and returned to prose.

`--unit-max-syllables` (default 300) is a safety valve: a merged prose unit over the cap falls back to its structural cuts.

**Prose is grouped by function, not by length.** Do not impose a minimum unit length (e.g. "150–350 syllables per block"): the commentary's own joints — a sa bcad opener, a lemma and its gloss (`… ཞེས་པ་ནི།`), an objection and its reply (`… ཅེ་ན། / འོ་ན་ …`), a quotation frame — are naturally 15–300 syllables, and block IDs are citation addresses, so gluing a short opener or an objection onto its neighbour loses precision that cannot be recovered. Length is only a guard: the unit cap above for over-long merges, `OVER_LENGTH` (> 250) in `commentary-resegment` QC for review, and a short-fragment merge there for split artifacts. Longer prose units come from merging more on functional signals (`commentary-resegment` M1: the next block continues the same explanation), never from a length floor.

**Recommended flags (benchmark v2).** Three opt-in refinements of `--units`, each measured
alone against v1 on the 8-file benchmark (`$INBOX/benchmark-seg-toc/variants/` in the
21-taras vault), none of which lowered any file's score:

| Flag | What it does | Effect (boundary F1, mean of 8) |
|---|---|---|
| `--enum-chain broad` | the opener chain also fires when the block before ends with any count/enumeration closer (`… ལས།`, `… ཡོད་པ་ལས།`, `… གཉིས་སོ།`, `… ལ་`), not only `ལ་ N།` | 0.789 → 0.797 |
| `--quotes inline` | for commentaries whose editors keep the quoted root lines **inside** the explanation (no separate verse block), a quoted root pāda is merged into the prose unit around it. Use `separate` (default) when the editors give each quoted stanza its own block | 0.789 → 0.878 (gendun-drub 0.55 → 0.85, drakpa 0.37 → 0.76) |
| `--colophon-guard` | in the last 20% of the text, a `ཞེས/ཅེས` block that is the colophon (`… འདི་ནི།`, `… མིང་པས་སོ།`, `… གྱིས་སྦྱར་བ།`) is not glued to the explanation before it | frame placement 0.569 → 0.840 (with the pass-5 frame rules) |
| `--stanza-breaks` (v2.1) | a quoted **first line of a root stanza** starts a new block when it follows a finished sentence (`…པའོ། །`, `…སོ།`) — also inside a prose block, inside a detected "stanza" that paired a closing sentence with the next quote (that sentence goes back to the explanation), and under `--quotes inline` (the quote stays with its gloss but does not join the block before). After a lead-in `…ནི།` or mid-sentence (`… ལ།`, `… སྟེ།`) it stays put | 0.708 → 0.741 deterministic (drakpa 0.25 → 0.51, stanza openers 6 → 20 of 21; no file lower). End to end with Opus, drakpa 0.86–0.90 → **0.937** (two runs, ±0.001) |

```
python3 $SKILL/scripts/segment_commentary.py IN OUT --units --root "$SOURCE_TEXTS/<root>.md" \
    --enum-chain broad --quotes <separate|inline> --colophon-guard --stanza-breaks
```

`--stanza-breaks` matters most for commentaries that gloss the root stanza line by line with
the stanza's opening line buried at the end of the previous explanation (drakpa): without it
the re-segmentation model has to find every stanza opener itself, and when it misses them the
score swings by ±0.05 between runs.

**Verse root texts are not commentaries.** A root treatise, praise or ritual in verse (no
`ཞེས་པ་ནི།` glosses of another text) goes through `root-text-pipeline` instead.

`--quotes` is a per-commentary choice: look at how the vault's other commentaries on the
same root (or the editor's sample) lay out quoted root lines, and declare it.

Note the default for `--max-syllables` is **50** if you omit it; the granularity target is ~40, so pass `--max-syllables 40` explicitly (the batch runner already defaults to 40). The cap is ignored under `--structural`.

The Stage-1 output goes to `$INBOX/` — never overwrite the source until boundaries are approved.

**Batch mode.** To process an entire directory in parallel:

```
python3 $SKILL/scripts/batch_segment.py \
    "$SOURCES/Commentaries" "$INBOX/segmented" \
    --preclean --max-syllables 40
```

It runs Stage 0 (with `--preclean`) then Stage 1 per file across all CPUs, skips files whose output already exists (`--force` to redo), and writes `batch_summary.tsv` (one row per file, including the quote-balance status) and `batch_flagged.tsv` (every `STAGE2_REVIEW` row across all files) into the output directory.

---

**Stage 2 — semantic refinement**

Most of the Stage-1 residue is mechanical and is handled by `$SKILL/scripts/stage2_refine.py`. Run it first, then hand-review only what it leaves behind.

```
python3 $SKILL/scripts/stage2_refine.py \
    "$INBOX/<file>.segmented.md" \
    "$INBOX/<file>.stage2.md" \
    --max-syllables 40 \
    --source "$COMMENTARIES/<file>.md" \
    --report "$INBOX/<file>.stage2.tsv"
```

It performs, deterministically and no-loss:

- **Newline expansion** (default) — `merge_short_segments` in Stage 1 joins consecutive source lines that were each under the cap, leaving an internal `\n` inside a block. For any over-cap block containing an internal `\n`, every `\n` becomes a paragraph break — each original source line becomes its own block. This restores boundaries the source already marked; it never guesses.
- **Citation lead-in / verse split** (default) — a short source-frame line glued onto a following stanza is peeled back onto its own block.
- **Connector split** (opt-in, `--split-connectors`) — over-cap *single-line* prose is split at strong sub-clause connectors (`ཅིང་`/`ཞིང་`/`སྟེ་`/`ཏེ་`/`ནས་`/`ལས་`), never producing a piece below 8 syllables. Off by default: a connector is a weaker signal than a source-marked line break, so prefer leaving a block whole over a wrong cut.

Passing `--source` adds a second no-loss assertion against the **original source file**, so any deviation inherited from Stage 1 is caught here rather than passed downstream silently. Blocks still over the cap that the tool can't safely split are reported as `STAGE2_MANUAL`.

**Hand-review** the `STAGE2_MANUAL` rows (and any `STAGE2_REVIEW` rows from Stage 1). These are prose runs with no lexical cue. Insert a paragraph break only at a genuine topic shift — where the commentary moves from a position to its reason, from one objection to the next, or from gloss to scriptural support. Rules for hand edits:

- Only *insert* `\n\n` boundaries. Do not change, reorder, or delete any syllable.
- For a verse embedded inside a larger prose paragraph (the script couldn't isolate it), do not split pādas: break before the first pāda and after the final `།།`, keeping the stanza together. Never merge two independent stanzas.
- Keep a `…ལས།` attribution line and its closing `ཞེས་སོ། །` on their own blocks (format-commentary §3).
- When a passage genuinely cannot be cut without breaking sense, leave it whole. Over-long is safer than wrong.

If you write any bespoke refinement code, read `$SKILL/scripts/segment_commentary.py` first — two facts save rewrites:

- **TSV index ≠ paragraph index.** The TSV numbers segments as the script counts them internally; `merge_short_segments` then merges short adjacent segments, so TSV row N does not map to output paragraph N.
- **Use the script's `_squeeze`** (the whitespace-translate table in `segment_commentary.py` / `stage2_refine.py`, not `re.sub(r'\s+','',s)`) for any no-loss check, or you may see phantom mismatches. If a mismatch appears, first test `squeeze(source) == squeeze(stage1_output)` to see whether it predates your change.

After Stage 2, re-run a no-loss check against the **original source** (the `--source` flag does this automatically) before proceeding.

---

**Procedure**

1. Confirm the file is OCR-clean (run `format-commentary` first if not).
2. If the file carries index numbers, block/verse IDs, headings, or per-line/per-verse breaks, run **`commentary-preclean`** to `$INBOX/`. Skip if it is already plain running text.
3. Run **Stage 1** (`segment_commentary.py`, on the Stage-0 output if you ran it) to `$INBOX/`, producing the segmented draft and the TSV report. Use `--units --root <root text>` for the vault layout, `--structural` for sentence-level layout, or `--max-syllables 40` for review-oriented output. For many files at once, use `batch_segment.py`.
   With `--units`, Stage 2 (`stage2_refine.py`) is not needed; the remaining meaning-based merges are done by `commentary-resegment` after the TOC headings are in.
4. Run **Stage 2** (`stage2_refine.py`) with `--source` pointing at the original. Then hand-review the `STAGE2_MANUAL` / `STAGE2_REVIEW` rows.
5. Re-run the no-loss check against the **original source file**.
6. Have a domain specialist approve the boundaries.

**Output**

- A boundary-segmented commentary draft in `$INBOX/` (not the source — the source is only updated after human approval).
- TSV reports listing each segment, the rule that triggered its boundary, its syllable count, and any review flag.

**Rules recap**

- No character changes — boundaries only. The scripts enforce this; hand edits must honor it too.
- OCR repair and translation are out of scope (other skills own those).
- Never write block IDs in this step.
- When in doubt, under-cut rather than over-cut.
