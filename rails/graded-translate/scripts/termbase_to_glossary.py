#!/usr/bin/env python3
"""termbase_to_glossary.py — turn a graded-translate termbase JSON into the
glossary file machine-translate's dm_translate.py accepts (--glossary).

One line per Tibetan form (a termbase `bo` of "ཕྱག / ཕྱག་འཚལ" gives two lines),
because the glossary hit-check is a literal substring match on each block.

A Tibetan form locked to different renderings in different verses (དབང:
"power" at 1-10, "empowerment" at 2-3) gets a third, verse-scope column, so a
call only receives the rendering that applies to its verses. With --scope-all,
every line gets that column. Forms written with
"..." are skipped: they can never match a block.

Usage:
    python3 termbase_to_glossary.py <kw>/en-bo-en-termbase-general.json -o glossary-en-general.tsv
    python3 termbase_to_glossary.py --lang zh <kw>/en-bo-zh-termbase-general.json -o glossary-zh-general.tsv
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("termbase", type=Path)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--lang", default="en", help="field holding the locked rendering (en, zh, …); default en")
    ap.add_argument("--scope-all", action="store_true",
                    help="give every line its verse-scope column, so a term is only hinted in the verses where it is locked (use when a phrase is locked in some verses but its Tibetan also occurs elsewhere with another sense, e.g. ཆུ་སྐྱེས་ཞལ is her lotus face in 1-8 but the Lord's lotus face in 1-1)")
    a = ap.parse_args(argv)
    tb = json.loads(a.termbase.read_text(encoding="utf-8"))

    rows = defaultdict(list)          # form -> [(en, verse_ids, key)]
    skipped = []
    for key, e in sorted(tb.items(), key=lambda kv: kv[1].get("rank", 10**9)):
        en = (e.get(a.lang) or "").strip()
        if not en:
            continue
        for f in (x.strip() for x in (e.get("bo") or "").split("/")):
            if not f:
                continue
            if "..." in f or "…" in f:
                skipped.append((key, f)); continue
            rows[f].append((en, e.get("verse_ids") or [], key))

    out = [f"# Glossary from {a.termbase.name} — <tibetan form>\\t<locked rendering>[\\t<verse ids>]",
           "# The third column appears only where one form has different renderings by verse."]
    n_scoped = 0
    for f, items in rows.items():
        if a.scope_all or len({en for en, _, _ in items}) > 1:
            for en, vids, key in items:
                if not vids:
                    print(f"warning: {f} has several renderings but '{key}' has no verse_ids; left unscoped", file=sys.stderr)
                    out.append(f"{f}\t{en}")
                else:
                    out.append(f"{f}\t{en}\t{','.join(vids)}"); n_scoped += 1
        else:
            out.append(f"{f}\t{items[0][0]}")
    a.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {len(out) - 2} lines to {a.out} ({n_scoped} verse-scoped)")
    for key, f in skipped:
        print(f"skipped '{key}': form '{f}' contains '...'", file=sys.stderr)


if __name__ == "__main__":
    main()
