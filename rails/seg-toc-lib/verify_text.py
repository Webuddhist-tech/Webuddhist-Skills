#!/usr/bin/env python3
"""
Strict text check for the segmentation + TOC workflows (root texts and commentaries):
is the output exactly the source text — every letter AND every space — apart from the
layout the workflow is allowed to add?

    python verify_text.py <source.md> <output.md>            # check, exit 1 on a difference
    python verify_text.py <source.md> <output.md> --fix      # also restore the source spacing

Allowed differences (the workflow's job): heading lines; trailing block IDs (` ^1-2`); a line
or block break where the source has a space, nothing, or a line break; a space where the
source has a line break (a printed line joined inside a paragraph); the frontmatter.

Reported — everything else:
  letters      a character deleted, added or changed (never fixable: the output is wrong)
  spacing      inside a line, a space added where the source has none, a space removed,
               or a run of spaces changed (`། །` → `།།`, `ནོ། །དེ` → `ནོ། ། དེ`)

--fix rewrites only the spacing inside lines, copying the source's own whitespace; it refuses
when the letters differ. Checks of the individual scripts compare text with all whitespace
removed, so they cannot see spacing; this is the gate that can.
"""
import re
import sys
from pathlib import Path

FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)
HEAD = re.compile(r"^#{1,6}\s")
ID = re.compile(r"([ \t]+\^[\w-]+)[ \t]*$")


def source_tokens(text):
    """[(gap before, char)] for every non-whitespace character of the source."""
    text = FRONT.sub("", text)
    text = "\n".join(l for l in text.split("\n") if not HEAD.match(l))
    out, gap = [], ""
    for ch in text:
        if ch.isspace():
            gap += ch
        else:
            out.append((gap, ch))
            gap = ""
    return out


def walk(src_text, out_text, fix):
    toks = source_tokens(src_text)
    k = 0
    issues = {"letters": 0, "spacing": 0}
    examples = []
    m = FRONT.match(out_text)
    head, body = (m.group(0), out_text[m.end():]) if m else ("", out_text)
    new_lines = []
    for line in body.split("\n"):
        if HEAD.match(line):
            new_lines.append(line)
            continue
        idm = ID.search(line)
        content, suffix = (line[:idm.start()], idm.group(1)) if idm else (line, "")
        rebuilt, gap, first = [], "", True
        for ch in content:
            if ch.isspace():
                gap += ch
                continue
            if k >= len(toks) or toks[k][1] != ch:
                issues["letters"] += 1
                if len(examples) < 3:
                    ctx = "".join(c for _, c in toks[max(0, k - 12):k + 3])
                    examples.append(f"letters: expected {toks[k][1] if k < len(toks) else 'END'!r}, "
                                    f"got {ch!r} after …{ctx}")
                return issues, examples, None
            sgap = toks[k][0]
            if first:
                rebuilt.append(gap)              # line start: the break is the layout
            elif "\n" in sgap:
                rebuilt.append(gap)              # a printed line joined: any space is fine
            elif gap != sgap:
                issues["spacing"] += 1
                if len(examples) < 5:
                    ctx = "".join(c for _, c in toks[max(0, k - 8):k])
                    examples.append(f"spacing: source {sgap!r} → output {gap!r} at …{ctx}|{ch}")
                rebuilt.append(sgap if fix else gap)
            else:
                rebuilt.append(gap)
            rebuilt.append(ch)
            k += 1
            gap, first = "", False
        rebuilt.append(gap)
        new_lines.append("".join(rebuilt) + suffix)
    if k < len(toks):
        issues["letters"] += 1
        examples.append(f"letters: {len(toks) - k} source characters missing at the end of the output")
    return issues, examples, head + "\n".join(new_lines)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    fix = "--fix" in sys.argv
    if len(a) != 2:
        sys.exit(__doc__)
    src, out = Path(a[0]), Path(a[1])
    issues, examples, fixed = walk(src.read_text(encoding="utf-8"), out.read_text(encoding="utf-8"), fix)
    for e in examples:
        print("  " + e)
    if issues["letters"]:
        print(f"✗ {out.name}: LETTERS DIFFER from {src.name} — the output is wrong; nothing fixed")
        sys.exit(1)
    if issues["spacing"] and fix:
        out.write_text(fixed, encoding="utf-8")
        again, _, _ = walk(src.read_text(encoding="utf-8"), fixed, False)
        assert not any(again.values()), "spacing fix did not converge"
        print(f"✓ {out.name}: letters identical; {issues['spacing']} spacing difference(s) restored "
              f"from the source — now identical (letters and spacing)")
        return
    if issues["spacing"]:
        print(f"✗ {out.name}: letters identical, {issues['spacing']} spacing difference(s) "
              f"(run with --fix to restore the source spacing)")
        sys.exit(1)
    print(f"✓ {out.name}: identical to {src.name} (letters and spacing; only breaks, headings, IDs added)")


if __name__ == "__main__":
    main()
