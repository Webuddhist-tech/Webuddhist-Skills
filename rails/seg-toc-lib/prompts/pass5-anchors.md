# Pass 5 — Anchor every node in the text (+ frame sections)

You are an expert in classical Tibetan Buddhist commentaries and their ས་བཅད (sa bcad).

You receive:
- a finished, QC-clean TOC tree (`* 2.2.1 title` lines), and
- the commentary it was extracted from.

Your task: for **every** tree node, find the place in the commentary where that node's
section **begins**, and copy the opening words found there verbatim into the node's line
as `[[context]]`. Then add the editorial **frame** nodes for the front and back matter.
A deterministic script later inserts each heading at the start of the block that contains
its context, so the context only has to point at the right spot — it is never copied into
the text.

## Where a node begins (the convention of the vault's human-edited files)

Read the text in order and keep a cursor: every node begins **after** the node before it
in the tree.

**Exception — parts treated in a different order than announced.** Sometimes a
commentary announces its parts as A, B, C, D but then explains them as B, D, C, A. Do not
force the tree's order onto the text: anchor **each** node where its own section really
begins (searching within its parent's section), even if that is before an elder
sibling's anchor. Keep the tree lines and numbering as they are — `commentary-toc-ingest`
reorders the siblings to the text's order (keeping each node's title and its announced
ID) and reports the change.

1. **A node with children** begins at its own **division announcement** — the sentence
   that names it and counts its parts:
   `གཉིས་པ་སྐུའི་རྣམ་པའི་སྒོ་ནས་བསྟོད་པ་ལ་གཉིས། …`, `དང་པོ་ལ་གཉིས། …`, `དང་པོ་ལ་དྲུག …`
2. **The first top-level node (1)** begins at the sentence that announces the work's
   top-level division (`… འཆད་པ་ལ་གསུམ། མདོར་བསྟན་པ། རྒྱས་པར་བཤད་པ། …`), because that
   announcement opens the body of the commentary. Not at the author's opening verses.
3. **A first child (`….1`)** begins at its own opener — `དང་པོ་ནི།`, or `དང་པོ་ལ་ N།` when
   it is itself divided. (It usually sits in the same sentence run as its parent's
   announcement; that is expected — the script stacks the two headings.)
4. **Any other node** begins at its opener: the ordinal + title restated
   (`གཉིས་པ་ … ནི།`, `(བཞི་པ་) …`, `གསུམ་པ་ … ལ་ N།`), even when the line holds nothing but
   that opener and the quoted root verse follows.
5. **Never** anchor a node on the place where its title is merely *listed* inside its
   parent's enumeration (a dkar-chag listing several titles in a row). The node's own
   opener comes later — find that one.
6. If a node has no explicit opener (the commentator moves on silently), anchor on the
   first words that start treating its topic (often the quoted root verse).

## Frame nodes (editorial sections outside the sa bcad)

Add these lines **only when the text has that part**, each with its `[[context]]`.
Front matter comes before node 1; back matter after the last tree node.

| Line to add | Where it begins |
|---|---|
| `* I. མཆོད་བརྗོད།` | the first words after the title line: the homage (`ན་མོ་ …`), the author's salutation verses, the promise to compose |
| `* II. <title>` | a second introductory section between the homage and node 1 that is **not** part of the tree — e.g. the source or class of the text (`… རྒྱུད་ … ཁུངས་ …`), an overview of the outline, a preliminary practice. Title it with the commentary's own words for it (e.g. `རྒྱུད་ཀྱི་ཁུངས་བསྟན་པ།`) |
| `* a. བསྔོ་བ།` | the author's closing dedication or aspiration **verses**, often introduced by `སྨྲས་པ།`, after the last section's explanation has ended |
| `* b. མཇུག་བྱང།` | the colophon (see below) — same context as its first child |
| `* b.1 འགྱུར་བྱང།` | only if there is a **translation / transmission** colophon (who translated or handed down the root: `… གྱིས་བསྒྱུར་བ།`, `… ནས་བརྒྱུད་པ།`) |
| `* b.1 མཛད་བྱང།` (or `b.2` after `འགྱུར་བྱང།`) | the **author's** colophon |

If there is a colophon but no dedication verses, the colophon takes `a.` / `a.1` (`a.2`)
instead of `b.` / `b.1` (`b.2`).

**Where the colophon begins.** The first words of the sentence in which the author (or
editor) speaks *about the work itself*: names it, names himself, says he composed /
wrote / noted it down — typically `ཞེས་ <name of the work> … འདི་ནི། … གྱིས་ … སྦྱར་བའོ།`,
`ཅེས་ … འདི་ཡང་ … ས་སྨྲས་པའོ།`, `ཞེས་ … མིང་པས་སོ།`, `ཞེས་པའང་ … བྲིས་པ།`, or a closing
`<title of the root/commentary> … རྫོགས་སོ།`. A `ཞེས་/ཅེས་` that only closes a quotation
inside the last explanation is **not** the colophon. The last explanation (the benefit
verses, the final summary) always ends **before** the colophon begins.

## Copying the context

- Copy the **first 12–20 syllables** starting exactly at the node's beginning,
  **character for character** — same spelling, same tshegs and shads, same spaces
  (`། །` stays `། །`). Do not normalise, do not fix spelling, do not skip brackets.
- The context must be unique enough to find in order: if the opener is short and
  repeated (`དང་པོ་ནི།`), include the words that follow it.

## Output

Rewrite the tree with every node line as `* <id> <title> [[<context>]]` (titles and
numbering unchanged), frame lines added, nothing else changed. Keep the
`## དཀར་ཆག / Table of Contents` header. Write the whole tree to the output path you are
given. If a node truly cannot be found, write `[[?]]` for it.
