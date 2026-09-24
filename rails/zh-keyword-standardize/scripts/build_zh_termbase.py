#!/usr/bin/env python3
"""build_zh_termbase.py — turn a decisions file into the Chinese termbase, grade
file and review table (zh-keyword-standardize Step 5).

The decisions file is the only thing a person edits. Everything this script
writes is derived from it plus the base (English) termbase and grade file, so
re-running it after a change to one decision rebuilds all three outputs
consistently.

Decisions file (JSON):

  {
    "_meta": {
      "lang": "zh", "grade": "general", "script": "Traditional",
      "choices": "one line saying what the project owner chose",
      "decided_by": "who made the flagged picks, and when",
      "sources_note": "which sources were used, most trusted first",
      "source_labels": {"classical": "classical canon (CBETA T1108)", "mt": "DharmaMitra zh draft"},
      "baseline": "the machine draft already uses 63 of 137 locked words (46%)"
    },
    "terms": {
      "homage":  {"zh": "敬禮", "source": ["classical"], "note": "why", "decision": true},
      "tara":    {"zh": "度母", "source": ["classical", "mt"], "note": "why"},
      "ability": {"zh": "能", "source": ["classical"], "note": "why", "add_verses": {"1-5": "ནུས"}},
      "greater": {"zh": "更殊勝", "source": ["mt", "standard"], "note": "why", "decision": true,
                  "new_entry": {"bo": "ཆེ་བ", "en": "greater", "verse_ids": ["2-3"], "split_from": "great"}},
      "om":      {"zh": "嗡", "source": ["recitation"], "note": "why",
                  "new_entry": {"bo": "ཨོཾ", "en": "Oṃ", "verse_ids": ["I-3", "1-15"]}}
    }
  }

- Every key of the base termbase needs a decision; unknown keys need `new_entry`.
- `source` codes: attested, classical, standard, recitation, kept, mt, new.
- `decision`: true (uses _meta.decided_by) or a string; marks a pick made where the
  sources disagreed or had nothing. These go first in the review table.
- `add_verses` {verse: Tibetan form}: lock the term in more verses than English did.
- `new_entry.split_from`: take the form and those verses away from the parent term
  and retag the parent's keywords there (ཆེ་བ at 2-3: "greater", not "great").
  Without it, a keyword is added for each verse (mantra syllables English left unlocked).

Usage:
    python3 build_zh_termbase.py --decisions <kw>/zh-decisions-general.json \\
        --base-termbase <kw>/en-bo-en-termbase-general.json \\
        --base-grade-file <kw>/bo_en_keyword_general.json \\
        --meaning-text <en translation .md> \\
        --reference <zh-references/zh-classical-*.md> --mt-draft <Dharmamitra/zh/…-zh.md> \\
        --out-dir <kw> [--force]
"""
import argparse, copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from zh_common import blocks, load_json, forms, clean_bo, source_label


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decisions", required=True, type=Path)
    ap.add_argument("--base-termbase", required=True, type=Path)
    ap.add_argument("--base-grade-file", required=True, type=Path)
    ap.add_argument("--meaning-text", type=Path, help="fact-checked translation used as the meaning reference (grade-file `text`)")
    ap.add_argument("--reference", type=Path, action="append", default=[],
                    help="aligned reference file(s), IDs ^<prefix>-<block id>; repeatable")
    ap.add_argument("--reference-prefix", default="zhc-")
    ap.add_argument("--mt-draft", type=Path, help="zero-shot machine draft in the target language (evidence counts)")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite existing outputs")
    a = ap.parse_args(argv)

    dec = load_json(a.decisions); meta = dec.get("_meta", {}); D = dec["terms"]
    L = meta.get("lang", "zh"); G = meta.get("grade", "general")
    base = load_json(a.base_termbase); gbase = load_json(a.base_grade_file)
    meaning = blocks(a.meaning_text) if a.meaning_text else {}
    ref = {}
    for r in a.reference:
        for k, v in blocks(r, a.reference_prefix).items():
            ref.setdefault(k, v)
    mt = blocks(a.mt_draft) if a.mt_draft else {}

    errs = []
    missing = [k for k in base if k not in D]
    unknown = [k for k in D if k not in base and "new_entry" not in D[k]]
    if missing: errs.append(f"no decision for base term(s): {missing}")
    if unknown: errs.append(f"decision(s) for unknown term(s) without new_entry: {unknown}")
    for k, d in D.items():
        if not (d.get(L) or "").strip():
            errs.append(f"'{k}': empty '{L}' rendering")
        if not d.get("source"):
            errs.append(f"'{k}': no source")
    if errs:
        raise SystemExit("decisions file has problems:\n  " + "\n  ".join(errs))

    def evidence(val, vids):
        out = {}
        if ref:
            rv = [v for v in vids if v in ref]
            out["reference"] = f"{sum(val in ref[v] for v in rv)}/{len(rv)} of its verses" if rv else "no aligned verse"
        if mt:
            out["machine_draft"] = f"{sum(val in mt.get(v, '') for v in vids)}/{len(vids)} of its verses"
        return out

    def entry(k, bo, en, rank, vids, d, zh_only=False):
        e = {"bo": bo, "en": en, L: d[L], "rank": rank, "verse_ids": vids,
             f"{L}_source": source_label(d["source"], meta.get("source_labels")), f"{L}_note": d.get("note", "")}
        if d.get("decision"):
            e[f"{L}_decision"] = d["decision"] if isinstance(d["decision"], str) else meta.get("decided_by", "flagged pick")
        e[f"{L}_evidence"] = evidence(d[L], vids)
        if zh_only:
            e[f"{L}_only"] = True
        return e

    tb = {}
    for k, e in base.items():
        tb[k] = entry(k, e["bo"], e.get("en", ""), e.get("rank"), list(e.get("verse_ids") or []), D[k])
    retag = {}   # (verse, bo) -> new term
    for k, d in D.items():
        ne = d.get("new_entry")
        if not ne:
            continue
        if k in tb:
            raise SystemExit(f"'{k}' has new_entry but already exists in the base termbase")
        par = ne.get("split_from")
        if par:
            p = tb[par]
            p["bo"] = " / ".join(f for f in forms(p["bo"]) if f != ne["bo"])
            p["verse_ids"] = [v for v in p["verse_ids"] if v not in ne["verse_ids"]]
            p[f"{L}_evidence"] = evidence(p[L], p["verse_ids"])
            for v in ne["verse_ids"]:
                retag[(v, ne["bo"])] = k
        tb[k] = entry(k, ne["bo"], ne.get("en", k), ne.get("rank", 999), list(ne["verse_ids"]), d, zh_only=True)
    for k, d in D.items():
        for v, bo in (d.get("add_verses") or {}).items():
            if v not in tb[k]["verse_ids"]:
                tb[k]["verse_ids"].append(v)
        if d.get("add_verses"):
            tb[k][f"{L}_evidence"] = evidence(tb[k][L], tb[k]["verse_ids"])

    g = {}
    for vid, v in gbase.items():
        nv = {"text": meaning.get(vid, v.get("text", "")), "bo_text": v.get("bo_text", ""), f"{L}_text": "", "keywords": []}
        for kw in v.get("keywords", []):
            kk = copy.deepcopy(kw)
            t = retag.get((vid, kk.get("bo")), kk.get("term"))
            if t != kk.get("term"):
                kk["term"] = t; kk["en"] = tb[t]["en"]
            if t not in tb:
                errs.append(f"[{vid}] keyword term '{t}' has no termbase entry"); continue
            kk[L] = tb[t][L]
            nv["keywords"].append(kk)
        g[vid] = nv

    def addkw(vid, term, bo):
        if vid not in g:
            errs.append(f"'{term}': verse {vid} is not in the grade file"); return
        if clean_bo(bo) not in clean_bo(g[vid]["bo_text"]):
            errs.append(f"'{term}': Tibetan {bo} is not in verse {vid}"); return
        if any(k.get("term") == term for k in g[vid]["keywords"]):
            return
        e = tb[term]
        g[vid]["keywords"].append({"key": (e["en"] or term).lower(), "rank": e["rank"], "score": None, "count": 1,
                                   "bo": bo, "term": term, "en": e["en"], "grade": G, L: e[L], f"{L}_only": True})
    for k, d in D.items():
        ne = d.get("new_entry")
        if ne and not ne.get("split_from"):
            for vid in ne["verse_ids"]:
                addkw(vid, k, ne["bo"])
        for vid, bo in (d.get("add_verses") or {}).items():
            addkw(vid, k, bo)
    if errs:
        raise SystemExit("build failed:\n  " + "\n  ".join(errs))

    a.out_dir.mkdir(parents=True, exist_ok=True)
    stem = a.base_termbase.name.split("-termbase-")[0]           # en-bo-en
    src = stem.split("-")[1] if stem.count("-") >= 2 else "bo"
    out_tb = a.out_dir / f"en-{src}-{L}-termbase-{G}.json"
    out_g = a.out_dir / f"{src}_{L}_keyword_{G}.json"
    out_md = a.out_dir / f"termbase-{L}-{G}.md"
    for p in (out_tb, out_g, out_md):
        if p.exists() and not a.force:
            raise SystemExit(f"{p} exists — pass --force to rebuild it from the decisions file")

    kept = 0
    if out_g.exists():       # a rebuild must not wipe the Phase 2 text already written back
        old = load_json(out_g)
        for vid, v in g.items():
            t = (old.get(vid) or {}).get(f"{L}_text")
            if t:
                v[f"{L}_text"] = t; kept += 1
    out_tb.write_text(json.dumps(tb, ensure_ascii=False, indent=2), encoding="utf-8")
    out_g.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    load_json(out_tb); load_json(out_g)

    def row(e):
        return (f"| {e['bo']} | {e['en']} | **{e[L]}** | {e[f'{L}_source']} | {', '.join(e['verse_ids'])} | "
                f"{e[f'{L}_note']} |")
    H = "| Tibetan | English | Chinese | Source | Verses | Why |\n|---|---|---|---|---|---|"
    fl = [e for e in tb.values() if f"{L}_decision" in e]; rest = [e for e in tb.values() if f"{L}_decision" not in e]
    only = [k for k, e in tb.items() if e.get(f"{L}_only")]
    md = ["---", f"title: {meta.get('title', 'Chinese word list')}", f"language: Chinese ({meta.get('script', 'Traditional')})",
          f"lang_tag: {meta.get('lang_tag', 'zh-Hant')}", "file_type: termbase-review", f"grade: {G}",
          f"termbase: {out_tb.name}", f"grade_file: {out_g.name}", f"decisions: {a.decisions.name}",
          f"built_by: zh-keyword-standardize/scripts/build_zh_termbase.py", f"entries: {len(tb)}",
          f"decided_flagged: {len(fl)}", "status: awaiting native-speaker review", "---", "",
          f"# {meta.get('title', 'Chinese word list')}", "",
          "The locked Chinese words for this text. Every Chinese translation step must use these words for these",
          f"Tibetan words. **Edit `{a.decisions.name}`, not this file** — this file is rebuilt from it.", ""]
    if meta.get("choices"):
        md += [f"**Choices:** {meta['choices']}", ""]
    if meta.get("sources_note"):
        md += [f"**Sources:** {meta['sources_note']}", ""]
    if only:
        md += [f"**Chinese-only entries:** {', '.join(only)}.", ""]
    if meta.get("baseline"):
        md += [f"**Baseline:** {meta['baseline']}", ""]
    md += [f"## Flagged picks — please look at these first ({len(fl)})", "",
           f"Sources disagreed or had nothing. Decided by: {meta.get('decided_by', '—')}.", "", H] + [row(e) for e in fl]
    md += ["", f"## Sources agree ({len(rest)})", "", H] + [row(e) for e in rest] + [""]
    out_md.write_text("\n".join(md), encoding="utf-8")

    print(f"termbase   : {out_tb}  ({len(tb)} entries, {len(only)} {L}-only, {len(fl)} flagged)")
    print(f"grade file : {out_g}  ({len(g)} verses, {sum(len(v['keywords']) for v in g.values())} keywords)")
    print(f"review     : {out_md}")
    if kept:
        print(f"kept       : {kept} verses' {L}_text from the previous grade file")
    print("next       : validate_grade_file.py --lang", L, "; check_termbase_consistency.py --lang", L,
          "--grade-file … --translation <machine draft> (baseline → _meta.baseline); termbase_to_glossary.py --lang",
          L, "--scope-all")


if __name__ == "__main__":
    main()
