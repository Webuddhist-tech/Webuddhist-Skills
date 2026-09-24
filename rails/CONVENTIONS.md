# Annotation Conventions — Block IDs, Tag Schemes and Translation History

The authoritative reference for how a WeBuddhist text is marked up. Every skill
under `rails/` and `library/` implements this document. When a skill and this
document disagree, this document wins — fix the skill.

This file exists because the same job was re-implemented in four vaults with
four slightly different tag vocabularies. There is one vocabulary. It is here.

---

## 1. Content block IDs — the citation unit

Every verse or discrete prose block ends with a block ID. This is the only
mechanism for verse-level cross-referencing (`[[file#^1-23]]`).

```
[verse or prose block] ^1-1
```

- Placed at the end of the **last line** of the block, preceded by one space.
- **No zero-padding.** `^6-33`, never `^06-033`.
- The scheme in use is declared per file in the `verse_id_format` frontmatter
  field, so a parser never has to guess.

Two schemes exist side by side.

### 1a. `chapter-verse` — Tibetan, Pāli, Chinese, English, and the generic path

`^chapter-verse`, e.g. `^1-1`, `^6-33`. Verse numbers restart at 1 in each
chapter. Content before chapter 1 uses `^0-N`.

### 1b. Four-zone scheme — Sanskrit only

Sanskrit editions carry front matter, chapter intros and colophons that the
flat scheme cannot address, so they use zones:

| Zone | Symbol | Content ID | Heading ID |
|---|---|---|---|
| Pre-title | `T` | `^T-1`, `^T-2` … | — |
| Front matter | Roman numeral | `^I-1`, `^I-2` … | `^I-0`, `^II-0` … |
| Chapter intro | — | `^N-I`, `^N-II` … (chapter-relative) | — |
| Main verses | Arabic numeral | `^N-V` (`^1-1`, `^6-134`) | `^N-0` |
| Chapter colophon | lowercase letter | `^N-a`, `^N-b` … | — |
| Book colophon (after the last chapter) | lowercase letter | `^a`, `^b` … | — |

**Interpolated verses** — when a source edition repeats a verse number
(`॥24॥ … ॥24॥`), the second occurrence takes `^C-Vx1`, the third `^C-Vx2`. The
counter always starts at `1`, even for a single duplicate. Never a bare `^C-Vx`.

**Book title ID.** The generic rule below says the `#` title line takes no ID.
Sanskrit is the one documented exception: when the book *is* the root (nothing
above it), `#` takes `^0`. Only when the book sits inside a larger collection —
so `##` is the book level — does `#` go unlabelled.

---

## 2. Heading anchors — the `-0` slot

Headings are **editorial structure added to the text**, not original content.
To mark that distinction and to guarantee no collision with content IDs, every
heading block ID ends in **`-0`**. The zero slot is reserved for the heading;
original content in that section always starts at `1`.

| Level | Markdown | Purpose | Block ID | Example |
|---|---|---|---|---|
| 1 | `#` | Title of the work | none (see §1b) | `# Bodhisattvacaryāvatāra` |
| 2 | `##` | Chapter | `^N-0` | `## 1. ལེའུ་དང་པོ། ^1-0` |
| 3 | `###` | Section | `^N-N-0` | `### 1.2 Some Section ^1-2-0` |
| 4 | `####` | Sub-section | `^N-N-N-0` | `#### 1.2.3 Sub-section ^1-2-3-0` |

```markdown
## 0. Introduction ^0-0

༄། །བྱང་ཆུབ་སེམས་དཔའི་སྤྱོད་པ་ལ་འཇུག་པ་བཞུགས་སོ། ། ^0-1

## 1. ལེའུ་དང་པོ། ^1-0

བདེ་གཤེགས་ཆོས་ཀྱི་སྐུ་མངའ་སྲས་བཅས་དང་། །
ལུང་བཞིན་མདོར་བསྡུས་ནས་ནི་བརྗོད་པར་བྱ། ། ^1-1

### 1.2 Some sub-section ^1-2-0

First prose block. ^1-2-1
Second prose block. ^1-2-2
```

Rules:
- Chapter `0` is always the pre-chapter introduction (`## 0. Introduction ^0-0`).
- IDs must not exceed four segments (three path segments plus the `0`).
  Flatten anything deeper.
- No zero-padding on any segment.

---

## 3. Commentary block IDs — keyed off a human label

Commentaries follow §1 and §2 with one difference in **who assigns the key**.
A `##` heading's ID in a commentary is written **by hand** by the contributor
and is never generated, edited or guessed by a skill — the contributor chooses
the label (`^1-0`, `^I-0`, `^a-0`, or any short token) to key that section to
the root text's structure. Everything beneath it is then derived from that same
label:

```markdown
# ༄༅། །ཕྱག་འཚལ་ཉེར་གཅིག་གི་བསྟོད་འགྲེལ … ^0
## དང་པོ་སྦྱོར་བ་ཚོགས་བསགས། ^1-0        ← manual, never touched
### ཚོགས་ཞིང་སྤྱན་འདྲེན་པ། ^1-1-0         ← derived
དེའང་རྗེ་བཙུན་སྒྲོལ་མའི་ཡོན་ཏན་… ^1-1      ← derived, body counter off the same label
![[bo-root-text#^1-1]]                    ← transclusion: never consumes a counter value
```

The `#` title is the one auto-generated ID (`^0`). Transclusion lines are
structural, not content — they never take an ID and never advance the body
counter.

---

## 4. `^toc-X-Y-Z` — a separate namespace

The standalone decimal outline block that `add-toc` writes at the top of a
document uses `^toc-X-Y-Z`. **This is not the same namespace as the `^N-0`
heading anchors** and the two must not be conflated: `^toc-1-2-0` indexes a
line in the outline block, `^1-2-0` indexes the actual body heading. A TOC
entry may link to its heading; it never replaces it.

---

## 5. Inline TOC wikilinks

Texts in the commentarial tradition announce their own structure inline
(*sa bcad* / ས་བཅད): a sentence enumerates the upcoming sections before
treating each one. Those phrases are original content, and they are also the
textual source of the headings. Tagging them makes that link explicit.

```markdown
## ལེའུ་དང་པོ། ^1-0
[[#^1-0|ལེའུ་དང་པོ་]]ལ་[[#^1-1-0|མདོར་བསྟན་པ་]]དང་[[#^1-2-0|རྒྱས་པར་བཤད་པ་]]གཉིས་ཡོད་པ་ལས།

### མདོར་བསྟན་པ། ^1-1-0
[[#^1-1-0|དང་པོ་མདོར་བསྟན་པ་]]ནི་འདི་དང་འདིའོ།།
```

- In the **enumeration sentence**, each announced term links forward to the
  heading it introduces: `[[#^N-N-0|term]]`.
- In the **body of a section**, the restatement of that section's title links
  to its own heading. This self-reference is deliberate: it marks the phrase as
  the textual source of the heading, so a backlink index can show, for every
  heading, every place that announced it.
- Cross-file: `[[relative/path#^N-N-0|term]]`.
- Display text is the structural term alone, not the full grammatical phrase.
- Wikilinks are the **only** inline tagging mechanism. No italics, no HTML
  spans.

This step is optional — run it only for texts that actually contain such
announcements.

---

## 6. Deprecated — `^TOC-N`

Older drafts and one-off scripts used `^TOC-N` for chapter anchors
(`## 1. … ^TOC-1`). **It is wrong.** The canonical form is `^N-0`. A parser
expecting `^N-0` does not recognise a `^TOC-N` anchor, so the text silently
ends up with no table of contents and no error. Correct any `^TOC-N` you
encounter before using the file.

---

## 7. Translation history properties

A translation that goes through more than one pass (machine draft → termbase
enforcement → commentary fact-check → translator decisions) records that history in
its own frontmatter, so the file says what was done to it without a separate log.
Use these keys; set only the ones that apply. The vault linters ignore keys they do
not know, and `status` stays `draft` until a person has reviewed the text — no skill
sets `complete`.

| Key | Set by | Meaning |
|---|---|---|
| `draft` | each pass that edits the text | integer, the current draft number |
| `draft_history` | each pass | list, one line per draft: number — what it was — where its text lives (a file path, the grade file's `<tgt>_text`, or a git commit) |
| `generated` / `revised` | first write / later passes | ISO dates |
| `rails_used` | each skill | skills and phases applied, e.g. `graded-translate (Phase 1, Phase 2); commentary-fact-check (Phase 1, Phase 2)` |
| `termbase`, `grade_file` | graded-translate | paths of the locked termbase and grade file |
| `fact_checked` | commentary-fact-check Phase 2 | ISO date of the fix pass |
| `fact_check_commentaries` | commentary-fact-check | list of commentary paths checked |
| `fact_check_consensus` | commentary-fact-check Phase 1b | path of the consensus table (when more than one commentary) |
| `fact_check_fixes_log` | commentary-fact-check Phase 2 | path of the fixes log |
| `fact_check_fixes_applied` | commentary-fact-check Phase 2 | integer |
| `fact_check_open_items` | Phase 2, then the translator | integer: split readings and judgment calls still undecided (0 when settled) |
| `translator_decisions` | the translator | integer: open items decided |
| `translator_notes` | the translator | list of one-line notes a reader should see — a reading kept against a commentary, a textual variant followed |
| `note` | each pass | one paragraph in plain language: how the text was made and what is still pending |

Example (Twenty-One Tārās, general grade, after the fact-check):

```yaml
draft: 3
draft_history:
  - 1 — DharmaMitra raw output (3-TRANSFORMATIONS/Translations/Dharmamitra/en-general/)
  - 2 — termbase-enforced (graded-translate Phase 2); text kept in grade_file en_text
  - 3 — commentary fact-check fixes applied (this file)
fact_checked: 2026-09-24
fact_check_commentaries:
  - 1-SOURCES/Commentaries/New raw data/bo-རྗེ་བཙུན་གྲགས་པ་རྒྱལ་མཚན།.md
fact_check_fixes_applied: 11
fact_check_open_items: 0
translator_decisions: 7
status: draft
```

---

## 8. Translation track folder layout

The current translation is the only note at the top of its track folder; the evidence
behind it goes in `reports/`, and machine drafts live in their own track folders.
A reader should never have to guess which file to use.

```
3-TRANSFORMATIONS/Translations/
├── 00-INDEX-current-translations.md   ← one row per language: current file, draft, checks, what's left
├── <lang>-<grade>/
│   ├── <source stem>-<lang>-<grade>.md  ← the current translation (edited in place, draft N)
│   └── reports/                       ← fact-check reports, consensus, fixes logs,
│                                         back-translation and consistency checks, comparisons
├── Dharmamitra/<tag>/                 ← machine drafts (machine-translate); raw, never edited by hand
└── Gemini/<tag>/
```

- Skills that write a report about a translation write it to `<translation-dir>/reports/`
  and link it from the translation's frontmatter (§7) by its full vault path.
- A new draft replaces the text in place (§7 records the history); never add a second
  "final" copy next to it.
- Update the index row when a translation's draft number, checks or status change.

The keywords folder (`$KEYWORDS`, the word-list work behind the translations) is laid out the same way:

```
$KEYWORDS/
├── 00-INDEX.md        ← what each file is, and which one to edit or read
├── STATE.md           ← running log
├── shared/            ← keyword-extract output (Tibetan side, used by every language)
├── <lang>/            ← one per target language: termbase, grade file, glossary
│   ├── notes/         ← working notes from building the list
│   └── references/    ← aligned reference texts (e.g. the classical Chinese version)
```

## Provenance

Consolidated from `webuddhist-library-data-pipeline/docs/reference/conventions.md`
and `docs/03-verse-ids.md` (the most complete written spec), reconciled against
the commentary ID rules in `21-taras-rails` (`Obsidian-Block-ID-to-Commentary`,
`commentary-segmentation`) and the vault rules in
`bodhisattvacharyavatara-rails/4-SYSTEM/CLAUDE.md`.
