---
name: wiki-article-inventory
description: Determine, for every standalone article subject, whether bo.wikipedia already has the article — via title/variant lookup and Wikidata sitelinks — and save a per-subject inventory with dated wikitext snapshots, feeding the kwiki terms.yaml.
profile: rails-vault
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/wiki-article-inventory/SKILL.md
---

# wiki-article-inventory

This is Step 8 of the keyword-extraction pipeline
(`4-SYSTEM/Guidelines/keyword-extraction-methodology.md` §Step 8). For each standalone subject
from Step 7 it answers "does bo.wikipedia already have this article?" — the fact that decides
between the pipeline's create path and its update path (one subject = one article; existing
articles are updated with cited sections, never forked). Title search alone misses articles
that live under other spellings or redirects, so existence is checked by **two mechanisms**:
direct title+variant lookup on bo.wikipedia, and Wikidata QID resolution with a bo.wikipedia
sitelink check. Correct output is an inventory covering *every* subject (API failures recorded,
never skipped), with a dated wikitext snapshot for each existing article — planning context for
generation, which must still re-fetch the live article when it runs.

---

## Inputs

- **The subject list** — `$WORK/AI_translation/keyword-extraction/output/article_subjects.json`
  (Step 7 output). Only subjects with `verdict: standalone` are inventoried.
- **Variant/synonym sets** — the `variants` field of each subject row (backed by
  `tibetan_term_registry.json` if a subject's set is empty).
- **Network access** to `https://bo.wikipedia.org/w/api.php` and
  `https://www.wikidata.org/w/api.php`. If the network is unavailable, stop and report — do
  not emit an inventory of guesses.
- **The output track directory** — `$TRANSFORMATIONS/Wikipedia/tara21/` (created by prior
  pipeline work; contains `slot-articles/`).

## Output

- `$TRANSFORMATIONS/Wikipedia/tara21/wiki-inventory.yaml` — one record per standalone
  subject (the authoritative extended data, including the per-subject `action`).
- `$TRANSFORMATIONS/Wikipedia/tara21/work/wiki-snapshots/<subject-slug>.wiki` — dated
  wikitext snapshot of each **existing** article (`<subject-slug>` = the subject term with
  final tsheg/shad stripped; the exact page title lives in the YAML record).
- `$TRANSFORMATIONS/Wikipedia/tara21/terms.yaml` — the kwiki registry file, **minimal
  schema only** (see Rules 4–5).

---

## Output file format

`wiki-inventory.yaml`:

```yaml
version: 1
corpus_id: tara21
checked: YYYY-MM-DD           # date of the most recent write — runs are resumable; each
                              # record's own snapshot_date/error date is the authoritative one
subjects:
  - subject: "བདུད།"
    action: update            # update | create
    exists: true
    found_by: [title-lookup, wikidata-sitelink]   # which mechanism(s) hit
    title: "བདུད།"             # canonical page title after redirect resolution
    url: "https://bo.wikipedia.org/wiki/..."
    qid: Q1298199
    length_bytes: 4213
    sections: ["...", "..."]  # H2 headings of the existing article
    assessment: substantial    # substantial | stub | disambiguation
    snapshot: work/wiki-snapshots/བདུད.wiki
    snapshot_date: YYYY-MM-DD
  - subject: "མྱུར་མ།"
    action: create
    exists: false
    found_by: []
    qid: null                 # record the QID when found even without a bo sitelink
    note: "No bo.wikipedia page under term or variants; no Wikidata bo sitelink."
  - subject: "…"
    action: null              # unresolved — never guessed; resolve via a refresh run
    exists: null              # API failure — recorded, not dropped
    error: "HTTP 503 from bo.wikipedia after 3 retries, YYYY-MM-DD"
```

`terms.yaml` (the shape `kangyur_wiki.registry.save()` emits — nothing beyond these keys):

```yaml
version: 1
corpus_id: tara21
corpus_name: tara21
terms:
  - term: "བདུད།"
    editor: null
    status: candidate
    wikipedia_url: "https://bo.wikipedia.org/wiki/..."   # null when the article does not exist
```

---

## Rules

1. **Read-only toward Wikipedia.** GET requests only — no login, no edits, no page creation.
   Publishing belongs exclusively to the pipeline's `/publish` gate.
2. **Both mechanisms run for every subject.** (a) Title lookup with `redirects=1` for the term
   and each variant, plus a `list=search` fallback; (b) Wikidata `wbsearchentities` on the
   Tibetan term (language `bo`) and its English glosses, then `wbgetentities` with
   `props=sitelinks` checking for a `bowiki` sitelink. A subject `exists` if either mechanism
   finds a bo.wikipedia article; `found_by` records which. A QID found without a bo sitelink
   is still recorded (it seeds the eventual interlanguage link).
3. **Snapshots are planning context, not drafting input.** Every snapshot carries its date;
   article generation must re-fetch the live article at run time. Never draft an update
   against a snapshot alone.
4. **`terms.yaml` carries only the kwiki `TermRecord` fields** (`term`, `editor`, `status`,
   `wikipedia_url`) under the `version`/`corpus_id`/`corpus_name` header. All extended data —
   `action`, QID, sections, assessment, snapshot paths — lives in `wiki-inventory.yaml` only.
   Do not add keys to `terms.yaml`: the pipeline's loader defines the schema.
5. **Existence is derived, never stored as a boolean in `terms.yaml`.** A subject that exists
   gets its `wikipedia_url`; one that does not gets `null` — matching kwiki's own convention
   (a red link is the registry saying the article is missing).
6. **Every standalone subject gets a record; unresolved subjects are never guessed.** API
   failures after 3 retries are recorded as `exists: null`, `action: null` with the error text
   and date — never silently skipped. Unresolved subjects are **excluded from `terms.yaml`**
   (a null `wikipedia_url` there would falsely assert a confirmed red link); they enter it
   after a refresh run resolves them.
7. **A disambiguation page is not the article.** Record `assessment: disambiguation` and
   `action: create` (the new article will need a disambiguated title; flag it ⚑ in the
   record's `note`).
8. **API etiquette.** Send a descriptive `User-Agent` identifying the project; at most one
   request per second; pass `maxlag=5` and back off when the API asks.
9. **Resumable.** On re-run, subjects already carrying a dated record are skipped unless
   explicitly refreshing; a refresh overwrites only that subject's record and snapshot.
10. **`status: candidate` for every term.** Under the review-at-end model no term is approved
    here; the human review happens over finished articles, and publishing stays behind the
    `/publish` gate regardless.
11. **Never clobber human registry data.** If `terms.yaml` already exists, merge instead of
    rewriting: for terms already present, preserve their existing `editor` and `status` and
    update only `wikipedia_url`; append new terms with `editor: null`, `status: candidate`.
    Never remove a term that a human added.

---

## Procedure

1. Load `article_subjects.json`; collect the `standalone` subjects and their variant sets.
   Create `$TRANSFORMATIONS/Wikipedia/tara21/work/wiki-snapshots/` if absent.
2. For each subject, in queue order:
   a. **Title lookup:** `action=query&titles=<term|variants>&redirects=1&prop=info` against
      bo.wikipedia (batch the term and its variants in one call). Any resulting existing,
      non-disambiguation page → candidate hit.
   b. **Search fallback:** if (a) misses, `action=query&list=search&srsearch=<term>` — accept
      only a result whose title matches the term or a variant (modulo final tsheg/shad);
      near-matches go in `note`, not in `title`.
   c. **Wikidata:** `wbsearchentities` with `language=bo` for the term, then for each English
      gloss with `language=en`; for plausible matches, `wbgetentities&props=sitelinks|labels`
      and check `bowiki`. Verify the entity actually denotes this subject (labels/description
      against the glosses) before accepting — a gloss like "king" must not resolve ཏུ་རེ to
      generic royalty.
   d. If the article exists: fetch wikitext (`prop=revisions&rvprop=content|timestamp`,
      current revision), write the snapshot file, record title, URL, QID, `length_bytes`,
      H2 `sections`, and `assessment` (`stub` when the prose is a few sentences or carries a
      stub template; `disambiguation` per Rule 7; otherwise `substantial`).
   e. Write the subject's record into `wiki-inventory.yaml` as you go (progressive, so an
      interrupted run resumes per Rule 9).
3. After all subjects: emit `terms.yaml` from the inventory — exactly the minimal schema of
   Rule 4, `status: candidate` for new entries, merging per Rule 11 if the file exists, and
   excluding unresolved (`exists: null`) subjects per Rule 6.
4. **Self-verification:** every standalone subject has exactly one inventory record; every
   `exists: true` record has a snapshot file on disk and a URL; every record's `action` is
   consistent — `update` ⇔ (`exists: true` and `assessment` ≠ `disambiguation`), `create` for
   confirmed-missing articles and disambiguation hits, `null` only on error records;
   `terms.yaml` parses, has no extra keys, contains one entry per *resolved* subject, and has
   lost no pre-existing human entry. Report the create/update/error counts.

---

## Completion check

- [ ] Every `standalone` subject from `article_subjects.json` has exactly one record in
      `wiki-inventory.yaml` (including `exists: null` error records)
- [ ] Both mechanisms attempted per subject; `found_by` recorded on every hit
- [ ] Every existing article has a dated snapshot file under `work/wiki-snapshots/` and its
      canonical title + URL in the record
- [ ] QIDs recorded wherever found, including for `create` subjects
- [ ] `terms.yaml` written with only `term`/`editor`/`status`/`wikipedia_url` per entry;
      `wikipedia_url: null` only for *confirmed*-missing articles; unresolved subjects
      excluded; pre-existing `editor`/`status` values preserved on merge
- [ ] No write operation was made against Wikipedia or Wikidata
- [ ] Disambiguation pages flagged ⚑ and counted as `create`
