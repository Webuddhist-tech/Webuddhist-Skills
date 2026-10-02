#!/usr/bin/env python3
"""worksheet.py — lay out the evidence for every locked term, verse by verse,
so each target-language rendering can be chosen with its context in view
(keyword-standardize Step 3).

For each base-termbase term it prints the Tibetan form(s), the English lock and
its note, and for every verse the term is locked in: the Tibetan line, the
fact-checked meaning text, the aligned reference (classical canon) stanza and the
machine draft. It also flags reference IDs that match no verse, and
multi-syllable Tibetan forms that occur in verses where the term is not locked
(ཆུ་སྐྱེས་ཞལ is her lotus face in 1-8 but the Lord's in 1-1 — scope the
glossary; single syllables are skipped, they match inside other words).

With --template, it also writes an empty decisions file (every base key, `zh`
blank) for build_termbase.py, unless that file already exists.

Usage:
    python3 worksheet.py --base-termbase <kw>/en/en-bo-en-termbase-general.json \\
        --base-grade-file <kw>/en/bo_en_keyword_general.json \\
        --meaning-text <en translation .md> --reference <$KEYWORDS/zh/references/zh-classical-*.md> \\
        --mt-draft <Dharmamitra/zh/…-zh.md> -o <kw>/zh/zh-worksheet-general.md \\
        [--template <kw>/zh/zh-decisions-general.json] [--decisions <existing decisions, shown per term>]
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import blocks, load_json, forms, clean_bo


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-termbase", required=True, type=Path)
    ap.add_argument("--base-grade-file", required=True, type=Path)
    ap.add_argument("--meaning-text", type=Path)
    ap.add_argument("--reference", type=Path, action="append", default=[])
    ap.add_argument("--reference-prefix", default="zhc-")
    ap.add_argument("--mt-draft", type=Path)
    ap.add_argument("--decisions", type=Path, help="existing decisions file: show the current pick per term")
    ap.add_argument("--template", type=Path, help="write an empty decisions file here (never overwrites)")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--grade", default="general")
    ap.add_argument("-o", "--out", required=True, type=Path)
    a = ap.parse_args(argv)

    tb = load_json(a.base_termbase); g = load_json(a.base_grade_file)
    meaning = blocks(a.meaning_text) if a.meaning_text else {}
    ref = {}
    for r in a.reference:
        for k, v in blocks(r, a.reference_prefix).items():
            ref.setdefault(k, v)
    mt = blocks(a.mt_draft) if a.mt_draft else {}
    dec = load_json(a.decisions)["terms"] if a.decisions else {}

    out = [f"# {a.lang} worksheet — {a.grade} grade", "",
           "One section per locked term. Pick the rendering from the evidence, most trusted first: attested translation >",
           "classical canon or related-language list (reference) > standard Buddhist term > machine draft. Write the pick, its source codes and a",
           "one-line reason into the decisions file. Mark `decision: true` when the sources disagree or have nothing.", ""]
    stray_ref = sorted(k for k in ref if k not in g)
    if stray_ref:
        out += [f"**Warning:** reference IDs with no verse in the grade file: {', '.join(stray_ref)}", ""]
    n_scope = 0
    for k, e in sorted(tb.items(), key=lambda kv: kv[1].get("rank") or 10**9):
        vids = list(e.get("verse_ids") or [])
        out += [f"## `{k}` — {e['bo']} → {e.get('en', '')}", ""]
        if e.get("note"):
            out += [f"English note: {e['note']}", ""]
        if k in dec:
            d = dec[k]
            out += [f"Current pick: **{d.get(a.lang, '')}** ({', '.join(d.get('source') or [])}) — {d.get('note', '')}", ""]
        elsewhere = [v for v, vv in g.items() if v not in vids and
                     any("་" in f and clean_bo(f) in clean_bo(vv.get("bo_text", "")) for f in forms(e["bo"]))]
        if elsewhere:
            n_scope += 1
            out += [f"Also occurs, unlocked, in: {', '.join(elsewhere)} — check whether it means the same there.", ""]
        out += ["| verse | Tibetan | meaning (English) | reference | machine draft |", "|---|---|---|---|---|"]
        for v in vids:
            cell = lambda s: (s or "—").replace("\n", " / ").replace("|", "\\|")
            out.append(f"| {v} | {cell(g.get(v, {}).get('bo_text'))} | {cell(meaning.get(v) or g.get(v, {}).get('text'))} | "
                       f"{cell(ref.get(v))} | {cell(mt.get(v))} |")
        out.append("")
    a.out.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {a.out}: {len(tb)} terms, {len(ref)} reference blocks, {len(mt)} machine-draft blocks, "
          f"{n_scope} term(s) whose Tibetan also occurs where it is not locked")

    if a.template:
        if a.template.exists():
            print(f"{a.template} exists — not overwritten")
        else:
            t = {"_meta": {"lang": a.lang, "grade": a.grade, "script": "", "lang_tag": a.lang,
                           "title": f"{a.lang} word list", "choices": "", "decided_by": "", "sources_note": "",
                           "source_labels": {}, "baseline": ""},
                 "terms": {k: {a.lang: "", "source": [], "note": ""} for k in tb}}
            a.template.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote template {a.template} ({len(tb)} terms to fill)")


if __name__ == "__main__":
    main()
