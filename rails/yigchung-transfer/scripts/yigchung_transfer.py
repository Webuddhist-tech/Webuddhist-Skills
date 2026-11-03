#!/usr/bin/env python3
"""Carry the <small>…</small> yigchung marks of a root text over to a
block-aligned translation.

A yigchung (small-script rubric) in the root is a yigchung in every
translation of it, so each root block that carries <small> needs the matching
translation text marked too. Block ids make the block match certain; what has
to be decided is *which part* of the translation block is small.

  whole block small in the root (every line of it inside a tag)
      - one tag per line, and the translation has as many lines
          -> each translation line wrapped            (applied)
      - otherwise
          -> the whole translation block wrapped once  (applied)
  only part of the root block small
      -> listed in the worklist with root and translation side by side, for a
         person or model to decide by meaning. Never applied by this script.

A translation block that already carries <small> is left alone and reported.
Also reported: <small> in the translation where the root block has none.

Usage (from the vault root):

    python3 4-SYSTEM/Skills/yigchung-transfer/scripts/yigchung_transfer.py \\
        --root <root file> --translation <translation file>           # dry run + worklist
    ... --write                                                       # apply in place
    ... --check                                                       # report only: are they consistent?
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

FM_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.DOTALL)
REF_RE = re.compile(r"([ \t]*\^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*[ \t]*)$")
TRANSCLUSION_RE = re.compile(r"^\s*!\[\[.*?#\^.*?\]\]\s*$")
TAG_RE = re.compile(r"</?small>", re.IGNORECASE)
WHOLE_LINE_RE = re.compile(r"^\s*<small>(?:(?!</?small>).)*</small>\s*$", re.IGNORECASE)
BLANK_SPLIT = re.compile(r"(\r?\n[ \t]*\r?\n)")


def ref_of(line):
    m = REF_RE.search(line)
    return m.group(1).strip().lstrip("^") if m else None


def root_blocks(body):
    """ref -> content lines (no transclusions, no blank lines, id removed)."""
    out = {}
    for raw in re.split(r"\r?\n[ \t]*\r?\n", body.strip()):
        lines = [l for l in raw.split("\n") if l.strip() and not TRANSCLUSION_RE.match(l)]
        if lines and not lines[0].lstrip().startswith("#") and ref_of(lines[-1]):
            out[ref_of(lines[-1])] = [REF_RE.sub("", l).rstrip() for l in lines]
    return out


def classify(lines):
    """'none' | 'lines' (one tag per line, all lines) | 'block' (all small, other shapes) | 'partial'."""
    text = "\n".join(lines)
    if not TAG_RE.search(text):
        return "none"
    if all(WHOLE_LINE_RE.match(l) for l in lines):
        return "lines"
    inner = text.strip()
    if (inner.lower().startswith("<small>") and inner.lower().endswith("</small>")
            and len(re.findall(r"<small>", inner, re.I)) == 1):
        return "block"
    return "partial"


def wrap(lines, mode):
    """Wrap translation content lines (ids already removed)."""
    if mode == "lines":
        return [re.sub(r"^(\s*)(.*?)(\s*)$", r"\1<small>\2</small>\3", l) for l in lines]
    first, last = 0, len(lines) - 1
    out = list(lines)
    out[first] = re.sub(r"^(\s*)", r"\1<small>", out[first], count=1)
    out[last] = out[last].rstrip() + "</small>"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--translation", required=True)
    ap.add_argument("--write", action="store_true", help="apply the mechanical cases in place")
    ap.add_argument("--check", action="store_true", help="report consistency only; exit 1 if anything is unmatched")
    ap.add_argument("--worklist", help="where to write the worklist (default: 0-INBOX/temp/yigchung-transfer-<stem>.md)")
    args = ap.parse_args(argv)

    root_path, tr_path = pathlib.Path(args.root), pathlib.Path(args.translation)
    root_text = root_path.read_text(encoding="utf-8")
    m = FM_RE.match(root_text)
    rb = root_blocks(root_text[m.end():] if m else root_text)

    tr_text = tr_path.read_text(encoding="utf-8")
    m = FM_RE.match(tr_text)
    fm, body = (tr_text[:m.end()], tr_text[m.end():]) if m else ("", tr_text)

    parts = BLANK_SPLIT.split(body)          # blocks at even indexes, separators at odd
    applied, already, partial, orphan, missing, notes = [], [], [], [], [], []
    seen = set()
    for i in range(0, len(parts), 2):
        raw_lines = parts[i].split("\n")
        idx = [j for j, l in enumerate(raw_lines) if l.strip() and not TRANSCLUSION_RE.match(l)]
        if not idx or raw_lines[idx[0]].lstrip().startswith("#"):
            continue
        ref = ref_of(raw_lines[idx[-1]])
        if not ref:
            continue
        seen.add(ref)
        content = [raw_lines[j] for j in idx]
        suffix = REF_RE.search(content[-1]).group(1)
        content[-1] = REF_RE.sub("", content[-1]).rstrip()
        root_mode = classify(rb.get(ref, []))
        tr_mode = classify(content)

        if tr_mode != "none":
            (already if root_mode != "none" else orphan).append(ref)
            continue
        if root_mode == "none":
            continue
        if root_mode == "partial":
            partial.append((ref, rb[ref], content))
            continue
        mode = root_mode
        if mode == "lines" and len(rb[ref]) != len(content):
            mode = "block"
            notes.append(f"^{ref}: root wraps {len(rb[ref])} lines one by one, translation has "
                         f"{len(content)} — wrapped as one block")
        new = wrap(content, mode)
        new[-1] = new[-1] + suffix
        for j, line in zip(idx, new):
            raw_lines[j] = line
        parts[i] = "\n".join(raw_lines)
        applied.append((ref, mode))

    for ref, lines in rb.items():
        if classify(lines) != "none" and ref not in seen:
            missing.append(ref)

    print(f"root         {root_path}: {sum(1 for l in rb.values() if classify(l) != 'none')} blocks with <small>")
    print(f"translation  {tr_path}")
    if not args.check:
        print(f"  to apply   : {len(applied)}  ({sum(1 for _, m in applied if m == 'lines')} line by line, "
              f"{sum(1 for _, m in applied if m == 'block')} as one block)")
    print(f"  already marked (left alone)          : {len(already)}")
    print(f"  partial in root — needs a decision   : {len(partial)}  {[r for r, *_ in partial][:10]}")
    print(f"  <small> in translation, none in root : {len(orphan)}  {orphan[:10]}")
    print(f"  root block with <small> not found    : {len(missing)}  {missing[:10]}")
    for n in notes:
        print(f"  NOTE {n}")

    if args.check:
        unmatched = len(applied) + len(partial) + len(orphan) + len(missing)
        print("\nconsistent" if not unmatched else f"\n{unmatched} block(s) not consistent with the root")
        return 0 if not unmatched else 1

    wl = pathlib.Path(args.worklist) if args.worklist else pathlib.Path("0-INBOX/temp") / f"yigchung-transfer-{tr_path.stem}.md"
    if partial:
        wl.parent.mkdir(parents=True, exist_ok=True)
        out = [f"# Yigchung transfer worklist — {tr_path.name}", "",
               "Only part of each root block below is small. Mark the translation text that renders "
               "exactly the small part, in the translation file itself, then re-run with --check.", ""]
        for ref, rl, tl in partial:
            out += [f"## ^{ref}", "", "**Root**", "", *[f"    {l}" for l in rl], "",
                    "**Translation**", "", *[f"    {l}" for l in tl], ""]
        wl.write_text("\n".join(out), encoding="utf-8")
        print(f"\nworklist: {wl}")

    if not args.write:
        print("\ndry run: nothing written. Re-run with --write.")
        return 0
    tr_path.write_text(fm + "".join(parts), encoding="utf-8")
    print(f"\nwrote {tr_path}: {len(applied)} block(s) marked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
