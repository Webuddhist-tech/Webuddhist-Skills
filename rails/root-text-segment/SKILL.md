---
name: root-text-segment
description: >
  Step 2 of root-text-pipeline: cut a Tibetan root text into units — pādas for a verse text,
  sentences plus verse lines for a prose text — keeping the printed edition's paragraph
  breaks, and put the frame headings on it by pattern: front matter (Sanskrit / Chinese
  title, Tibetan title, homage) under ཀླད་ཀྱི་དོན། ^I-0, the colophons under མཇུག་བྱང། ^a-0
  with མཛད་བྱང། / འགྱུར་བྱང།. Writes the grouping input. Deterministic, no model; the text
  is verified unchanged. Use for "split the root text into pādas", "find the front matter
  and colophons", "prepare the root text for grouping".
profile: rails-vault
supersedes:
  - Nalanda-texts-rails/4-SYSTEM/Skills/root-text-segmentation/SKILL.md
---

# root-text-segment

---

## Inputs

| Input | Description |
|---|---|
| `source` | the root text (`$SOURCE_TEXTS/<id>.md` or `$INBOX/root/<id>.md`) |
| `id` | working folder `$INBOX/<id>-root` |
| `--form` *(optional)* | `auto` (default, as `root-text-classify`), `verse` or `prose` |
| `--front-title` / `--body-title` *(optional)* | defaults `ཀླད་ཀྱི་དོན།` / `གཞུང་དངོས།` (e.g. `--front-title མཚན་དོན་དང་འགྱུར་ཕྱག`) |

## Output

| File | What |
|---|---|
| `$INBOX/<id>-root/prepared.md` | one unit per block; title `# … ^0`; frame headings; `## གཞུང་དངོས། ^1-0` over the body (replaced by the tree's parts in `root-text-toc-ingest`) |
| `$INBOX/<id>-root/group-in.md` | numbered units for `root-text-group`: `P<n>` pāda, `S<n>` sentence, `V<n>` verse line inside prose; `[frame]` lines; `¶` at each kept raw paragraph break |
| `$INBOX/<id>-root/state.json` | form, unit types, kept breaks, settings — read by the later steps |
| `$INBOX/<id>-root/breaks-review.md` | only if any: raw breaks that end mid-sentence |

## Output file format

`group-in.md`:

```
## ཀླད་ཀྱི་དོན། ^I-0
[frame] ༄༅༅། །རྒྱ་གར་སྐད་དུ། …

## གཞུང་དངོས། ^1-0
P1  <pāda> །
P2  <pāda> །
¶
P3  <pāda> །
```

---

## Rules

1. **No character changes** — asserted before writing.
2. **Pādas** end at a shad (`།`) or tsheg-shad (`༔`) cluster before the next syllable; a
   footnote marker stays on the line it follows. (`༔` matters: terma texts cannot be split
   without it.)
3. **Prose units** (form `prose`, for prose and mixed texts) are **sentences**, cut at a final
   verb (`…འོ།` `…སོ།` `…ཏོ།` `…ནོ།` `…འགྲུབ་བོ།` `…ཤོག` `…ཅིག` `…ཞེ་ན།`, or at 200
   syllables), and **verse passages** inside — 4+ lines closed by `། །` in one metre (exact up
   to 9 syllables, ±1 up to 12, ±2 above; a loose run is refused when over a third of its
   lines end on a final verb: those are rubrics) — stay line by line (`V`).
4. **Raw paragraph breaks are kept.** A unit always ends at one, and `group-in.md` marks it
   `¶`. A paragraph that ends mid-sentence — no shad, or a connective (`…ཏེ།` `…ནས།`
   `…དང་།` `…ལས།` …) — is not kept: it goes to `breaks-review.md` for a person to check
   (about 40 such breaks in 35 of the 565 Nalanda files).
5. **Front matter by pattern only:** `རྒྱ་གར་སྐད་དུ། … བོད་སྐད་དུ། … ཕྱག་འཚལ་ལོ།` (a Chinese
   title, `རྒྱའི་སྐད་དུ།`, counts the same) → `## ཀླད་ཀྱི་དོན། ^I-0` with three frame blocks.
   Without language labels: the title repeated at the start (first 3 syllables) and, in
   prose, a homage before or after it. A verse text's lone homage line stays in the body.
6. **Colophons by wording:** the closing matter → `## མཇུག་བྱང། ^a-0`, each colophon a `###`
   sub-section in text order, starting at its own wording — author (`…མཛད་པ་རྫོགས་སོ།`,
   `…མཛད་པའི་<title>་རྫོགས་སོ།`) → `### མཛད་བྱང།`, translators (`…ལོ་ཙཱ་བ…`,
   `…བསྒྱུར་ཅིང / ཞིང / ནས / ཏེ`, `…གཏན་ལ་ཕབ`) → `### འགྱུར་བྱང།`. Closing verses in another
   metre stay in the body; verse after the translators' colophon (their dedication) stays
   inside it.

---

## Procedure

```bash
python $SKILLS/seg-toc-lib/root_text_build.py segment \
    "<source>" "$INBOX/<id>-root" [--form verse|prose]
```

Read the report line: units (pādas and metre, or sentences and verse lines), the frame
elements found, raw breaks kept / flagged, and the printed heading list. A flagged break →
mention it in the final report.

---

## Completion check

- [ ] Report line read; frame elements match what is in the text
- [ ] `prepared.md`, `group-in.md`, `state.json` written (text assertion passed)
- [ ] Flagged raw breaks (if any) noted for the report
