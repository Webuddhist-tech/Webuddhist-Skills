#!/usr/bin/env python3
"""tally_report.py — compute a fact-check report's Result lines from its tables.

Hand-counting verdicts is error-prone (twice on the Twenty-One Tārās the
written totals disagreed with the table). This reads every table row whose
first two cells are `| <verse-id> | <verdict> |`, counts per chapter, and
prints the Result line each chapter subsection should carry.

  ERROR row      -> the verse has an error ("⚠ ERROR")
  MISMATCH row   -> judgment-call discrepancy
  any other row  -> ignored (notes, OK rows)

Scope — which verses were audited, so "clean" can be counted — comes from the
commentary JSON written by extract_commentary.py (its keys are the verses the
commentary covers), or from --verses.

Usage:
    python3 tally_report.py <report>.md --scope <commentary>.json
    python3 tally_report.py <report>.md --verses 1-1 1-2 1-3
"""
import argparse, json, re
from collections import defaultdict

ROW = re.compile(r"^\|\s*((?:\w[\w\-]*)?\d)\s*\|\s*([^|]+?)\s*\|", re.M)


def key(v):
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in v.split("-")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--scope", help="extract_commentary.py JSON: its keys are the audited verses")
    g.add_argument("--verses", nargs="+")
    a = ap.parse_args(argv)
    scope = list(json.load(open(a.scope, encoding="utf-8"))) if a.scope else a.verses
    scope = [v for v in scope if not v.endswith("-0")]
    err, mis, nmis = set(), set(), 0
    for vid, verdict in ROW.findall(open(a.report, encoding="utf-8").read()):
        v = verdict.upper()
        if "ERROR" in v: err.add(vid)
        elif "MISMATCH" in v: mis.add(vid); nmis += 1
    by = defaultdict(list)
    for v in scope: by[v.split("-")[0]].append(v)
    outside = sorted((err | mis) - set(scope), key=key)
    tot = defaultdict(int)
    for ch in sorted(by, key=lambda c: (not c.isdigit(), int(c) if c.isdigit() else c)):
        vs = by[ch]; e = sorted(set(vs) & err, key=key); m = sorted((set(vs) & mis) - err, key=key)
        rows = sum(1 for vid, verdict in ROW.findall(open(a.report, encoding="utf-8").read())
                   if vid in vs and "MISMATCH" in verdict.upper())
        clean = len(vs) - len(e) - len(m)
        tot["v"] += len(vs); tot["e"] += len(e); tot["m"] += len(m); tot["c"] += clean
        print(f"Chapter {ch}: **Result: {clean}/{len(vs)} clean, {len(e)} verse(s) with errors"
              + (f" ({', '.join(e)})" if e else "") + f", {len(m)} with mismatches only"
              + (f" ({', '.join(m)})" if m else "") + f"; {rows} mismatch row(s).**")
    print(f"\n**Overall: {tot['v']} verses checked — {tot['c']} clean, {tot['e']} with errors, {tot['m']} with mismatches only.**")
    if outside:
        print(f"\nwarning: rows for verses outside the scope: {', '.join(outside)}")


if __name__ == "__main__":
    main()
