#!/usr/bin/env python3
"""Normalise every SKILL.md body: logical paths, and cross-references to the
post-consolidation skill names. Frontmatter (incl. `supersedes:`) is never touched.

Idempotent — safe to re-run.  python3 tools/normalise.py [--dry-run]

Guards that keep a re-run from undoing later work:
- RENAME maps only names that are retired. A name that is a live skill folder
  in rails/ or library/ is never rewritten, whatever the table says (e.g.
  `commentary-resegment` was merged away once and is a live skill again).
- A line that already names the new skill (a legacy-name table) or says
  "former" (a history note) keeps the old name.
- Line endings are kept as found, so a run on Windows does not rewrite every
  file it touches with CRLF.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry-run" in sys.argv

PATHS = [
  ("0-INBOX/temp/", "$WORK/"), ("0-INBOX/", "$INBOX/"),
  ("1-SOURCES/Commentaries/", "$COMMENTARIES/"),
  ("1-SOURCES/Translations/", "$TRANSLATIONS/"),
  ("1-SOURCES/References/", "$REFERENCES/"),
  ("1-SOURCES/Text/", "$SOURCE_TEXTS/"), ("1-SOURCES/", "$SOURCES/"),
  ("2-RAILS/Sections/Raw/", "$SECTIONS_RAW/"), ("2-RAILS/Sections/", "$SECTIONS/"),
  ("2-RAILS/sections/raw/", "$SECTIONS_RAW/"), ("2-RAILS/sections/", "$SECTIONS/"),
  ("2-RAILS/Bilingual-Glossaries/Raw/", "$GLOSSARIES_RAW/"),
  ("2-RAILS/Bilingual-Glossaries/", "$GLOSSARIES/"),
  ("2-RAILS/Local-Wiki/", "$LOCAL_WIKI/"), ("2-RAILS/Claims/", "$CLAIMS/"),
  ("2-RAILS/Verses/", "$VERSES/"), ("2-RAILS/termbases/", "$TERMBASES/"),
  ("2-RAILS/", "$RAILS/"), ("3-TRANSFORMATIONS/", "$TRANSFORMATIONS/"),
  ("texts/<text-id>/work/", "$WORK/"),
]

# old skill name -> (new name, optional phase hint)
RENAME = {
 # toc-generate and segment-commentary are retired too (deprecated/): the
 # segmentation + TOC workflows replaced them, one skill per step.
 "toc-generate": ("commentary-toc-extract", None),
 "toc-tree-extraction": ("commentary-toc-extract", None),
 "toc-candidate-extraction": ("commentary-toc-extract", None),
 "toc-tree-ingest": ("commentary-toc-ingest", None),
 "TOC-to-HEADING": ("commentary-toc-ingest", None),
 "root-text-frontmatter": ("frontmatter", "Variant 1"),
 "commentary-frontmatter": ("frontmatter", "Variant 2"),
 "translation-frontmatter": ("frontmatter", "Variant 3"),
 "reference-frontmatter": ("frontmatter", "Variant 4"),
 "segment-commentary": ("commentary-segment", None),
 "commentary-segmentation": ("commentary-segment", None),
 "block-resegmentation": ("commentary-resegment", None),
 "root-text-segmentation": ("root-text-pipeline", None),
 "section-summary-raw": ("section-summary", "Phase 1"),
 "section-summary-combined": ("section-summary", "Phase 2"),
 "glossary-extract-raw": ("bilingual-glossary", "Phase 1"),
 "glossary-combine": ("bilingual-glossary", "Phase 2"),
 "glossary-contested": ("bilingual-glossary", "Phase 3"),
 "glossary-select": ("bilingual-glossary", "Phase 4"),
 "claims-consolidation": ("claims-consolidate", "Phase 1"),
 "claims-consolidation-audit": ("claims-consolidate", "Phase 2"),
 "claims-consolidation-bo": ("claims-consolidate", None),
 "tree-guided-claims": ("commentary-claims", "Strategy 1"),
 "toc-scaffolded-claims": ("commentary-claims", "Strategy 2"),
 "gemini-translate": ("machine-translate", "Engine 1"),
 "dharmamitra-translate": ("machine-translate", "Engine 2"),
 "zeroshot-translator": ("zeroshot-translate", "Mode 3"),
 "zero-shot-translate": ("zeroshot-translate", "Mode 2"),
 "translate-zero-shot": ("zeroshot-translate", "Mode 1"),
 "translate-commentary-ai": ("translate-commentary", None),
 "source-property-extractor": ("extract-source-metadata", "Mode 2"),
 "colophon-metadata-extractor": ("extract-source-metadata", "Mode 1"),
 "Obsidian-Block-ID-to-Commentary": ("add-block-ids", "Mode 1"),
 "add-block-id-root-text": ("add-block-ids", "Mode 2"),
 "commentary-verse-id": ("add-block-ids", "Mode 4"),
 "commentary-fact-check-apply-fixes": ("commentary-fact-check", "Phase 2"),
 "verse-context-batch": ("verse-context", "Mode 2"),
 "root-verse-context-creator": ("verse-context", "Mode 3"),
 "Outline-Extractor": ("outline-extract", None),
 "Root-Text-Structure": ("format-tibetan-root-text", None),
 "clean-commentary-text": ("clean-raw-text", "Mode 2"),
 "english-keyword-extraction": ("keyword-extract", "Mode 1"),
 "pali-keyword-extraction": ("keyword-extract", "Mode 2"),
 "Transclusion-rootext-into-commentaries": ("transclusion", "Mode 1"),
 "Transclude-Rootexto-Commentary": ("transclusion", "Mode 2"),
 "root-verse-transclusion": ("transclusion", "Mode 3"),
 "ABC-Commentary-Formator": ("format-commentary", "Mode 3"),
 "format-chinese-commentary": ("format-commentary", "Mode 2"),
 "BCA-Term-Definition": ("term-definition", None),
 "term-definition-from-commentaries": ("term-definition", None),
}

LIVE = {d for b in ("rails", "library") for d in os.listdir(os.path.join(ROOT, b))
        if os.path.isfile(os.path.join(ROOT, b, d, "SKILL.md"))}
assert all(new in LIVE for new, _ in RENAME.values()), \
    "RENAME points at a skill that does not exist: " + \
    ", ".join(sorted({n for n, _ in RENAME.values()} - LIVE))

changed = 0
for bucket in ("rails", "library"):
    for d in sorted(os.listdir(os.path.join(ROOT, bucket))):
        p = os.path.join(ROOT, bucket, d, "SKILL.md")
        if not os.path.isfile(p):
            continue
        raw = open(p, encoding="utf-8", newline="").read()
        crlf = "\r\n" in raw
        raw = raw.replace("\r\n", "\n")
        m = re.match(r"^---\n.*?\n---\n", raw, re.S)
        fm, body = (raw[:m.end()], raw[m.end():]) if m else ("", raw)
        orig = body
        for a, b in PATHS:
            body = body.replace(a, b)
        body = re.sub(r"\$WORK/\$WORK/", "$WORK/", body)
        for old, (new, phase) in RENAME.items():
            if old == d or new == d:      # don't rewrite a skill's own name
                continue
            if old in LIVE:               # a live skill is never "renamed"
                continue
            repl = f"`{new}`" + (f" ({phase})" if phase else "")
            pat = re.compile(rf"`{re.escape(old)}`(?! \((?:Phase|Mode|Variant|Engine|Strategy|Simple))")
            # A line that already names the new skill (a legacy-name table row) or
            # says "former" (a history note) is about the old name — keep it.
            body = "\n".join(
                l if f"`{new}`" in l or re.search(r"\bformer\b", l, re.I)
                else pat.sub(repl.replace("\\", "\\\\"), l)
                for l in body.split("\n"))
        if body != orig:
            changed += 1
            if not DRY:
                out = fm + body
                open(p, "w", encoding="utf-8", newline="").write(
                    out.replace("\n", "\r\n") if crlf else out)
            print(f"  {'would fix' if DRY else 'fixed'}: {bucket}/{d}")
print(f"\n{changed} skill files normalised")
