# Prose grouping — root-text-group (form `prose`)

Produces the `prose` version of a root text written mainly in prose: a treatise, a sādhana
or ritual manual, a letter. First draft (2026-10) — no editor-checked reference yet; the
rules below are what the editors' feedback will refine.

You receive the body of a Tibetan root text already cut into units. Each line is one unit:

- `S<n>  <text>` — a **prose sentence**, cut at a final verb (`…འོ།` `…སོ།` `…ཏོ།` `…ནོ།`
  `…ཤོག` `…ཅིག` `…ཞེ་ན།`) or, rarely, at 200 syllables.
- `V<n>  <text>` — one **verse line** (pāda) of a verse passage inside the prose: the
  homage, a quoted scripture, a praise, a song.

`n` runs through the whole file. Headings (`## …`) divide it; a block never crosses one.
Lines marked `[frame]` (title, homage, colophons) are not part of any block and are not
numbered. `[^n]` markers are footnote references — ignore them for meaning.

A line `¶` is a **paragraph break of the printed edition**. Its editors broke the text by
sense (at the end of a chapter, a new topic or step, a change of speaker), so a block
never crosses `¶` — the script refuses it. Your job is only to cut further INSIDE each
printed paragraph, where it holds more than one point or step.

Your task: group the units into blocks as a careful editor of a classical prose text
would — **one paragraph per point, one stanza per stanza**.

## Prose — paragraphs (`S` lines)

1. **A paragraph is one point or one step.** In a treatise: a claim with its reasons and
   examples, a definition, an objection, an answer. In a ritual or sādhana: one step of the
   practice — what to visualize, the mantra to recite, the gesture, and its short rubric.
   Typical size 1–5 sentences; split a run longer than about 8 sentences where the topic
   turns.
2. **A new paragraph starts** where the text turns to a new point: at a discourse marker
   that opens a step or topic — `དེ་ནས་`, `དེ་ལ་`, `དེ་ཡང་`, `གཞན་ཡང་`, `ད་ནི་`,
   `དེ་ལྟར་`, `འདི་ལ་`, an ordinal (`དང་པོ་`, `གཉིས་པ་ནི་`) — or at a new subject.
   Not every `དེ་ནས་` must open a paragraph: short consecutive actions of one step stay
   together.
3. **An objection and its answer are separate paragraphs.** The objection — an opponent's
   view or doubt — ends at `…ཞེ་ན།` / `…སྙམ་ན།`; the answer (often `…མ་ཡིན་ཏེ།`,
   `བདེན་མོད་ཀྱི།`, `དེ་ནི་…`) starts the next paragraph. A **teaching question** that the
   author asks to introduce a list or a definition (`…གང་ཞེ་ན།`, `…ཅི་ཞེ་ན།`, "what are
   the five?") stays in one paragraph with its answer.
4. **A mantra stays with its step.** A mantra line and the instruction around it (`…ཞེས་
   པས་…`, `…ཞེས་བཟླས་སོ།`) belong to the same paragraph.
5. **A quotation's lead-in and close stay prose.** `ཇི་སྐད་དུ།`, `…ལས།`, `…ལས་ཀྱང་།` before
   a quoted verse end the paragraph before it; `ཞེས་གསུངས་སོ།` / `ཞེས་བྱ་བ་ལ་སོགས་པ་
   གསུངས་སོ།` after it opens the next paragraph (it is prose, numbered `S`). When there is
   no prose to join — a `¶` or a heading on the other side — the lead-in or close **stands
   as its own block** (`དེ་བས་ན།`, `ཞེས་གསུངས་པས་སོ། །`). Never put it into the stanza
   (editors' choice, 2026-10-09).
5a. **Lists follow the text.** Whether a list whose items are full sentences (the five
   wisdoms, the five kinds of touch) stays one paragraph or gets one paragraph per item is
   decided by how this text presents it — there is no fixed length or count. Judge each
   text on its own (editors, 2026-10-09: "གཙོ་བོ་ཡིག་ཆ་སོ་སོའི་གནས་སྟངས་ལ་གཞི་འཛིན་དགོས།").

## Verse — stanzas (`V` lines)

6. Group verse lines as in `stanza-grouping.md`: **by sense, with no default length** —
   a stanza ends where a sentence or petition ends (a connective — `…སྟེ།` `…ནས།` `…ལ།`
   `…དང་།` — means it goes on); one stanza holds one point; a short lead line (`ན་མོ།`,
   `ཧཱུཾ།`) attaches forward. A passage of 2 or 3 lines is one block.

## Always

7. **Never mix `S` and `V` lines in one block** — the script refuses it.
8. Never reorder or skip a unit; every unit belongs to exactly one block; blocks never
   cross a heading or a `¶`.

Output: write ONLY a JSON object to the output path:

```json
{"stanzas": [[1, 4], [5, 7], …],
 "notes": {"<first unit of a block worth a word>": "one short English reason"}}
```

`[a, b]` = units a..b inclusive, all blocks in order, covering every unit exactly once.
Notes are optional for prose paragraphs; give one for every verse block of 1–2 lines or
more than 6, and for any paragraph you split or joined against rule 2.
