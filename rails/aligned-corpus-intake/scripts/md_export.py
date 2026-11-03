#!/usr/bin/env python3
"""Read Google-Docs Markdown exports of human-made alignment documents.

    python3 md_export.py <file.md>            # rows, with emphasis runs
    python3 md_export.py <file.csv> --meta    # a metadata sheet

The Dzongsar team aligns a text by keeping two Google Docs whose paragraphs are
an auto-numbered list: row N of one document is paired with row N of the other
(see ../references/md-export-format.md). Exported with "Download → Markdown",
each row becomes one numbered list item:

    12. རིགས་ཀྱི་བུ་གང་ལ་ལ་ … ཇི་ལྟར་བསླབ་པར་བྱ།␠␠
    13.␠␠
       ***continuation line of row 13 (indented, verse)***␠␠

The number in front of a row is the row number, i.e. the alignment key. An
empty item is a row with no text on this side (its counterpart has no
equivalent here). Anything before the first numbered item is row 0 (typically
the document's own title line).

The reader never alters wording. It only:
  * splits rows at the list numbers and keeps every other line inside its row;
  * removes the export's Markdown markup — the two-space hard break, the
    indentation of continuation lines, backslash escapes (``\\[`` → ``[``) and
    the ``*``/``**``/``***`` emphasis markers — recording each emphasised span
    (offsets into the clean text) so nothing the humans marked is lost.
"""
import csv
import json
import re
import sys

ROW_RE = re.compile(r"^(\d+)\.(?:[ \t ]+(.*))?$")
_ESCAPABLE = set("\\`*_{}[]()#+-.!|<>~=")
STYLES = {1: "italic", 2: "bold", 3: "bold_italic"}


def strip_markup(line):
    """Return (clean_text, runs). runs = [{"start", "end", "style"}] in clean
    offsets. Unbalanced markers are removed too and reported as a run with
    "unclosed": True."""
    out, runs = [], []
    open_runs = {}                     # marker length -> start offset
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch == "\\" and i + 1 < n and line[i + 1] in _ESCAPABLE:
            out.append(line[i + 1])
            i += 2
            continue
        if ch == "*":
            j = i
            while j < n and line[j] == "*":
                j += 1
            k = j - i
            pos = len("".join(out))
            # close the most recent open run of the same marker length, or of
            # a combination that adds up (*** closing ** + *)
            if k in open_runs:
                start = open_runs.pop(k)
                if pos > start:
                    runs.append({"start": start, "end": pos, "style": STYLES.get(k, f"{k}*")})
            elif k == 3 and 1 in open_runs and 2 in open_runs:
                for kk in (1, 2):
                    start = open_runs.pop(kk)
                    if pos > start:
                        runs.append({"start": start, "end": pos, "style": STYLES[kk]})
            else:
                open_runs[k] = pos
            i = j
            continue
        out.append(ch)
        i += 1
    text = "".join(out)
    for k, start in open_runs.items():
        if len(text) > start:
            runs.append({"start": start, "end": len(text), "style": STYLES.get(k, f"{k}*"), "unclosed": True})
    runs.sort(key=lambda r: (r["start"], r["end"]))
    return text, runs


def read_rows(path):
    """Rows of a numbered-list export, in document order.

    Returns a list of dicts {"row", "text", "raw", "runs"} with row 0 holding
    any text before the first numbered item. `text` keeps the row's line
    structure (one line per non-blank source line, outer whitespace and the
    two-space hard break trimmed); `raw` is the row exactly as exported."""
    rows = []
    cur = {"row": 0, "raw": []}
    for line in open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n"):
        m = ROW_RE.match(line)
        if m:
            rows.append(cur)
            cur = {"row": int(m.group(1)), "raw": [m.group(2) or ""]}
        else:
            cur["raw"].append(line)
    rows.append(cur)
    out = []
    for r in rows:
        lines, runs, off = [], [], 0
        for raw_line in r["raw"]:
            clean, rr = strip_markup(raw_line)
            lead = len(clean) - len(clean.lstrip(" \t "))
            clean = clean.strip(" \t ")
            if not clean:
                continue
            if lines:
                off += 1                                   # the joining "\n"
            for x in rr:
                s, e = max(0, x["start"] - lead), min(len(clean), x["end"] - lead)
                if e > s:
                    runs.append(dict(x, start=s + off, end=e + off))
            lines.append(clean)
            off += len(clean)
        text = "\n".join(lines)
        if r["row"] == 0 and not text:
            continue
        out.append({"row": r["row"], "text": text, "raw": "\n".join(r["raw"]), "runs": runs})
    nums = [r["row"] for r in out if r["row"]]
    if nums != sorted(nums) or len(set(nums)) != len(nums):
        raise ValueError(f"{path}: row numbers are not strictly increasing")
    return out


OP_PREFIX = "openpecha:"


def _clean_segment(text):
    """A segment's text in the shape read_rows gives a row: one line per
    non-blank source line, outer whitespace trimmed. Wording is untouched."""
    return "\n".join(l.strip(" \t ") for l in text.replace("\r\n", "\n").split("\n")
                     if l.strip(" \t "))


def op_rows(op_root, ref):
    """Rows of an OpenPecha API v2 download (layout: openpecha_model.py), so
    an aligned OpenPecha text can be read by md_rows like a row-aligned pair.

      '<text_id>'          row k = the k-th segment of the text's segmentation
                           annotation (1-based, in document order)
      '<text_id>#parent'   row k = the parent text's spans that the upstream
                           alignment annotation pairs with segment k (joined
                           by a newline, in the parent's order); empty when
                           segment k has no aligned counterpart

    The pairing row k <-> row k is therefore exactly the human alignment
    annotation. An alignment span that does not coincide with a segment, or a
    parent span aligned to more than one segment, is refused (a human must
    decide how to read it) rather than silently re-paired."""
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import openpecha_model
    text_id, _, side = ref.partition("#")
    m = openpecha_model.load(op_root, text_id)
    segs = m["segments"]
    if side == "":
        return [{"row": k, "text": _clean_segment(m["content"][s["start"]:s["end"]]),
                 "raw": m["content"][s["start"]:s["end"]], "runs": [],
                 "openpecha": {"text_id": text_id, "instance_id": m["instance_id"], "segment": s["id"],
                               "start": s["start"], "end": s["end"]}}
                for k, s in enumerate(segs, 1)]
    if side != "parent":
        raise ValueError(f"{OP_PREFIX}{ref}: unknown side {side!r} (use '#parent')")
    if not m["alignment"]:
        raise ValueError(f"{OP_PREFIX}{ref}: {text_id} has no alignment in tree.json")
    parent = openpecha_model.load(op_root, m["alignment"]["parent_text"], m["alignment"]["parent_instance"])
    by_span = {(s["start"], s["end"]): k for k, s in enumerate(segs, 1)}
    targets, owner = {}, {}
    for p in m["alignment"]["pairs"]:
        k = by_span.get((p["start"], p["end"]))
        if k is None:
            raise ValueError(f"{OP_PREFIX}{ref}: alignment span {p['start']}-{p['end']} is not a segment of {text_id}")
        t = (p["target_start"], p["target_end"], p["target_id"])
        if owner.setdefault(t[2], k) != k:
            raise ValueError(f"{OP_PREFIX}{ref}: parent span {t[2]} is aligned to segments {owner[t[2]]} and {k}")
        targets.setdefault(k, [])
        if t not in targets[k]:
            targets[k].append(t)
    out = []
    for k, s in enumerate(segs, 1):
        ts = sorted(targets.get(k, []))
        raw = "\n".join(parent["content"][a:b] for a, b, _ in ts)
        out.append({"row": k, "text": "\n".join(_clean_segment(parent["content"][a:b]) for a, b, _ in ts),
                    "raw": raw, "runs": [],
                    "openpecha": {"text_id": parent["text_id"], "instance_id": parent["instance_id"],
                                  "aligned_to_segment": s["id"],
                                  "spans": [{"id": i, "start": a, "end": b} for a, b, i in ts]}})
    return out


def read_source_rows(raw_root, rel, op_dir="openpecha-api"):
    """Rows of a manifest row source: a Markdown export under raw_root, or
    'openpecha:<text_id>[#parent]' read from raw_root/op_dir (see op_rows)."""
    import pathlib
    if rel.startswith(OP_PREFIX):
        return op_rows(pathlib.Path(raw_root) / op_dir, rel[len(OP_PREFIX):])
    from common import raw_path
    return read_rows(raw_path(raw_root, rel))


def read_meta(path):
    """A Dzongsar metadata sheet exported as CSV: rows `field,BO,EN[,ZH]`
    under an `Entries,…` header (an optional banner row above it is
    skipped). Returns {field: {"bo": …, "en": …, "zh": …}} with empty cells
    dropped — cell text only, never hyperlinks."""
    meta, header = {}, None
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.reader(fh):
            if not row:
                continue
            if header is None:
                if row[0].strip() == "Entries":
                    header = [h.strip().lower() for h in row[1:]]
                continue
            vals = {h: v.strip() for h, v in zip(header, row[1:]) if v.strip()}
            if vals:
                meta[row[0].strip()] = vals
    if header is None:
        raise ValueError(f"{path}: no 'Entries,…' header row")
    return meta


if __name__ == "__main__":
    p = sys.argv[1]
    if "--meta" in sys.argv:
        print(json.dumps(read_meta(p), ensure_ascii=False, indent=1))
    else:
        for r in read_rows(p):
            flag = f" runs={len(r['runs'])}" if r["runs"] else ""
            print(f"{r['row']:4d}{flag} {r['text'][:100]!r}")
