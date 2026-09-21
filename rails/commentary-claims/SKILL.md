---
name: commentary-claims
description: >
  Extract every distinct claim or fact a single commentary makes into one
  claims file for that commentary — stated in the commentary's own language with a
  short English gloss, and every claim citing the block ID it came from.

  Trigger on "extract the claims", "what does this commentary claim", "build the
  claims file", "pull the facts out of this commentary", "claims extraction".

  Three extraction strategies exist; which one to use depends on whether the
  commentary has a TOC tree. Output is one claims file per commentary, which
  `claims-consolidate` then reads across commentaries by topic.
profile: rails-vault
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/tree-guided-claims/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/toc-scaffolded-claims/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/commentary-claims/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Extract every claim a commentary makes

| Strategy | Use when | Cost / fidelity |
|---|---|---|
| 1 — Tree-guided | A `toc-generate` tree exists. **Default.** | Highest fidelity; one isolated subagent per node |
| 2 — TOC-scaffolded | A tree exists but a single consolidated pass is enough | Cheaper; output organised by the tree |
| 3 — Flat | **No tree exists** | Lowest fidelity; no structural scaffold to keep the extractor oriented |

**Prefer strategy 1 whenever a tree exists.** Extracting node by node in a fresh
isolated context is what stops the extractor drifting — by the middle of a long
commentary a single-context pass has silently shifted its notion of what counts as a
claim, and the second half of the file comes out thinner than the first. The cost is
more subagent dispatches; the benefit is that node 40 is extracted as carefully as
node 1.

Strategy 3 is the fallback for a commentary with no tree. If you find yourself
reaching for it on a commentary that *could* have a tree, build the tree first
(`toc-generate`) — it pays for itself here and again in `section-summary`.

**All three share the same output contract:** the commentary's own language, a short
English gloss, and a block-ID citation on every claim. A claim without a citation is
not a claim, it is a paraphrase — drop it.

---

## Strategy 1 — Tree-guided — node by node, isolated subagents

The default when a TOC tree exists.

This is **method 3** in the vault's claims-extraction comparison: use the commentary's own
ས་བཅད (sa bcad) tree as the *scaffold for extraction itself* — read one tree node's own
source window, in isolation, and extract fresh claims from it — rather than extracting once
over the whole file (as `commentary-claims` and the `opus`/`sonnet` runs do) and only
afterward filing the result under the tree's headings.

### Why this skill exists, and what it is not

`toc-scaffolded-claims` was meant to be exactly this — a third, independent extraction
method — but the run that produced `$TRANSFORMATIONS/Wikipedia/tara21/claims/toc-scaffolded/`
was not one: `_comparison-report.md`'s headline finding is that those files are the
`sonnet` category-scaffolded run's claims, re-bucketed under the tree with a Grounding index
and Referent tags added on top — 114 of 118 Tibetan strings in one file byte-identical to
sonnet's, sonnet's `claim_count` copied verbatim rather than recomputed, sonnet's
transcription errors inherited unchanged. Re-bucketing is a real and useful operation, but
it is not a second extraction, and the report is explicit that presenting it as one hid real
defects (a cross-document contamination, a fabricated mantra promoted to canonical status)
that a genuine independent extraction would very likely not have reproduced.

**This skill is what the report asked for instead:** re-run the tree-scaffolding as a true
extraction, with each node's claims drawn fresh from that node's own text — never copied,
paraphrased-from, or checked against `opus`, `sonnet`, or `toc-scaffolded`'s existing files.
The orchestrating agent must not open those files while running this skill, and per-node
subagents (see Procedure) are never given their paths at all — the same structural isolation
`toc-generate` uses to keep its four passes from contaminating one another applies
here to keep this extraction independent of the earlier ones.

The five guards the comparison report specifies for a trustworthy tree-scaffolded run are
load-bearing rules of this skill, not optional cleanup:

1. **Claim IDs are never node IDs.** A claim's ID and a node's decimal must be visibly
   different strings (Rule 3 below) — the `toc-scaffolded` files had `1.1` denoting both a
   claim and a section, five such collisions on one file alone.
2. **`claim_count` is computed by counting, at the end, never inherited or estimated**
   (Rule 9, Procedure Step 8b).
3. **A node-boundary check backs every claim's placement** — each node is read from its own
   line window alone (Procedure Step 5), never the whole file, so a claim cannot be extracted
   under the wrong node by construction rather than by discipline.
4. **`stated` means the referent's verbatim name occurs in *this claim's own* quoted
   Tibetan** — not merely somewhere in the node's segment (Rule 8).
5. **Every claim is independently re-derived**, never re-bucketed (this section, Rule 1).

`$SKILL/scripts/verify_claims.py` is the deterministic backstop
for guards 1, 2 and 4 (and a partial check on 3) — run it before considering any output file
final; see its own docstring for exactly what it checks.

---

### Inputs

| Input | Description | Path / format |
|---|---|---|
| **Commentary file** | Exactly one file from `$COMMENTARIES/`. Must carry frontmatter with `registered_id`, `title`, `author`, `lang_tag`. | `$COMMENTARIES/<filename>.md` |
| **`registered_id`** | The short ID from that file's frontmatter. Names the output file. | e.g. `karma-maitri` |
| **TOC tree** | The decimal-numbered ས་བཅད tree for this same commentary, built by `toc-generate`, **QC'd clean (or human-reviewed past its flags) by both `qc_check_tree.py` and `qc_tree_vs_source.py`** — see that skill's Pass 4. A tree that has not been checked against the source itself is not a scaffold, it is a guess. | `$SECTIONS_RAW/toc-tree/<id>.md` (promoted, preferred), or its pre-promotion `$WORK/toc-tree-<id>.md` working copy |
| **Segment addressing** | How the commentary's blocks are addressed. Determined by inspection, same as `commentary-claims` Step 2 — this vault's post-migration commentaries carry `^I-n` block IDs throughout. | block ID (preferred when present), else line number |

If the commentary file has no `registered_id`, **stop** and run `frontmatter` (Variant 2)
first. If no TOC tree exists for this `registered_id`, or the tree exists but has not been
run through `qc_tree_vs_source.py` against this exact file version, **stop** and run
`toc-generate`'s Pass 4 first — do not invent a structure and do not scaffold against
an unchecked tree.

If the human contributor supplies more than one commentary, run this skill once per
commentary. Never merge two commentaries into one file.

### Output

One file per commentary at:

```
$CLAIMS/raw/tree-guided/<registered-id>.md
```

`<registered-id>` is taken verbatim from the commentary's frontmatter. Create
`$CLAIMS/raw/tree-guided/` if it does not exist. This sits alongside `$CLAIMS/<id>.md`
(`commentary-claims`, fixed categories) and `$CLAIMS/raw/toc-scaffolded/<id>.md`
(`toc-scaffolded-claims`, re-bucketed under the tree) — three methods, three subfolders, never
overwriting one another. See `$RAILS/About Rails.md` §6b.

**This moved here from `$TRANSFORMATIONS/Wikipedia/<corpus>/claims/tree-guided/` on
2026-08-04.** Claims are descriptive rails — every claim cites `$SOURCES/` only, same as any
other `$RAILS/` file — not pipeline-owned experimental output; they belong in the rails any
transformation can draw on, not filed under one specific downstream pipeline. If the kwiki
Wikipedia pipeline's own claims stage (4b) later needs this file, it reads it from here like any
other rail. See `$SYSTEM/Guidelines/vault-annex.md` §6 for the fuller history of this move.

---

### Output file format

```markdown
---
registered_id: <registered-id>
title: "<Tibetan title verbatim from the commentary frontmatter>"
title_in_english: "<English title verbatim from the commentary frontmatter>"
author: "<Tibetan author verbatim>"
author_in_use: "<verbatim from the commentary frontmatter — the human-curated in-article name form; omit the key if the source frontmatter does not carry it>"
author_in_english: "<English author verbatim>"
source_file: $COMMENTARIES/<filename>.md
toc_tree_source: <path to the toc-tree file actually used>
tree_qc_reports: [<path to qc_check_tree.py's report>, <path to qc_tree_vs_source.py's report>]
language: bo
citation_form: block-id | segment | line
method: tree-guided-extraction
claim_id_scheme: "c-<decimal-with-dashes>-<n>, e.g. node 1.2.3's third claim is c-1-2-3-3 — never a bare decimal, never collides with a node heading number"
claim_count: <integer, computed by counting ### claim headings below — never copied from another file>
status: draft
---

## Tree-guided claims — <title_in_english>

**Commentary:** `<registered-id>` · <author_in_english>
**Source:** [`<filename>.md`](../../../$COMMENTARIES/<filename>.md)
**TOC tree:** [`toc-tree-<registered-id>.md`](<relative path to toc_tree_source>)
**Citation form:** <one sentence stating how the citations in this file resolve to the
source — block ID, segment number, or line number.>

> Every claim below was extracted fresh from this node's own text, in isolation, by a
> subagent that saw only this node's source window and never any other commentary's claims
> file. No claim is copied, paraphrased, or re-bucketed from `opus`, `sonnet`, or
> `toc-scaffolded`. Headings and their decimal numbers are drawn from the commentary's own
> TOC tree, not invented here. Claim IDs (`c-...`) are never node decimals.

---

### Grounding index

<Same structure and rules as `toc-scaffolded-claims`'s Grounding index: Figures/forms,
Persons, Places, Texts/mantras, Events/dates — one entry per distinct referent actually
named in the commentary body, its TOC-tree node titles, or its frontmatter. Keep every
kind-group heading even when empty ("None attested."). Populated cumulatively as each
node's subagent reports what it found in its own window (Procedure Step 6); the
orchestrating agent merges the reports, deduplicating only when the source itself equates
two mentions (same name, or an explicit "that is, …" identification) — never on the
orchestrator's own judgment that two named things are traditionally the same.>

#### Figures and forms (deities, aspects, emanations)
| ID | Name (verbatim) | What the source says it is | Attested at |
|---|---|---|---|
| FIG-1 | … | | |

#### Persons (authors, teachers, lineage figures, requesters)
| ID | Name (verbatim) | Role stated in the source | Attested at |
|---|---|---|---|
| PER-1 | … | | |

#### Places
| ID | Name (verbatim) | Context | Attested at |
|---|---|---|---|
| PLC-1 | … | | |

#### Texts and mantras cited
| ID | Name / incipit (verbatim) | How the source uses it | Attested at |
|---|---|---|---|
| TXT-1 | … | | |

#### Events and dates
| ID | Event / date (verbatim) | Context | Attested at |
|---|---|---|---|
| EVT-1 | … | | |

---

### 0. Front matter

<Anything before the tree's first node's window — opening formula, homage, colophon
preamble — extracted as its own claims, same rules as every other node. Omit this heading
only if the tree's first node genuinely opens the document.>

#### c-0-1 <short label>
**བོད་ཡིག:** <the claim, commentator's own wording, quoted from THIS node's window only>
**English:** <one-line gloss>
**Type:** structural | word-gloss | etymology | iconography | identification | doctrinal | activity | practice | ritual | mantra | benefit | attribution
**Referent:** <Grounding-index ID(s) with basis — `(stated)` only if the name is inside
*this claim's own* `**བོད་ཡིག:**` string, `(node)` from the enclosing node's title,
`(section-opener)` from the node's own opening sentence — or exactly `[unanchored]`.>
**Cite:** ($COMMENTARIES/<filename>.md#^<block-id>)

---

### 1. <node title, exactly as the tree gives it> [[<pointer, if the tree has one>]]

<Claims from this node's own window before its first child's window begins.>

#### c-1-1 <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** <…>
**Referent:** <…>
**Cite:** ($COMMENTARIES/<filename>.md#^<block-id>)

---

#### 1.1 <child node title> [[<pointer>]]

##### c-1-1-1 <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** <…>
**Referent:** <…>
**Cite:** ($COMMENTARIES/<filename>.md#^<block-id>)

⚑ **c-1-1-2 <short label — internal tension>**
- **Position 1:** <Tibetan> — (…md#^<block-id>)
- **Position 2:** <Tibetan> — (…md#^<block-id>)
**English:** <one line stating what the tension is>

---

<... one heading per TOC-tree node, in the tree's own document order, depth mirrored by
heading level (## depth 1, ### depth 2, #### depth 3+, capped at #### — flatten anything
deeper into a nested list under the #### heading) ...>

### Z. Back matter

<Anything after the tree's last node's window — closing benefits, colophon, dedication.
Omit if the tree's last node genuinely closes the document.>

---

### Internal tensions (rollup)

<One line per ⚑ claim above. If none, write "None observed." and keep the heading.>

- ⚑ c-1-1-2 — <one-line English gloss> (see node 1.1)

---

### Unanchored claims (rollup)

<One line per claim marked `[unanchored]`, with the reason. If every claim is anchored,
write "None — all claims anchored." and keep the heading.>

- c-1-2-4 — <reason>

---

### Coverage log

| Node | Source window | Claims extracted | Notes |
|---|---|---|---|
| 0 (front matter) | ^I-1–^I-<n> | c-0-1, … | |
| 1 | ^I-<n>–^1-<n> | c-1-1 | |
| 1.1 | ^1-<n>–^1-<n> | c-1-1-1, c-1-1-2 | |
| … | | | |
| Z (back matter) | | | |

**Nodes with no independently attested line (`[[?]]` in the tree):** <list them and which
neighbouring node's window you folded their extraction into — do not skip a node's claims
just because its own pointer is unresolved.>
**Segments yielding no claim:** <list ranges that are pure root-text quotation, colophon,
or scribal matter, so a reviewer can see nothing was skipped silently.>
```

---

### Rules

1. **Fresh extraction, node by node — never re-bucketing.** Each node's claims are derived
   by reading that node's own source window and asking "what does the commentator assert
   here", exactly as `commentary-claims` asks it of the whole file. Never open an existing
   `opus`/`sonnet`/`toc-scaffolded` claims file for this commentary while running this
   skill, and never give a per-node subagent their paths (Procedure Step 4). If a claim in
   this file happens to match one in an existing file, that is either a real, independently
   re-found claim or evidence this rule was violated — not something to reconcile by hand.
2. **The TOC tree is the scaffold, never re-derived.** Use node titles, decimal numbers,
   and document order exactly as the tree gives them. A wrong tree is a
   `toc-generate`/QC problem, not something to silently fix here — stop and say so.
3. **Claim IDs are `c-<decimal-with-dashes>-<n>`, never a bare decimal.** Node `1.2.3`'s
   third claim is `c-1-2-3-3`. This string can never be mistaken for a node heading
   (`## 1.2.3 …`) even out of context — the load-bearing property the `toc-scaffolded`
   files lacked (guard 1).
4. **One commentary per file, read window by window in isolation.** Do not consult the
   root text, another commentary, or a different node's already-written claims to decide
   what a passage means.
5. **Every claim carries a citation**, in the commentary's own block-ID or line form —
   `commentary-claims` Rule 4, unchanged. A claim with no citation is not a claim.
6. **The commentator's own vocabulary, verbatim** — `commentary-claims` Rule 3, unchanged.
7. **Exhaustive, not selective; splitting preferred to merging** — `commentary-claims`
   Rule 6, unchanged, applied within each node's window.
8. **`stated` means the name is in the claim's own quotation.** A `Referent:` tag of
   `(stated)` is valid only when the referent's verbatim name or epithet occurs inside that
   claim's own `**བོད་ཡིག:**` string — not merely somewhere in the node's window. If the
   name is absent from the claim's own quotation but present in the window or inherited
   from the node's title, use `(section-opener)` or `(node)` instead; if none apply, write
   `[unanchored]` (guard 4). This is the fix the comparison report names explicitly: on the
   original `toc-scaffolded` run, 7 of 14 claims tagged `FIG-1 (stated)` in one file
   contained no form of the referent's name at all.
9. **`claim_count` is counted, not carried.** After writing every claim, count the actual
   `###`-level claim headings (excluding ⚑ tension entries, which are their own count) and
   put that integer in the frontmatter. Never copy a count from another file, another
   node's running total, or an estimate (guard 2).
10. **A claim belongs to the node whose window contains its citation.** If a passage seems
    to discuss a neighbouring node's topic (a title-keyword coincidence — a node titled
    "overcoming what is discordant" pulling in a claim from a different section that
    happens to share a word with that title), the deciding fact is which node's window the
    *cited block* is actually inside, never which node's title the content sounds closer
    to. This is the guard against the exact failure the comparison report documents on
    `lobsang-dawa`'s tree (guard 3).
11. **No parametric knowledge, no cross-commentary content.** Never add a fact this
    commentary does not itself state, and never let a claim's content or citation
    originate in a different commentary file — the comparison report's karma-maitri
    finding (a claim whose Tibetan string and citation both belong to lobsang-dawa's file,
    not karma-maitri's) is exactly the failure this rule exists to prevent structurally:
    a per-node subagent is given only ITS OWN commentary's file, never another's.
12. **Grounding is source-attested only** — same three permitted sources as
    `toc-scaffolded-claims` Rule 13: the commentary body, the TOC tree's node titles, the
    commentary's own frontmatter. Never enrich from tradition or general knowledge.
13. **Distinct referents get distinct entries**, even when tradition equates them —
    `toc-scaffolded-claims` Rule 16, unchanged.
14. **Never mark `status: complete`.** This skill writes `status: draft`. Only a domain
    specialist promotes a claims file.
15. **Do not modify `$SOURCES/` or the TOC tree file.** Read-only on both.
16. **Empty nodes are kept, not deleted.** Write "None — announcement only." under a node
    heading with no claims of its own rather than omitting the heading.
17. **Run `verify_claims.py` before considering the file final** (Procedure Step 9). A
    file that has not been run through it is a draft of a draft.

---

### Procedure

**This is an orchestrator skill, structured like `toc-generate`: you (the
orchestrating agent) do the bookkeeping — loading, windowing, merging, running the
verifier — and dispatch one ISOLATED subagent per node for the actual extraction. Do not
extract claims yourself in this context; a subagent that only ever sees one node's own
window is what makes guards 1, 3 and "fresh extraction, never re-bucketing" structural
rather than a matter of discipline.**

#### Step 1 — Load the commentary and the tree

a. Read the commentary's frontmatter; record `registered_id`, `title`, `title_in_english`,
   `author`, `author_in_english`, and `author_in_use` (where present — copy it verbatim,
   never compose one). Stop if `registered_id` is absent.
   `author_in_use` (added 2026-08-18) is the human-curated name form downstream article
   prose uses when citing this author's view. If the source commentary gains or changes
   this key **after** this claims file was extracted, copy the new value into this file's
   frontmatter directly — that is a metadata sync, not a re-extraction, and never a reason
   to re-run this skill.
b. Load the TOC tree (`$SECTIONS_RAW/toc-tree/<id>.md`, or its pre-promotion `$WORK/toc-tree-<id>.md` working copy). Record
   `toc_tree_source`.
c. Confirm both QC reports exist and are recent (`qc_check_tree.py`'s and
   `qc_tree_vs_source.py`'s, the latter checked against this *exact* file). If either is
   missing, stop and run `toc-generate` Pass 4 first. Record both report paths.
d. Parse every tree line into an ordered list: decimal, depth, title, pointer (`[[N]]`,
   `[[?]]`, or none).

#### Step 2 — Determine the citation form

Same inspection as `commentary-claims` Step 2. This vault's post-migration commentaries
carry `^I-n` / `^<chapter>-<n>` block IDs on every content block — prefer `citation_form:
block-id` and cite `#^<block-id>` directly; fall back to `segment`/`line` only for a
commentary that has not been through the block-ID stamping stage.

#### Step 3 — Compute each node's reading window

Identical definition to `toc-scaffolded-claims` Step 4: a node's window starts at its own
pointer and ends the line before the next node's pointer (any depth), or end-of-file for
the last node. A node whose pointer is `[[?]]` gets no window of its own — fold its
heading into the nearest neighbour with a real pointer and note the fold in the Coverage
log, exactly as `toc-scaffolded-claims` Step 4c prescribes. Anything before the first
node's window is `Front matter`; anything after the last is `Back matter`.

#### Step 4 — Dispatch one ISOLATED subagent per node

For each node (front matter and back matter count as nodes here), dispatch a separate
subagent. Give it **only**:

- this skill's Rules 1, 3, 5–13 (not the whole file — the extraction rules, not the
  orchestration mechanics)
- the commentary's file path and the node's own line range (start–end, inclusive; tell it
  to read via `sed -n 'START,ENDp' <file>` or the Read tool with offset/limit — never the
  whole file)
- the node's decimal and title, so it can form claim IDs and know what to write under
- **nothing else.** Do not give it the paths of `opus`/`sonnet`/`toc-scaffolded`/any other
  node's output. Do not let it see the merged claims file being built.

Ask it to reply with: the claims it extracted (Tibetan quotation, English gloss, `Type:`,
`Referent:` with basis, citation) in this node's window only, plus any Grounding-index
candidates it noticed (referent name, kind, what the source says, its own citation).
Independent nodes have no dependencies — dispatch several in parallel, one message,
multiple subagent calls.

#### Step 5 — Assemble, don't re-derive

Merge each subagent's reply into the output file at the node's position in tree order.
This is mechanical assembly (like `toc-generate`'s merge step) — do not re-read the
source yourself and second-guess a subagent's extraction; if a reply looks wrong, dispatch
a fresh subagent for that node rather than editing its claims in this context.

#### Step 6 — Build the Grounding index

Collect every subagent's referent candidates into the five kind-groups. Deduplicate only
when the source itself equates two mentions (Rule 12/13). Assign stable IDs (`FIG-1`,
`PER-1`, …) in first-appearance order.

#### Step 7 — Number the claims and write headings

a. Claim IDs per Rule 3, sequential within each node (`c-1-2-1`, `c-1-2-2`, …). Numbers
   are stable — never renumber existing entries when appending.
b. Heading depth mirrors tree depth (`##`/`###`/`####`, capped, deeper levels flattened
   into a nested list), reproducing the node's decimal and title exactly, with its
   pointer (or the line it was folded to) in `[[...]]`.

#### Step 8 — Finalise

a. Write the Internal tensions and Unanchored claims rollups from what each node's
   subagent flagged.
b. **Count the actual `###`-level claim headings and set `claim_count` to that number** —
   never inherit it (Rule 9).
c. Build the Coverage log: one row per node (plus Front/Back matter), its window, the
   claim IDs drawn from it, and any fold note from Step 3.
d. Set `status: draft`.
e. Write to `$CLAIMS/raw/tree-guided/<registered-id>.md`.

#### Step 9 — Run the deterministic verifier

```bash
python $SKILL/scripts/verify_claims.py \
  $CLAIMS/raw/tree-guided/<registered-id>.md \
  --source $COMMENTARIES/<filename>.md
```

It checks: every quoted Tibetan string is literally present (NFC + tsheg/shad-stripped) in
its cited block; `claim_count` matches the file's actual claim headings; no claim ID
collides with a node decimal or another claim ID; every `stated` tag's referent name
actually occurs in that claim's own quotation; the coverage log's claimed "no claim"
ranges are genuinely uncited elsewhere. Fix every issue it reports (dispatch a fresh
per-node subagent for the offending node rather than hand-editing) and re-run until clean,
or note remaining issues for human review — never suppress a finding to make the count
read zero.

#### Step 10 — Self-verification

- [ ] Every node subagent saw only its own window and this commentary's own file
- [ ] Every claim heading has a `**Cite:**` and a `**Referent:**` (valid ID(s) with basis,
      or `[unanchored]`)
- [ ] No claim ID collides with any node decimal or any other claim ID
- [ ] `claim_count` equals a fresh count of the `###` headings present
- [ ] `verify_claims.py` has been run and its output reviewed (clean, or issues logged)
- [ ] `$SOURCES/` and the TOC tree file unmodified

---

### Completion check

- [ ] Commentary and TOC tree loaded; both QC reports confirmed against this exact file
- [ ] Extraction ran node by node via isolated subagents, never re-bucketed from another
      claims file
- [ ] Output written to `$CLAIMS/raw/tree-guided/<registered-id>.md`
- [ ] Frontmatter complete: `registered_id`, `title`, `author`, `author_in_use` (when the
      source frontmatter carries it, copied verbatim), `source_file`,
      `toc_tree_source`, `tree_qc_reports`, `citation_form`, `method: tree-guided-extraction`,
      `claim_id_scheme`, `claim_count`, `status: draft`
- [ ] Every TOC-tree node has a heading in tree order, none skipped or renumbered
- [ ] Every claim ID matches `c-<decimal-with-dashes>-<n>` and collides with nothing
- [ ] Every claim has Tibetan, English gloss, `Type:`, `Referent:` (with basis, or
      `[unanchored]`), and a citation
- [ ] Grounding index present, all five kind-groups, every entry source-attested
- [ ] `verify_claims.py` run; issues fixed or explicitly logged for human review
- [ ] `claim_count` equals the actual number of claim headings
- [ ] `$SOURCES/` and the TOC tree file unmodified

---

## Strategy 2 — TOC-scaffolded — one consolidated pass, organised by the tree

Same scaffold, single pass. Use when the commentary is short enough that drift is not a risk.

This skill produces a **TOC-scaffolded, referent-anchored claims inventory**: the same exhaustive, cited, one-claim-at-a-time extraction that `commentary-claims` performs, but grouped under the commentary's own ས་བཅད (sa bcad) structure instead of the fixed nine-category scheme, and with each claim **anchored to the specific referent it is about** whenever the source attests one. Where `commentary-claims` answers "what does this commentary assert, by topic?", this skill answers "what does this commentary assert, **in the order and hierarchy it itself imposes on the text — and about whom, where, and when, exactly?**"

It exists for two reasons. First, a category-scaffolded claims file (A. Framing, B. Word-gloss, …) is excellent for auditing one commentary in isolation, but it scatters a single section's material across nine categories, making it slow to compare *the same stretch of root text* across several commentaries. A TOC-scaffolded file keeps every claim under the heading of the actual section it belongs to, so opening several commentaries' files side by side and scrolling to the matching node shows what each commentator says about that same stretch, in one place.

Second, a claim floating free of its referent is not verifiable. "She acts swiftly to help" is unfalsifiable until the file records *which* figure, in *which* form or aspect, the commentary itself says this about — and commentaries usually do say: the deity's specific epithet, the form being praised in that section, the named speaker, the place, the lineage figure, the text being quoted, the date in the colophon. The commentary's own TOC is often where this disambiguation lives (a section titled "praise via the wrathful form" tells you the referent of every claim under it). This skill therefore harvests every such **grounding element** — person, figure/form, place, text, event, date — from the commentary, its TOC tree, and its frontmatter, registers each one verbatim with a citation, and ties claims to them. A claim that cannot be tied to any attested referent is explicitly marked, because that untethered-ness is itself a finding about the commentary.

Correct output looks like this: a reader who has never opened the commentary can scan the file top to bottom and see, node by node, everything the commentator states about that node — in his own vocabulary, each claim individually cited **and each claim's subject pinned to a registry entry that resolves to a verbatim source string** — matching the shape of the commentary's own TOC tree. Nothing in the file comes from the root text, from another commentary, or from the model's own knowledge.

---

### Inputs

| Input | Description | Path / format |
|---|---|---|
| **Commentary file** | Exactly one file from `$COMMENTARIES/`. Must carry frontmatter with `registered_id`, `title`, `author`, `lang_tag`. | `$COMMENTARIES/<filename>.md` |
| **`registered_id`** | The short ID from that file's frontmatter. Names the output file. | e.g. `karma-maitri` |
| **TOC tree** | The decimal-numbered ས་བཅད tree for this same commentary, built by `toc-generate` (Claude-native) or the Gemini `extract_toc_tree.py`. This is the scaffold every heading in the output is drawn from. | `$WORK/toc-tree-<id>.md`, or `$WORK/TOC-<id>/toc-tree-<id>.md` |
| **Segment addressing** | How the commentary's blocks are addressed. Determined by inspection, same as `commentary-claims` Step 2. | numbered segments, or line numbers |

If the commentary file has no `registered_id`, **stop** and run `frontmatter` (Variant 2) first. If no TOC tree exists for this `registered_id` under either path above, **stop** and run `toc-generate` (or the Gemini script) on this commentary first — do not invent a structure or fall back to the A–I categories.

If the human contributor supplies more than one commentary, run this skill once per commentary. Never merge two commentaries into one file.

### Output

One file per commentary at:

```
$CLAIMS/raw/toc-scaffolded/<registered-id>.md
```

`<registered-id>` is taken verbatim from the commentary's frontmatter. Create `$CLAIMS/raw/toc-scaffolded/` if it does not exist. This sits alongside any existing per-model category-scaffolded runs (e.g. `$CLAIMS/sonnet/<id>.md`, `$CLAIMS/opus/<id>.md`) without touching them.

---

### Output file format

```markdown
---
registered_id: <registered-id>
title: "<Tibetan title verbatim from the commentary frontmatter>"
title_in_english: "<English title verbatim from the commentary frontmatter>"
author: "<Tibetan author verbatim>"
author_in_english: "<English author verbatim>"
source_file: $COMMENTARIES/<filename>.md
toc_tree_source: <path to the toc-tree file actually used>
language: bo
citation_form: segment | line
scaffold: toc-tree
claim_count: <integer — total claims in this file>
status: draft
---

## TOC-scaffolded claims — <title_in_english>

**Commentary:** `<registered-id>` · <author_in_english>
**Source:** [`<filename>.md`](../../../$COMMENTARIES/<filename>.md)
**TOC tree:** [`toc-tree-<registered-id>.md`](<relative path to toc_tree_source>)
**Citation form:** <one sentence stating how the `§`/`L` numbers in this file resolve to the source.>

> Every claim below is drawn from this commentary alone. Headings and their
> decimal numbers are drawn from the commentary's own TOC tree, not invented
> here. Every Referent tag resolves to an entry in the Grounding index, and
> every Grounding-index entry resolves to a verbatim string in this source.
> No claim originates in the root text, in another commentary, or outside
> `$SOURCES/`.

---

### Grounding index

<The registry of every named referent the commentary, its TOC tree, or its
frontmatter attests. One entry per distinct referent, grouped by kind. Each
entry has a stable ID used by the Referent: lines below. Include ONLY kinds
that actually occur; keep the group heading with "None attested." for kinds
that do not — the absence is a finding.>

#### Figures and forms (deities, aspects, emanations)
| ID | Name (verbatim) | What the source says it is | Attested at |
|---|---|---|---|
| FIG-1 | <Tibetan/original name or epithet exactly as written> | <one line, from the source only> | §<n>, §<n> |
| FIG-2 | … | | |

#### Persons (authors, teachers, lineage figures, requesters)
| ID | Name (verbatim) | Role stated in the source | Attested at |
|---|---|---|---|
| PER-1 | … | | |

#### Places
| ID | Name (verbatim) | Context | Attested at |
|---|---|---|---|
| PLC-1 | … | | |

#### Texts and mantras cited
| ID | Name / incipit (verbatim) | How the source uses it | Attested at |
|---|---|---|---|
| TXT-1 | … | | |

#### Events and dates
| ID | Event / date (verbatim) | Context | Attested at |
|---|---|---|---|
| EVT-1 | … | | |

---

### 0. Front matter

<Anything before the TOC tree's first node — opening formula, homage to the
deity, verse announcing intent — captured here as usual claim entries. Omit
this heading only if the tree's first node genuinely opens the document.>

#### 0.1 <short label>
**བོད་ཡིག:** <the claim, commentator's own wording>
**English:** <one-line gloss>
**Type:** structural | word-gloss | etymology | iconography | identification | doctrinal | activity | practice | ritual | mantra | benefit | attribution
**Referent:** <ID(s) from the Grounding index this claim is about, with the
basis in parentheses: "(stated)" when the referent is named in the claim's
own passage, "(node)" when it is inherited from the enclosing TOC-node's
title, "(section-opener)" when the section's opening sentence fixes it. If
no attested referent applies, write exactly `[unanchored]`.>
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### 1. <node title, exactly as it reads in the TOC tree> [[<line>]]

<Claims found in this node's own text before its first child node begins —
i.e. the section's announcement / opening statement, if it makes assertions
of its own beyond dividing into parts.>

#### 1.1 <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** <…>
**Referent:** <…>
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### 1.1 <child node title> [[<line>]]

#### 1.1.1 <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** <…>
**Referent:** FIG-2 (node) <e.g. — a claim inside a section the TOC itself
titles "praise via the wrathful form" is *about* that form; the node title
is the source's own disambiguation and the claim inherits it>
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

⚑ **1.1.2 <short label — internal tension>**
- **Position 1:** <Tibetan> — (…md §<n>)
- **Position 2:** <Tibetan> — (…md §<n>)
**English:** <one line stating what the tension is>

---

<... one heading per TOC-tree node, in the tree's own document order,
depth mirrored by heading level (## for depth 1, ### for depth 2, #### for
depth 3+, capped at #### — flatten anything deeper into the same heading
with a nested list) ...>

### Z. Back matter

<Anything after the TOC tree's last node — closing benefits, colophon,
dedication — if the tree does not extend that far. Omit if the tree's last
node genuinely closes the document.>

---

### Internal tensions (rollup)

<One line per ⚑ claim above, for fast scanning: node number, claim id, and
the one-line English gloss. If none, write "None observed." and keep the
heading.>

- ⚑ 1.1.2 — <one-line English gloss> (see node 1.1)

---

### Unanchored claims (rollup)

<One line per claim marked `[unanchored]` above: claim id + why no referent
could be attested (subject never named, pronoun with no antecedent in the
source, generic statement the commentary itself leaves generic). This list
is the file's honesty ledger — a reviewer reads it to see which claims
cannot yet be rooted back to anything concrete. If every claim is anchored,
write "None — all claims anchored." and keep the heading.>

- 1.2.4.b — <reason> 

---

### Coverage log

| Node | Source range | Claims extracted | Notes |
|---|---|---|---|
| 0 (front matter) | §1–§<n> | 0.1, … | |
| 1 | §<n>–§<n> | 1.1 | |
| 1.1 | §<n>–§<n> | 1.1.1, 1.1.2 | |
| … | | | |
| Z (back matter) | §<n>–§<n> | | |

**Nodes with no independently attested line (`[[?]]` in the tree):** <list
them and state which neighbouring node's range you folded their text into.>
**Segments yielding no claim:** <list ranges that are pure root-text
quotation, colophon, or scribal matter, so a reviewer can see nothing was
skipped silently.>
```

---

### Rules

1. **The TOC tree is the scaffold, never re-derived.** Use the node titles, decimal numbers, and document order exactly as they appear in the tree file. Do not renumber, reorder, merge, or split nodes — if the tree is wrong, that is a `toc-generate` problem, not something to silently fix here.
2. **One commentary per file, read in isolation.** Same as `commentary-claims` Rule 1: do not open a second commentary, do not consult the root text to decide what a passage means.
3. **Every claim carries a citation**, exactly as in `commentary-claims` Rule 4. A claim with no `($COMMENTARIES/<filename>.md §<n>)` reference is not a claim — delete it.
4. **The commentator's own vocabulary, verbatim** — `commentary-claims` Rule 3, unchanged.
5. **English is a gloss, not a translation** — one line, for orientation only, never cited from.
6. **Exhaustive, not selective**, and **splitting preferred to merging** — `commentary-claims` Rule 6, unchanged. Every distinct assertion under a node gets its own numbered entry.
7. **No parametric knowledge.** Never add a fact this commentary does not itself state.
8. **Keep the `Type:` tag on every claim**, using the same vocabulary as `commentary-claims` (structural, word-gloss, etymology, iconography, identification, doctrinal, activity, practice, ritual, mantra, benefit, attribution). This is what still lets a reader filter by facet even though the top-level grouping is now structural, not topical.
9. **Never mark `status: complete`.** This skill writes `status: draft`. Only a domain specialist promotes a claims file.
10. **Do not modify `$SOURCES/` or the TOC tree file.** This skill reads both and writes only to `$CLAIMS/raw/toc-scaffolded/`.
11. **Empty nodes are kept, not deleted.** If a node's own text yields no claim beyond dividing into children, write "None — announcement only." under its heading and move on; do not omit the heading.
12. **Front matter and back matter are never silently dropped.** If the tree's first node does not open the document, or its last node does not close it, the leftover text still gets claims extracted under `## 0. Front matter` / `## Z. Back matter`.
13. **Grounding is source-attested only.** A Grounding-index entry may be created from exactly three places: the commentary body, the TOC tree's node titles, and the commentary's own frontmatter (author, date, title). Never add an entry — or enrich one — from the model's general knowledge of the tradition, however standard the identification seems. If the commentary says only "the protector," the registry entry is "the protector," not the deity the tradition means by it.
14. **Every claim carries a `Referent:` line.** The line either names Grounding-index ID(s) with the basis — `(stated)` from the claim's own passage, `(node)` inherited from the enclosing TOC-node title, `(section-opener)` from the sentence that opens the section — or reads exactly `[unanchored]`. Node-title inheritance is legitimate grounding *because the title is the commentator's own words*: a claim under a section the author titled "praise via the wrathful form" is about that form on the author's authority, not the extractor's.
15. **`[unanchored]` is a verdict, not a failure to try.** Use it only after checking the claim's passage, its section opener, and its full node-path ancestry. Never resolve an unanchored claim by guessing; never delete a claim because it is unanchored. Every `[unanchored]` claim appears in the Unanchored claims rollup with the reason.
16. **Distinct referents get distinct entries — even when tradition equates them.** If the commentary praises a peaceful form in one section and a wrathful form in another, those are two registry entries; whether they are "the same deity" is the commentary's call to make, recorded only if it makes it. Conflating referents the source keeps apart destroys exactly the verifiability this skill exists to add.
17. **Text-generic, always.** The registry kinds (figures/forms, persons, places, texts, events/dates) and the anchoring mechanism are fixed; nothing in this skill's execution may hard-code a particular deity, text, or tradition. The skill must run unchanged on any commentary with a TOC tree.

---

### Procedure

#### Step 1 — Load the commentary

a. Read the full frontmatter of the target file in `$COMMENTARIES/`.
b. Record `registered_id`, `title`, `title_in_english`, `author`, `author_in_english`.
c. If `registered_id` is absent, stop and report; run `frontmatter` (Variant 2) first.

#### Step 2 — Load the TOC tree

a. Look for `$WORK/toc-tree-<registered-id>.md`; if absent, look for `$WORK/TOC-<registered-id>/toc-tree-<registered-id>.md`.
b. If neither exists, stop and report: run `toc-generate` (or the Gemini `extract_toc_tree.py`) on this commentary first.
c. Record the path actually used as `toc_tree_source`.
d. Parse every tree line (`* <decimal> <title> [[<line>]]`) into an ordered list, in the exact document order the tree file lists them, keeping decimal, depth (number of decimal segments), title text, and the line number (or `?` if unattested).

#### Step 3 — Determine the citation form

Same as `commentary-claims` Step 2: inspect the commentary body for leading segment numbers or Obsidian block IDs; set `citation_form` accordingly; state the resolved form in the output header.

#### Step 4 — Compute each node's reading window

a. Flatten the parsed tree into document order (already true of the parse in Step 2d — every node, at any depth, in the order it appears in the tree file).
b. For each node in that order, its window starts at its own `[[line]]` and ends the line before the next node's `[[line]]` (any depth), or end-of-file for the last node. This means a parent node's window (before its first child) covers only its own opening/announcement text — correct, since the child's window then takes over.
c. For a node whose line is `?`, do not guess a line number. Fold its heading into the surrounding window of the nearest node (parent or preceding sibling) that does have a line number, and note this fold in the Coverage log's `Nodes with no independently attested line` row. The heading still appears in the output in its correct tree position; only its window boundary is approximate.
d. Anything before the first node's window is the `Front matter` window; anything after the last node's window is the `Back matter` window.

#### Step 5 — Read the commentary in full, in order — and harvest grounding elements as you go

a. Read from the first line to the last. Do not sample or skip ahead to sections that look substantive.
b. Read in contiguous chunks sized so no chunk truncates mid-argument, same discipline as `commentary-claims` Step 3.
c. Track which node-window each chunk falls in as you go.
d. **While reading, collect every named referent into the Grounding index:** proper names and fixed epithets of figures and their forms/aspects, persons (author, teachers, lineage figures, the requester in the colophon), places, texts and mantras cited by name or incipit, and events or dates. Also harvest the TOC tree's own node titles (a title like "praise via the peaceful form" names a form) and the frontmatter (author, date). Record each entry's name verbatim, what the source itself says it is, and every location where it is attested. Assign stable IDs (`FIG-1`, `PER-1`, `PLC-1`, `TXT-1`, `EVT-1`, …).
e. Keep referents distinct exactly as the source keeps them distinct (Rule 16). Merge two mentions into one entry only when the source itself equates them (same name, or an explicit "that is, …" identification).

#### Step 6 — Extract claims window by window, anchored

For each node window, in tree order:

a. Identify every distinct assertion the commentator makes within that window's lines.
b. For each assertion, write the Tibetan in the commentator's own wording, then the one-line English gloss, then the `Type:` tag.
c. **Anchor the claim (Rule 14):** determine what the claim is *about* and write the `Referent:` line. Search in this order and record the basis found: (1) the claim's own passage — is the subject named there? → `(stated)`; (2) the sentence that opens the section → `(section-opener)`; (3) the enclosing node's title and then each ancestor node's title up the tree → `(node)`. A claim may carry several referents (e.g. a figure and the text being quoted about it). If all three searches fail, write `[unanchored]` and log it in the Unanchored claims rollup with the reason.
d. Attach the segment or line citation.
e. Where the commentator marks an alternative view (འམ། / གཞན་དག་ན་རེ། / ཁ་ཅིག་ན་རེ།), mark it ⚑ inline under that node, and add a one-line entry to the Internal tensions rollup at the end. When the alternative view comes from a named source, that source is also a Grounding-index entry and the ⚑ claim's Referent line includes it.
f. If a window yields no claim of its own (pure announcement, or pure quotation), write "None — announcement only." (or the appropriate reason) under its heading rather than omitting the heading.

#### Step 7 — Number the claims

a. Number sequentially within each node: `<decimal>.1`, `<decimal>.2`, … (e.g. node `1.1` → claims `1.1.1`, `1.1.2`). Front matter uses `0.1, 0.2, …`; back matter uses `Z.1, Z.2, …`.
b. Numbers are stable identifiers — never renumber an existing file when appending.

#### Step 8 — Write headings at the right depth

a. Depth-1 tree nodes get `##`, depth-2 get `###`, depth-3+ all get `####` (flatten deeper levels into a nested bullet list under the `####` heading rather than inventing `#####`).
b. Each heading reproduces the node's decimal number and title exactly as the tree gives it, followed by its `[[line]]` (or the line it was folded to, if originally `?`).

#### Step 9 — Finalise the Grounding index, rollups, and Coverage log

a. Write the Grounding index tables (all five kind-groups, "None attested." where empty), placing them before the first claims section so a reader meets the referents before the claims that use them.
b. Sweep every `Referent:` line and confirm each ID it names exists in the index; sweep every index entry and confirm at least one claim or ⚑ position references it — an entry nothing points to is either a missed anchoring opportunity (fix the claims) or noise (delete the entry).
c. List every ⚑ claim from Step 6e as a one-line entry: node number, claim id, English gloss.
d. List every `[unanchored]` claim in the Unanchored claims rollup with its reason.
e. Build the Coverage log table: one row per node (plus Front matter / Back matter), its source range, and the claim IDs drawn from it.
f. List any node whose line was folded (from Step 4c) and which neighbour it was folded into.
g. List any source ranges that yielded no claim at all, with the reason.

#### Step 10 — Write the file

a. Write to `$CLAIMS/raw/toc-scaffolded/<registered-id>.md`, creating the directory if needed.
b. Fill `claim_count` with the total across all nodes plus front/back matter.
c. Set `status: draft` and `scaffold: toc-tree`.

#### Step 11 — Self-verification

a. Confirm every numbered claim heading has a `**Cite:**` line (except ⚑ tension entries, which cite inline per position) **and a `**Referent:**` line that is either valid index ID(s) or exactly `[unanchored]`**.
b. Confirm every Grounding-index entry's "Attested at" locations actually contain the verbatim name — an entry whose name cannot be found at its cited location is invented; delete it and re-anchor its dependants.
c. Confirm no claim text or index entry mentions another commentary, the root text file, or a fact from outside this source (Rule 13).
d. Confirm every tree node has a corresponding heading, in the tree's own order, with no node skipped.
e. Confirm the Coverage log's ranges span the whole source file with no unexplained gap.
f. Confirm `claim_count` equals the number of claim entries actually present, and the Unanchored rollup lists exactly the claims marked `[unanchored]`.

---

### Completion check

- [ ] Commentary read in isolation, from first line to last
- [ ] TOC tree loaded from an existing `toc-generate` (or Gemini) output; skill stopped and reported if none was found — no structure was invented
- [ ] Output written to `$CLAIMS/raw/toc-scaffolded/<registered-id>.md` with `<registered-id>` matching the source frontmatter
- [ ] Frontmatter complete: `registered_id`, `title`, `author`, `source_file`, `toc_tree_source`, `citation_form`, `scaffold: toc-tree`, `claim_count`, `status: draft`
- [ ] Every TOC-tree node has a heading, in the tree's own document order and decimal numbering, none skipped or renumbered
- [ ] Every claim has a Tibetan statement, an English gloss, a `**Type:**`, a `**Referent:**` (valid index IDs with basis, or `[unanchored]`), and a `**Cite:**`
- [ ] Grounding index present with all five kind-groups (empty ones carry "None attested."), every entry verbatim-attested at its cited locations, no entry unreferenced by any claim
- [ ] No Grounding-index entry or referent identification drawn from parametric knowledge — only from the commentary body, its TOC-node titles, or its frontmatter
- [ ] Unanchored claims rollup lists exactly the `[unanchored]` claims, each with a reason
- [ ] Nodes with no independently attested line are listed in the Coverage log with the neighbour they were folded into
- [ ] Front matter and back matter (if any) captured, not dropped
- [ ] Alternative or conflicting positions marked ⚑ inline and listed in the Internal tensions rollup
- [ ] Coverage log accounts for the entire source file, including ranges that yielded nothing
- [ ] `claim_count` equals the number of claim entries actually present
- [ ] `$SOURCES/` and the TOC tree file unmodified

---

## Strategy 3 — Flat — no tree available

The fallback. Say in your report that the extraction was unscaffolded.

This skill produces the **per-commentary claims inventory**: an exhaustive, numbered list of every distinct assertion one commentary makes, in that commentary's own words, with a one-line English gloss under each.

It exists because the commentaries in this vault are long, unstructured, and mutually divergent, and because reading them comparatively — verse against verse, commentator against commentator — silently flattens what each one actually says. A claims file is built by reading **one commentary in isolation**, start to finish, with the root text closed. The result is a record of that commentator's position as *he* states it, before any synthesis, comparison, or alignment happens.

Correct output looks like this: a reader who has never opened the commentary can scan the claims file and know every interpretive move the commentator makes, in his own vocabulary, and can jump to the exact segment that supports each one. Nothing in the file comes from the root text, from another commentary, or from the model's own knowledge of Tārā literature.

---

### Inputs

| Input | Description | Path / format |
|---|---|---|
| **Commentary file** | Exactly one file from `$COMMENTARIES/`. Must carry frontmatter with `registered_id`, `title`, `author`, `lang_tag`. | `$COMMENTARIES/<filename>.md` |
| **`registered_id`** | The short ID from that file's frontmatter. Names the output file and prefixes every claim ID. | e.g. `karma-maitri` |
| **Segment addressing** | How the commentary's blocks are addressed. Determined by inspection — see Procedure Step 2. | numbered segments, or line numbers |

If the commentary file has no `registered_id` in its frontmatter, **stop** and run `frontmatter` (Variant 2) first. Do not invent an ID.

If the human contributor supplies more than one commentary, run this skill once per commentary. Never merge two commentaries into one claims file.

### Output

One file per commentary at:

```
$CLAIMS/raw/<registered-id>.md
```

`<registered-id>` is taken verbatim from the commentary's frontmatter (`karma-maitri` → `$CLAIMS/raw/karma-maitri.md`). Create `$CLAIMS/` if it does not exist.

---

### Output file format

```markdown
---
registered_id: <registered-id>
title: "<Tibetan title verbatim from the commentary frontmatter>"
title_in_english: "<English title verbatim from the commentary frontmatter>"
author: "<Tibetan author verbatim>"
author_in_english: "<English author verbatim>"
source_file: $COMMENTARIES/<filename>.md
language: bo
citation_form: segment | line
claim_count: <integer — total claims in this file>
status: draft
---

## Claims — <title_in_english>

**Commentary:** `<registered-id>` · <author_in_english>
**Source:** [`<filename>.md`](../../$COMMENTARIES/<filename>.md)
**Citation form:** <one sentence stating how the `§` numbers in this file resolve
to the source — segment numbers carried in the source text, or line numbers.>

> Every claim below is drawn from this commentary alone. No claim originates in
> the root text, in another commentary, or outside `$SOURCES/`.

---

### A. Framing claims

<Claims the commentator makes about the text as a whole before glossing it:
what the praise is, who spoke it, how it is divided, what the commentary
intends to do, lineage and transmission statements.>

#### A1. <short label>
**བོད་ཡིག:** <the claim in the commentator's own Tibetan wording — quoted or
minimally compressed, never rephrased into other vocabulary>
**English:** <one-line gloss>
**Type:** structural
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

#### A2. <short label>
...

---

### B. Word and phrase glosses

<Claims that explain what a word or phrase means: etymologies, ཚིག་འགྲེལ,
synonym substitutions, grammatical readings.>

#### B1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** etymology | word-gloss | grammar
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### C. Identification and iconography claims

<Claims identifying a figure, colour, implement, posture, retinue, seat, or
ornament, and claims about what each stands for.>

#### C1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** iconography | identification
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### D. Doctrinal claims

<Claims about doctrine: the pāramitās, the kāyas, emptiness, the grounds and
paths, the two accumulations, karma, the nature of mind.>

#### D1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** doctrinal
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### E. Activity and function claims (ཕྲིན་ལས)

<Claims about what the deity does: what is pacified, subdued, increased,
magnetised; which obstacles are removed; which beings are protected.>

#### E1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** activity
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### F. Practice and ritual claims

<Claims instructing practice: visualisation sequence (དམིགས་རིམ), mantra
recitation, offerings, timing, posture, number of repetitions.>

#### F1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** practice | ritual | mantra
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### G. Benefit claims (ཕན་ཡོན)

<Claims about results of recitation or practice: what is averted, obtained,
purified, accomplished, and under what conditions.>

#### G1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Type:** benefit
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### H. External attributions

<Claims the commentator attributes to a named source outside this commentary:
a tantra, a sūtra, a named master, an oral instruction. Record the attribution
as the commentator states it. Do not verify, correct, or expand the reference.>

#### H1. <short label>
**བོད་ཡིག:** <…>
**English:** <…>
**Attributed to:** <the source exactly as the commentator names it>
**Type:** attribution
**Cite:** ($COMMENTARIES/<filename>.md §<n>)

---

### I. Internal tensions

<Only if the commentary states two positions that do not sit together, or
offers an alternative reading with འམ། / གཞན་དག་ན་རེ། / ཁ་ཅིག་ན་རེ།. Mark each
with ⚑ and record both positions with their own citations. If the commentary
is internally consistent throughout, write "None observed." and keep the
heading.>

⚑ **I1. <short label>**
- **Position 1:** <Tibetan> — (…md §<n>)
- **Position 2:** <Tibetan> — (…md §<n>)
**English:** <one line stating what the tension is>

---

### Coverage log

| Source range | Claims extracted | Notes |
|---|---|---|
| §1–§<n> | A1–…, B1–… | |
| §<n>–§<n> | … | |

**Segments yielding no claim:** <list ranges that are pure root-text quotation,
colophon, or scribal matter, so a reviewer can see nothing was skipped silently.>
```

---

### Rules

1. **One commentary per file, read in isolation.** Do not open a second commentary while extracting. Do not consult the root text to decide what a passage means. If the commentary quotes the root text, the quotation is context for the claim, not itself a claim.
2. **No root-text-derived organisation.** Claims are grouped by the categories A–I above, never by root verse number. A claims file must be readable without the root text open.
3. **The commentator's own vocabulary, verbatim.** Quote the Tibetan as written. Compression is allowed; substitution is not. If he writes བདུད་སྡེ་འཇོམས་པས་ན་དཔའ་མོ།, the claim reads བདུད་སྡེ་འཇོམས་པས་ན་དཔའ་མོ། — never "she is heroic because she conquers māras" in Tibetan paraphrase.
4. **Every claim carries a citation.** A claim with no `($COMMENTARIES/<filename>.md §<n>)` reference is not a claim — delete it. This is the §8 hard rule of `$RAILS/About Rails.md`.
5. **English is a gloss, not a translation.** One line, plain, for orientation only. It never adds information absent from the Tibetan and is never cited from.
6. **Exhaustive, not selective.** Every distinct assertion gets its own entry, including ones that merely restate a root phrase in other words — that restatement *is* the commentator's reading. Splitting is preferred to merging: two assertions in one sentence become two claims.
7. **No parametric knowledge.** Never add a fact about Tārā, a tantra, a lineage, or an iconographic convention that this commentary does not state. If the commentator's reference is obscure, record it as written and leave it obscure.
8. **Never mark `status: complete`.** This skill writes `status: draft`. Only a domain specialist promotes a claims file.
9. **Do not modify `$SOURCES/`.** This skill reads the commentary and writes only to `$CLAIMS/raw/`.
10. **Empty categories are kept, not deleted.** If a commentary makes no ritual claims, section F remains with the single line `None.` — the absence is itself a finding about that commentary.

---

### Procedure

#### Step 1 — Load the commentary

a. Read the full frontmatter of the target file in `$COMMENTARIES/`.
b. Record `registered_id`, `title`, `title_in_english`, `author`, `author_in_english`.
c. If `registered_id` is absent, stop and report; run `frontmatter` (Variant 2) first.

#### Step 2 — Determine the citation form

a. Inspect the body of the commentary.
b. If blocks carry leading segment numbers (`2 དང་པོ་ནི། …`), set `citation_form: segment`; `§<n>` refers to that number.
c. If blocks carry no numbers, set `citation_form: line`; `§<n>` refers to the file's line number.
d. If blocks carry Obsidian block IDs (`^<n>`), set `citation_form: segment` and cite `#^<n>` in the standard `About Rails` §8 form instead of `§<n>`.
e. State the resolved form in the **Citation form** line of the output header.

#### Step 3 — Read the commentary in full, in order

a. Read from the first block to the last. Do not sample, skim, or jump to the sections that look substantive.
b. Read in contiguous chunks sized so that no chunk is truncated mid-argument.
c. Keep a running note of the source range covered — this becomes the Coverage log.

#### Step 4 — Extract claims chunk by chunk

For each chunk:

a. Identify every distinct assertion the commentator makes.
b. For each assertion, write the Tibetan in his own wording, then the one-line English gloss.
c. Assign it to exactly one category A–I. When an assertion could sit in two categories, place it in the more specific one (C over D, F over E).
d. Attach the segment or line citation.
e. Where the commentator marks an alternative view (འམ། / གཞན་དག་ན་རེ། / ཁ་ཅིག་ན་རེ།), record it in section I with ⚑ as well as in its own category.

#### Step 5 — Number the claims

a. Number sequentially within each category: `A1, A2, …`, `B1, B2, …`.
b. Numbers are stable identifiers — never renumber an existing claims file when appending.

#### Step 6 — Write the Coverage log

a. Record each source range against the claim IDs drawn from it.
b. List explicitly any ranges that yielded no claims, with the reason (root-text quotation, colophon, scribal matter).

#### Step 7 — Write the file

a. Write to `$CLAIMS/raw/<registered-id>.md`, creating the directory if needed.
b. Fill `claim_count` with the total across all categories.
c. Set `status: draft`.

#### Step 8 — Self-verification

a. Confirm every `###` claim heading has a `**Cite:**` line.
b. Confirm no claim text mentions another commentary or the root text file.
c. Confirm every category heading A–I is present, including empty ones.
d. Confirm the Coverage log's ranges span the whole source file with no unexplained gap.

---

### Completion check

- [ ] Exactly one commentary was read, in isolation, from first block to last
- [ ] Output written to `$CLAIMS/raw/<registered-id>.md` with `<registered-id>` matching the source frontmatter
- [ ] Frontmatter complete: `registered_id`, `title`, `author`, `source_file`, `citation_form`, `claim_count`, `status: draft`
- [ ] All nine category headings A–I present; empty ones carry `None.` rather than being deleted
- [ ] Every claim has a Tibetan statement, an English gloss, a `**Type:**`, and a `**Cite:**`
- [ ] Every citation resolves to a segment or line that actually exists in the source file
- [ ] No claim draws on the root text, another commentary, or parametric knowledge
- [ ] Alternative or conflicting positions recorded in section I with ⚑
- [ ] Coverage log accounts for the entire source file, including segments that yielded nothing
- [ ] `claim_count` equals the number of claim entries actually present
- [ ] `$SOURCES/` unmodified

---

## After this skill

`claims-consolidate` reads every commentary's claims file for one topic and builds the
question-driven topic page, then audits it.
