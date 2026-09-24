#!/usr/bin/env python3
"""termbase_to_md.py — write a graded-translate termbase JSON as the
termbase.md table that translation-qa and check_termbase_consistency.py
(rails mode) read.

One row per Tibetan form: | Tibetan | Rendering | Notes |. Where a form has
different renderings by verse, they are joined with " / " and the verse scope
is spelled out in Notes (the table format has no per-verse column; use
check_termbase_consistency.py --grade-file for exact per-verse checking).

Usage:
    python3 termbase_to_md.py <kw>/en-bo-en-termbase-general.json -o termbase.md [--title "..."]
"""
import argparse, json
from collections import defaultdict
from pathlib import Path


def cell(s):
    return " ".join(str(s or "").replace("|", "/").split())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("termbase", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--title", default=None)
    a = ap.parse_args(argv)
    tb = json.loads(a.termbase.read_text(encoding="utf-8"))
    rows = defaultdict(list)
    order = []
    for key, e in sorted(tb.items(), key=lambda kv: kv[1].get("rank", 10**9)):
        for f in (x.strip() for x in (e.get("bo") or "").split("/")):
            if f and "..." not in f and "…" not in f:
                if f not in rows: order.append(f)
                rows[f].append((key, e))
    lines = [f"# {a.title or 'Termbase — ' + a.termbase.stem}", "",
             f"Generated from `{a.termbase.name}` ({len(tb)} entries). One rendering per Tibetan form;",
             "the JSON termbase is the source of truth — regenerate this file, don't edit it.", "",
             "| Tibetan | Rendering | Notes |", "|---|---|---|"]
    for f in order:
        items = rows[f]
        ens = list(dict.fromkeys(e["en"] for _, e in items))
        notes = []
        if len(ens) > 1:
            notes.append("by verse: " + "; ".join(f"{e['en']} ({', '.join(e.get('verse_ids') or ['all'])})" for _, e in items))
        n = items[0][1].get("note")
        if n: notes.append(n)
        lines.append(f"| {f} | {cell(' / '.join(ens))} | {cell(' — '.join(notes))} |")
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(order)} rows to {a.out}")


if __name__ == "__main__":
    main()
