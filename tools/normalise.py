#!/usr/bin/env python3
"""Normalise every SKILL.md body: logical paths, and cross-references to the
post-consolidation skill names. Frontmatter (incl. `supersedes:`) is never touched.

Idempotent — safe to re-run.  python3 tools/normalise.py [--dry-run]
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry-run" in sys.argv

PATHS = [
  ("0-INBOX/temp/", "$WORK/"), ("0-INBOX/", "$WORK/"),
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
 "toc-tree-extraction": ("toc-generate", None),
 "toc-candidate-extraction": ("toc-generate", "Phase A"),
 "toc-tree-ingest": ("toc-generate", "Phase E"),
 "TOC-to-HEADING": ("toc-generate", "Phase E"),
 "toc-generator": ("toc-generate", "Simple mode"),
 "root-text-frontmatter": ("frontmatter", "Variant 1"),
 "commentary-frontmatter": ("frontmatter", "Variant 2"),
 "translation-frontmatter": ("frontmatter", "Variant 3"),
 "reference-frontmatter": ("frontmatter", "Variant 4"),
 "commentary-segmentation": ("segment-commentary", "Phase 1"),
 "commentary-resegment": ("segment-commentary", "Phase 2"),
 "block-resegmentation": ("segment-commentary", "Phase 3"),
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

changed = 0
for bucket in ("rails", "library"):
    for d in sorted(os.listdir(os.path.join(ROOT, bucket))):
        p = os.path.join(ROOT, bucket, d, "SKILL.md")
        if not os.path.isfile(p):
            continue
        raw = open(p, encoding="utf-8").read()
        m = re.match(r"^---\n.*?\n---\n", raw, re.S)
        fm, body = (raw[:m.end()], raw[m.end():]) if m else ("", raw)
        orig = body
        for a, b in PATHS:
            body = body.replace(a, b)
        body = re.sub(r"\$WORK/\$WORK/", "$WORK/", body)
        for old, (new, phase) in RENAME.items():
            if old == d or new == d:      # don't rewrite a skill's own name
                continue
            repl = f"`{new}`" + (f" ({phase})" if phase else "")
            body = re.sub(rf"`{re.escape(old)}`(?! \((?:Phase|Mode|Variant|Engine|Strategy|Simple))",
                          repl.replace("\\", "\\\\"), body)
        if body != orig:
            changed += 1
            if not DRY:
                open(p, "w", encoding="utf-8").write(fm + body)
            print(f"  {'would fix' if DRY else 'fixed'}: {bucket}/{d}")
print(f"\n{changed} skill files normalised")
