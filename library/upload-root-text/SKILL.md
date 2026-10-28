---
name: upload-root-text
description: >
  Pipeline 2 agent wrapper around tools/run_upload.py (lint -> parse ->
  upload) for a completed texts/<text-id>/annotated.md. Invoked via
  /upload texts/<text-id>/. Defaults to dry-run + --offline; never passes
  --execute without explicit human confirmation in the conversation, and
  always confirms the target DATA_PIPELINE_API_BASE first. On a confirmed
  execute run, flips the text's ledger.json entry to "uploaded", then offers
  the final WeBuddhist library ingestion trigger
  (tools/uploader/webuddhist_ingest.py — the WeBuddhist backend pulls the
  text from OpenPecha by text_id; see docs/09-webuddhist-ingest.md).

  Trigger this skill whenever an annotated text should move toward the
  backend — "upload this text", "push it to the backend", "run pipeline 2",
  "lint and parse the annotated file", "do a dry run of the upload" — not
  just when the user types /upload.
profile: library-pipeline
supersedes:
  - webuddhist-library-data-pipeline/skills/upload-root-text/SKILL.md
  - data-pipeline/skills/upload-root-text/SKILL.md
---

# upload-root-text

Pipeline 2 agent wrapper around `tools/run_upload.py`, the deterministic
lint → parse → upload chain. This skill does not implement any lint, parse,
or upload logic itself — that all lives in `tools/linter/`, `tools/parser/`,
and `tools/uploader/upload.py`, which `tools/run_upload.py` shells out to in
sequence. This skill's job is to invoke that chain correctly, read its
output back to the human in plain language, and enforce the hard rule below.

Invocation: `/upload texts/<text-id>/`

---

## Prerequisite

`texts/<text-id>/annotated.md` must exist and be the product of a completed
Pipeline 1 run (`skills/annotate-root-text/SKILL.md`'s `validate` step
`"done"` — i.e. the human-review checkpoint after validation was already
confirmed). If `annotated.md` is missing, stop and point at
`/annotate <path> [text-id] [language]` instead of proceeding — do not
attempt to lint/parse/upload a `work/` intermediate.

---

## Default invocation — dry-run, offline

Always run this first, with no flags beyond `--offline`:

```bash
python3 tools/run_upload.py texts/<text-id>/ --offline
```

- **Dry-run is the default** for both `tools/run_upload.py` and
  `tools/uploader/upload.py` — no `--execute` flag means nothing is ever
  POSTed and `annotated.md`'s frontmatter is never touched.
- **`--offline` is required** while `DATA_PIPELINE_API_BASE` is the
  unreachable dummy default (`http://dummy-backend.example.invalid/v2` — see
  `tools/common/config.py`). It skips the linter's persons-API and BDRC
  network lookups; without it, the linter will hang or fail trying to reach
  a host that doesn't exist. Only drop `--offline` once
  `DATA_PIPELINE_API_BASE` points at a real, reachable backend (see
  Environment setup, below) — check this before ever omitting the flag.

This one command chains all three tools in order and writes:

```
texts/<text-id>/payloads/<stem>.lint.json          # or .lint.errors.json on failure
texts/<text-id>/payloads/<stem>.text.json
texts/<text-id>/payloads/<stem>.edition.json
texts/<text-id>/payloads/<stem>.toc.json
texts/<text-id>/upload-report.json
texts/<text-id>/status.json                        # updated with lint/parse/upload step states
```

If lint fails, `run_upload.py` aborts before parse/upload run at all — see
below for how to read the error file.

---

## Reading `payloads/<stem>.lint.errors.json`

Produced only when lint fails (`status: "error"`). Shape:

```json
{
  "status": "error",
  "source": "<absolute path>",
  "validated_at": "<ISO timestamp>",
  "error_count": <N>,
  "errors": ["<message>", "..."],
  "notes": ["<info-level message>", "..."],
  "warnings": ["<person-lookup warning>", "..."],
  "resolved": { "...partial text_input built so far..." }
}
```

Summarise `error_count` and every string in `errors` to the human — each one
is already a specific, actionable message (e.g. `"category_id: required
field missing"`, `"source: required; add a source field with the text's
URL"`, `"language: required field missing"`). Common patterns and where to
send the human to fix them:

| Error pattern | Cause | Fix |
|---|---|---|
| `title` / `language` / `category_id` / `source` / `edition_type` / `author` `: required field missing` | A required frontmatter field from `docs/reference/frontmatter-schema.md` is absent in `annotated.md` | Re-run `skills/root-text-frontmatter/SKILL.md` (or edit the frontmatter directly), then re-run the lint step |
| `lang_tag: "<x>" is not a known tag` | Frontmatter uses a non-canonical `lang_tag` (e.g. `sk` instead of `sa` for Sanskrit) | Fix to the schema's code — see `docs/reference/frontmatter-schema.md` and `docs/reference/conventions.md` |
| `alt_titles: required (not found in source or BDRC)` | Only happens **without** `--offline` — with `--offline` this is an `INFO` note, not an error | Confirm you passed `--offline`; if intentionally online, set `alt_titles` explicitly in frontmatter |
| `toc: no headers found in document` | Body has no `##`/`###` headings for the parser to build a TOC from | Re-run `skills/format-*-root-text/SKILL.md` / `skills/add-toc/SKILL.md` |
| block reference errors (`missing reference (^chapter-index)`) | A content block lacks its trailing block ID | Re-run the `verse_ids` step of Pipeline 1 |

After fixing, re-run the same `--offline` dry-run command — `run_upload.py`
re-lints by default (pass `--skip-lint` only to reuse a still-valid prior
`lint.json` without editing the source in between, e.g. when only re-running
the parse step after a parser code change).

`notes` (INFO-level) are expected in offline mode — e.g. `"alt_titles: not
resolved (offline mode -- BDRC lookup skipped...)"` — these are not failures,
just report them as informational.

---

## Reading the dry-run report

`tools/uploader/upload.py` (invoked by `run_upload.py`'s step 3) writes
`texts/<text-id>/upload-report.json`:

```json
{
  "mode": "dry-run",
  "api_base": "<DATA_PIPELINE_API_BASE at run time>",
  "file_type": "root-text",
  "source": "<path to annotated.md>",
  "requests": [
    {"step": "text",    "method": "POST", "url": "...", "payload_bytes": N, "payload_keys": [...], "status": "planned"},
    {"step": "edition",  "method": "POST", "url": "...", "payload_bytes": N, "payload_keys": [...], "status": "planned"},
    {"step": "toc",      "method": "POST", "url": "...", "payload_bytes": N, "payload_keys": [...], "status": "planned"}
  ]
}
```

Root text uploads are always exactly these 3 planned requests, in this
order, with `status: "planned"` — no alignment step (that only applies to
`file_type: translation`, out of scope for this repo). Summarise for the
human: mode (dry-run), the 3 planned requests with their method + resolved
URL (the URL still contains literal `{text_id}` / `{edition_id}` placeholders
in dry-run, since nothing has actually been created yet), and confirm
`annotated.md`'s frontmatter is untouched (dry-run never patches it). If
`run_upload.py`'s own console output ended with "Dry run complete -- no
requests were sent, frontmatter untouched.", the run is clean.

---

## HARD RULE — `--execute`

**Never pass `--execute` to `run_upload.py` or `upload.py` unless the human
has explicitly confirmed it in this conversation.** A dry-run summary is not
consent. Before asking for that confirmation:

1. **Confirm the target `DATA_PIPELINE_API_BASE` with the human first** —
   state plainly what it currently resolves to (check the environment /
   `.env`, don't assume). It defaults to the dummy, unreachable
   `http://dummy-backend.example.invalid/v2`; the documented production
   value is documented in `config/settings.example.env` and `docs/08-upload.md`,
   but it is only set via environment variable — never hardcode it or set it
   yourself. If it's still the dummy default, executing will just fail to
   connect (safe, but pointless) — flag that to the human rather than
   quietly running `--execute` against a host that isn't real. If it's a
   real host, make sure the human means to upload to *that* host right now.
2. Ask directly: "Ready to execute the upload against `<API_BASE>` — this
   will POST 3 requests and patch `text_id`/`edition_id`/`toc_id` into
   `annotated.md`. Confirm?" Wait for a clear yes.
3. Only then run:
   ```bash
   python3 tools/run_upload.py texts/<text-id>/ --execute --offline
   ```
   (keep `--offline` unless the human has separately confirmed persons-API /
   BDRC lookups should run live too — it only affects the lint step, not
   whether the upload itself executes).

This mirrors the "Explicit permission required" rule for sending
requests/publishing on the user's behalf — an execute run is an irreversible
write to a real backend once it's a real backend, and must never happen
silently.

### After an execute run

Report the patched-back IDs. `tools/uploader/upload.py` patches
`text_id`, `edition_id`, and `toc_id` into `annotated.md`'s frontmatter as
each POST succeeds (see `docs/reference/frontmatter-schema.md`'s "post-upload
state" example), and records the same in `upload-report.json` under each
request's `response_id` field with `"status": "ok"`. Summarise: which IDs
were assigned, and confirm `annotated.md` now carries them. If any step
errored mid-sequence, `had_error` stops the chain — report exactly which
step failed and that earlier steps' IDs (if any) are still patched into the
file (the patch happens incrementally, per step, not atomically at the end).

**Then update the ledger** — only if all 3 requests succeeded: in
`ledger.json` (repo root), set the text's entry to `status: "uploaded"`,
`uploaded: <today's ISO date>`. If the run errored mid-sequence, leave the
entry as `"annotated"` — the ledger records completed uploads, not attempts.
If the text has no ledger entry at all (annotated before the ledger existed,
or ingested from an explicit path outside `input/`), add one now with what
`status.json` and the frontmatter know, rather than skipping the record.

---

## Final step — WeBuddhist library ingestion (after a confirmed upload)

Getting the text into the **WeBuddhist library backend** is a separate,
last trigger — the WeBuddhist backend pulls the text from OpenPecha by
`text_id`; it accepts no payload files (read `docs/09-webuddhist-ingest.md`
before the first run).

1. **Dry-run first, always:**
   ```bash
   python3 tools/uploader/webuddhist_ingest.py texts/<text-id>/
   ```
   Show the human the plan — endpoint, and especially the two enum names
   (`destination_url`, `openpecha_api_url`). Confirm `openpecha_api_url`
   names the same OpenPecha environment the upload above actually went to —
   a mismatch makes the WeBuddhist backend pull from the wrong host.
2. **Execute only on the same explicit-confirmation contract as
   `--execute` above** — a human, in this conversation, confirming the
   enum pair and destination. Requires `WEBUDDHIST_ADMIN_TOKEN` (see
   Environment setup; never echo the token):
   ```bash
   python3 tools/uploader/webuddhist_ingest.py texts/<text-id>/ --execute
   ```
3. **Report the response**: a dict of newly created texts (the backend also
   ingests related translations/commentaries it discovers — list them), or
   `"All texts are already uploaded"` (idempotent, fine). Then record
   `"ingested": <today's ISO date>` on the text's `ledger.json` entry
   (status stays `"uploaded"`).

---

## Environment setup

Before the first real (non-dummy) run:

1. Copy `config/settings.example.env` to `.env` (or export the same
   variables directly) and fill in real values — primarily
   `DATA_PIPELINE_API_BASE`, plus the `WEBUDDHIST_*` variables for the
   ingestion trigger (`WEBUDDHIST_API_BASE`, `WEBUDDHIST_DESTINATION`,
   `WEBUDDHIST_OPENPECHA_API`, and — for execute only —
   `WEBUDDHIST_ADMIN_TOKEN`, which must never be committed).
   `tools/common/config.py` is the only place any tool reads these from.
2. `pip install -r tools/requirements.txt` (PyYAML, rdflib, pyewts).

Neither step is needed for the default offline dry-run against the dummy
backend — that works out of the box.

---

## Provenance

New to this repo. `tools/run_upload.py`, `tools/uploader/upload.py`, and
`tools/linter/` are the deterministic tools this skill wraps (see their own
provenance notes — adapted from the vault's `4-SYSTEM/scripts/linter-root-text/`,
`parser-root-text/`, and `upload_root_text_translation.py`). This wrapper
skill itself has no vault predecessor: the vault's upload script had no
agent-facing wrapper and no dry-run-by-default / execute-confirmation
contract — both are new here, driven by this repo's "backend URL is a
configurable dummy for now" decision (see the implementation plan's
"Confirmed decisions").
