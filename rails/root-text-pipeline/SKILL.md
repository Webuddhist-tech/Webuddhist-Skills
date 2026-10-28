---
name: root-text-pipeline
description: >
  Run the WHOLE root-text workflow on one Tibetan ROOT TEXT — a treatise, praise, ritual,
  sādhana, prayer or letter in its own voice, not a commentary: classify → segment → TOC
  extraction (if the text announces parts) → TOC ingest → grouping into stanzas /
  paragraphs → block IDs, with the checks between steps. Produces the vault's root-text
  layout: verse one pāda per line with stanzas as blocks; prose as paragraphs with its verse
  passages as stanzas; front matter and colophons under fixed frame headings; the text's own
  announced parts as headings; block IDs. Use for "process this root text", "segment and
  head this root text", "run the root-text workflow". Each step is also its own skill
  (root-text-classify … root-text-block-ids). Commentaries go to commentary-pipeline.
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-pipeline

Turns a root text that arrives as run-on text (in the printed edition's paragraphs, which it
keeps — Rule 6) into the layout of the vault's processed root texts (the BCA and Tārā root
files, the Liturgy-rails chants). Nothing is forced: a frame heading appears only when its
element is in the text, and a text that announces no parts gets no body headings (only
`གཞུང་དངོས།` to separate it from the front matter). The text itself is never changed —
every step checks it.

This skill only **orchestrates**. Each step is its own skill, with its own rules:

| # | Step skill | Does | Model? |
|---|---|---|---|
| 1 | `root-text-classify` | verse / prose / mixed — or commentary (stop) | no |
| 2 | `root-text-segment` | units (pādas / sentences), raw paragraph breaks, front matter and colophon frame | no |
| 3 | `root-text-toc-extract` | heading tree of the text's announced parts (passes 1–5) — only if it announces parts | yes |
| 4 | `root-text-toc-ingest` | the tree's top-level parts as headings | no |
| 5 | `root-text-group` | stanzas (verse) / paragraphs and stanzas (prose) | yes |
| 6 | `root-text-block-ids` | build the final file, stamp IDs, verify the text | no |

All steps call one library, `$SKILLS/seg-toc-lib/root_text_build.py`, which keeps
its state in the working folder (`state.json`), so the steps can be run one at a time.

---

## Inputs

| Input | Description |
|---|---|
| `source` | the root text, normally `$SOURCE_TEXTS/<id>.md` (or its copy in `$INBOX/root/`) — first line the title, then the text in the printed edition's paragraphs, footnote apparatus `[^n]: …` at the end (kept as is) |
| `id` | short id for the working folder (usually the file stem) |
| form *(optional)* | `auto` (default, from step 1); `verse` / `prose` forces it |

If the source is a commentary or the `id` is unclear, stop and ask.

## Output

| File | What |
|---|---|
| `$INBOX/<id>-root/prepared.md` · `group-in.md` · `state.json` | steps 2/4: units, frame and body headings, the grouping input (raw paragraph breaks marked `¶`) |
| `$INBOX/<id>-root/breaks-review.md` | only if any: raw paragraph breaks that end mid-sentence, not kept |
| `$WORK/TOC-<id>/toc-tree-<id>.md` | step 3: the anchored tree (only if the text announces parts) |
| `$INBOX/<id>-root/groups-free.json` · `final-free.md` | **verse form**, steps 5–6 |
| `$INBOX/<id>-root/groups-prose.json` · `final-prose.md` | **prose form**, steps 5–6 |

One version per text. The `$SOURCES/` file is replaced by it only after a human approves it.

---

## Output file format

```markdown
# ༄༅། །<title> ^0

## ཀླད་ཀྱི་དོན། ^I-0

༄༅༅། །རྒྱ་གར་སྐད་དུ། <Sanskrit title> ^I-1

བོད་སྐད་དུ། <Tibetan title> ^I-2

<homage> ཕྱག་འཚལ་ལོ། ། ^I-3

## <first part, or གཞུང་དངོས།> ^1-0

<pāda> །
<pāda> །
<pāda> །
<pāda> ། ^1-1

<prose paragraph on one line> ^1-2

## <next part> ^2-0
…

## མཇུག་བྱང། ^a-0

### མཛད་བྱང། ^a-1-0

<… མཛད་པ་རྫོགས་སོ།> ^a-1

### འགྱུར་བྱང། ^a-2-0

<… ལོ་ཙཱ་བ … བསྒྱུར་ … གཏན་ལ་ཕབ་པའོ།> ^a-2

[^1]: <footnotes exactly as in the source>
```

---

## Rules (across all steps)

1. **No character changes.** Only line breaks, block breaks, headings and IDs are added; each
   script asserts that the text (headings aside) is unchanged, footnotes included
   (`…ཀྱིས༌[^1]མཆོད…`).
2. **Frame headings by pattern only** (step 2), and only when the element is present — see
   `root-text-segment`. Same layout as the commentary frame.
3. **Body headings only where the text announces parts**, and only its top-level parts
   (steps 3–4). No candidates → no tree → `གཞུང་དངོས།`.
4. **One version per text:** `final-free.md` for a verse text, `final-prose.md` for a prose
   or mixed one. There is no fixed four-pāda śloka version.
5. **Never** let a block cross a heading; every unit belongs to exactly one block.
6. **Raw paragraph breaks are kept; we only cut inside them.** The source paragraphs are the
   printed edition's, and its editors broke by sense, not by page: checked on all 565
   Nalanda files against the Word books, 95% of page breaks fall inside a paragraph and 99%
   of paragraphs end at a sentence or verse-line end. A break that ends mid-sentence is not
   kept but listed for review. Headings may still fall inside a raw paragraph (about 30%).
   Details in `root-text-segment` and `root-text-group`.
7. Never stamp IDs into a file that is cited elsewhere without re-running what cites it.
8. **Models.** The workflows run on Gemini API calls (Gemini 3.8 Flash, thinking high) by
   default and on another model, as agents, only when the prompt explicitly asks
   (`$SKILLS/seg-toc-lib/SKILL.md`). **Exception for now:** the two root-text
   model steps (3 and 5) have no Gemini runner yet, so they run as isolated Claude subagents
   (`model: opus`, high effort) — say so in the report.
9. **Strict text gate.** Step 6 ends with `verify_text.py` against the source: letters and
   spacing identical, only breaks, headings and IDs added (one space between the shads of
   `། །`, none after it; no space at a line start or end).

---

## Procedure

Run the steps in order; after each, read its report and stop on anything listed under
"stop if" before going on.

1. **`root-text-classify`** on `<source>`. Stop if `commentary` (exit 1): ask the editor —
   a commentary goes to `commentary-pipeline`.
2. **`root-text-segment`** `<source>` → `$INBOX/<id>-root`. Check the report: frame
   elements found, raw breaks kept / flagged, the heading list.
3. **Does the text announce parts?** Look for `<topic> བཤད་བྱ་སྟེ།`, `<topic> ཆོ་ག་ནི།`,
   `དང་པོ་ … ནི།`, chapter closings `…ལེའུ་དང་པོའོ།`. If yes, run **`root-text-toc-extract`**
   on `$INBOX/<id>-root/prepared.md`. If pass 1 finds nothing, skip steps 3–4 (no tree).
4. **`root-text-toc-ingest`** with the anchored tree. Stop if `not placed` > 0.
5. **`root-text-group`**: split a long input, one isolated subagent per part, join.
6. **`root-text-block-ids`**: build, stamp IDs, verify. Stop if it refuses the grouping
   (mixes prose and verse, crosses a `¶` or a heading, or misses a unit) — fix the groups
   JSON and re-run.
7. **Report**: form, frame elements, body headings, raw breaks kept and flagged
   (`breaks-review.md`), block sizes and the notes on 1–2-line and 7+-line blocks. A human
   approves the file before it replaces the source.

---

## Completion check

- [ ] Step 1 returned `verse`, `prose` or `mixed` (not `commentary`); the form is in `state.json`
- [ ] Frame headings present exactly for the elements found (front matter / author / translators)
- [ ] Body headings: top-level parts only, `not placed: 0` — or none, if the text announces no parts
- [ ] One final file: `final-free.md` (verse) or `final-prose.md` (prose / mixed)
- [ ] Every unit in exactly one block; no block crosses a heading or a raw paragraph break (`¶`)
- [ ] Flagged raw breaks (`breaks-review.md`), if any, listed in the report
- [ ] Final file: text and footnotes unchanged — `verify_text.py` ✓ (letters and spacing), IDs stamped (`^0`, `^I-n`, `^N-n`, `^a-n`)
- [ ] Source in `$SOURCES/` untouched until a human approved the file
