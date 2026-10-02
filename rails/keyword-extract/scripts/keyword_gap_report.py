#!/usr/bin/env python3
"""keyword_gap_report.py — list the TF-IDF terms that YAKE missed.

Mode 1 builds a termbase from YAKE keywords (keywords.py). YAKE scores phrases
by position and co-occurrence, so it can skip a term that is rare but
distinctive — on the Twenty-One Tārās it missed "yakṣa" entirely, which the
TF-IDF pass (generate_en_translation_idf.py) ranked 43rd. This report puts the
two lists side by side so a reviewer can add the missing content terms before
graded-translate Phase 1 locks the termbase.

A TF-IDF word counts as covered when it (or its singular/plural) is a token of
any YAKE key. Diacritics are compared exactly (tārā ≠ tara).

Usage:
    python3 keyword_gap_report.py \\
        --yake   output/<stem>-keyword_verses_yake.json \\
        --tfidf  <outdir>/<stem>_keyword_verses.json \\
        [--top 60] [--md gap-report.md]

Run generate_en_translation_idf.py with --keep-transliterated first, or the
Sanskrit loanwords (the terms most likely to be missing) are filtered out.
"""
import argparse, json, pathlib, sys


def variants(w: str) -> set:
    v = {w}
    if w.endswith("es") and len(w) > 4: v.add(w[:-2])
    if w.endswith("s") and len(w) > 3: v.add(w[:-1])
    if w.endswith("ing") and len(w) > 5: v |= {w[:-3], w[:-3] + "e"}
    if w.endswith("ed") and len(w) > 4: v |= {w[:-2], w[:-1]}
    v |= {w + "s", w + "es"}
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yake", required=True, type=pathlib.Path, help="keywords.py verse JSON")
    ap.add_argument("--tfidf", required=True, type=pathlib.Path, help="generate_en_translation_idf.py *_keyword_verses.json")
    ap.add_argument("--top", type=int, default=60, help="how many top TF-IDF terms to check (default 60)")
    ap.add_argument("--md", type=pathlib.Path, help="also write a markdown report here")
    a = ap.parse_args()

    yake = json.loads(a.yake.read_text(encoding="utf-8"))
    tfidf = json.loads(a.tfidf.read_text(encoding="utf-8"))

    covered = set()
    for v in yake.values():
        for kw in v.get("keywords", []):
            for tok in kw.get("key", "").lower().split():
                covered |= variants(tok)

    ranked = sorted(tfidf.items(), key=lambda kv: kv[1].get("rank", 10**9))[: a.top]
    gaps = []
    for word, info in ranked:
        if variants(word.lower()) & covered:
            continue
        verses = sorted({o["verse_id"] for o in info.get("occurrences", [])})
        gaps.append((info.get("rank"), word, info.get("total_count", 0), verses))

    lines = [f"# TF-IDF terms missing from the YAKE keywords (top {a.top})", "",
             f"YAKE file: `{a.yake.name}`  ", f"TF-IDF file: `{a.tfidf.name}`", "",
             f"{len(gaps)} of the top {len(ranked)} TF-IDF terms are not among the YAKE keywords.",
             "Review each: add real content terms (names, classes of beings, technical words) to the",
             "keyword set before graded-translate Phase 1; ignore generic words.", "",
             "| TF-IDF rank | term | count | verses |", "|---|---|---|---|"]
    lines += [f"| {r} | {w} | {c} | {', '.join(vs)} |" for r, w, c, vs in gaps]
    out = "\n".join(lines) + "\n"
    if a.md:
        a.md.write_text(out, encoding="utf-8")
        print(f"Written -> {a.md}")
    sys.stdout.write(out)


if __name__ == "__main__":
    main()
