> Bundled with `aligned-corpus-intake` from `KF-project/heart-sutra-rails/4-SYSTEM/How-to guides/Ingest a row-aligned corpus.md` (2026-10-03). Paths are the vault's literal layout; `4-SYSTEM/Skills/aligned-corpus-intake/` is this skill's folder.

# Ingest a row-aligned corpus (Google Docs → Markdown + CSV)

How to turn a text whose root, translations and commentaries were **segmented and aligned by hand in Google Docs** — two numbered documents per alignment, row *N* of one paired with row *N* of the other — into `1-SOURCES/` files: one stored segmentation per text, every human alignment carried onto it, headings first, then ids, then transclusions.

Worked example: the Heart Sūtra vault (`heart-sutra-rails`), intake of **2026-10-03**. Its manifest (`0-INBOX/raw-data/intake-manifest.yaml`) and report (`0-INBOX/heart-sutra-intake-report.md`) are the reference run — open them side by side with this guide.

The procedure is the `aligned-corpus-intake` skill, **Route B** (`4-SYSTEM/Skills/aligned-corpus-intake/SKILL.md`). This guide is the walk-through; the skill is the authority.

---

## 0. The problem, in one paragraph

Every human alignment was made against its *own copy* of the root text: each commentary's aligners cut the root into rows their own way; each translation was paired with yet another cut (sometimes another edition). The library can store **one** copy of each text with **one** segmentation. So every alignment has to be moved onto the stored segmentation **without changing any segmentation** — not the stored root's, not the commentary's, not the translation's — and without losing a single human decision.

**The solution:** don't move segment boundaries; compute a concordance. Reduce both the copy and the stored root to their letters, diff them, and let every letter of a copy row vote for the stored segment it lands in. A commentary row then transcludes the stored segment(s) its paired copy row falls in. Rows are never merged or split. (`antx`-style annotation transfer does the same diff; the concordance keeps per-row coverage and spans, so nothing is approximated silently.)

---

## 1. Before you start

1. **Get the tooling.** Copy the whole folder `4-SYSTEM/Skills/aligned-corpus-intake/` from `heart-sutra-rails` into your vault (or pull it from `rails-template` once it has been backported there — see `Sync with rails-template.md`). Route B needs, in that folder: `scripts/md_export.py`, `scripts/concordance.py`, `scripts/md_adapter.py`, `scripts/toc_rows.py`, and the updated `build_sources.py`, `vault_writer.py`, `verify.py`; `prompts/place-toc-at-rows.md`; `references/md-export-format.md`. The `toc-generate` skill is used unchanged. Python 3 with PyYAML.
2. **Put the raw data in `0-INBOX/raw-data/`**: every Doc exported with *Download → Markdown*, every metadata sheet with *Download → CSV*. Rename them so pairs are visible — the Heart Sūtra pattern:

   | File | What |
   |---|---|
   | `<p>-root-bo(display).md` | the stored segmentation of the Tibetan |
   | `<p>-root-sa(bo-sa).md` + `<p>-root-bo(bo-sa).md` | a root ↔ translation pair |
   | `<p>-root-zh(bo-zh).md` + `<p>-root-bo(bo-zh).md` | another pair (its Tibetan side cut — and edited — differently) |
   | `<p>-comm-N(root-com).md` + `<p>-root-N(root-com).md` | commentary *N* ↔ its own cut of the root |
   | `<p>-comm-N(toc).md` | optional TOC doc for commentary *N* |
   | `<p>-comm-N.csv`, `<p>-root.csv` | metadata sheets |

3. **Never edit anything in `0-INBOX/raw-data/`.** Corrections go in the manifest.

---

## 2. Decisions to take with the vault owner — before building

| Decision | Heart Sūtra answer | Why it matters |
|---|---|---|
| Which cut of each text is **stored** | the Tibetan "display" doc (32 rows) | Only it reaches the library; every other cut becomes evidence in the sidecars |
| **Direction** of each relation | Sanskrit = root (it came first); Tibetan = its translation; Chinese and all commentaries were aligned to the Tibetan → they point at the Tibetan and are uploaded that way | "Data stays true to itself": never re-point an alignment past the text it was made against |
| **Wrong-looking pairings** | three Sanskrit↔Tibetan pairings fixed (rows 2, 5, 15 — reasons in the manifest); one stray character removed (commentary 1, row 83) | Fix only on a human decision; record reason, who, when; the original stays in the sidecar |
| **A reading the copies disagree on** | the display has ཕྱིན་པ་ in ^9 and ^12, all nine commentary copies lack it → keep the display text; the variant is recorded per row and nothing after it shifts | The stored text is never edited to match a copy |
| **Where each TOC comes from** | Tāranātha: the team's TOC doc (numbered labels); the others: `toc-generate` from their own *sa bcad*; a commentary without *sa bcad*: none, with the reason | Ids are derived from the TOC, so it must exist first |
| **The root's TOC** | The root has no outline and the data no TOC for it → Lobsang Gyaltsen Sengge's outline, projected through his row alignment onto the Tibetan, and through the pairings onto the Sanskrit and the Chinese (the only outline covering title → colophon with nodes on distinct segments) | The root's ids follow its TOC too (`^1-12`), and every transclusion into it is regenerated |

Read every **short** pair (root ↔ translation) row by row before building — that is where a shifted pairing hides (Heart Sūtra: Tibetan row 14 empty, so the Tibetan of Sanskrit row 14 sat on row 15).

---

## 3. Step by step

All commands run from the vault root. `S=4-SYSTEM/Skills/aligned-corpus-intake/scripts`.

### 3.1 Look at every file

```bash
python3 4-SYSTEM/Skills/aligned-corpus-intake/scripts/md_export.py "0-INBOX/raw-data/<p>-comm-1(root-com).md"
```

Lists rows (row 0 = text before `1.`, usually the Doc's title line). Check each pair has the same number of rows and lines up at the start, middle and end. `--meta` on a `.csv` prints the metadata sheet.

### 3.2 Check the copies are the same text

```python
import sys; sys.path.insert(0, "4-SYSTEM/Skills/aligned-corpus-intake/scripts")
from md_export import read_rows; from concordance import Concordance
stored = [(str(r["row"]), r["text"]) for r in read_rows("0-INBOX/raw-data/<p>-root-bo(display).md") if r["text"].strip()]
copy   = [(r["row"], r["text"]) for r in read_rows("0-INBOX/raw-data/<p>-root-1(root-com).md") if r["text"].strip()]
print(Concordance(stored, copy).stats)
```

`copy_only` / `target_only` are letters present on one side only. Tens of letters: readings and variants (fine — recorded per row). Hundreds: look before going on.

### 3.3 Write the manifest

`0-INBOX/raw-data/intake-manifest.yaml`, in dependency order (root, its translations, then everything aligned to them). Copy the shape from the Heart Sūtra manifest or `templates/manifest.example.yaml` (Route B entries). Per work: `text`, `pair {own_side, target_side}`, `target`, `id_scheme` (`flat` for a text with no TOC, `h2` for commentaries), `title`, `toc`, `frontmatter` (from the CSV; `category_id` empty for a human), and any `pair_corrections` / `text_corrections` with `reason`, `decided_by`, `date`.

### 3.4 TOC first

For each commentary choose one:

- **`toc: {kind: labels, doc: <toc doc>, labels: [...]}`** — the TOC doc carries heading labels (e.g. `༥༽ ཤེར་ཕྱིན་གྱི་ངོ་བོ་རྒྱས་པར་བཤད་པ།`). List them **verbatim, in order**. The build places each at a row boundary and moves a label that sits inside a row out into the heading. Check the TOC doc first: a Markdown export loses the Docs' colours, so a doc whose *sa bcad* was only colour-marked arrives with no labels at all.
- **`toc: {kind: tree, id: <registered-id>, tree: 2-RAILS/Sections/Raw/toc-tree/<id>.md}`** — run `toc-generate`:
  1. `python3 $S/build_sources.py 0-INBOX/raw-data/intake-manifest.yaml --stage pre-toc` → `0-INBOX/temp/TOC-<id>/source.md` (+ `source.json`). This is the file `toc-generate` reads; its line numbers are the pointers.
  2. `toc-generate` Phases 0–C exactly as its SKILL.md says (`chunk_file.py --index-only`; one isolated subagent per chunk for Phase A, another for Phase B; `python3 $S/toc_rows.py merge <id>`; one subagent for Phase C). Tell each subagent to read the source with `sed` — the rows are single lines of up to ~19 000 characters and a file viewer truncates them.
  3. `qc_check_tree.py` (against candidates + enumerations) on the tree **before** placement — it does not strip `[[N]]` pointers and reports spurious "unattested" titles on a pointered tree.
  4. **Placement**: one isolated subagent with `aligned-corpus-intake/prompts/place-toc-at-rows.md` → `0-INBOX/temp/TOC-<id>/placement.md` (tree + `[[line]]` pointers + a TSV of opening clauses). `toc-generate`'s own prompts emit no pointers, and headings may only stand between rows — this pass supplies both. Then `python3 $S/toc_rows.py place <id>` (refuses if the subagent changed anything but the pointers).
  5. `qc_tree_vs_source.py --source 0-INBOX/temp/TOC-<id>/source.md`. Check **every** flag against the source yourself. On the Heart Sūtra, every flag that survived review was one of: several headings on one row (one row announcing a chain; several sections opening inside one long row); a section opening on a bare ordinal (`གཉིས་པ་ནི།`) with its title only in the parent's enumeration; a title only in a closing formula (`འདིས་ནི་ … བསྟན་ཏོ།`); a part placed at the passage an announcing verse names; a division count misread by the heuristic (the text says `གཉིས་ཏེ`). Write the evidence lines at the end of the QC report and `issues_after_review: 0`. Anything else → a repair round (`pass4-qc-repair.md`, isolated subagent) and placement again. A part the author announces but never opens is removed and reported (Lama Kunga 3.2.3.15.3).
  6. `python3 $S/toc_rows.py promote <id> <work-key> [--accept]` → `2-RAILS/Sections/Raw/toc-tree/<id>.md` with `pointer_source_sha1` (from `source.json`) and the placement TSV under `## Placement`; the candidates, enumerations and both QC reports move next to it. The build refuses a tree whose sha1 no longer matches.
- **`toc: {kind: projected, source_work: <commentary key>}`** — for the **root and its translations**, once the commentary TOCs are done (the projection reads them): carries one commentary's outline onto the stored root through that commentary's human row alignment, and onto each translation through its pairing. To choose the commentary, project all of them (count, per outline, how many nodes land on distinct root segments in order and whether title, homage, text and colophon are covered) and take the best fit; write the reason in the manifest. Rebuilding regenerates every transclusion into the re-keyed files.
- **`toc: {kind: none, reason: "…"}`** — no outline. A commentary whose Phase A finds only a doctrinal list (Heart Sūtra: Vairocana's "five excellences") and whose Phase B finds no division announcement has no *sa bcad*; do not build a tree from a doctrinal list — it would title the whole rest of the text with its last item.

### 3.5 Test build, verify, dry-run

```bash
python3 4-SYSTEM/Skills/aligned-corpus-intake/scripts/build_sources.py 0-INBOX/raw-data/intake-manifest.yaml --out <scratch> --report <scratch>/report.json
python3 4-SYSTEM/Skills/aligned-corpus-intake/scripts/verify.py 0-INBOX/raw-data/intake-manifest.yaml --root <scratch> --json <scratch>/verify.json
```

Every work must read `OK … missing=0`, `rows` = blocks (plus rows that were only a TOC label), `aligned_ok n/n`, `content_ok n/n`. Then run `translation-upload`'s linter and parser on a **copy** (the linter rewrites files and both write into their own folders): the only error should be the empty `category_id`; the parser must build text, edition, TOC and alignment payloads.

### 3.6 Build into the vault

Same command without `--out`; `verify.py` again on the vault. Then register the commentary ids, the `1-SOURCES/Annotations/` folder and the id deviations in the vault annex, and write the intake report (works, review items, what was not ingested and why, verifier output).

---

## 4. Ids — what the build writes

| File | Ids | Example |
|---|---|---|
| Root and translations (projected TOC) | headings `^<path>-0` from the projected outline; body `^<top-level>-<n>`; the title line `^0-1` | Tibetan `^1-13` (row 15) transcludes Sanskrit `^1-10` (row 14, a corrected pairing); Sanskrit `^1-11` (row 15) has no Tibetan counterpart; each block's row number stays in its sidecar |
| Commentaries | headings `^<path>-0` from the TOC; body `^<top-level>-<n>` counted through deeper headings; before the first heading `^0-<n>` | `## … ^2-0`, `### … ^2-1-0`, body `^2-7` |
| Any text without a TOC (`id_scheme: flat`) | `^N` = the row number in the alignment Doc | only if the vault owner wants no TOC |

Transclusions sit on their own lines directly before the block they belong to. A commentary row that comments on part of a stored segment repeats that segment's transclusion (the library's parser counts only `![[…]]` embeds attached to a block). The sidecar keeps the exact character span.

---

## 5. Pitfalls met on the Heart Sūtra

- The older `parallel` adapter **merges rows** that share a target — never use it for this format; `md_rows` keeps every row as one block.
- `toc-generate`'s Phase C prompt writes no `[[line]]` pointers although its checker and ingest script expect them → the placement pass (3.4 step 4).
- A TOC doc's numbers can be one running count across levels (`༢༽ …`, `༼༡༽ …`, `༤༽ …`): the doc does not state the nesting, so the labels go in flat rather than inventing a hierarchy.
- A TOC doc may contain author's sentences the aligned commentary lacks (three *sa bcad* sentences in Tāranātha's): report them; do not add text to the commentary.
- `translation-upload`'s current upload script requires *identity* alignment (translation `^N` = root `^N`). A real translation pairing is rarely pure identity (translator-only rows, corrected pairings, a 111-row Chinese against a 32-row Tibetan). The parser builds the pairs correctly; the upload step needs to accept non-identity alignments for these files.
- Edition variants between two Tibetan copies (spellings, ཨོཾ in the mantra, a missing གཟིགས) are expected: `verify.py` lists rows below 90 % letter agreement as variants, and fails only below 50 %.
