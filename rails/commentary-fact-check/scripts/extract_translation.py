#!/usr/bin/env python3
"""
Parse a translation file into a {verse_id: text} dict, optionally filtered to
one chapter. A verse is every line of its block up to the line that ends in the
block ID (`… ^1-5`), so multi-line verses are kept whole. Works for both
layouts: one line per verse (`{text} ^{verse_id}`), and the transclusion layout
(`![[<root>#^1-5]]` above each translated block — those lines are skipped).
YAML frontmatter is ignored; heading markers (`## `) are stripped.

Before 2026-09 this read one line at a time and kept only the line carrying
the ID — for a four-line verse, only its last line.

Usage:
    python3 extract_translation.py <translation>.md [--chapter 1] [--json out.json]
"""
import argparse
import json
import re


ID_RE = re.compile(r"(?<!\S)\^((?:\w[\w\-]*)?\d)\s*$")


def strip_frontmatter(content):
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            return content[end + 4:]
    return content


def parse(content):
    verses = {}
    acc = []
    for raw in strip_frontmatter(content).splitlines():
        line = raw.strip()
        if not line:
            acc = []                      # a block ends at a blank line
            continue
        if line.startswith("![["):        # transclusion of the source block
            continue
        m = ID_RE.search(line)
        if not m:
            acc.append(re.sub(r"^#+\s*", "", line))
            continue
        last = re.sub(r"^#+\s*", "", line[: m.start()].strip()).strip()
        if last:
            acc.append(last)
        vid = m.group(1)
        if vid in verses:
            print(f"warning: block ID ^{vid} appears more than once; keeping both", flush=True)
            verses[vid] += "\n" + "\n".join(acc)
        else:
            verses[vid] = "\n".join(acc)
        acc = []
    return verses


def sort_key(vid):
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in vid.split("-")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("translation", help="Path to the graded translation .md file")
    ap.add_argument("--chapter", default=None, help="Restrict output to one chapter (e.g. 1, or 'a'/'b' for colophon)")
    ap.add_argument("--json", default=None, help="Write filtered {verse_id: text} JSON to this path")
    args = ap.parse_args()

    content = open(args.translation, encoding="utf-8").read()
    verses = parse(content)

    if args.chapter is not None:
        verses = {vid: t for vid, t in verses.items() if vid.split("-")[0] == args.chapter}

    print(f"Parsed {len(verses)} verse blocks" + (f" for chapter {args.chapter}" if args.chapter else ""))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(verses, f, ensure_ascii=False, indent=2)
        print(f"Wrote to {args.json}")
    else:
        for vid in sorted(verses, key=sort_key):
            print(f"{vid}: {verses[vid]}")


if __name__ == "__main__":
    main()
