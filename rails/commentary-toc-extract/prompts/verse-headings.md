# Verse-keyed / top-level headings (for commentaries without a usable sa bcad)

Use this prompt **instead of passes 1–4** when the commentary is declared as
`headings: verses` or `headings: top` — i.e. it explains the root text verse by verse
(or in a few large parts) and either has no sa bcad, or its sa bcad is not what the
vault's editors use as headings. The output is an anchored tree in the same format as
pass 5, ready for `toc_tree_ingest.py`.

You receive:
- the **mode** (`verses` or `top`),
- the commentary,
- (for `verses`) the root text, so you can tell which root stanza each passage explains.

## Mode `verses` — one heading per root stanza

The editors' convention for a *verse-by-verse* commentary on the Praise to the
Twenty-One Tārās (adapt the stanza names for another root text):

```
* 1. <the commentary's own name for the praise proper, else བསྟོད་པ་དངོས།>
   * 1.1 ཕྱག་འཚལ་བ།            ← only if the opening homage line (ཨོཾ་རྗེ་བཙུན་མ་…ཕྱག་འཚལ་ལོ།)
                                   is quoted and explained on its own
   * 1.n ཕྱག་འཚལ་དང་པོ།  …  ཕྱག་འཚལ་ཉེར་གཅིག་པ།   ← one node per homage stanza, in order
* 2. <the commentary's own name for the next part, else ཕན་ཡོན།>
* 3. …
```

Rules:
1. **Top level (`1.`, `2.`, …)** = the parts the body really has, in order: the praise
   proper; then whatever the commentary treats as a separate part after the 21 homages —
   the mantra/application (`འཇུག་གི་དོན།`), the benefits (`ཕན་ཡོན།`), a summary of the
   meaning (`གཞུང་གི་དོན་བསྡུ་བ།`). Use the commentary's own words for each title when it
   names the part; otherwise the default in brackets above. Do **not** make top-level
   nodes for the author's opening verses, the dedication or the colophon — those are
   frame sections added separately.

   **Fixed rules for what counts as a separate part** (do not decide case by case):
   - A wrap-up or overview that follows the last stanza (`དེ་ལྟར་ན་…`, correspondences,
     enumerations of what the praise contains) stays **inside** the praise proper, under
     the last stanza node, unless the commentary announces it with its own title
     (`… བསྡུ་བ་ནི།`, `… དོན་བསྡུས་པ།`).
   - The benefits section is **always** its own part, beginning where the commentary
     turns to the root text's benefit verses or to their lead-in (`འཇུག་གི་དོན་…`,
     `ཕན་ཡོན་…`). Its title: the commentary's own phrase if it has one, else `ཕན་ཡོན།`.
     The root mantra verse, when the commentary treats it together with the benefits,
     belongs to this part (no separate part for it).
   - The commentary's explanation of the root text's **own colophon** (who spoke the
     praise, which tantra it comes from) stays **inside** the benefits part; it is not a
     top-level part and not a frame node (the frame `མཛད་བྱང།` is the commentator's own
     colophon).
   So a verse-by-verse commentary on this root text normally has exactly two parts:
   `1.` the praise proper and `2.` the benefits — more only when the commentary itself
   names a further part.
2. **Stanza nodes** use the fixed editorial titles `ཕྱག་འཚལ་<ordinal>།`:
   དང་པོ། གཉིས་པ། གསུམ་པ། བཞི་པ། ལྔ་པ། དྲུག་པ། བདུན་པ། བརྒྱད་པ། དགུ་པ། བཅུ་པ།
   བཅུ་གཅིག་པ། བཅུ་གཉིས་པ། བཅུ་གསུམ་པ། བཅུ་བཞི་པ། བཅོ་ལྔ་པ། བཅུ་དྲུག་པ། བཅུ་བདུན་པ།
   བཅོ་བརྒྱད་པ། བཅུ་དགུ་པ། ཉི་ཤུ་པ། ཉེར་གཅིག་པ། — not the commentary's own wording.
   The ordinal is the stanza's place among the 21 homage stanzas of the root text, never
   the node number: when `1.1` is `ཕྱག་འཚལ་བ།`, node `1.n` is stanza n−1 (`1.15` =
   `ཕྱག་འཚལ་བཅུ་བཞི་པ།`). Each ordinal is used exactly once, in the sequence above —
   check the finished list before writing it.
3. **Children of a stanza** only when the commentary itself splits its treatment of the
   stanza into named parts:
   - a recurring split used for every stanza, e.g. a word commentary followed by a
     visualisation (`ཚིག་འགྲེལ།` / `གསལ་འདེབས་ཚུལ།`) → give every stanza those two
     children (`1.n.1`, `1.n.2`), titled with the commentary's own label;
   - a one-off division of one stanza (`… ལ་བཞི། ཡི་གེའི་དོན། སྤྱིའི་དོན། སྦས་དོན། མཐར་ཐུག`)
     → children for that stanza only, titled as the commentary names them.
   A part after the stanzas (e.g. the mantra) may likewise get children if it is divided.
   Otherwise no children: do not invent sub-headings from the content.
4. **Node `1.` begins where the first stanza's treatment begins** (same anchor as `1.1`),
   not at preliminary remarks before it (the class of the tantra, the source of the text,
   an overview). Those preliminaries belong to the frame (`II.`, added by pass 5), never
   to the praise proper.
5. A stanza node begins where the treatment of that stanza begins: its ordinal lead-in
   if there is one (`ཚིགས་བཅད་གཉིས་པ་…`, `གཉིས་པ་ནི།`), else the first quoted words of
   the stanza, else the first words explaining it. Its first child begins at the same
   place unless the child has its own lead-in. A lead-in names the child (`ཚིག་འགྲེལ་ནི།`,
   `གསལ་འདེབས་ཚུལ་ནི།`); `ཞེས་པ་ལ།` / `ཞེས་པ་ནི།` after the quoted stanza is **not** one —
   it points back to the quote, so the quote belongs to the child that explains it: a
   stanza opening with its quote has its first child (e.g. `ཚིག་འགྲེལ།`) anchored on that
   same quote, never on `ཞེས་པ་ལ།`.

## Mode `top` — top-level parts that follow the root text's own sections

The body's top-level parts are **the root text's own sections**, in the root's order. For
the Praise to the Twenty-One Tārās the root text has three: the praise proper (from the
opening homage line `ཨོཾ་རྗེ་བཙུན་མ་…` through the root-mantra verse
`རྩ་བའི་སྔགས་ཀྱིས་བསྟོད་པ་འདི་དང་། …`), the benefits (from `ལྷ་མོ་ལ་གུས་ཡང་དག་ལྡན་པའི། །`),
and the root's own colophon (`… རྣམ་པར་སྣང་མཛད་ཀྱིས་གསུངས་པ…`). Look at the root text you
are given and use its sections. So:

```
* 1. བསྟོད་པ་དངོས།
* 2. <the commentary's own name for the benefits part, else ཕན་ཡོན།>
* 3. མཛད་བྱང།          ← only if the commentary explains the root's own colophon
```

Rules (fixed — do not decide case by case):
1. **Titles.** Part 1 is always `བསྟོད་པ་དངོས།`, whatever the commentary calls it. Part 2
   takes the commentary's own short name when it announces the part (drop the leading
   ordinal and a trailing `གྱི་དོན་ནི།` / `ཀྱི་དོན་ནི།` / `ནི།`, e.g. `གསུམ་པ་མཇུག་ཕན་ཡོན་གྱི་དོན་ནི།`
   → `མཇུག་ཕན་ཡོན།`), else `ཕན་ཡོན།`. Part 3 is always `མཛད་བྱང།`.
2. **Where each part begins.** If the commentary opens the part with its own announcement
   (`གཉིས་པ་ … ནི།`, `གསུམ་པ་ … ནི།`), the part begins there. Otherwise it begins where the
   commentary starts treating that root section:
   - part 1 at the commentary's treatment of the root's **opening homage line**
     (`ཨོཾ་རྗེ་བཙུན་མ་…`) if it quotes or explains it, else at the first stanza;
   - part 2 at the first **benefit** verse (`ལྷ་མོ་ལ་གུས་…`) — the root-mantra verse and its
     explanation stay in part 1;
   - part 3 where the commentary explains who spoke the praise / where it comes from.
3. **No descent.** Parts 1–3 get no children, even when the commentary divides them.
4. **Front matter `II.`** Anything between the homage/opening verses and part 1 is front
   matter, never a numbered part:
   - a passage that only **lists** the outline of the praise (`བསྟོད་པ་འདི་ལ་དོན་གཉིས་ཏེ། …`)
     is `* II. བསྟོད་པའི་ས་བཅད།` with **no children** — titles that are merely listed are
     never nodes;
   - a **preliminary practice** the commentary treats before the praise (the accumulation
     of merit with its seven limbs, an invitation of the field of merit …) is `* II. <its
     name>`, and keeps its own announced divisions as `II.1`, `II.2`, `II.2.1` …; it begins
     at the sentence that announces the commentary's top-level division
     (`… སྦྱོར་དངོས་མཇུག་གསུམ་ … དང་པོ་ …`), and `II.1` at the same place.

## Anchors

Append `[[context]]` to every line exactly as in pass 5: the first 12–20 syllables at
the node's beginning, copied **character for character** (same tshegs, shads and
spaces), long enough to be unique in order. A node with children begins at its own
announcement; never anchor on a place where the title is only listed in an enumeration.

## Output

```
## དཀར་ཆག / Table of Contents

* 1. <title> [[<context>]]
   * 1.1 <title> [[<context>]]
…
```

Three spaces of indentation per level. Output only numbered nodes (and `II.` lines in
`top` mode) — the `I.` homage section and the closing `a.` / `b.` sections are added by
the frame pass. Write the whole tree to the output path you are given.
