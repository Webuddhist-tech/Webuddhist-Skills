#!/usr/bin/env python3
"""Regenerate CATALOG.md and PROVENANCE.md from the skills' own frontmatter.

Run after adding or changing a skill:  python3 tools/build-catalog.py
"""
import os, re, sys, yaml, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GROUPS = [
 ("Intake & cleanup", ["epub-to-markdown","raw-to-sources","clean-raw-text","tibetan-ocr-quality",
                       "json-to-source-text","json-to-commentary"]),
 ("Formatting",       ["format-root-text","format-tibetan-root-text","format-sanskrit-root-text",
                       "format-commentary"]),
 ("Structure & table of contents",
                      ["toc-generate","add-toc","tag-inline-toc","outline-extract",
                       "structural-outline-ingest","spine-map"]),
 ("Segmentation, block IDs & transclusion",
                      ["segment-commentary","add-block-ids","transclusion"]),
 ("Metadata & frontmatter",
                      ["frontmatter","extract-source-metadata","property-creator","author-metadata-sync"]),
 ("Terminology & glossaries",
                      ["bilingual-glossary","interlinear-gloss","keyword-extract",
                       "pali-biterm-extraction","term-definition","term-localization"]),
 ("Summaries & context",
                      ["section-summary","verse-context","multilevel-summary","local-wiki-article"]),
 ("Claims",           ["commentary-claims","claims-consolidate"]),
 ("Translation",      ["machine-translate","zeroshot-translate","translate-commentary",
                       "verse-translate","translation-qa"]),
 ("Validation",       ["vault-audit","commentary-fact-check"]),
 ("Wiki article production",
                      ["article-subject-filter","wiki-article-inventory","wiki-article-from-claims",
                       "gemini-article-polish"]),
 ("Authoring skills", ["create-skill"]),
]

def load(bucket, d):
    p = os.path.join(ROOT, bucket, d, "SKILL.md")
    if not os.path.isfile(p):
        return None
    raw = open(p, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if not m:
        h = re.search(r"^#\s+(.+)$", raw, re.M)
        return {"name": d, "description": (h.group(1).strip() if h else d),
                "_nofm": True, "_path": f"{bucket}/{d}/SKILL.md", "_dir": d, "_bucket": bucket}
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        # tolerate hand-written frontmatter with unquoted colons
        fm = {}
        for k in ("name", "description"):
            km = re.search(rf"^{k}:\s*(.+(?:\n\s+.+)*)$", m.group(1), re.M)
            if km:
                fm[k] = " ".join(km.group(1).split())
        fm["_yaml_broken"] = True
    fm["_path"] = f"{bucket}/{d}/SKILL.md"
    fm["_dir"] = d
    fm["_bucket"] = bucket
    return fm

def first_sentence(desc, limit=155):
    s = " ".join(str(desc).split())
    s = re.split(r"(?<=[a-z0-9\)])\.\s", s)[0].rstrip(".")
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"

rails = {d: load("rails", d) for d in sorted(os.listdir(os.path.join(ROOT, "rails")))
         if os.path.isdir(os.path.join(ROOT, "rails", d))}
rails = {k: v for k, v in rails.items() if v}
lib = {d: load("library", d) for d in sorted(os.listdir(os.path.join(ROOT, "library")))
       if os.path.isdir(os.path.join(ROOT, "library", d))}
lib = {k: v for k, v in lib.items() if v}

# root-level org skills (pre-existing, left in place)
SKIP = {"rails", "library", "tools", "skills", ".git", ".claude"}
org = {}
for d in sorted(os.listdir(ROOT)):
    if d in SKIP or d.startswith(".") or not os.path.isdir(os.path.join(ROOT, d)):
        continue
    fm = load(".", d)
    if fm:
        fm["_path"] = f"{d}/SKILL.md"
        org[d] = fm
for d in sorted(os.listdir(os.path.join(ROOT, "skills"))) if os.path.isdir(os.path.join(ROOT, "skills")) else []:
    fm = load("skills", d)
    if fm:
        org[d] = fm

grouped = {n for _, names in GROUPS for n in names}
ungrouped = sorted(set(rails) - grouped)

out = [f"""# Skill catalogue

Every skill in this repo. Generated from each skill's own frontmatter —
run `python3 tools/build-catalog.py` after adding or changing one.

- **{len(rails)}** text-processing skills in [`rails/`](rails/README.md)
- **{len(lib)}** library ingestion skills in [`library/`](library/README.md)
- **{len(org)}** org & engineering skills at the repo root

The rails and library skills consolidate **{sum(len(v.get('supersedes') or []) for v in {**rails, **lib}.values())}**
skill files that were duplicated across six repos. See [`PROVENANCE.md`](PROVENANCE.md)
for the full mapping.

---

## rails/ — text processing
"""]

for title, names in GROUPS:
    rows = [rails[n] for n in names if n in rails]
    if not rows:
        continue
    out.append(f"\n### {title}\n")
    out.append("| Skill | Does | Absorbs |")
    out.append("|---|---|---|")
    for fm in rows:
        n = len(fm.get("supersedes") or [])
        out.append(f"| [`{fm['_dir']}`]({fm['_path']}) | {first_sentence(fm['description'])} | {n} |")

if ungrouped:
    out.append("\n### Ungrouped\n")
    out.append("| Skill | Does | Absorbs |")
    out.append("|---|---|---|")
    for n in ungrouped:
        fm = rails[n]
        out.append(f"| [`{n}`]({fm['_path']}) | {first_sentence(fm['description'])} | {len(fm.get('supersedes') or [])} |")

out.append("\n---\n\n## library/ — WeBuddhist library ingestion\n")
out.append("> These require a checkout of `webuddhist-library-data-pipeline` — see [`library/README.md`](library/README.md).\n")
out.append("| Skill | Does | Absorbs |")
out.append("|---|---|---|")
for n, fm in lib.items():
    out.append(f"| [`{n}`]({fm['_path']}) | {first_sentence(fm['description'])} | {len(fm.get('supersedes') or [])} |")

out.append("\n---\n\n## Org & engineering skills\n")
out.append("Pre-existing skills at the repo root — GitHub workflow, API and docs work. Not part of the rails consolidation.\n")
out.append("| Skill | Does |")
out.append("|---|---|")
for n, fm in org.items():
    warn = " **⚠ no frontmatter — not discoverable by Claude; needs `name:` + `description:`**" if fm.get("_nofm") else ""
    out.append(f"| [`{n}`]({fm['_path']}) | {first_sentence(fm['description'])}{warn} |")

out.append("""
---

## Not in this repo

Deliberately left in their home vaults, because they build a finished product
for one specific text rather than processing text in general:

| Skill | Vault |
|---|---|
| `Tara-Plan-Creator` | 21-taras-rails |
| `BCA-Daily-Practice-Plan-HHDL`, `DKR-Fellow-Plan-Generator`, `Himalayan-Plan-Transformer`, `Daily-Challenge-Creator`, `day-package-pipeline`, `english-plan-evaluator`, `practice-verse-alignment`, `BCA-Verse-Distribution-Updater`, `Verse-package-file-creator`, `AI-summary-generator`, `verse-commentary-summarizer`, `BCA-Verse-Context-Summary`, `generate-modern-chinese`, `dalai-lama-plan-translation`, `hashtag-insert` | bodhisattvacharyavatara-rails |
| `daily-tipitaka-day`, `atthakatha-summaries`, `practice-summaries` | abhidhamma-rails |
| `inbox-diff` | Liturgy-rails |
| the 17-step `cowork-pipeline/` (Wikipedia publication programme) | 21-taras-rails |
| Documentation & UX skills (`doc-audit`, `user-journey-map`, `figma-issue-handoff`, …) | webuddhist-knowledge |

If one of these turns out to generalise, bring it over and note it here.
""")

open(os.path.join(ROOT, "CATALOG.md"), "w", encoding="utf-8").write("\n".join(out))

# ---- PROVENANCE ----------------------------------------------------------
prov = ["""# Provenance

Where every skill in `rails/` and `library/` came from, and what it replaced.

Generated by `tools/build-catalog.py`. The `supersedes:` list in each skill's own
frontmatter is the source of truth; this file is a rollup of them.

**The source repos were not modified.** Every path below still exists in its home
repo and still works. This repo is now the canonical copy: fix a skill here, and
retire the vault copy when the team has moved over.

---
"""]
allsk = {**{f"rails/{k}": v for k, v in rails.items()}, **{f"library/{k}": v for k, v in lib.items()}}
total = 0
for key, fm in sorted(allsk.items()):
    sup = fm.get("supersedes") or []
    total += len(sup)
    prov.append(f"### `{key}`\n")
    prov.append(f"*profile: `{fm.get('profile','?')}`* — absorbs {len(sup)} source file(s):\n")
    for s in sup:
        prov.append(f"- `{s}`")
    prov.append("")
prov.insert(1, f"\n**{len(allsk)} canonical skills, consolidated from {total} source files across 6 repos.**\n")
open(os.path.join(ROOT, "PROVENANCE.md"), "w", encoding="utf-8").write("\n".join(prov))
print(f"CATALOG.md + PROVENANCE.md written — {len(allsk)} skills, {total} sources, {len(org)} org skills")
