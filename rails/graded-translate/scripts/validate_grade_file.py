#!/usr/bin/env python3
"""validate_grade_file.py — sanity-check a graded-translate Phase 1 termbase and
grade file before Phase 2 locks them.

Every check below is something that went wrong unnoticed on the Twenty-One Tārās
and was only found later by the commentary fact-check or by hand.

ERRORS (exit 1):
  E1  a keyword's `term` has no entry in the termbase
  E2  a keyword's Tibetan (`bo`) does not occur in that verse's `bo_text`
  E3  a keyword's Tibetan is not one of its term's Tibetan forms
      (1-21: མཐུ was filed under `power`, whose Tibetan is དབང)
  E4  a keyword's `en` differs from its term's locked rendering
  E5  one Tibetan form locked to two renderings in the same verse, or with
      overlapping verse_ids (context-dependent senses must be verse-scoped)
  E6  a keyword has no rendering in the target-language field (--lang)

WARNINGS:
  W1  a termbase form contains "..." — it can never match a text or be sent
      as a glossary line; split it or list the parts
  W2  one English keyword in the base draft stood for Tibetan words that are
      locked as different terms ("power" for ནུས / དབང / མཐུ) — confirm the split
  W3  one Tibetan word has several renderings — fine only if verse-scoped
  W4  termbase verse_ids and the verses whose keywords use the term disagree
  W5  a term's Tibetan is nested in another term's Tibetan in the same verse
      (the drift check reports the shorter one as COVERED; make sure that is
      intended, e.g. Tara inside the Sanskrit title)

Usage:
    python3 validate_grade_file.py --termbase <kw>/en-bo-en-termbase-general.json \\
        --grade-file <kw>/bo_en_keyword_general.json
    python3 validate_grade_file.py --lang zh --termbase <kw>/en-bo-zh-termbase-general.json \\
        --grade-file <kw>/bo_zh_keyword_general.json
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path


def forms(bo: str) -> list:
    return [f.strip() for f in (bo or "").split("/") if f.strip()]


def clean(s: str) -> str:
    return re.sub(r"[\s།༄༅༎༑]+", "", s or "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--termbase", required=True, type=Path)
    ap.add_argument("--grade-file", required=True, type=Path)
    ap.add_argument("--lang", default="en",
                    help="target-language field holding the locked rendering (en, zh, hi, …); default en")
    a = ap.parse_args(argv)
    L = a.lang
    tb = json.loads(a.termbase.read_text(encoding="utf-8"))
    g = json.loads(a.grade_file.read_text(encoding="utf-8"))
    E, W = [], []

    # termbase-level
    by_form = defaultdict(list)
    for key, e in tb.items():
        for f in forms(e.get("bo")):
            if "..." in f or "…" in f:
                W.append(f"W1 termbase '{key}': form '{f}' contains '...'")
            else:
                by_form[f].append(key)
    for f, keys in by_form.items():
        if len({tb[k].get(L) for k in keys}) > 1:
            vids = [set(tb[k].get("verse_ids") or []) for k in keys]
            overlap = any(vids[i] & vids[j] for i in range(len(vids)) for j in range(i + 1, len(vids)))
            unscoped = any(not v for v in vids)
            desc = "; ".join(f"{tb[k].get(L)} ({','.join(tb[k].get('verse_ids') or ['all'])})" for k in keys)
            if overlap or unscoped:
                E.append(f"E5 {f} has several renderings with overlapping/unscoped verses: {desc}")
            else:
                W.append(f"W3 {f} is verse-scoped: {desc}")

    en_to_bo = defaultdict(lambda: defaultdict(set))
    used = defaultdict(set)
    for vid, v in g.items():
        bo_text = clean(v.get("bo_text"))
        seen = defaultdict(set)
        present = []
        for kw in v.get("keywords", []):
            term, bo, en = kw.get("term"), kw.get("bo") or "", kw.get(L)
            if kw.get("key") and bo:
                en_to_bo[kw["key"].lower()][(bo, term or "?")].add(vid)
            if not term:
                continue
            used[term].add(vid)
            e = tb.get(term)
            if e is None:
                E.append(f"E1 [{vid}] keyword '{kw.get('key')}' -> term '{term}' not in termbase"); continue
            if bo and "..." not in bo and bo_text and clean(bo) not in bo_text:
                E.append(f"E2 [{vid}] '{term}': Tibetan {bo} is not in this verse")
            if bo and forms(e.get("bo")) and bo not in forms(e.get("bo")):
                E.append(f"E3 [{vid}] keyword Tibetan {bo} filed under '{term}', whose Tibetan is {e.get('bo')}")
            if not en:
                E.append(f"E6 [{vid}] '{term}': no '{L}' rendering in the grade file")
            elif e.get(L) and en != e[L]:
                E.append(f"E4 [{vid}] '{term}': grade file says '{en}', termbase says '{e[L]}'")
            if bo:
                seen[bo].add(en); present.append((term, bo))
        for bo, ens in seen.items():
            if len(ens) > 1:
                E.append(f"E5 [{vid}] {bo} locked to {sorted(ens)} in the same verse")
        for t1, b1 in present:
            for t2, b2 in present:
                if t1 != t2 and b1 != b2 and clean(b1) and clean(b1) in clean(b2):
                    W.append(f"W5 [{vid}] '{t1}' ({b1}) is inside '{t2}' ({b2})")
    for key, bos in en_to_bo.items():
        terms = {t for _, t in bos}
        if len(terms) > 1:   # the English word stood for Tibetan words locked as *different* terms
            W.append("W2 English '" + key + "' renders " + "; ".join(
                f"{b} → {t} ({','.join(sorted(vs))})" for (b, t), vs in bos.items()))
    for key, e in tb.items():
        tv = set(e.get("verse_ids") or [])
        if tv and used.get(key) is not None and tv != used[key]:
            W.append(f"W4 '{key}': termbase verse_ids {sorted(tv)} vs keywords in {sorted(used[key])}")

    for line in sorted(set(E)): print(line)
    for line in sorted(set(W)): print(line)
    print(f"\n{len(set(E))} error(s), {len(set(W))} warning(s) — termbase {len(tb)} entries, grade file {len(g)} verses")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main())
