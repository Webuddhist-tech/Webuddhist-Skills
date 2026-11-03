---
name: yigchung-upload
description: >
  Parse the <small>…</small> yigchung (small-script rubric) marks out of an
  already-uploaded root text or translation, turn each one into a span over the
  live edition content — tags excluded — and attach them to the edition as
  yigchung annotations. Every span is proven against the upload parser and the
  live content before anything is sent. Dry-run by default; never executes
  without explicit human confirmation.

  Trigger this skill when the user wants the small-print marks published:
  "upload the yigchungs", "add the small annotations to the edition", "push the
  <small> marks to the backend", "annotate the yigchung spans", "the small text
  should be an annotation".
profile: rails-vault
supersedes:
  - Dzongsar-dolma-bumtsok-rails/3-SKILLS/yigchung-upload/SKILL.md
---

# yigchung-upload

A yigchung (ཡིག་ཆུང, small script) is a rubric or instruction set in small type — marked in the vault with `<small>…</small>`. The upload parser strips those tags so they never enter the edition content; this skill puts the information back as **yigchung annotations**: one span per mark, `start` inclusive and `end` exclusive, over the edition content, covering exactly the text between the tags and never the tags themselves.

One script, `$SKILL/scripts/yigchung_upload.py`:

```
GET  /v2/editions/{edition_id}/content      <- the offsets must be offsets into this
GET  /v2/editions/{edition_id}/yigchungs    <- what is already there
POST /v2/editions/{edition_id}/yigchungs    <- {"span": {"start": N, "end": M}}, once per mark
```

**Why the offsets can be trusted.** The script does not re-derive the content its own way. It imports the upload parser (`translation-upload/scripts/parser-root-text/parser.py`) and replays its content build line for line, carrying the tag positions along. Then, before any plan is printed, it requires the replayed content to equal the parser's content *and* the live edition content character for character, and the text under every span to equal the text between its tags. A note edited since upload, or an edition that is not this note's, fails the second check instead of receiving shifted spans.

---

## Inputs

| Input | Description | Required |
|---|---|---|
| **Note** | A root text or translation in `$SOURCES/` that has **already been uploaded** — its frontmatter carries `edition_id` — and whose body marks yigchungs with `<small>…</small>` | yes |
| **Upload parser** | `$SKILLS/translation-upload/scripts/parser-root-text/parser.py`, which must strip `<small>` tags (it defines `SMALL_TAG_RE`). The script refuses to run otherwise | yes |
| **Credentials** | The API key in a git-ignored `$SYSTEM/scripts/.env`; `set -a; source $SYSTEM/scripts/.env; set +a` before running. Never print, pass on the command line, or commit one | for every run except `--no-live` |

If the note has no `edition_id`, stop: upload it first with `root-text-upload` or `translation-upload`.

## Output

- `$SKILL/scripts/output/<note-stem>.yigchungs.json` — the payload: the list of spans.
- `$SKILL/scripts/output/<note-stem>.yigchung-review.md` — one row per span with its segment, offsets and the exact text it covers, for review.
- On `--execute`: the yigchung ids, appended per edition to `$SKILL/scripts/upload_ledger.json` after every call.

Nothing under `$SOURCES/` is written.

---

## Output file format

`<note-stem>.yigchungs.json`:

```json
[
  {"span": {"start": 0, "end": 49}},
  {"span": {"start": 17411, "end": 17437}}
]
```

`<note-stem>.yigchung-review.md`:

```markdown
# Yigchung review — <note file name>

edition `<edition_id>` · <N> spans · content <chars> chars · live match: yes

| # | segment | start | end | text under the span |
|---|---|---|---|---|
| 1 | I-1 | 0 | 49 | ༄༅། །བླ་མ་དང་འཇམ་པའི་དབྱངས་ལ་གུས་པས་ཕྱག་འཚལ་ལོ། ། |
```

A `⚑` after the segment marks a span that is not confined to its own block's segment — legitimate for a mark that runs across blocks, but read it.

`upload_ledger.json`:

```json
{
  "<edition_id>": {
    "source_file": "<note path>",
    "yigchungs": [{"id": "<yigchung id>", "start": 0, "end": 49, "ts": "<iso time>"}]
  }
}
```

---

## Rules

1. **Spans never include the tags.** `start` is the offset of the first character after `<small>`, `end` the offset of `</small>`, both in the edition content — which contains no tags.
2. **Dry run first, always.** It writes the payload and the review file and runs every check; any failed check aborts before a plan is printed.
3. **The live content is the truth.** If the replayed content differs from the live edition content by a single character, do not upload — the note changed after upload, or the ids point elsewhere. Fix that first; never adjust offsets by hand.
4. **Review before executing.** Read the review file: every span on the segment it belongs to, the text under it exactly the small-print text, no span starting or ending mid-word. Whitespace just inside a tag at a line end is trimmed by the parser, so the span ends at the last visible character — that is correct, and the checks line reports how many such marks there are.
5. **Never pass `--execute` without explicit human confirmation in the conversation.** State the host, edition id and span count, and wait for a clear yes.
6. **Never duplicate.** Spans already live are skipped. If the edition holds yigchungs that are not in the payload, stop and report — a human decides whether to delete them (`DELETE /v2/yigchungs/{id}`).
7. **Marks in headings are not annotated.** Headings are not edition content; the script warns and skips them.
8. **One edition per invocation**, then `--verify`.

---

## Procedure

### Step 1 — Dry run

```bash
set -a; source $SYSTEM/scripts/.env; set +a
python3 $SKILL/scripts/yigchung_upload.py "<note>"
```

Read the checks block. All three lines must be `True`: replayed content equals the upload parser's content, equals the live edition content, and every span's text equals its tag text.

### Step 2 — Review

Open `scripts/output/<note-stem>.yigchung-review.md` and check the rules in Rule 4. For a translation, also confirm its spans fall on the same block ids as the root's — a rubric in the root is normally a rubric in its translation.

### Step 3 — Confirm with the human

State the host, the edition id, the span count, and anything the review turned up. Wait for a clear yes.

### Step 4 — Execute

```bash
python3 $SKILL/scripts/yigchung_upload.py "<note>" --execute
```

It re-runs every check first, then posts one span per call, recording each id in the ledger. It stops on the first error; re-running resumes, because spans already live are skipped.

**A 201 is not proof of a write.** The backend's create query only writes when a `MarkType {name: 'yigchung'}` node exists, and returns a generated id either way. If that node is missing, every POST "succeeds" and nothing is stored. So the script reads the first yigchung back by id and stops if it is not there, and reads the whole list back at the end. If it stops this way, the backend needs that node seeded — nothing in the vault is wrong and nothing needs cleaning up.

### Step 5 — Verify

```bash
python3 $SKILL/scripts/yigchung_upload.py "<note>" --verify
```

The live yigchungs must equal the payload: none missing, none unexpected.

### Step 6 — Report and record

Report per edition: edition id, spans created, verify result. Commit the ledger.

---

## Flags

| Flag | Effect |
|---|---|
| *(none)* | dry run — extract, check against the parser and the live content, write payload and review file, send nothing |
| `--execute` | post the spans not yet live; needs human confirmation |
| `--verify` | compare the live yigchungs with the payload and exit |
| `--no-live` | offline: skip the live checks (the live-content check is lost — never execute from an offline run) |

Environment: `WEBUDDHIST_API_KEY` (`X-API-Key`), `WEBUDDHIST_APP` (optional `X-Application`), `WEBUDDHIST_API_BASE` (default `https://library.webuddhist.com`), `LEDGER_PATH`.

---

## Completion check

- [ ] Note carries `edition_id`; the upload parser strips `<small>` tags
- [ ] Dry run: all three checks `True`, no ERROR lines
- [ ] Review file read: every span on its own segment, text exactly the small-print text
- [ ] Human confirmed `--execute` in this conversation, with host and edition named
- [ ] `--execute` completed; ids in the ledger
- [ ] `--verify`: none missing, none unexpected
- [ ] Nothing under `$SOURCES/` changed
