---
name: add-block-ids
description: >
  Add Obsidian block IDs to a text so every verse, prose block, and heading
  can be cited and transcluded. Covers the four cases that occur in practice: a
  commentary keyed off headings a human labelled by hand, a Sanskrit root text using
  the four-zone scheme, expert-segmented liturgy notes being prepared for the sources
  folder, and the narrow verse/prose-only pass.

  Trigger on "add block IDs", "add Obsidian block IDs", "tag this with block ids",
  "stamp the IDs", "add the citation anchors", "re-index this file", "add TOC/section
  ids".

  Run AFTER segmentation and formatting — block IDs are stamped onto blocks that
  already exist, never used to create them.
profile: any
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/Obsidian-Block-ID-to-Commentary/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/add-block-id-root-text/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/add-block-id-root-text/SKILL.md
  - Liturgy-rails/.claude/skills/block-ids/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/commentary-verse-id/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/commentary-verse-id/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Stamp block IDs onto a text

**Read `rails/CONVENTIONS.md` first.** It defines every ID scheme below; this skill
only applies them. The four modes differ in *what supplies the key*:

| Mode | Text | Key comes from |
|---|---|---|
| 1 | Commentary with `##` headings | **The human contributor**, by hand, on each `##` heading |
| 2 | Sanskrit root text | The four-zone scheme (front matter / verses / colophons) |
| 3 | Liturgy notes in `$INBOX` | Expert segmentation already in the note |
| 4 | Commentary, verses and prose only | Sequential within the section |

**The rule that matters most (mode 1).** A commentary's `##` heading ID is written by
hand by the contributor and is **never generated, edited, or guessed**. The
contributor chooses the label — `^1-0`, `^I-0`, `^a-0`, any short token — to key that
section to the root text's structure, and everything beneath it derives from that
same label (`^1-1`, `^1-2`, …). Before tagging anything, scan every `##` heading and
stop if one is unlabelled. The `#` title is the single exception: it is
auto-generated as `^0`.

**Transclusion lines never take an ID and never advance a body counter.** They are
structural, not content (`rails/CONVENTIONS.md` §3). Getting this wrong shifts every
subsequent ID in the section.

**No lines are added or removed by any mode.** Total line count is unchanged; IDs are
appended to existing lines.

---

## Mode 1 — Commentary, keyed off hand-written `##` labels

The most common case. Derives `###`/`####` and body IDs from the contributor's `##` label.

This skill stamps every `###`/`####` sub-heading and body-text block of a Tibetan commentary file with a trailing Obsidian block-reference id, keyed off a label the human contributor has already written by hand on the enclosing `##` heading — so each becomes individually linkable and transcludable. The `##` heading's own id is never generated, edited, or guessed by this skill: it must already be there, written by hand, before the skill will touch anything else in that section. Sub-headings get their own hierarchical id built from that label; body-text blocks (a verse stanza, a prose paragraph — whatever a blank line sets off) are numbered sequentially off the same label within the section, restarting at each new `##`. Root-text transclusion lines (`![[...]]`) are structural navigation, not commentary content, so they are always skipped: never tagged, and never counted against the body-block sequence.

---

### Inputs

- `file` — path to a commentary markdown file, typically under `$COMMENTARIES/`. It must contain at least one `##` heading, and **every `##` heading must already end in a manually-added `^{label}-0` id** (see Rule 1) before the skill will tag anything else. It may optionally contain `###` and `####` sub-headings and root-text transclusions (`![[...]]`); it does not need any of these to run.

### Output

- The same `file` modified in place (or a caller-specified output path), with a block id appended to the end of every qualifying `#`/`###`/`####` heading and body-text-block line. `##` heading lines are never modified. No lines are added or removed; total line count is unchanged.

---

### Output file format

Given input where the `##` headings already carry hand-written labels:

```
## ༄༅། །ཕྱག་འཚལ་ཉེར་གཅིག་གི་བསྟོད་འགྲེལ་བདུད་རྩིའི་དགའ་ཚལ་བཞུགས་སོ། །

### མཆོད་བརྗོད། ^I-0

ཨོཾ་སྭ་སྟི།

### དང་པོ་སྦྱོར་བ་ཚོགས་བསགས། ^1-0

#### ཚོགས་ཞིང་སྤྱན་འདྲེན་པ།

དེའང་རྗེ་བཙུན་སྒྲོལ་མའི་ཡོན་ཏན་...

![[bo-root-text#^1-1]]

ཨོཾ་ནི་མགོ་འདྲེན། རྒྱལ་བ་ཀུན་གྱི་...
```

Output:

```
## ༄༅། །ཕྱག་འཚལ་ཉེར་གཅིག་གི་བསྟོད་འགྲེལ་བདུད་རྩིའི་དགའ་ཚལ་བཞུགས་སོ། ། ^0

### མཆོད་བརྗོད། ^I-0

ཨོཾ་སྭ་སྟི། ^I-1

### དང་པོ་སྦྱོར་བ་ཚོགས་བསགས། ^1-0

#### ཚོགས་ཞིང་སྤྱན་འདྲེན་པ། ^1-1-0

དེའང་རྗེ་བཙུན་སྒྲོལ་མའི་ཡོན་ཏན་... ^1-1

![[bo-root-text#^1-1]]

ཨོཾ་ནི་མགོ་འདྲེན། རྒྱལ་བ་ཀུན་གྱི་... ^1-2
```

Note three things: the `##` headings (`^I-0`, `^1-0`) are exactly what the contributor wrote — untouched — and everything underneath is built from that label, not from a running section count; the title still gets an auto-generated `^0`; and the transclusion line is untouched and did not consume a body-counter value.

A section nested four deep, off a heading manually labeled `^5-0`, follows the same pattern:

```
### ... ^5-0
#### ... ^5-1-0
##### ... ^5-1-1-0

body text segment ^5-1

body text segment ^5-2

body text segment ^5-3
```

A section whose contributor used a Roman-numeral label instead:

```
### ... ^II-0
#### ... ^II-1-0

body text segment ^II-1

body text segment ^II-2
```

---

### Rules

1. **`##` heading ids are always manual — this skill never generates, edits, or guesses one.** Every `##` heading must already end in a block id of the form `^{label}-0`, written by hand by the human contributor. `{label}` can be anything the contributor is using to key that section (a plain running number, a Roman numeral, a letter, or any other short token) — this skill does not care what scheme it follows, only that it's already there. Before tagging anything, the skill scans every `##` heading in the file:
   - If **any** `##` heading is missing a `^{label}-0` id, the skill stops immediately, writes nothing, and tells the human contributor exactly which heading(s) (by line number and text) need an id added by hand. It does not invent a fallback numeric id for the missing ones, even to keep going on the rest of the file.
   - Only once **every** `##` heading in the file already carries a manual `^{label}-0` id does the skill proceed to tag the title, sub-headings, and body-text blocks.
   - The `#` title (at most one per file) is the one exception: it is still auto-generated as `^0`, exactly as before.
2. **`###`/`####` and body-text ids are all keyed off the enclosing `##` heading's manual label, never off a running section count:**
   - `###` → `^{label}-{h3}-0`, where `h3` counts `###` headings within the current `##` section and resets to 1 at each new `##`.
   - `####` → `^{label}-{h3}-{h4}-0`, where `h4` counts `####` headings within the current `###` sub-section and resets to 1 at each new `###` (and, in turn, at each new `##`). A `####` heading requires an enclosing `###` — one that appears directly under a `##` with no `###` above it is an error, not a guessed `^{label}-0-1-0`.
   - Body-text blocks (a run of consecutive non-blank, non-heading, non-transclusion lines) get `^{label}-{n}`, where `n` is a counter starting at 1 that increments for every body block in that section — it does **not** reset at `###`/`####` sub-headings, only at the next `##`. A body block sitting under a `####` still gets the two-segment `^{label}-{n}` form, never `^{label}-{h3}-{n}` or deeper.
   - Concretely: a `##` heading manually tagged `^I-0` produces body ids `^I-1`, `^I-2`, …; one tagged `^1-0` produces `^1-1`, `^1-2`, …; one tagged `^a-0` produces `^a-1`, `^a-2`, ….
   - `#####` and deeper are **not supported** — abort and flag for human review rather than inventing a fifth tier.
3. **Transclusion lines are never modified and never receive an id**, and they never consume a body-counter value — treat them as invisible to the numbering, not merely unlabeled.
4. **A heading line always starts a new block**, even if it directly abuts the previous or next line with no blank line around it. Some raw commentary files are missing a blank line before a heading; the heading still gets its own id (or, for `##`, is still recognized and its label still extracted).
5. **The id is appended to the end of the block's last line only** (` ^id`), never inserted as a separate line. A multi-line verse stanza gets exactly one id, on its final line. `##` heading lines are never appended to, since their id is already there.
6. **No body content may appear between the `#` title and the first `##` heading.** This shape has no validated numbering — abort and ask the human contributor rather than guessing.
7. **Idempotent:** a `#`/`###`/`####`/body line whose block already ends in a ` ^{label}-...` suffix is left untouched and does not consume a counter slot, so re-running on an already-tagged file is a no-op. `##` heading lines are always left untouched regardless (see Rule 1) — this includes both a first run and every re-run.
8. **Original line endings (CRLF or LF), YAML frontmatter (if present), and total line count are preserved** — ids are appended to existing lines only, and never to `##` headings.
9. **Do not hand-edit ids with the Edit tool for bulk tagging** — always use `apply.py` so the heading/body counters stay consistent across the whole file. Manual edits are only for two things: (a) adding the required `^{label}-0` id to a `##` heading before running the skill, and (b) fixing a specific flagged anomaly after review (for example, closing a numbering gap left by a previous partial or buggy run).

---

### Procedure

The skill uses a helper script `apply.py` located in the same directory as this SKILL.md. Construct the path at runtime from the skill's own location.

1. **Check `##` heading labels first.** Every `##` heading in the target file must already end in a `^{label}-0` id. `apply.py audit` performs this check automatically and aborts with a line-numbered list if any are missing — but glance at the file yourself too. If any are missing, stop here and tell the human contributor which heading(s) need one added by hand; do not proceed until they've done so.

2. **Audit.** Run:
   ```bash
   python "<this-skill-dir>/apply.py" audit "<path-to-file.md>"
   ```
   This reports, per `##` section (identified by its manual label), the first id, last id, and body-block count that would be tagged, without writing anything. Confirm the labels and ranges look plausible (e.g. match the `##` headings you can see in the file) before applying.

3. **Dry-run to a scratch copy.** Copy the target file to a scratch/output location and run:
   ```bash
   python "<this-skill-dir>/apply.py" apply "<scratch-copy.md>"
   ```
   Do not write directly to the vault file on the first pass.

4. **Spot-check the output.** Read the first ~30 lines, a `##` section boundary (confirming the `##` line itself is byte-identical to the input, and that the first body id under it starts with `^{that heading's own label}-1`), and at least one point where a transclusion sits between two body blocks — confirm the transclusion is untouched and the two neighboring body ids are back-to-back (no gap).

5. **Verify idempotency.** Run `apply.py apply` a second time on its own output and confirm the file is byte-identical (no diff).

6. **Verify line count and content are unchanged.** Compare `wc -l` on the original file and the tagged output — they must match exactly. Stripping every ` ^...` suffix the script added (the pre-existing `##` ids were already there, so leave those alone when checking) should reproduce the original file byte-for-byte.

7. **Write the result to the real file.** Once verified, overwrite the actual `file` in the vault with the tagged content (or run `apply.py apply "<path-to-file.md>"` directly on it once confidence is established).

---

### Completion check

- [ ] Every `##` heading in the file already had a manually-added `^{label}-0` id before any tagging ran; if any were missing, the human contributor added them first
- [ ] `apply.py audit` was run first and its label/section report reviewed before any file was modified
- [ ] Output was dry-run to a scratch copy before touching the vault file
- [ ] First ~30 lines, a `##` boundary (heading line byte-identical to input, first body id under it matching that heading's own label), and a transclusion-adjacent pair of body blocks spot-checked in the output
- [ ] Idempotency verified (second run on the tagged output produces no diff)
- [ ] Total line count of the output matches the original file, and stripping all newly-added ids reproduces the original content exactly
- [ ] No transclusion line, blank line, frontmatter line, or `##` heading line was modified or tagged
- [ ] No numbering gaps remain where a transclusion sits between two body blocks
- [ ] Every `###`/`####`/body-text id shares its enclosing `##` heading's own manual label
- [ ] Final tagged file written to the correct vault path

---

## Mode 2 — Sanskrit root text — four-zone scheme

Front matter in Roman numerals, chapter verses in Arabic, colophons in lowercase letters, book back matter separately. See `rails/CONVENTIONS.md` §1b.

This skill applies the vault's block ID convention to a Sanskrit root-text `.md` file. It is **not** for commentaries or translations of commentaries.

---

### Workflow

The skill uses a helper script `apply.py` located in the same directory as this SKILL.md. Always follow this order:

#### 1 — Script reads the file (audit)

`apply.py` is in the same directory as this skill file. Construct the path at runtime from the skill's own location:

```bash
python "<this-skill-dir>/apply.py" audit "<path-to-file.md>"
```

The audit prints:
- Heading structure with gaps flagged
- Every block without an ID, labelled `[auto]` or `[needs LLM judgment]`
- Verse counts per chapter vs. Sanskrit expected
- Other issues (null bytes, bad spacing, multiple blanks)

#### 2 — LLM identifies zones

Read the audit output. For every block marked `[needs LLM judgment]`, determine its zone by reading the content:
- Is it front matter, a chapter intro, a verse, a chapter colophon, or book back matter?
- Does it contain an interpolated verse (duplicate source number → `^C-Vx1`)?
- Is it a multi-line stanza (ID goes on the **last** line only)?

Note any decisions that the script cannot apply automatically.

#### 3 — Script applies mechanical changes

```bash
python "<this-skill-dir>/apply.py" apply "<path-to-file.md>"
```

The script handles:
- `^0`, `^I-0`, `^N-0` heading IDs
- `^0-N` → `^I-N` legacy ID fixes
- `^N-a` for known chapter colophon lines
- `^C-N` verse IDs from ordinal prefixes (`N. verse text`) — prefix stripped after
- `^a`, `^b`… for book back-matter blocks
- Blank lines between verse blocks, null bytes, spacing normalisation

After applying it prints a fresh audit showing what remains.

#### 4 — LLM applies remaining changes

For anything still flagged — ambiguous blocks, interpolated verses, multi-line stanzas, colophons not matching known patterns — apply the IDs and edits directly using the Edit tool.

---

### Block ID Convention

Sanskrit root texts follow a **three-zone** scheme based on content role, not heading level:

#### Zone markers

| Zone | Symbol | Rule |
|---|---|---|
| Pre-title intro | `T` | Content before the `#` title heading: `^T-1`, `^T-2`… |
| Front matter | Roman numeral (`I`, `II`…) | Sections and content preceding Chapter 1 |
| Main verses | Arabic numeral (`1`, `2`…) | Chapter and verse numbers |
| Back matter | Lowercase letter (`a`, `b`…) | Colophons, appendices, closing material |

#### Heading IDs

| Heading level and role | ID format | Example |
|---|---|---|
| `#` — book is the root (no collection above it) | `^0` | `# शबोधिचर्यावतारः ^0` |
| `#` — collection title (book is at `##`) | no ID | `# Abhidhammapiṭake` |
| `##` — book under a collection | `^1-0`, `^2-0`… | `## Dhammasaṅgaṇī ^1-0` |
| `##` or `###` — front matter section heading | `^I-0`, `^II-0`… | `## Introduction ^I-0` |
| `##` or `###` — chapter heading | `^N-0` | `## 1. Chapter One ^1-0` |
| `##` or `###` — back matter section (after last chapter) | `^a-0`, `^b-0`… | `## Colophon ^a-0` |

#### Content IDs

| Content type | ID format | Example |
|---|---|---|
| Pre-title block | `^T-N` | `^T-1` |
| Front matter content | `^I-N`, `^II-N`… | `^I-1`, `^I-2` |
| Chapter intro (before first verse) | `^N-I`, `^N-II`… | `^1-I`, `^1-II` |
| Chapter verse | `^N-V` | `^1-1`, `^6-134` |
| Chapter colophon / back matter | `^N-a`, `^N-b`… | `^8-a` |
| Book colophon (standalone, after last chapter) | `^a`, `^b`… | `^a` |

#### Interpolated / extra verses (duplicate source numbers)

Some Sanskrit editions include verses that share the same number as an adjacent verse. The source signals this in several ways:

- Verse number marker appears twice: `॥24॥ … ॥24॥`
- Printed edition uses repeated ordinals: `24. verse / 24. verse`
- A verse carries no number marker at all between two numbered verses

When the source shows duplicate numbering at position V, assign:

| Situation | ID format | Example |
|---|---|---|
| First (canonical) occurrence | `^C-V` | `^8-24` |
| Second occurrence (one duplicate) | `^C-Vx1` | `^8-24x1` |
| Third occurrence (two duplicates) | `^C-Vx2` | `^8-24x2` |

**Rule**: Never use a bare `^C-Vx` — always append the counter starting at `1`, even when there is only one duplicate. The next canonical verse is unaffected: `^8-24`, `^8-24x1`, `^8-25`.

#### Constraints
- **Verse IDs only**: `^chapter-verse` or `^chapter-subsection-verse` — max 3 segments (not counting the `xN` suffix on interpolated verses).
- Verse counter is **per-chapter** (restarts at 1 for each `##` chapter).
- Verse numbers come from `॥N॥` markers in the Sanskrit text when present; otherwise count stanzas.

---

### Step 0 — OCR Cleanup (run before any other step)

OCR-sourced files frequently contain artifacts that must be removed **before** parsing block structure. Failure to clean first causes spurious blocks and incorrect ID counts.

#### Standalone line numbers
Many scanned texts embed page or folio line-numbers as standalone paragraphs:

```
1

सुगतान् ससुतान् सधर्मकायान्...

2

प्रणिपत्यादरतोऽखिलांश्च वन्द्यान्।
```

These number-only blocks (`^\d+\s*$`) are **not content** — remove them entirely. Do not assign block IDs to them.

Detection pattern (Python): `re.compile(r'^\d+\s*(?:\^[\w-]+)?\s*$')`

#### Leading ordinal prefixes on content blocks

OCR or copy-paste from printed editions sometimes prepends a number followed by a period or parenthesis. **Do not strip these in Step 0.** Leave them in place until Step 3 (indexing), because on verse blocks the number may be the source's own verse number — stripping it early loses the information needed to assign the correct `^C-V`.

**At indexing time (Step 3)**, for each prefixed non-heading line:

1. **Is the block a verse?** — Read the prefix as the source verse number. Use it to set `V` in `^C-V`. If the same number appears on two consecutive verse blocks, the second gets `^C-Vx1` (see *Interpolated / extra verses* above). After the ID is assigned, remove the prefix from the rendered line.
2. **Is the block front matter, pre-title, or back matter?** — The number carries no indexing meaning. Remove the prefix and assign the zone ID normally.
3. **Is the block a heading (`##` / `###`)?** — Do not touch. The number is an intentional structural label.

| Content zone | When to strip | Notes |
|---|---|---|
| Verse (`^N-V`) | After reading as verse number | Informs `V`; strip after ID is set |
| Front matter / pre-title / back matter | At indexing time | No indexing value; strip and assign zone ID |
| `##` / `###` heading | **Never** | Preserve exactly |

Detection pattern (Python — apply only to non-heading lines after ID assignment): `re.sub(r'^\d+[.)]\s*', '', line)`

#### Other OCR artifacts to remove
- Stray characters on Sanskrit syllables from PDF extraction.
- Hyphenation artifacts at line breaks.
- Page headers/footers repeated in the text body (e.g. `-116-`, `[p. 42]`).

#### Block boundary after cleanup
After removal, collapse any sequences of multiple blank lines into a single blank line. A single blank line is the only block separator.

---

### Step 1 — Read and identify structure semantically

**Heading position alone is not sufficient to determine a block's role.** A prose block or verse appearing after a heading may belong to that heading's section, or it may be transitional material, a colophon, or chapter intro that looks like body content. Read the content to confirm.

#### 1a — Read the full text
Read the file in full before assigning any IDs.

#### 1b — Identify each block's content role by reading it
For every block (verse, prose line, or standalone phrase), determine its role:

- **Pre-title** (`^T-N`): content physically before the `#` title heading.
- **Front matter** (`^I-N`…): content whose topic is the author's own introduction, maṅgala, dedication, or statement of purpose — regardless of whether it sits under an explicit heading. Does NOT include the first verse of Chapter 1 even if no `##` heading separates them.
- **Chapter intro** (`^C-I`…): prose or verse at the start of a chapter, before the first numbered verse, that introduces the chapter topic. Identified by content, not position.
- **Verse** (`^C-V`): the metrically defined stanzas of the root text. Use `॥V॥` markers where present; otherwise identify by metre and content.
- **Chapter colophon** (`^C-a`…): Sanskrit closing phrase after the last verse of a chapter (e.g. ending `परिच्छेदः।`). Often has no heading and is easily mistaken for body content — read it to confirm it closes the chapter rather than continuing it.
- **Book colophon** (`^a`…): closing phrase(s) after the final chapter (e.g. `समाप्तः`, `कृतिः`, `इति`).

#### 1c — Note any ambiguous blocks
If a block's role is genuinely unclear after reading, add an editorial note `[Ed: role uncertain — treated as X]` inline and flag it for human review.

#### 1d — Audit existing IDs
Note any existing block IDs and whether they follow the convention above.

---

### Step 2 — Apply heading IDs

- `#` book title → `^0` (if book is root) or no ID (if collection).
- `##`/`###` front matter headings → `^I-0`, `^II-0`… in order of appearance.
- `##`/`###` chapter headings → `^N-0` where N matches the chapter number.

---

### Step 3 — Apply content IDs

#### Front matter
- Content under front matter headings: `^I-1`, `^I-2`… (reset for each Roman section).
- If front matter has no sub-heading, use `^I`, `^II`… for standalone items.

#### Chapter content
Scan each chapter in order:

1. **Chapter intro** (prose/verse before the first numbered verse): assign `^N-I`, `^N-II`…
2. **Verses**: extract verse number from `॥V॥` marker if present; otherwise count stanzas from 1.
   Assign `^N-V`.
3. **Chapter colophon** (line(s) after the last verse, before the next `##` heading):
   assign `^N-a`, `^N-b`… in order.

#### Book back matter
Lines after the final chapter's last verse/colophon that close the whole text:
assign `^a`, `^b`…

---

### Step 4 — Verse formatting

Each Sanskrit verse stanza:
- Two half-verses (hemistichs) on separate lines.
- Block ID on the last line of the stanza, preceded by a single space.
- One blank line between stanzas.

```
सुगतान् ससुतान् सधर्मकायान् प्रणिपत्यादरतोऽखिलांश्च वन्द्यान्। 
सुगतात्मजसंवरावतारं कथयिष्यामि यथागमं समासात्॥ ^1-1
```

---

### Dos and Don'ts

- **DO** derive verse numbers from `॥N॥` markers; do not renumber based on your own count unless markers are absent. The last segment of a verse ID **must match the actual verse number in the source text** — this is what makes root-text IDs citable. This is different from commentaries, where the last index is our own sequential counter with no source to match.
- **DON'T** use a sequential counter for verse IDs. Root text: last index = source verse number. Commentary: last index = own counter.
- **DO** treat chapter colophon lines as back matter even if they contain verse-like Sanskrit.
- **DO** assign `^I-0` etc. to front matter sections that currently use `^0-0`, `^0-1`…
- **DON'T** assign a block's zone (front matter / verse / colophon) based on its position under a heading alone — read the Sanskrit to confirm its role.
- **DON'T** apply this skill to commentaries or translations — use `format-commentary` instead.
- **DON'T** use more than 3 segments for verse IDs (`^C-S-V` max).
- **DON'T** put block IDs inside headings — only on content lines and heading lines per the table above.
- **DON'T** assign IDs to standalone OCR line-number lines — remove them in Step 0 before parsing.
- **DON'T** assign IDs to transclusion lines (`![[...]]`). These are references to other files and must be left exactly as-is.
- **DO** collapse multiple consecutive blank lines to a single blank before parsing block boundaries.
- **DON'T** use a bare `^C-Vx` for interpolated verses — always write `^C-Vx1` (counter starts at 1, even for a single interpolation).
- **DON'T** determine a block's zone by which `##` heading it sits under — determine it by content. A book colophon (`समाप्त`, `कृति`, `इति`) gets `^a`, `^b`… even if it physically appears inside the last chapter's heading section and no `##` heading separates it.
- **DON'T** write `^a-1` for a standalone book back matter block with no section heading — the format is `^a`, `^b`… (no trailing number). **Exception**: if a `## Heading ^a-0` exists above the block, treat it like front matter and number the content `^a-1`, `^a-2`… (same pattern as `^I-0` → `^I-1`, `^I-2`). Likewise, content under `## Heading ^b-0` gets `^b-1`, `^b-2`, `^b-3`…

---

## Mode 3 — Liturgy notes — stamp the inbox and prepare sources

Stamps IDs onto expert-segmented notes in `$INBOX` and writes the prepared copies to `$SOURCE_TEXTS`, with a health check.

`$WORK/` holds liturgy notes whose **TOC (headings) and segmentation
(blank-line-separated blocks) are already correct** — a domain expert made
every judgment call. The only thing missing is an addressable id per
heading and per segment. That job is fully mechanical, so it is a script,
not a judgment call, and not a subagent:

```
$SYSTEM/scripts/block_ids.py
```

**Never edit the text.** No splitting, merging, reordering, re-wrapping,
retitling, renumbering, or "fixing" of the expert's segmentation or
headings — not even something that looks like an obvious defect. If a file
looks wrong, report it and stop; correcting it is the expert's call, made
outside this pipeline.

### Format

```
## ༄༅། །Title              ^0
### Section k               ^k-0     a heading is "segment 0" of its section
<segment>                  ^k-1
#### Subsection j           ^k-j-0
<segment>                  ^k-j-1
```

- Flat texts (no `##` anywhere) number straight through: `^1`, `^2`, …
- Segments under the H1 *before* the first `##` get `^0-1`, `^0-2`, …
- A text with no headings at all numbers from `^1` (its title line is
  simply segment 1).
- The id goes on the **last line** of its unit, preceded by exactly one
  space, appended verbatim — a line already ending in a space keeps it, so
  the id is exactly reversible.
- Obsidian block ids allow **only digits, letters and hyphens**. Never a
  dot. `^2-1-1`, not `^2.1.1`.

### Workflow

Run from the vault root. Confirm the tree is clean first — the Obsidian
git plugin auto-commits every few minutes, so pin a baseline rather than
trusting floating HEAD:

```bash
git status --porcelain -- $WORK/ $SOURCE_TEXTS/
BASE=$(git rev-parse HEAD)
```

**1. Plan (writes nothing).** Classify every file and confirm the counts
match what the expert expects:

```bash
python3 $SYSTEM/scripts/block_ids.py plan 0-INBOX
```

Add `-v` to print the full id map for one file. Any `ABORT` line is a file
the parser refuses — read the reason, resolve it with the user, and never
force it through.

**2. Stamp.** Sources are read-only; stamped copies are written to
`$SOURCE_TEXTS/`:

```bash
python3 $SYSTEM/scripts/block_ids.py stamp 0-INBOX --out-dir $SOURCES/Text
```

`stamp` asserts the round-trip *before every individual write* and skips
any file that fails, so a bad parse can never produce a written file. A
source that already carries ids is refused unless you pass `--restamp`.

**3. Verify.** Non-negotiable, every run:

```bash
python3 $SYSTEM/scripts/block_ids.py verify $SOURCES/Text --src-dir 0-INBOX
```

Must print `0 FAILED`. It checks that frontmatter is byte-identical to the
source, that the body is byte-identical once ids are stripped, that every
heading and segment is stamped exactly once, and that no id is duplicated
or stranded mid-segment. On failure, delete the output and fix the script
— never hand-edit a stamped file.

**4. Report.** Per run: files stamped, type breakdown, total ids, verify
result, and any aborted file with its reason.

### The contract

`strip(stamp(x)) == x`, byte for byte — trailing whitespace, blank runs,
and a missing final newline all preserved. This is what makes "the
segmentation is intact" a proven property rather than a promise, and it is
why `strip` exists as a command. To re-check it by hand at any time:

```bash
python3 $SYSTEM/scripts/block_ids.py strip "$SOURCE_TEXTS/<name>.md" \
  | diff - "$WORK/<name>.md" && echo IDENTICAL
```

### Linting after human edits

Experts do edit stamped notes in Obsidian, and vault-backup commits sync
those edits in. That easily breaks ids — stranded mid-block, deleted, or
missing the space before `^`. `lint` finds it without needing a source:

```bash
python3 $SYSTEM/scripts/block_ids.py lint $SOURCES/Text
```

Report what it finds. Never silently re-stamp: if the expert resegmented a
text, every downstream id shifts, and whether to accept that renumbering
is their decision.

### What the script refuses, and why

Each of these aborts one file with a reason rather than guessing:

- more than one H1, or an H1 that is not the first thing in the body
- an H3 before any H2, or a heading deeper than `###`
- an H2 with **both** direct segments and H3 children — the id scheme
  cannot express that unambiguously; the fix is to give those loose
  segments their own `###`
- missing or unterminated frontmatter
- a source that already carries ids (without `--restamp`)

### Corpus state (surveyed 2026-08-26)

103 files, 2,039 segments, 128 headings → **2,167 ids**. Every file has at
most one H1 and it is always the title, so real TOC levels are `##` and
`###` only; nesting never goes deeper than `###`.

| Type | Shape | Files |
|---|---|---|
| A | H1 title only, no TOC | 95 |
| B | H1 + H2 | 5 |
| C | H1 + H2 + H3 | 2 |
| D | no headings at all | 1 |

Quirks that are **source truth, not defects** — preserve them:

- ~1,225 lines carry trailing whitespace, spread across all line
  positions. Genuine source noise. Never `rstrip`.
- 14 "blank" lines are a lone space; they must count as separators.
- 27 separators are double-blank; they must not create empty segments.
- 85 of 103 files have no final newline.
- `བཀའ་ཐང་བསྡུས་པ།` has a legitimate 79-line segment.

### Downstream, not yet updated

**`$SYSTEM/CLAUDE.md` §2 currently instructs agents "Notes carry no block
IDs … Do not add `^chapter-verse` anchors."** That directive is superseded
by this skill and will otherwise cause an agent to undo this work — it
needs rewriting. `README.md` ("What a source note contains") and
`$SYSTEM/scripts/build_payloads.py` say the same thing and are equally
stale. Note that block ids are what the pipeline repo's
`tools/parser/parser.py` derives spans from, so stamping them is what
makes that standard parser able to read these notes at all.
`$SOURCES/liturgy-catalog.json`
is also stale — 100 entries, none of whose `file` values match the current
103 inbox filenames (the catalog stores names truncated before the final
`།`). Flag both before any upload; do not quietly rewrite them as part of
a stamping run.

---

## Mode 4 — Commentary — verses and prose only

The narrow pass when headings are not in scope.

This skill tags every segment of a segmented Tibetan commentary file — each root-text quote line and each following commentary paragraph — with a trailing Obsidian block-reference id (` ^{chapter}-{n}`), so every block becomes individually linkable/transcludable. The chapter number comes from the nearest preceding root-text transclusion; the counter within that chapter increments across every segment in reading order and only resets when the transclusion's chapter number changes. Segments that appear before any transclusion has occurred (no root text transcluded yet — e.g. front matter, homage, or introductory commentary) are tagged as chapter `0` (`^0-1`, `^0-2`, ...) rather than being skipped, so every taggable segment in the file always ends up with an id. Correct output preserves every existing line, character, and line ending exactly — it only appends an id to the end of qualifying lines.

---

### Inputs

- `file` — path to a `*_segmented.md` commentary file under `$COMMENTARIES/Transcluded/` (or similar). It does not need to already contain a transclusion — if it has none at all, every taggable segment is tagged under chapter `0`.

### Output

- The same `file` modified in place (or a caller-specified output path), with a block id appended to the end of every qualifying line. No lines are added or removed; total line count is unchanged.

---

### Output file format

Given input (note: the first two lines appear *before* any transclusion):

```
མཚན་གྱི་དོན།

> རྒྱ་གར་སྐད་དུ། ...

![[bo-བློ་ལྡན་ཤེས་རབ།#^1-1]]
> བདེ་གཤེགས་ཆོས་ཀྱི་སྐུ་མངའ་སྲས་བཅས་དང་། །ཕྱག་འོས་ཀུན་ལའང་གུས་པས་ཕྱག་འཚལ་ཏེ། །

ཞེས་ཏེ་བདེ་གཤེགས་... (commentary paragraph)

གཉིས་པ་(བཤད་པར་དམ་བཅའ་བ་)ནི།
```

Output:

```
མཚན་གྱི་དོན། ^0-1

> རྒྱ་གར་སྐད་དུ། ... ^0-2

![[bo-བློ་ལྡན་ཤེས་རབ།#^1-1]]
> བདེ་གཤེགས་ཆོས་ཀྱི་སྐུ་མངའ་སྲས་བཅས་དང་། །ཕྱག་འོས་ཀུན་ལའང་གུས་པས་ཕྱག་འཚལ་ཏེ། ། ^1-1

ཞེས་ཏེ་བདེ་གཤེགས་... (commentary paragraph) ^1-2

གཉིས་པ་(བཤད་པར་དམ་བཅའ་བ་)ནི། ^1-3
```

Note how the two segments before the first transclusion get `^0-1` and `^0-2` (chapter `0`), and the counter resets to 1 as soon as the real chapter `1` begins at the first transclusion.

---

### Rules

1. Transclusion lines (`![[...]]`) are never modified and never receive an id.
2. The "chapter" number is the integer before the dash in the transclusion's block ref (`#^1-1` → chapter `1`, `#^2-1` → chapter `2`).
3. Before the first transclusion in the file, the chapter is `0` — segments here (front matter, homage, introductory commentary with no root text transcluded yet) are tagged `^0-1`, `^0-2`, ... rather than left untagged.
4. A per-chapter counter starts at 1 the first time that chapter number is seen (including chapter `0` at the very start of the file), and resets to 1 only when a later transclusion's chapter number differs from the current one. It does not reset on every transclusion — multiple transclusions within the same chapter (e.g. `#^1-2`, `#^1-3`) continue the same running counter.
5. Every non-blank, non-transclusion, non-heading line gets ` ^{chapter}-{counter}` appended to its end, from the very first content line of the file onward; the counter increments after each tagged line. This includes root-quote lines (`> ...`) and commentary paragraphs alike — everything in reading order gets the next sequential id within its chapter.
6. YAML frontmatter, blank lines, and markdown headings (`#`, `##`, ...) are left untouched and do not consume a counter value.
7. Idempotent: lines that already end with a block id (matching `\s\^\d+-\d+\s*$`) are skipped, so re-running on an already-tagged file is a no-op.
8. Original line endings (CRLF or LF) and total line count must be preserved — ids are appended to existing lines only, never inserted as new lines.
9. Do not hand-edit ids with the Edit tool for bulk tagging — always use `apply.py` so the counter logic stays consistent across the whole file. Manual edits are only for fixing a specific flagged anomaly after review.

---

### Procedure

The skill uses a helper script `apply.py` located in the same directory as this SKILL.md. Construct the path at runtime from the skill's own location.

1. **Audit first.** Run:
   ```bash
   python "<this-skill-dir>/apply.py" audit "<path-to-file.md>"
   ```
   This reports, per chapter, the first id, last id, and count of segments that would be tagged, without writing anything. Confirm the chapter numbers and counts look plausible (e.g. match the expected number of chapters in the root text) before applying.

2. **Dry-run to a scratch copy.** Copy the target file to a scratch/output location and run:
   ```bash
   python "<this-skill-dir>/apply.py" apply "<scratch-copy.md>"
   ```
   Do not write directly to the vault file on the first pass.

3. **Spot-check the output.** Read the first ~80 lines and at least one chapter boundary (where the chapter number changes) to confirm ids look right and no root-quote or commentary line was skipped or double-tagged.

4. **Verify idempotency.** Run `apply.py apply` a second time on its own output and confirm the file is byte-identical (no diff). This confirms the script won't double-tag if run again later.

5. **Verify line count is unchanged.** Compare `wc -l` on the original file and the tagged output — they must match exactly.

6. **Write the result to the real file.** Once verified, overwrite the actual `file` in the vault with the tagged content (or run `apply.py apply "<path-to-file.md>"` directly on it once confidence is established).

---

### Completion check

- [ ] `apply.py audit` was run first and its chapter/count report reviewed before any file was modified
- [ ] Output was dry-run to a scratch copy before touching the vault file
- [ ] First ~80 lines and at least one chapter boundary spot-checked in the output
- [ ] Idempotency verified (second run on the tagged output produces no diff)
- [ ] Total line count of the output matches the original file
- [ ] No transclusion line, blank line, heading, or frontmatter line was modified
- [ ] Final tagged file written to the correct vault path
