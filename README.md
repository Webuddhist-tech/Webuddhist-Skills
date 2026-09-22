# Webuddhist-Skills

The shared skill library for WeBuddhist / OpenPecha. One canonical copy of every
skill the team uses, so the same job is not re-implemented in each new repo.

**[→ CATALOG.md](CATALOG.md)** — every skill, what it does, where it came from.

```
rails/      text processing — intake, structure, terminology, translation, claims
library/    getting an annotated text into the WeBuddhist library backend
tools/      build-catalog.py — regenerates CATALOG.md and PROVENANCE.md
*/          org & engineering skills — GitHub workflow, API, docs, design
```

## Why this repo exists

Text work happens in per-text Obsidian vaults — `21-taras-rails`,
`bodhisattvacharyavatara-rails`, `abhidhamma-rails`, `Liturgy-rails` — plus the
library pipeline repos. Each new text got a new vault, and each new vault got a
copy of the skills from the last one.

By the time we counted, there were **241 skill files across 8 repos**, of which
**172 were duplicates of 50 distinct jobs**. Five copies of `add-toc`. Four of
`tag-inline-toc`. Nine files doing frontmatter.

Almost none of that duplication was meaningful. The copies differed in
hard-coded folder paths, line wrapping, and which text the examples came from —
not in what they did. Fixing a bug in one left the other four broken.

## How the duplication was removed

**One skill per job.** 50 canonical skills now cover what 172 files used to.
Each lists in its own frontmatter exactly which files it supersedes
([`PROVENANCE.md`](PROVENANCE.md) rolls them up).

**Paths are parameterised, not hard-coded.** Skills refer to
`$COMMENTARIES/<id>.md`, not `1-SOURCES/Commentaries/<id>.md`.
[`rails/PROFILES.md`](rails/PROFILES.md) resolves those names per repo. This is
what lets one skill serve four vaults and the pipeline.

**Tag schemes are written down once.** The genuine variation between vaults was
in block-ID conventions — `^chapter-verse` vs the Sanskrit four-zone scheme, the
`-0` heading slot, the separate `^toc-X-Y-Z` namespace, the deprecated `^TOC-N`.
[`rails/CONVENTIONS.md`](rails/CONVENTIONS.md) is now the single authority, and
skills implement it rather than restating it differently each time.

**Multi-step families became one skill with phases.** The clearest case:
candidate extraction → enumeration → tree building → QC → ingest were five
skills that only ever ran in sequence and only ever read each other's output.
They are now [`rails/toc-generate`](rails/toc-generate/SKILL.md), one skill with
five phases and documented entry points, so you can still run just the candidate
scan or just the ingest. The same applies to
[`bilingual-glossary`](rails/bilingual-glossary/SKILL.md) (extract → combine →
contest → select) and [`segment-commentary`](rails/segment-commentary/SKILL.md).

The intent was that nothing be summarised away — each phase should carry the
full text of the skill it replaced. **A later review found that was not always
true**, and the gaps were repaired: a heading-ingest procedure had been cut from
~100 lines to 15, an original-language output variant had been reduced to a
single paragraph, and a table of heading anchors that a checker script parses
had been dropped. If you find another, treat it the same way — restore from the
vault original rather than paraphrasing what is left.

## A skill must be self-contained

A skill is installed into repos that do not share this one's layout, so
**everything it depends on travels with it**: `scripts/`, `prompts/`,
`templates/` it copies from, `references/` a reader may need. A skill that
points at a document elsewhere in a vault breaks the moment it is installed
somewhere that lacks it.

The only things a skill may assume are the folder layout named in
[`rails/PROFILES.md`](rails/PROFILES.md) and the host vault's own annex, which
is where anything text-specific lives — the commentary roster, the addressing
scheme, the tier order, the analysis language. **That division is what makes a
shared skill possible**: the skill holds the procedure, the annex holds the
facts. When you find a fact hard-coded in a skill — a commentary id, a chapter
count, a file name — it belongs in the annex, and the skill should read it from
there.

## Using a skill

Point Claude at this repo, or copy the skill folder into a project's
`.claude/skills/`. Then, before running one:

1. Check its `profile:` — `rails-vault` needs a vault's folder layout,
   `library-pipeline` needs the ingest repo's, and `any` runs anywhere. A skill
   marked `vault-local` in a vault belongs to that text and is not shared here.
2. Resolve its `$NAME` paths from [`rails/PROFILES.md`](rails/PROFILES.md).
   Those tokens are for a skill's prose only: a wiki link or transclusion inside
   a vault file needs the resolved literal path, because nothing expands them at
   read time.
3. If it writes block IDs, read [`rails/CONVENTIONS.md`](rails/CONVENTIONS.md).
   It is the single authority, including the per-vault deviations a text may
   register in its annex (§7).

**Installing into a Railroads vault**, use that vault's installer rather than
copying by hand — it resolves the logical paths, drops the library-only
frontmatter keys, and writes the slash-command stubs in one pass:

```bash
python3 4-SYSTEM/scripts/install-skills.py --from ../Webuddhist-Skills
```

Skills with a **Phases** / **Modes** / **Variants** table near the top are
separately addressable — run the phase that was asked for, not the whole
pipeline.

## Adding or changing a skill

Fix it **here**, not in a vault copy. Then:

```bash
python3 tools/build-catalog.py
```

which regenerates `CATALOG.md` and `PROVENANCE.md` from the skills' frontmatter.

Every skill needs `name:`, `description:`, `profile:` and — if it replaces
anything — `supersedes:`. A skill with no frontmatter cannot be discovered or
triggered by Claude at all; `CATALOG.md` flags any that are missing it.

## The source repos were not touched

Every superseded file still exists in its home repo and still works. This repo
is the canonical copy going forward: fix things here, and retire the vault copies
once the team has moved over. Nothing breaks in the meantime.
