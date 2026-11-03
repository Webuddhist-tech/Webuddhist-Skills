#!/usr/bin/env python3
"""Convert an interleaved bilingual translation into the vault's transclusion form.

Input: a translation whose every block carries the root text inline, then a
separator, then the translation, and ends in the root's block id:

    ༄༅། །བླ་མ་དང་…ཕྱག་འཚལ་ལོ། །
    <br>
    恭敬頂禮上師與文殊妙音。 ^I-1

    ## ༄༅། །བཅོམ་ལྡན་འདས་…<br>《世尊釋迦王祈請文十五頌》 ^I-0

Output: the root part replaced by a transclusion of the root block, so the
translation is aligned to the root by block id instead of carrying a copy of it:

    ![[<root>#^I-1]]

    恭敬頂禮上師與文殊妙音。 ^I-1

    ![[<root>#^I-0]]

    ## 《世尊釋迦王祈請文十五頌》 ^I-0

Safety: the inline root part of every block must equal the root file's block
with the same id (compared without whitespace, <small> tags, heading marks and
the id). One mismatch — a wrong id, a missing block, an edited root line — and
nothing is written. Block ids must be the root's, in the root's order.

Usage (from the vault root):

    python3 4-SYSTEM/Skills/bilingual-to-transclusion/scripts/bilingual_to_transclusion.py \\
        --root <root file> --src <interleaved file>              # dry run
    ... --write                                                  # rewrite --src in place
    ... --write --out <path>                                     # write elsewhere
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
REF_RE = re.compile(r"[ \t]*\^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)[ \t]*$")
TRANSCLUSION_RE = re.compile(r"^\s*!\[\[.*?#\^.*?\]\]\s*$")
TAG_RE = re.compile(r"</?small>", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,})[ \t]+")


def split_fm(text):
    m = FM_RE.match(text)
    return (m.group(0), text[m.end():]) if m else ("", text)


def blocks(body):
    """[(ref, [lines])] — one entry per blank-line-separated block, transclusions dropped."""
    out = []
    for raw in re.split(r"\r?\n[ \t]*\r?\n", body.strip()):
        lines = [l.rstrip("\r") for l in raw.split("\n") if not TRANSCLUSION_RE.match(l)]
        lines = [l for l in lines if l.strip()]
        if not lines:
            continue
        m = REF_RE.search(lines[-1])
        out.append((m.group(1) if m else None, lines))
    return out


def norm(text):
    text = TAG_RE.sub("", text)
    text = REF_RE.sub("", text) if "\n" not in text else "\n".join(REF_RE.sub("", l) for l in text.split("\n"))
    text = re.sub(r"^#+", "", text, flags=re.M)
    return re.sub(r"\s+", "", text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, help="the root text the translation aligns to")
    ap.add_argument("--src", required=True, help="the interleaved bilingual file")
    ap.add_argument("--sep", default="<br>", help="separator between root and translation (default <br>)")
    ap.add_argument("--link", default=None,
                    help="link target written in each transclusion (default: the root's vault path, e.g. "
                         "1-SOURCES/Text/<root>.md)")
    ap.add_argument("--write", action="store_true", help="write the result (default: dry run)")
    ap.add_argument("--out", help="write here instead of rewriting --src")
    args = ap.parse_args(argv)

    root_path, src_path = pathlib.Path(args.root), pathlib.Path(args.src)
    link = args.link or root_path.as_posix()
    _, root_body = split_fm(root_path.read_text(encoding="utf-8"))
    fm, src_body = split_fm(src_path.read_text(encoding="utf-8"))

    root_blocks = blocks(root_body)
    root_map = {r: "\n".join(ls) for r, ls in root_blocks if r}
    root_order = [r for r, _ in root_blocks if r]
    src_blocks = blocks(src_body)

    problems, out_blocks = [], []
    src_order = [r for r, _ in src_blocks]
    if None in src_order:
        problems.append(f"{src_order.count(None)} block(s) without a block id, first after "
                        f"{src_order[src_order.index(None) - 1] if src_order.index(None) else 'start'}")
    if [r for r in src_order if r] != root_order:
        missing = [r for r in root_order if r not in set(src_order)]
        extra = [r for r in src_order if r and r not in root_map]
        problems.append(f"block ids differ from the root's (missing {missing[:8]}, not in root {extra[:8]}"
                        f"{'' if missing or extra else ', order differs'})")

    for ref, lines in src_blocks:
        if ref is None:
            continue
        joined = "\n".join(lines)
        if joined.count(args.sep) != 1:
            problems.append(f"^{ref}: expected exactly one {args.sep!r}, found {joined.count(args.sep)}")
            continue
        root_part, trans_part = joined.split(args.sep, 1)
        if norm(root_part) != norm(root_map.get(ref, "")):
            problems.append(f"^{ref}: inline root text differs from the root block")
            continue
        trans_lines = [REF_RE.sub("", l).rstrip() for l in trans_part.split("\n")]
        trans_lines = [l.strip() if i == 0 else l for i, l in enumerate(trans_lines)]
        trans_lines = [l for l in trans_lines if l.strip()]
        if not trans_lines:
            problems.append(f"^{ref}: no translation after the separator")
            continue
        heading = HEADING_RE.match(lines[0])
        if heading:
            if len(trans_lines) != 1:
                problems.append(f"^{ref}: heading translation spans {len(trans_lines)} lines")
                continue
            body = f"{heading.group(1)} {trans_lines[0].strip()} ^{ref}"
        else:
            trans_lines[-1] = f"{trans_lines[-1]} ^{ref}"
            body = "\n".join(trans_lines)
        out_blocks.append(f"![[{link}#^{ref}]]\n\n{body}")

    print(f"root  {root_path}  ({len(root_order)} blocks)")
    print(f"src   {src_path}  ({len(src_blocks)} blocks)")
    if problems:
        for p in problems[:40]:
            print(f"  ERROR {p}")
        if len(problems) > 40:
            print(f"  … {len(problems) - 40} more")
        sys.exit("ABORT: nothing written")
    print(f"  every inline root block matches the root: {len(out_blocks)} blocks")
    print(f"  transclusion link: ![[{link}#^<id>]]")

    result = fm + "\n\n".join(out_blocks) + "\n"
    if not args.write:
        print("\ndry run: nothing written. Re-run with --write.")
        return 0
    out = pathlib.Path(args.out) if args.out else src_path
    out.write_text(result, encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
