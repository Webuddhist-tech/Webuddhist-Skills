# Stanza grouping (sense mode) — root-text-group

Produces the `free` version, the one version every verse root text gets: blocks by sense,
with no fixed length. (The earlier rule — four lines by default — scored block-boundary
F1 0.95 on 10 Liturgy-rails texts; this sense-only rule has not been benchmarked yet.)

You receive a Tibetan verse text (a prayer, praise, aspiration, liturgy, ritual or treatise
in verse) already cut into lines. Each line is `P<n>  <text>`. Lines end with `། །`, `ག །`,
`༔`, `ཿ` or similar. `[^n]` markers are footnote references — ignore them for meaning.

Your task: group the lines into blocks as a careful editor would — **one block per unit of
sense**. If the input has headings (`## …`), a block never crosses one — group each
section separately. Lines marked `[frame]` (titles, homage, colophons) are not part of any
block and are not numbered.

**A line `¶` is a paragraph break of the printed edition.** Its editors broke the text by
sense, so a block never crosses `¶` (the script refuses it): the line before `¶` always
ends a block. Within a paragraph, group as below.

There is **no default length**. Do not count lines: a block is as long as its unit of
sense. Many verse units happen to be four lines (in edited chanting texts most stanzas
are), but that is a result of the sense, never a reason for a boundary.

1. **A block ends where a sentence or petition ends.** Finite endings close a unit:
   `…ཤོག`, `…གསོལ་བ་འདེབས།`, `…ཕྱག་འཚལ་ལོ།`, `…མཛད་དུ་གསོལ།`, `…བྱིན་གྱིས་རློབས།`, `…འོ།`,
   `…བྱ།`, `…བསམ།`, an imperative or optative. Connective endings (`…སྟེ།` `…ཏེ།` `…ནས།`
   `…ཞིང་།` `…ཅིང་།` `…ལ།` `…ནི།`, genitive `…གི།` `…ཡི།` `…འི།`, `…དང་།`) mean the sentence
   continues: the block goes on to where it closes.
2. **One block, one point.** A block holds one sentence, or a few short sentences that make
   a single point together — one deity's description, one step of a visualization, the
   items of one list (`…དང་། …དང་། …ལའོ།`), a question with its answer. A new subject, a new
   step, or a turn such as `དེ་ནས་`, `དེ་ལྟར་`, `ཡང་`, `གཞན་ཡང་` starts a new block.
3. **A long sentence may be split** where it runs over about eight lines (a long list, a
   chain of clauses): cut where one item or sub-step is complete, never in the middle of an
   item.
4. **A refrain or repeated petition line** that closes each stanza belongs to that stanza.
5. **Lead lines attach forward.** A short invocation or exclamation (`ན་མོ། …`, `ཨེ་མ་ཧོ།`,
   `ཀྱེ༔`, `ཧཱུཾ༔`, a homage formula introducing the stanza) belongs to the block it
   introduces, not to its own block and not to the block before.
6. **Prose rubrics stand alone.** A line that is not verse but an instruction or a
   colophon-like remark (`ཞེས་ལན་གསུམ།`, `…ཞེས་པ་འདི་ནི་…`, `ཅེས་…གྱིས་སྦྱར་བའོ།`, a chapter's
   closing line `…ལེའུ་…པའོ།`) is its own block. A mantra stays with the line that
   introduces or labels it.
7. Never reorder or skip a line; every line belongs to exactly one block; no block crosses
   a `¶` or a heading.

Output: write ONLY a JSON object to the output path:

```json
{"stanzas": [[1, 4], [5, 10], …],
 "notes": {"<first line number of a block>": "one short English reason"}}
```

`[a, b]` = lines a..b inclusive, all blocks in order, covering every line exactly once.
Give a note for every block of 1–2 lines or of more than 6 lines, and for any block whose
boundary you were unsure of.
