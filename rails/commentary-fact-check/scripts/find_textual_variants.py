#!/usr/bin/env python3
"""find_textual_variants.py — list the places where a commentary's quotation
of the root text differs from the root edition in the vault.

Commentaries quote each root line before explaining it, so a line-by-line
comparison of those quotations against the root finds the commentator's
readings automatically. On the Twenty-One Tārās this surfaced, by hand,
sgrol ma vs sgron ma at 1-16, 'gyur vs 'gyur cig at 2-6, and ha ra / ta ra
swapped between 1-18 and 1-20 in Tāranātha's copy. These are textual variants,
not translation errors: report them separately in the fact-check.

For each root line the script finds the best-matching run of syllables in that
verse's commentary passage. A match ≥ --min (default 0.75) counts as a
quotation; if it is not identical, the differing syllables are listed.
Lines with no quotation above the threshold are reported as not quoted.
Commentaries that paraphrase the root while glossing it (Tāranātha) quote
fewer lines verbatim; lowering --min finds more, with more false alarms.

Usage:
    python3 find_textual_variants.py <commentary>.md --root <root>.md [--md out.md] [--min 0.6]
"""
import argparse, difflib, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from extract_commentary import extract  # noqa: E402

ID_RE = re.compile(r"(?<!\S)\^((?:\w[\w\-]*)?\d)\s*$")


def syllables(s):
    s = re.sub(r"[༄༅།༎༑༔\s]+", "་", s)
    return [x for x in s.split("་") if x and not re.fullmatch(r"[\W\d_]+", x)]


def root_lines(path):
    """{verse_id: [line, …]} for the root's content blocks."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    if text.startswith("---"):
        e = text.find("\n---", 3)
        text = text[e + 4:] if e != -1 else text
    out, acc = {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            acc = [] if not line else acc
            if line.startswith("#"):
                acc = []
            continue
        m = ID_RE.search(line)
        body = line[: m.start()].strip() if m else line
        # a Tibetan block often puts two metrical lines on one line: split at "། །"
        acc += [p for p in re.split(r"(?<=།)\s*།?\s+", body) if syllables(p)]
        if m:
            out[m.group(1)] = acc
            acc = []
    return out


def best_window(line_syl, passage_syl):
    n, best = len(line_syl), (0.0, None)
    for size in {n - 1, n, n + 1} - {0}:
        for i in range(0, max(1, len(passage_syl) - size + 1)):
            win = passage_syl[i:i + size]
            r = difflib.SequenceMatcher(None, line_syl, win, autojunk=False).ratio()
            if r > best[0]:
                best = (r, win)
                if r == 1.0:
                    return best
    return best


def diff(a, b):
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append(f"{'་'.join(a[i1:i2]) or '∅'} → {'་'.join(b[j1:j2]) or '∅'}")
    return "; ".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commentary")
    ap.add_argument("--root", required=True)
    ap.add_argument("--min", type=float, default=0.75)
    ap.add_argument("--md", type=pathlib.Path)
    a = ap.parse_args(argv)
    passages, order, _ = extract(open(a.commentary, encoding="utf-8").read(), None)
    roots = root_lines(a.root)
    rows, not_quoted, checked = [], [], 0
    for vid in order:
        psyl = syllables(passages.get(vid, ""))
        for line in roots.get(vid, []):
            ls = syllables(line)
            if len(ls) < 3:
                continue
            checked += 1
            r, win = best_window(ls, psyl)
            if r < a.min or win is None:
                not_quoted.append(vid)
            elif r < 1.0:
                rows.append((vid, "་".join(ls), "་".join(win), diff(ls, win), r))
    name = pathlib.Path(a.commentary).name
    out = [f"# Textual variants — {name}", "",
           f"Root: `{pathlib.Path(a.root).name}`. {checked} root lines checked; "
           f"{len(rows)} quoted with a difference; lines not quoted in {len(set(not_quoted))} verse(s).", "",
           "Differences are the commentator's reading of the root, not translation errors. "
           "Spelling-only differences (du/tu, ra/rwa) are common; check the ones that change a word.", "",
           "| Verse | Root (vault edition) | Commentary's quotation | Difference | Match |",
           "|---|---|---|---|---|"]
    out += [f"| {v} | {r} | {c} | {d} | {m:.2f} |" for v, r, c, d, m in rows]
    if not_quoted:
        out += ["", f"Not quoted (match < {a.min}): " + ", ".join(sorted(set(not_quoted), key=order.index))]
    text = "\n".join(out) + "\n"
    if a.md:
        a.md.write_text(text, encoding="utf-8"); print(f"Written -> {a.md}")
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
