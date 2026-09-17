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

Nothing was summarised away in the process — each phase carries the full text of
the skill it replaced.

## Using a skill

Point Claude at this repo, or copy the skill folder into a project's
`.claude/skills/`. Then, before running one:

1. Check its `profile:` — `rails-vault`, `library-pipeline`, or `any`.
2. Resolve its `$NAME` paths from [`rails/PROFILES.md`](rails/PROFILES.md).
3. If it writes block IDs, read [`rails/CONVENTIONS.md`](rails/CONVENTIONS.md).

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
