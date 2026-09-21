---
name: headings-not-content
description: >
  Keep markdown headings out of an edition's uploaded content and
  segmentation, and build the table of contents from them instead. Headings
  are editorial structure, not text: the parser must record each one for the
  TOC and emit no `type: "title"` segment. Covers the parser change, the span
  arithmetic a TOC section needs once headings are gone, and the pre-flight
  that must pass before any TOC is regenerated against an already-uploaded
  edition.

  Trigger this skill whenever heading handling in the ingest chain comes up —
  "the title is in the content", "remove the title segments", "regenerate the
  TOC", "why is the chapter heading a segment", "strip the heading numbers" —
  and before changing tools/parser/parser.py's heading branch.
profile: library-pipeline
---

# headings-not-content

**Policy, settled 2026-09-20: a markdown heading never appears in an
edition's `content`, and never becomes a segment.** Headings are editorial
structure added to the text. They belong to the table of contents, which
stores its own title strings, and nowhere else.

The headings stay in the source markdown. They are what the TOC builder
reads, and what a human navigates by. Only the uploaded payload is
heading-free.

---

## The parser change

`tools/parser/parser.py` is canonical. `reference/parser-heading-branch.py`
in this folder holds the three edited functions verbatim, as applied to the
BCA and liturgy vault forks — copy the shape, not the file, because those
forks carry their own divergences (`FORK(liturgy-rails)` markers).

**1. `_build_content_and_segmentation` records headings instead of emitting
them.** It returns a third value:

```python
if is_header:
    ...
    # `pos` is NOT advanced and no segment is appended, so the heading
    # leaves no trace in the uploaded content or segmentation.
    headings.append({"reference": ref_no_caret, "title": text, "pos": pos})
```

`pos` at that moment is the offset, in the heading-free content, where this
heading's body begins.

**2. `build_edition` hands the headings to `build_toc` in memory only** —
`return out_path, {**out, "_headings": headings}`. The written
`edition.json` is unchanged in shape; `_headings` is TOC input, not edition
data.

**3. `build_toc` reads the headings, not the segments.** A section's span is

```
[heading.pos, next heading of the same-or-higher level .pos)   # last one: to content end
```

with a fallback to the old title-segment scan when `_headings` is absent, so
an `edition.json` read back from disk still builds a TOC.

Note the span change: it used to be `[heading.end, next_heading.start)`,
which left the heading's own characters sitting between sections. With the
heading gone there is nothing in between, so one offset serves as both this
section's start and the previous section's end.

### A commentary parser needs one extra step

`parser_commentary.py` runs `_strip_verse_ids` after building the content,
which removes inline `^ref>` markers and remaps every span. Heading offsets
live in that same coordinate space and must be remapped too. Each heading's
`pos` is a segment-line boundary by construction, so it is always a key in
the existing `mapping` — assert that rather than guessing:

```python
for h in headings:
    assert h["pos"] in mapping, f"heading {h['reference']} at {h['pos']} is not a line boundary"
    h["pos"] = mapping[h["pos"]]
```

---

## Heading ordinals are display scaffolding — strip them

`## 1. ལེའུ་དང་པོ། ...` should read `## ལེའུ་དང་པོ། ...`. The number is
redundant once the TOC carries the structure, and it leaks into the TOC
section titles the backend stores. **The block ID must survive untouched.**

Two things make this safe to automate:

- **Require the block ID.** Numbered headings are everywhere in these vaults
  — day packages number session steps, docs number rules, rails notes number
  points. Only a heading carrying a heading block ID is a TOC node. Matching
  on the block ID targets exactly those and nothing else.
- **Match digits in any script.** Python's `\d` covers every Unicode decimal
  digit, so Devanagari `१०.` and Tibetan `༡༠.` strip like ASCII `10.`.
  Require the `.` — a bare leading number without it is part of the title.

`bodhisattvacharyavatara-rails/4-SYSTEM/scripts/strip_heading_numbers.py` is
the implementation, with `--dry-run` as the default posture.

---

## Before regenerating a TOC against an uploaded edition

A regenerated TOC is only valid if its spans refer to the content the backend
actually holds. **Parse the source and compare its `content` to the live
edition byte for byte first.**

If the markdown has drifted since upload, the TOC built from it carries spans
measured against a *different* string, and will silently point at the wrong
text. Drift is not hypothetical: of the ten BCA editions checked on
2026-09-20, three had drifted (−5, −22 and −627 characters). Reconcile those
— re-upload the content, or recover the source that was uploaded — before
touching their TOC.

`bodhisattvacharyavatara-rails/4-SYSTEM/scripts/title-segment-removal/preflight_toc.py`
does this check.

---

## Removing title segments from an already-uploaded edition

No re-upload needed. `PATCH /v2/editions/{id}/content` with
`{"type": "delete", "start": S, "end": E}` over the title segment's span
removes the text, DETACH-deletes the segment, and shifts every later span.

**Go bottom-up — descending by span start.** The backend's
`_adjust_span_for_delete` leaves a span strictly before the deleted range
untouched, so every op can use coordinates from a single snapshot with
nothing recomputed. Descending order also submits the largest offset first,
so a stale `content_length` fails the validator cleanly on call 1 instead of
corrupting an edition halfway through.

**A content PATCH is not idempotent.** A delete whose response was lost has
still been applied; re-sending it eats the *next* `E - S` characters. Never
retry a write. Re-read the target segment before each call instead — that
also makes the run resumable.

**Check the TOC sections.** `TableOfContentsSection` spans go through the
same adjust function and sit in the same `DETACH DELETE` label list as
segments, so a title span that fully covered a TOC section would destroy it.
Simulate first. Note that the branch *order* in `_adjust_span_for_delete`
matters: a zero-length span sitting exactly on a delete boundary is caught by
an earlier branch and survives, even though the "fully encompassed" test
would also match it. Paraphrasing that function gives wrong answers; vendor
it verbatim.

The full toolchain — snapshot, simulate, execute, compare — is
`bodhisattvacharyavatara-rails/4-SYSTEM/scripts/title-segment-removal/`.
