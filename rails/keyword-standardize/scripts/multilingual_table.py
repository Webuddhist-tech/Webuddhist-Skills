#!/usr/bin/env python3
"""multilingual_table.py — one Markdown table of every standardised (locked) keyword
across languages: Tibetan | English | <each language> | verses | flags.

Reads the base English termbase and any number of target-language termbases built by
build_termbase.py; target-only entries (mantra syllables, splits) get their own rows.
Rebuild it whenever a word list changes — do not edit the output by hand.

Usage:
    python3 multilingual_table.py --base <kw>/en/en-bo-en-termbase-general.json \\
        --lang zh=<kw>/zh/en-bo-zh-termbase-general.json \\
        --lang vi=<kw>/vi/en-bo-vi-termbase-general.json \\
        --title "Praise to the Twenty-One Tārās" -o <kw>/standardised-keywords-general.md
"""
import argparse, json, sys
from pathlib import Path
NAMES = {"zh": "Chinese", "vi": "Vietnamese", "hi": "Hindi", "ne": "Nepali", "mn": "Mongolian", "th": "Thai"}


def vkey(v):
    head, _, n = v.partition("-")
    order = {"I": 0, "1": 1, "2": 2, "a": 3}
    return (order.get(head, 9), int(n) if n.isdigit() else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("--lang", action="append", default=[], help="code=path to that language's termbase (repeatable)")
    ap.add_argument("--title", default="")
    ap.add_argument("--grade", default="general")
    ap.add_argument("-o", "--out", required=True, type=Path)
    a = ap.parse_args(argv)
    base = json.loads(a.base.read_text(encoding="utf-8"))
    langs = []
    for spec in a.lang:
        code, _, p = spec.partition("=")
        langs.append((code, json.loads(Path(p).read_text(encoding="utf-8"))))
    keys = list(base)
    for _, tb in langs:
        keys += [k for k in tb if k not in keys]
    rows, flagged, only = [], {c: 0 for c, _ in langs}, []
    for k in keys:
        e = base.get(k) or next(tb[k] for _, tb in langs if k in tb)
        cells = [e.get("bo", ""), (base.get(k) or {}).get("en") or f"({e.get('en', k)})"]
        marks = []
        for code, tb in langs:
            t = tb.get(k)
            if not t:
                cells.append("—"); continue
            val = t.get(code, "")
            if f"{code}_decision" in t:
                val += " ⚑"; flagged[code] += 1
            cells.append(val)
            if t.get(f"{code}_only"):
                marks.append(code)
        vids = set()
        for src in [base.get(k)] + [tb.get(k) for _, tb in langs]:
            if src: vids |= set(src.get("verse_ids") or [])
        if marks:
            only.append(k)
        note = ("added for " + ", ".join(marks)) if marks else ""
        if base.get(k):
            bv = set(base[k].get("verse_ids") or [])
            diff = {}
            for code, tb in langs:
                if k in tb and set(tb[k].get("verse_ids") or []) != bv:
                    diff.setdefault(", ".join(sorted(tb[k].get("verse_ids") or [], key=vkey)), []).append(code)
            if diff:
                note = "; ".join(f"{'/'.join(cs)} locked in {vs}" for vs, cs in diff.items())
        rows.append((k, cells, ", ".join(sorted(vids, key=vkey)), note))
    heads = ["Tibetan", "English"] + [NAMES.get(c, c) for c, _ in langs] + ["Verses", "Note"]
    L = ["---", f"title: Standardised keywords{' — ' + a.title if a.title else ''} ({a.grade} grade)",
         "file_type: termbase-overview", f"grade: {a.grade}",
         f"languages: [en{''.join(', ' + c for c, _ in langs)}]", f"terms: {len(rows)}",
         "built_by: keyword-standardize/scripts/multilingual_table.py", "---", "",
         f"# Standardised keywords{' — ' + a.title if a.title else ''}", "",
         "Every locked keyword: one Tibetan term, the one rendering each translation must use for it, and the verses",
         "where it is locked. **This file is rebuilt from the word lists — edit those, not this.** In the word lists,",
         "English is `en/en-bo-en-termbase-*.json`; other languages are `<lang>/<lang>-decisions-*.json`.", "",
         f"- **{len(base)}** terms come from the English word list. **{len(only)}** were added for other languages",
         "  (mantra syllables English left unlocked; \"greater\", split from \"great\"). English is shown in brackets for those.",
         "- ⚑ marks a pick made where the sources disagreed. The reason is in that language's review table."]
    for code, _ in langs:
        L.append(f"  {NAMES.get(code, code)}: {flagged[code]} ⚑ — see `{code}/termbase-{code}-{a.grade}.md`.")
    L += ["", "| # | " + " | ".join(heads) + " |", "|---" * (len(heads) + 1) + "|"]
    for i, (k, cells, vids, note) in enumerate(rows, 1):
        L.append(f"| {i} | " + " | ".join(c.replace("|", "\\|") for c in cells) + f" | {vids} | {note} |")
    a.out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {a.out}: {len(rows)} terms, languages en + {', '.join(c for c, _ in langs)}")


if __name__ == "__main__":
    main()
