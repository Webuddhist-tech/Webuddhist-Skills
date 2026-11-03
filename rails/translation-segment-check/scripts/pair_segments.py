#!/usr/bin/env python3
"""Pair every block of a translation with the root segment its transclusion names.

Deterministic, no model calls, writes nothing but stdout (or --out).

  pair_segments.py <translation.md>                    worksheet of all pairs
  pair_segments.py <translation.md> --ids 1-12,1-16    only these ids
  pair_segments.py <translation.md> --commentary 1-12  also every verse-aligned
                                                        commentary's passage for 1-12

A pair is keyed on the transclusion directly above the translated block, not on
the block's own id, so a transclusion that points at the wrong root segment shows
up here as a mismatch between the two ids.
"""
import argparse
import pathlib
import re
import sys

import os

# Vault root: $VAULT_ROOT, else four levels up (<vault>/4-SYSTEM/Skills/<skill>/scripts/).
VAULT = pathlib.Path(os.environ.get("VAULT_ROOT") or pathlib.Path(__file__).resolve().parents[4])
COMMENTARY_DIR = "1-SOURCES/Commentaries"
TRANSLATION_DIR = "1-SOURCES/Translations"

ID_RE = re.compile(r"\s\^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*$")
TRANS_RE = re.compile(r"^\s*!\[\[.*?#\^([A-Za-z0-9-]+)\]\]\s*$")


def body(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        text = text.split("\n---\n", 1)[1]
    return text


def blocks(path):
    """[(own_id, transcluded_id_or_None, [lines])] for every non-heading block."""
    out, pending = [], None
    for chunk in re.split(r"\n\s*\n", body(path)):
        lines = [l for l in chunk.strip("\n").splitlines() if l.strip()]
        if not lines:
            continue
        trans = [TRANS_RE.match(l).group(1) for l in lines if TRANS_RE.match(l)]
        lines = [l for l in lines if not TRANS_RE.match(l)]
        if trans:
            pending = trans[-1]
        if not lines or lines[0].startswith("#"):
            continue
        m = ID_RE.search(lines[-1])
        if not m:
            continue
        lines[-1] = lines[-1][: m.start()]
        out.append((m.group(1), pending, lines))
        pending = None
    return out


def root_from_frontmatter(path):
    """The translation's `root_text:` frontmatter value, or None."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    fm = text.split("\n---\n", 1)[0]
    m = re.search(r"^root_text:\s*['\"]?(.+?)['\"]?\s*$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    w = re.match(r"^\[\[([^\]|#]+)", val)          # tolerate a [[wiki link]] value
    if w:
        val = w.group(1)
    return val if val.endswith(".md") else val + ".md"


def commentary_passages(ref, root_stem, commentary_dir):
    """Text between the transclusion of ^ref and the next transclusion, per commentary."""
    found = []
    for f in sorted(commentary_dir.rglob("*.md")):
        lines = body(f).splitlines()
        grab, buf = False, []
        for l in lines:
            m = TRANS_RE.match(l)
            if m and root_stem in l:
                if grab:
                    break
                grab = m.group(1) == ref
                continue
            if grab and l.strip():
                buf.append(ID_RE.sub("", l).strip())
        if buf:
            found.append((f.stem, buf))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("translation")
    ap.add_argument("--root", help="root text (default: the translation's root_text: frontmatter)")
    ap.add_argument("--commentary-dir", default=COMMENTARY_DIR,
                    help=f"folder searched (recursively) for verse-aligned commentaries (default {COMMENTARY_DIR})")
    ap.add_argument("--translation-dir", default=TRANSLATION_DIR,
                    help=f"folder of reference translations (default {TRANSLATION_DIR})")
    ap.add_argument("--ids", help="comma-separated ids to include (default: all)")
    ap.add_argument("--commentary", help="comma-separated ids to dump commentary passages for")
    ap.add_argument("--no-reference", action="store_true",
                    help="omit the other 1-SOURCES translations' lines")
    ap.add_argument("--out")
    a = ap.parse_args()

    tpath = pathlib.Path(a.translation)
    if not tpath.is_absolute():
        tpath = VAULT / tpath
    a.root = a.root or root_from_frontmatter(tpath)
    if not a.root:
        sys.exit("no --root given and the translation has no root_text: in its frontmatter")
    rpath = VAULT / a.root
    if not rpath.exists():
        sys.exit(f"root text not found: {rpath}")
    root = {i: ls for i, _, ls in blocks(rpath)}
    refs = {}
    if not a.no_reference:
        for f in sorted((VAULT / a.translation_dir).glob("*.md")):
            if f.resolve() != tpath.resolve():
                refs[f.stem] = {i: ls for i, _, ls in blocks(f)}
    want = set(a.ids.split(",")) if a.ids else None

    out, problems = [], []
    pairs = blocks(tpath)
    seen = set()
    for own, trans, lines in pairs:
        seen.add(own)
        if want and own not in want:
            continue
        target = trans or own
        head = f"## ^{own}"
        if trans is None:
            problems.append(f"^{own}: no transclusion above the block")
            head += "   !! no transclusion"
        elif trans != own:
            problems.append(f"^{own}: transclusion points at ^{trans}")
            head += f"   !! transcludes ^{trans}"
        out.append(head)
        src = root.get(target)
        if src is None:
            problems.append(f"^{own}: root has no segment ^{target}")
            out.append(f"(root has no segment ^{target})")
        else:
            if len(src) != len(lines):
                out.append(f"(line count: root {len(src)}, translation {len(lines)})")
            n = max(len(src), len(lines))
            for k in range(n):
                out.append(f"  bo {k+1}: {src[k] if k < len(src) else '—'}")
                out.append(f"  tr {k+1}: {lines[k] if k < len(lines) else '—'}")
        for stem, r in refs.items():
            if target in r:
                out.append(f"  ref [{stem}]: " + " / ".join(r[target]))
        out.append("")

    missing = [i for i in root if i not in seen and (not want or i in want)]
    if missing:
        problems.append("root segments with no translated block: " + ", ".join("^" + m for m in missing))

    if a.commentary:
        for ref in a.commentary.split(","):
            out.append(f"# Commentary passages for ^{ref}")
            for stem, buf in commentary_passages(ref, rpath.stem, VAULT / a.commentary_dir):
                out.append(f"### {stem}")
                out.extend(buf)
                out.append("")

    head = [f"translation: {tpath.relative_to(VAULT)}", f"root: {a.root}",
            f"pairs: {len(pairs)}   root segments: {len(root)}"]
    head += ["!! " + p for p in problems] or ["structure: every block transcludes its own id"]
    text = "\n".join(head + [""] + out)
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
