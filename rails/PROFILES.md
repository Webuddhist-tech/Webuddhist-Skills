# Repo Profiles — where the files actually live

Every skill in this repo refers to its inputs and outputs by **logical
location** (`$COMMENTARIES`, `$WORK`, `$SECTIONS`) rather than a hard-coded
path. This file resolves those names per repo.

This indirection is the whole reason the skills can be shared. The four Rails
vaults and the library pipeline do the same work on the same texts; they differ
almost entirely in where things sit on disk. Previously that difference was
baked into every copy of every skill, which is why there were five `add-toc`s.

## How a skill uses this

A skill says:

> Read `$COMMENTARIES/<commentary-id>.md`, write to `$WORK/`.

You resolve `$COMMENTARIES` and `$WORK` from the profile of whatever repo you
are working in, using the table below. If the repo has a
`.claude/skill-profile.yml`, that file wins over this table.

---

## Profile: `rails-vault`

Used by **21-taras-rails**, **bodhisattvacharyavatara-rails**,
**abhidhamma-rails**, **Liturgy-rails**.

An Obsidian vault with a fixed five-stage layout. Material flows strictly
left to right; a later stage never writes back into an earlier one.

| Logical name | Path | Holds |
|---|---|---|
| `$INBOX` | `0-INBOX/` | Unprocessed arrivals; scratch |
| `$WORK` | `0-INBOX/temp/` | Intermediate drafts |
| `$SOURCE_TEXTS` | `1-SOURCES/Text/` | Root texts (canonical, citable) |
| `$COMMENTARIES` | `1-SOURCES/Commentaries/` | Commentaries |
| `$TRANSLATIONS` | `1-SOURCES/Translations/` | Existing human translations |
| `$REFERENCES` | `1-SOURCES/References/` | Secondary literature |
| `$RAILS` | `2-RAILS/` | Derived, reusable structure |
| `$SECTIONS` | `2-RAILS/Sections/` | Per-TOC-node summaries |
| `$SECTIONS_RAW` | `2-RAILS/Sections/Raw/<commentary>/` | Per-commentary raw summaries |
| `$VERSES` | `2-RAILS/Verses/` | Per-verse context packages |
| `$GLOSSARIES` | `2-RAILS/Bilingual-Glossaries/` | Consolidated glossaries |
| `$GLOSSARIES_RAW` | `2-RAILS/Bilingual-Glossaries/Raw/` | Per-source raw glossaries |
| `$LOCAL_WIKI` | `2-RAILS/Local-Wiki/` | Per-term wiki articles |
| `$CLAIMS` | `2-RAILS/Claims/` | Extracted + consolidated claims |
| `$TERMBASES` | `2-RAILS/termbases/` | Locked terminology |
| `$TRANSFORMATIONS` | `3-TRANSFORMATIONS/` | Audience-facing outputs |
| `$SYSTEM` | `4-SYSTEM/` | Skills, scripts, docs |

**Not every vault has every folder.** Liturgy-rails has no `Commentaries/`,
`Claims/` is 21-Taras-only, `termbases/` is BCA-only. A skill whose input
folder does not exist in the current vault should say so and stop, not invent
a location.

**Permission rule.** `1-SOURCES/` is the citation floor. The only edits
permitted to a source file are structural: block boundaries, block IDs,
navigation links, and factual `[Ed: …]` notes. Rewording, glossing or "fixing"
the text is interpretation and is forbidden — that belongs downstream in
`2-RAILS/` or `3-TRANSFORMATIONS/`.

---

## Profile: `library-pipeline`

Used by **webuddhist-library-data-pipeline** (canonical) and **data-pipeline**
(its predecessor — prefer the former).

Every text lives in its own directory under a per-text contract:

```
texts/<text-id>/
├── raw.md            original ingest — never overwritten after intake
├── work/             intermediate drafts
├── annotated.md      final, reviewed — the only file Pipeline 2 reads
├── payloads/         lint / text / edition / toc JSON
├── upload-report.json
└── status.json       step tracker (resumability)
```

| Logical name | Path |
|---|---|
| `$INBOX` | `input/` |
| `$WORK` | `texts/<text-id>/work/` |
| `$SOURCE_TEXTS` | `texts/<text-id>/raw.md` → `annotated.md` |
| `$PAYLOADS` | `texts/<text-id>/payloads/` |

Two rules that have no equivalent in a vault:

- **The ledger is the record.** `ledger.json` tracks every input file through
  `in_progress` → `annotated` → `uploaded`. Never reprocess a file already
  marked `annotated`/`uploaded` unless a human explicitly says to.
- **`--dry-run` is the default and `--execute` needs human confirmation.**
  `--execute` POSTs to a real backend and patches IDs into `annotated.md`. It
  is irreversible. See `library/README.md`.

This profile currently handles **root texts only** — no translations or
commentaries yet.

---

## Adding a profile

A new repo needs a row set here, not a forked copy of the skills. If a skill
cannot be expressed against these logical names, that is a signal the skill is
doing something genuinely repo-specific — keep it in that repo and note it in
`CATALOG.md` as vault-local.
