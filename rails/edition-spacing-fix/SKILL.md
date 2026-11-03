---
name: edition-spacing-fix
description: >
  Scan a published edition on the library backend for spacing errors — words run
  together ("whomI", "forthlike", "ofthe"), no space after punctuation
  ("wheels,fire"), doubled or stray spaces, odd whitespace — record every hit in
  a mapping file, and after human review fix the approved ones in place,
  bottom-up, through PATCH /v2/editions/{id}/content without moving a single
  segment boundary. Updates the mapping as each fix lands. Dry-run by default.

  Trigger when a user reports a spacing or run-together-word error in an
  uploaded text, or asks: "check the translation for spacing errors", "users say
  words are stuck together", "fix the missing spaces in the app", "patch the
  typos in the live edition", "whomI should be whom I".
profile: rails-vault
supersedes:
  - Dzongsar-dolma-bumtsok-rails/3-SKILLS/edition-spacing-fix/SKILL.md
---

# edition-spacing-fix

Spacing errors in an uploaded translation are visible to every reader of the app, but the backend holds its own copy of the content, and every segment is a character span into that copy. Fixing the vault file does nothing for readers, and re-uploading would destroy the alignments. This skill therefore works **on the live edition**: it scans the backend's content line span by line span, writes every finding to a **mapping** before anything changes, waits for a human to approve issue by issue, then replays only the approved fixes against the backend as minimal `insert` / `delete` operations, **highest position first**. Before it offers to send anything, it replays the backend's own span arithmetic over the live spans and proves that every line and every TOC boundary still selects exactly the expected text. Correct output: the live edition reads correctly, has the same segments with the same references and the same line count, and the mapping records which fixes landed and when.

One script: `$SKILL/scripts/spacing_fix.py`.

```
scan    <note>                          GET live content + segments + TOC -> mapping (read-only)
add     <map> --segment --line --original --proposed   record a hand-found issue
decide  <map> --approve ... --reject ... --set ID=text --comment ID=text
apply   <map>                           dry run: validate + simulate, print the bottom-up plan
apply   <map> --execute                 send the PATCH calls, mark each issue fixed as it lands
verify  <map>                           GET live, confirm every fixed issue, count remaining hits
note    <map> [--file F] [--write]      mirror the fixes into a vault file (dry run by default)
toc     <map> --fix T001 [--execute]    rebuild a TOC with fixed titles; spans recalculated (dry run by default)
```

---

## Inputs

| Input | Description | Required |
|---|---|---|
| **Uploaded note** | The vault file of the published text; its frontmatter must carry `edition_id` (and `text_id` for the title check). E.g. `$TRANSLATIONS/<file>.md` | yes |
| **Credentials** | `WEBUDDHIST_API_KEY` (and optionally `WEBUDDHIST_API_BASE`, `WEBUDDHIST_APP`) in the environment, from the git-ignored `$SYSTEM/scripts/.env`: `set -a; source $SYSTEM/scripts/.env; set +a`. Never print, pass on the command line, or commit a key | for every command that touches the API |
| **Word list** | The system dictionary (`/usr/share/dict/words`). Without it `word_join` detection is off and the scan says so | for `word_join` |
| **User reports** | Any specific error a reader reported (segment + text). Check it appears in the mapping; if the detector missed it, record it with `add` | when there are reports |

## Output

- `$WORK/edition-spacing-fix/<note-stem>.spacing-map.json` — the mapping, the source of truth. Updated by every command.
- `$WORK/edition-spacing-fix/<note-stem>.spacing-map.md` — the human review table, regenerated from the JSON on every save.
- `$WORK/edition-spacing-fix/<note-stem>.scan-content.json` — the exact live content the offsets in the mapping are stated against.
- On `apply --execute`: the live edition patched in place; each issue's `status: fixed`, `fixed_at`, `ops_sent` written into the mapping as it lands.
- On `note --write` (only with confirmation): the same fixes in the vault file.

---

## Output file format

The mapping (`*.spacing-map.json`):

```json
{
  "note": "$TRANSLATIONS/<file>.md",
  "note_stem": "<file>",
  "edition_id": "…", "text_id": "…", "api_base": "https://library.webuddhist.com",
  "scan_id": "2026-09-30T15:02:11+05:30", "scanned_at": "…",
  "scan_content_sha256": "…", "content_length": 52742,
  "segments": 332, "lines": 1082, "dash_style": "closed",
  "issues": [
    {
      "id": "S005",
      "segment": "I-6", "segment_id": "…", "line": 3, "line_offset": 29, "occurrence": 0,
      "start": 1234, "end": 1239,
      "original": "whomI", "proposed": "whom I",
      "categories": ["camel_join"], "confidence": "high",
      "line_before": "You are the true friend in whomI take refuge.",
      "line_after":  "You are the true friend in whom I take refuge.",
      "decision": "pending | approved | rejected",
      "status": "open | fixed | partial | gone",
      "comment": null, "proposed_override": null,
      "fixed_at": null, "ops_sent": null, "fixed_in_scan": null, "fixed_seq": null,
      "note_fixed": []
    }
  ],
  "toc_issues":   [ { "id": "T001", "section_id": "…", "original": "Invokingthe", "proposed": "Invoking the", "status": "manual", "fix_path": "…" } ],
  "title_issues": [ { "id": "X001", "original": "…", "proposed": "…", "status": "manual", "fix_path": "PATCH /v2/texts/{text_id}" } ],
  "history": [ { "at": "…", "action": "scan | add | decide | apply | verify | note", "…": "…" } ]
}
```

`start`/`end` are offsets into the scanned live content; `line` is the index of the line span inside the segment. The review table (`*.spacing-map.md`) has one row per issue — `ID | Segment | Line | Category | Conf. | Found | Proposed | Decision | Status` — then each issue in context (line before → after), then the TOC and title issues.

Detector categories:

| Category | Catches | Fix |
|---|---|---|
| `camel_join` | lower→Upper inside a word (`whomI`, `toBuddha`), a one-letter word run into a capitalised one (`OĀryā`) | insert a space |
| `punct_no_space` | `, ; : ! ?` straight into a letter (`wheels,fire`), a sentence period into a capital (`degeneration.By`) | insert a space |
| `word_join` | an unknown word that splits into two real words this text uses (`forthlike`, `ofthe`) — only on English lines, never on mantras | insert a space |
| `double_space`, `space_before_punct`, `edge_space` | doubled spaces, a space before `, ; : . ! ?`, whitespace at a line's edge | delete |
| `odd_space` | no-break / thin / zero-width spaces, tabs | replace with a space, or delete |
| `dash_spacing` | an em dash spaced on one side only, when the text's own style is closed | delete the stray space |
| `manual` | recorded by hand with `add` (user reports, lost letters) | as written |

---

## Rules

1. **The live edition is what gets scanned and fixed** — never infer the live state from the vault file. Scan per line span: the content stores lines with no separator, so a raw-string scan would report every line break as a missing space.
2. **Map before fixing.** No PATCH is sent for an issue that is not in the mapping with `decision: approved`. Every fix that lands is written back to the mapping (`status: fixed`, `fixed_at`, `ops_sent`) immediately, before the next call.
3. **Report to the human before any write, and wait.** Show the issues (segment, found → proposed), the TOC/title issues, and anything the detector could not propose. A dry-run summary is not consent. `apply --execute` needs an explicit yes in the conversation naming the edition and the host; `note --write` needs its own yes, because it edits a `$SOURCES/` file.
4. **Bottom-up only.** Ops are sent highest position first, so every lower offset stays valid without re-reading the content between calls.
5. **Insert and delete only, strictly inside one line span.** An insert on a line boundary would attach to the wrong line; a delete may not cross or empty a line. The script refuses both. A replace is sent as delete-then-insert at the same point.
6. **Simulate first, abort on any disagreement.** Before offering to send, the script replays the backend's span arithmetic (vendored from `openpecha-backend/database/span_database.py`, commit `7fa2564`, 2026-09-28) and requires every line to select exactly its expected text, no span dropped, the spans still tiling the content, and every TOC section still landing on line boundaries. If the backend's span code changes, re-pin the vendored functions before trusting a run.
7. **Never re-upload to fix spacing.** Re-creating an edition or segmentation loses every alignment that referenced it.
8. **Only spacing — unless the human decides otherwise.** The detector proposes spaces only. A fix that changes letters (a lost letter, a misspelling) goes in as a `manual` issue with a comment, and is sent only if the human approves that exact text.
9. **TOC titles and the text title are separate decisions.** The content PATCH cannot reach them. A TOC title is fixed only with `toc --execute`, after its own confirmation and after the content fixes have landed. That command DELETEs and re-POSTs the TOC: segments and alignments are untouched, but the TOC gets a new id. It recalculates every span — the scan-time TOC replayed through the ops sent — and requires the result to equal the backend's spans and to land on segment boundaries. It backs up the live TOC first and repoints `toc_id` in the note's frontmatter and the upload ledger. The text title goes through `PATCH /v2/texts/{id}`.
10. **False positives are rejected in the mapping, not hidden.** A rejection carries over to later scans. Only generic English/Dharma vocabulary goes into `references/allowlist.txt` — never a text-specific name or mantra syllable.

---

## Procedure

### Step 1 — Scan (read-only)

```bash
set -a; source $SYSTEM/scripts/.env; set +a
python3 $SKILL/scripts/spacing_fix.py scan "<uploaded note>"
```

Read `*.spacing-map.md`. Re-running `scan` refreshes offsets and keeps decisions, comments and fixed history.

### Step 2 — Triage (agent)

a. Confirm every error the users reported is in the mapping. If one is missing, record it:
   `spacing_fix.py add <map> --segment I-7 --line 3 --original "godsowered" --proposed "gods cowered" --comment "…"`
b. For each `review` issue, check the proposed text reads correctly in its line. Where the detector's proposal is wrong, correct it with `decide <map> --set ID=<text>` and add a `--comment` saying why.
c. Do not approve anything yourself. Note obvious false positives for the human.

### Step 3 — Report to the human and wait

List per issue: ID, segment `^ref` and line, found → proposed, and the comment where there is one. List the TOC and title issues separately with their fix route. Ask which to approve. Record the answer:

```bash
python3 $SKILL/scripts/spacing_fix.py decide <map> --approve S001,S002 --reject S007
# shorthands: --approve all | high | review
```

### Step 4 — Dry run

```bash
python3 $SKILL/scripts/spacing_fix.py apply <map>
```

It must print `all N line spans replay onto their expected text ✓ no span dropped ✓ TOC boundaries hold ✓` and the bottom-up plan. Any `ABORT` stops here: if the live content changed since the scan, re-run Step 1.

### Step 5 — Confirm and execute

State the host, edition id, number of issues and PATCH calls, and the content-length change. After a clear yes:

```bash
python3 $SKILL/scripts/spacing_fix.py apply <map> --execute
```

It stops on the first error; every issue above that point is already marked `fixed` in the mapping, and re-running `apply --execute` resumes. At the end it re-reads the edition and prints whether the content and spans equal the prediction — both must be `True`.

### Step 6 — Verify

```bash
python3 $SKILL/scripts/spacing_fix.py verify <map>
```

Every fixed issue must be confirmed live, and the segment and line counts must equal the scan's.

### Step 7 — Keep the vault in step (with confirmation)

The vault note is what any future upload is built from, so an unfixed note would bring the errors back. Show the dry-run diff, and write only after the human confirms the `$SOURCES/` edit:

```bash
python3 $SKILL/scripts/spacing_fix.py note <map>                  # dry run
python3 $SKILL/scripts/spacing_fix.py note <map> --write
python3 $SKILL/scripts/spacing_fix.py note <map> --file "<copy>.md" --write   # other copies, if any
```

### Step 7b — TOC titles (with confirmation, after Step 6)

```bash
python3 $SKILL/scripts/spacing_fix.py toc <map> --fix T001                 # dry run
python3 $SKILL/scripts/spacing_fix.py toc <map> --fix T001 --execute \
    --also "<other vault copy>.md"      # copies whose toc_id should follow
```

The dry run must print `equal to the backend's ✓ on segment boundaries ✓` and show only the approved title changes. `--execute` writes the backup and payload to `$WORK/edition-spacing-fix/`, DELETEs the old TOC, POSTs the rebuilt one, reads it back, and marks the T-issues `fixed` with `old_toc_id` and `new_toc_id`. A mapping made before scans stored the TOC needs `--snapshot <TOC JSON fetched before the content fixes>`.

### Step 8 — Report

Report: issues found, approved, fixed (with IDs), rejected, and the TOC/title issues still open, with the mapping's path.

---

## Completion check

- [ ] `scan` read the live edition; the mapping and review table exist under `$WORK/edition-spacing-fix/`
- [ ] Every user-reported error is in the mapping (detected or added with `add`)
- [ ] The human saw the issue list and decided each issue; decisions recorded with `decide`
- [ ] `apply` dry run passed every check before `--execute`
- [ ] The human confirmed `--execute` in this conversation, with the host and edition named
- [ ] After `--execute`: content and spans equal the prediction; every sent issue is `status: fixed` with `fixed_at` and `ops_sent`
- [ ] `verify` confirms every fixed issue live; segment and line counts unchanged
- [ ] TOC / title issues reported with their fix route; none patched without their own confirmation
- [ ] If a TOC was rebuilt: read-back equals the payload, exactly one TOC remains on the edition, and the new `toc_id` is in the note's frontmatter and the ledger
- [ ] The vault note updated with `note --write` only after the human confirmed it, or the gap reported
