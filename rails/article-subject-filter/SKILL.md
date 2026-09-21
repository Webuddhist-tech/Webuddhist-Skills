---
name: article-subject-filter
description: Classify every article-queue term as a standalone encyclopedic subject, section material for a named target article, or a glossary-only term — merging near-duplicate subjects — with a recorded reason for every verdict.
profile: rails-vault
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/article-subject-filter/SKILL.md
---

# article-subject-filter

This is Step 7 of the keyword-extraction pipeline
(`4-SYSTEM/Guidelines/keyword-extraction-methodology.md` §Step 7). The mechanical
article-viability gate (Step 6) answers "is there enough claim material?"; this skill answers
"is this an encyclopedic *subject*?" It prevents two failure modes: non-subjects (body parts,
directions, generic vocabulary) getting standalone articles, and one subject appearing as
several queue rows (དགྲ/དགྲ་བོ/དགྲ་ཡི) getting parallel articles. Because the pipeline runs with
**no intermediate human review** (single review at the end, over finished articles), correct
output is a complete audit trail: every input term accounted for under exactly one disposition,
every verdict carrying a one-line reason — nothing silently dropped, nothing silently merged.

---

## Inputs

- **The article queue** — `$WORK/AI_translation/keyword-extraction/output/article_queue.json`
  (gate v1 output: `rule` header + `article_queue` list; each row has `term`, `en_glosses`,
  `variants`, the three signal blocks, `root_text_blocks`, `rank`).
- **The Tibetan term registry** —
  `$WORK/AI_translation/keyword-extraction/output/tibetan_term_registry.json` (variant and
  synonym sets per term, used as merge evidence).
- **The methodology doc** — `4-SYSTEM/Guidelines/keyword-extraction-methodology.md` §Step 7
  (verdict definitions and the editorial rules: one subject = one article; hub-and-spoke for
  the 21 Tārās).
- **Available merge targets** — the consolidated topic pages in `$CLAIMS/` (`tara-01` …
  `tara-21`, `origin`, `structure`, `benefits`): section-material claims route to these (or to
  a planned standalone subject from this same run).

If any input file is missing, stop and report — do not reconstruct a queue from the `.md`
table.

## Output

Two new files, alongside (never replacing) the Step 6 outputs:

- `$WORK/AI_translation/keyword-extraction/output/article_subjects.json`
- `$WORK/AI_translation/keyword-extraction/output/article_subjects.md`

All prior step outputs (`article_queue.*`, `ranked_keywords.*`, `tibetan_term_registry.json`)
are left byte-for-byte unchanged.

---

## Output file format

`article_subjects.json`:

```json
{
  "rule": {
    "name": "subject-filter v1",
    "verdicts": ["standalone", "section-material", "glossary"],
    "input": "article_queue.json (gate v1, N terms)",
    "date": "YYYY-MM-DD"
  },
  "subjects": [
    {
      "subject": "སྒྲོལ་མ།",
      "verdict": "standalone",
      "reason": "Deity; primary subject of the corpus; existing bo.wikipedia subject class.",
      "merged_terms": [],
      "queue_ranks": [1],
      "pooled_claim_count": 453,
      "pooled_spread": 16,
      "en_glosses": ["tara"],
      "variants": ["སྒྲོལ་མ།"],
      "borderline": false
    },
    {
      "subject": "ཞལ།",
      "verdict": "section-material",
      "reason": "Body part, not a subject; iconographic detail of the Tārā forms.",
      "target": "tara-articles:iconography",
      "merged_terms": [],
      "queue_ranks": [10],
      "pooled_claim_count": 35,
      "pooled_spread": 14,
      "en_glosses": ["face"],
      "variants": ["ཞལ།"],
      "borderline": false
    }
  ],
  "merged": [
    {"term": "དགྲ་བོ།", "merged_into": "དགྲ།", "reason": "Same lemma, nominal variant."}
  ],
  "conservation": {"input_terms": 114, "standalone": 0, "section_material": 0,
                   "glossary": 0, "merged": 0, "accounted": 114}
}
```

`article_subjects.md`: a human-readable report with the same date/rule header, then three
tables (Standalone subjects / Section material with targets / Glossary-only), a Merges table
(`merged term → subject head, reason`), and the conservation line at the end. Borderline
verdicts are marked ⚑ in their table row.

---

## Rules

1. **Read-only toward prior outputs.** Never modify or overwrite any existing file under
   `$WORK/AI_translation/keyword-extraction/output/`. This skill only adds the two
   `article_subjects.*` files. A re-run overwrites only its own two outputs.
2. **Conservation of terms.** Every queue term appears exactly once in the output — either as
   a subject head (whose verdict is standalone, section-material, or glossary) or inside one
   subject's `merged_terms`. The four counters are disjoint:
   `standalone + section_material + glossary + merged = accounted = input_terms` must hold,
   and the `conservation` block must record the arithmetic. A term absent from the output, or
   counted twice, is a hard failure.
3. **Every verdict carries a one-line reason.** No verdict, merge, or target assignment may
   appear without one. Reasons are English, specific ("body part, not a subject" — not
   "unsuitable").
4. **Merge only identical subjects.** Merge rows only when they name the *same encyclopedic
   subject*: lemma variants (དགྲ/དགྲ་བོ/དགྲ་ཡི), verbal/nominal forms (ཕྱག་འཚལ/ཕྱག་འཚལ་བ), spelling
   or phrase forms of one mantra element (ཧཱུྃ/ཡི་གེ་ཧཱུཾ). Never merge doctrinally distinct terms
   however close (ཤེས་རབ vs ཡེ་ཤེས; བདུད vs གདོན stay separate). When in doubt, do not merge —
   flag ⚑ borderline with the reason instead.
5. **Pooled counts are provisional.** `pooled_claim_count` for a merged subject is the sum of
   member rows' counts and may double-count claims mentioning several forms; the authoritative
   pool is formed at claims-consolidation time by claim-ID union. Record the caveat in the
   `.md` header.
6. **Section material names its target.** Every `section-material` verdict must carry a
   `target`: an existing `$CLAIMS/` page, a standalone subject from this same run, or
   the collective `tara-articles:iconography` (material for the 21 Tārā articles' iconography
   sections).
7. **Judge subjecthood, not material volume.** The gate already decided sufficiency; claim
   counts must not influence the verdict (a 100-claim body part is still section material; a
   20-claim deity is still standalone).
8. **No human interaction mid-run.** Under the review-at-end model, do not pause to ask about
   borderline cases — decide, mark ⚑ `borderline: true`, and record the reason so the final
   review can overturn it cheaply.
9. **Language.** Analysis, reasons, and headers in English; terms in Tibetan script exactly as
   they appear in the queue (final tsheg/shad preserved).

---

## Procedure

1. Load `article_queue.json`; record its term count. Load `tibetan_term_registry.json` for
   variant sets. List `$CLAIMS/*.md` to know the existing merge targets.
2. **Normalization (merge) pass.** Compare all queue rows pairwise for subject identity using:
   shared lemma modulo case particles and verbal endings; honorific/plain equivalents;
   registry variant-set overlap; identical `en_glosses` plus overlapping `root_text_blocks`
   as supporting (never sufficient) evidence. For each cluster choose the head: the citation
   (lemma) form; tie-break by best (lowest) queue rank. Record every non-head row in `merged`
   with its reason.
3. **Verdict pass.** For each subject head, apply the tests in order:
   a. *Standalone* — a general encyclopedia would give it its own entry: deities and their
      named forms, classes of beings (གནོད་སྦྱིན, དྲི་ཟ, རོ་ལངས), cosmological entities (རི་རབ),
      named persons/gods (བརྒྱ་བྱིན, ཚངས་པ), doctrinal categories (ཕ་རོལ་ཕྱིན་པ, སྡུག་བསྔལ), mantra
      and its named elements (ཏུ་ཏྟཱ་ར, སྭཱ་ཧཱ), text-specific epithets with their own commentary
      literature (མྱུར་མ, ཏུ་རེ).
   b. *Section-material* — an attribute, body part, implement, color, direction, posture, or
      action whose claims describe *another* subject (ཞལ, ཞབས, གཡས/གཡོན, མཐིལ, ཁྲོ་གཉེར as a
      feature). Assign `target` per Rule 6.
   c. *Glossary* — generic vocabulary neither of the above.
   Write the one-line reason as the verdict is made, not retrospectively.
4. **Hub-and-spoke consistency check.** Verify the standalone list is coherent with the
   editorial rules: the 21 Tārā names/epithets resolve to their spoke articles (not to one
   merged "Tārā" row); སྒྲོལ་མ remains the hub subject.
5. Write `article_subjects.json`, then render `article_subjects.md` from it (never the other
   way around).
6. **Self-verification.** Recompute conservation from the written JSON: every input term
   found exactly once; counts match the `conservation` block; no verdict lacks a reason; no
   `section-material` row lacks a target. Fix before reporting completion.

---

## Completion check

- [ ] `article_subjects.json` and `article_subjects.md` written; no other file in
      `output/` modified
- [ ] Conservation holds: every `article_queue.json` term appears exactly once (head or
      merged), and the `conservation` arithmetic matches
- [ ] Every subject has a verdict ∈ {standalone, section-material, glossary} and a one-line
      reason; every merge has a reason
- [ ] Every `section-material` subject names a valid target
- [ ] No doctrinally distinct terms merged; doubtful merges left unmerged and flagged ⚑
- [ ] Borderline verdicts marked ⚑ `borderline: true` with reasons — none escalated to the
      human mid-run
