#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fix_midverse.py — Detect (and optionally fix) merged verse half-lines in an
already-formatted Tibetan file, preserving all existing block IDs.

Usage:
    # lint only — report every mergeable line, write nothing
    python3 fix_midverse.py --input texts/<text-id>/work/segmented.md --check

    # fix in place (only after a human has reviewed the --check report)
    python3 fix_midverse.py --input texts/<text-id>/work/segmented.md

    # fix to a separate output file instead of in place
    python3 fix_midverse.py --input ... --output texts/<text-id>/work/segmented.fixed.md

Two patterns are detected:

1. MID_VERSE BREAK — a single shad '།' preceded by a space and immediately
   followed by a Tibetan syllable (no space/shad after).
   Pattern: [letter] །[letter]  e.g. 'ཞིག །ན', 'གི །ས'
   Regex: r'(?<![།]) །(?=[^\s།])'

2. EMBEDDED SHAD_PAIR — '། །' in the MIDDLE of a line (not at end), followed
   by a Tibetan syllable. The second line starts fresh.
   Pattern: [text]། །[Tibetan][more text]
   Regex: r'། །(?=[ༀ-ཿ])'

Block IDs ('^N-N') are extracted before splitting and re-attached to the last
split line. No verse numbers are changed.

Detection/splitting logic is unchanged from the tested vault original
(bodhisattvacharyavatara-rails/4-SYSTEM/scripts/fix_midverse.py); only the
hardcoded vault paths were replaced with --input/--output/--check arguments.
"""

import re
import sys
import argparse

# Pattern 1: mid-verse single-shad break
MID_LINE_SHAD = re.compile(r'(?<![།]) །(?=[^\s།])')
# Pattern 2: embedded SHAD_PAIR followed by Tibetan syllable
EMBEDDED_PAIR = re.compile(r'། །(?=[ༀ-ཿ])')
# Block ID at end of line
BLOCK_ID_RE = re.compile(r'(\s*\^\S+)\s*$')


def split_line(line):
    """
    Split a merged verse line into correctly-terminated sub-lines.
    Returns a list of strings (without trailing newline).
    The block ID, if any, is moved to the last sub-line.
    """
    # Extract trailing block ID
    m = BLOCK_ID_RE.search(line)
    if m:
        bid = m.group(1)
        core = line[:m.start()]
    else:
        bid = ''
        core = line

    # Apply both split patterns via sentinel substitution
    # Use null-byte as sentinel so we can split cleanly after both passes
    core = MID_LINE_SHAD.sub(' །\x00', core)    # mid-verse: keep the ' །'
    core = EMBEDDED_PAIR.sub('། །\x00', core)   # embedded pair: keep '། །'

    parts = [p.strip() for p in core.split('\x00') if p.strip()]
    if not parts:
        return [line]

    result = []
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            result.append(part + bid)
        else:
            result.append(part)
    return result


def needs_split(line):
    return MID_LINE_SHAD.search(line) or EMBEDDED_PAIR.search(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', required=True,
                    help='Formatted Tibetan .md file to scan (e.g. texts/<text-id>/work/segmented.md)')
    ap.add_argument('--output', default=None,
                    help='Write fixed file here instead of in place (ignored with --check)')
    ap.add_argument('--check', action='store_true',
                    help='Lint only: report every line that would be split, write nothing, '
                         'exit 1 if any found')
    args = ap.parse_args()

    INPUT = args.input
    OUTPUT = args.output or INPUT

    with open(INPUT, 'r', encoding='utf-8') as f:
        raw = f.readlines()

    print(f"Read {len(raw)} lines from {INPUT}")

    output = []
    changed = 0
    shown = 0
    for i, line in enumerate(raw, 1):
        stripped = line.rstrip('\n')
        if needs_split(stripped):
            parts = split_line(stripped)
            if len(parts) > 1:
                changed += 1
                for p in parts:
                    output.append(p + '\n')
                if shown < 10 or args.check:
                    shown += 1
                    print(f"  [{i}] → {len(parts)} lines:")
                    for p in parts:
                        print(f"        {p}")
            else:
                output.append(line)
        else:
            output.append(line)

    if args.check:
        print(f"\nCheck complete. {changed} merged line(s) found — nothing written.")
        sys.exit(1 if changed else 0)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f"\nDone. {changed} lines split → file: {OUTPUT}")


if __name__ == '__main__':
    main()
