# library/ — WeBuddhist library ingestion and upload

Skills that take an annotated markdown file and get it into the **WeBuddhist
library backend**: lint it against the parser's expectations, build the JSON
payloads, and upload, receiving back the backend-assigned `text_id` /
`edition_id` / `toc_id`.

Everything in `rails/` is about *making* a good text. Everything here is about
*shipping* it.

---

## These skills require the pipeline repo

**They do not run standalone.** Each one drives Python that lives in
`webuddhist-library-data-pipeline`, not in this repo:

| Skill | Calls |
|---|---|
| `lint-annotations` | `tools/linter/lint_text_input.py` |
| `upload-root-text` | `tools/run_upload.py`, `tools/uploader/upload.py`, `tools/uploader/webuddhist_ingest.py`, `tools/common/config.py` |
| `annotate-root-text` | orchestrates the `rails/` annotation skills, then `tools/run_upload.py` |

Run them from inside a checkout of
[`OpenPecha/webuddhist-library-data-pipeline`](https://github.com/OpenPecha/webuddhist-library-data-pipeline).
The skill text is canonical here; the tooling is canonical there.

That split is deliberate. The uploader is the thing that writes to a real
backend — vendoring a copy into this repo would mean two uploaders drifting
apart, and the copy that drifts is the one that silently posts the wrong
payload shape.

`data-pipeline` (OpenPecha) is the predecessor of the same repo. Prefer
`webuddhist-library-data-pipeline`; it is newer and adds the input queue and
ledger.

---

## Three rules that are not negotiable

**1. `--dry-run` is the default. `--execute` needs explicit human confirmation.**

`--dry-run` validates payloads, plans the requests, and writes
`upload-report.json` without sending anything. `--execute` POSTs and PUTs to the
backend and patches `text_id` / `edition_id` / `toc_id` into `annotated.md` —
irreversible against a real backend. Never pass `--execute` because the dry run
looked fine; ask, and wait for an answer.

**2. The ledger is the record.** `ledger.json` tracks every input file through
`in_progress` → `annotated` → `uploaded`. Never reprocess a file already marked
`annotated` or `uploaded` unless a human explicitly says to, and keep the ledger
truthful — it is the only record of what has actually shipped.

**3. Never hand-edit `payloads/` or `upload-report.json`.** They are fully
reproducible from `annotated.md`. A hand-edit makes the payload disagree with
the text it claims to represent, and nothing downstream will catch it.

---

## Expected dirty state

Two files get modified as normal side effects of running the tools, not as bugs:

- **The linter patches frontmatter in place** — `lint_text_input.py` can rewrite
  `language`, `lang_tag`, `author` and `bdrc_work_id` directly in the source
  `.md` on every run. Each patch is printed, and easy to miss.
- **`tools/linter/languages.py` may be rewritten** by `load_languages()` whenever
  the linter runs without `--offline`; it caches the fetched language list as a
  fallback. Expect it dirty in `git status` after any online lint run.

## Backend URL

`DATA_PIPELINE_API_BASE` controls every backend call. It defaults to an
unreachable dummy host (`http://dummy-backend.example.invalid/v2`) so nothing
uploads anywhere real by accident. Pass `--offline` to the linter when you only
want structural validation.

---

## Scope

Root texts only, today — no translations or commentaries yet. A commentary that
needs to reach the library goes through `rails/` first and then waits for this
pipeline to grow a commentary path.
