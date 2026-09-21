---
name: format-root-text
description: >
  Format and normalise a root-text file (texts/<text-id>/work/*.md) that is
  not Tibetan or Sanskrit — handles frontmatter, block IDs (including
  Chapter 0), heading structures (TOC), and cleaning OCR artifacts.
  Reference docs/reference/conventions.md for the block-ID and heading
  standards this skill applies.

  Trigger this skill for segmenting/ID-ing any non-Tibetan, non-Sanskrit
  root text (Pāli, English, Chinese, Hindi…) — "format this root text",
  "add block IDs", "structure this sutta" — and as the `other`-language
  route of /annotate Steps 2–3. For Tibetan use format-tibetan-root-text;
  for Sanskrit use format-sanskrit-root-text.
profile: any
supersedes:
  - webuddhist-library-data-pipeline/skills/format-root-text/SKILL.md
  - data-pipeline/skills/format-root-text/SKILL.md
  - 21-taras-rails/4-SYSTEM/Skills/format-root-text/SKILL.md
  - abhidhamma-rails/4-SYSTEM/Skills/format-root-text/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/format-root-text/SKILL.md
---

# format-root-text

This skill normalises a root-text file under `$WORK/` to meet
this repo's structural and linking standards. It is the generic fallback for
languages that don't have a dedicated format skill —
`format-tibetan-root-text` handles Tibetan, `format-sanskrit-root-text`
handles Sanskrit; use this skill for anything else (Pāli, Chinese, English,
etc.), or as a general normalisation pass.

## Core Principles
Before processing any file, review `docs/reference/conventions.md` — it is
the canonical spec for block IDs and heading hierarchy in this repo. The
block ID is the single most important linking mechanism for verse-level
references.

### 1. Heading Structure (TOC)
- **Level 2 (`##`)**: Author-defined books or chapters.
- **Level 3 (`###`)**: Author-defined sub-sections (e.g., from the author's own Table of Contents).
- **Level 4 (`####`)**: DO NOT USE. Block IDs replace verse-level headings.
- **Chapter 0**: Any content preceding Chapter 1 (titles, colophons, homages, scribal intros) MUST be placed under a `## 0. Introduction` heading.

### 2. Block ID Format
- **Standard**: `^chapter-verse` (e.g., `^1-1`, `^6-33`).
- **Chapter 0**: Verses in the introduction section use `^0-verse` (e.g., `^0-1`, `^0-2`).
- **No Zero-Padding**: Use `^6-33`, NOT `^06-033`.
- **Placement**: At the end of the last line of the verse/passage, preceded by a single space.
- **Numbering**: Verse numbers restart at 1 for each chapter. Convert continuous numbering to per-chapter numbering.
- **Heading anchors**: chapter and section headings use `^N-0` / `^N-N-0` (ending in `-0`) — see `docs/reference/conventions.md`. Do not use `^TOC-N`.

---

## Step 1 — Audit and Identification
Identify what in `$WORK/` (or `raw.md`, if working from the
unprocessed source) lacks frontmatter, has missing/incorrect block IDs, or
has stray line numbers from OCR/PDF extraction.

## Step 2 — Process Formatting
For the file:
1. **Insert/Update Frontmatter**: Ensure the YAML block is at the very top (see `docs/reference/frontmatter-schema.md`).
2. **Standardise Headings**:
    - Ensure Chapter 1 starts with `## 1. [Title] ^1-0`.
    - Ensure pre-chapter material is under `## 0. Introduction ^0-0`.
    - Map author-defined structural divisions to `##` and `###`.
3. **Apply Block IDs**:
    - Add `^0-n` to introduction verses.
    - Add `^c-v` to chapter verses, restarting `v` at 1 for each `c`.
    - For Sanskrit, extract verse numbers from `॥N॥` (or hand off to `format-sanskrit-root-text`).
    - For Tibetan, count verses (runs of lines ending in `། །`) (or hand off to `format-tibetan-root-text`).
4. **Clean Content**:
    - Remove OCR artifacts, page numbers, and stray line-number prefixes (e.g., `7.`, `42.`).
    - Restore two-line formatting for verses if hemistichs are run together.

## Step 3 — Frontmatter Fields
Minimum required fields (full schema: `docs/reference/frontmatter-schema.md`):
```yaml
---
title:
author:
language:
file_type: root-text
lang_tag: sa | bo | zh | en | pi
source_description: "Detailed source info (required)"
verse_id_format: chapter-verse | verse | book-chapter-verse
---
```

## Step 4 — Non-root-text specifics (out of scope for this repo's current pipeline)

This repo's pipelines currently handle root texts only (see the repo
`README.md` for scope). The notes below are retained from the source skill
for when translation/commentary support is added:

- Commentary or translation passages should use their own block ID system (declared in `verse_id_format`).
- Transclude the relevant root verse(s) immediately before the commentary on that verse: `![[path/to/root-text#^1-1]]`.
- Use sequential individual transclusions for multi-verse sections.

---

## Dos and Don'ts
- **DO** work on one file at a time.
- **DO** use editorial notes `[Ed: ...]` in English for ambiguous cases.
- **DO** preserve original scripts in content while using English for metadata.
- **DON'T** renumber verses based on your own interpretation; follow the source's logical structure.
- **DON'T** put block IDs on heading lines other than the `^N-0` anchor itself.
- **DON'T** use `####` headings.
- **DON'T** use `^TOC-N` style chapter anchors — use `^N-0` (see `docs/reference/conventions.md`).

---

## Provenance

Adapted from `bodhisattvacharyavatara-rails/4-SYSTEM/Skills/format-root-text/SKILL.md`.
The source skill referenced a `1-Human-Sources/` folder and a
`[[1-Human-Sources-Guideline]]` wikilink doc that don't exist in this repo;
both are replaced above with `$WORK/` and
`docs/reference/conventions.md`.
