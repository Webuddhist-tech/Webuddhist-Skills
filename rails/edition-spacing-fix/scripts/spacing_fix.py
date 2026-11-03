#!/usr/bin/env python3
"""Find spacing errors in a published edition and fix them in place, bottom-up,
through `PATCH /v2/editions/{id}/content` — without moving a segment boundary.

The live edition is the thing users read, so it is what gets scanned: the
content is fetched from the backend and cut into its own line spans. The
content stores lines butted together with no separator, so a scan over the raw
string would report every line break as a missing space; scanning per line
span avoids that.

Every hit goes into a mapping file before anything is changed. A human reviews
the mapping, approves or rejects each issue, and only approved issues are ever
sent. Each one is recorded back into the mapping as it lands.

    scan    <note>                    GET the live edition, write the mapping
    add     <map> --segment R --line N --original X --proposed Y
    decide  <map> --approve/--reject/--set
    apply   <map> [--execute]         dry run by default; bottom-up PATCH calls
    verify  <map>                     GET the live edition, check every fix
    note    <map> [--file F] [--write] mirror the fixes into a vault note
    toc     <map> --fix T001 [--execute] rebuild a TOC with fixed titles, spans recalculated
    report  <map>                     rewrite the review table from the mapping

Why bottom-up: each op's offsets are stated against the content as it is on
the backend now. Applying them highest position first keeps every lower offset
valid, so nothing is recomputed between calls and an interrupted run resumes.

Why only insert and delete, strictly inside one line: the backend's span
arithmetic is unambiguous there — the line that holds the position grows or
shrinks and every later span shifts. An insert on a line boundary would attach
the text to the previous line, and a replace that spans a boundary can collapse
segments, so both are refused rather than risked.

Safety: nothing mutating is called without --execute, and before it offers to,
the script replays the backend's own span arithmetic (vendored below) over the
live spans and proves that every line — and every TOC section boundary — comes
out selecting exactly the expected text. Any disagreement aborts.

Env: WEBUDDHIST_API_KEY, WEBUDDHIST_API_BASE (default https://library.webuddhist.com),
WEBUDDHIST_APP (default "webuddhist"). Run from the vault root after
`set -a; source 4-SYSTEM/scripts/.env; set +a`.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import os
import pathlib
import re
import sys
import unicodedata
import urllib.error
import urllib.request

VAULT = pathlib.Path(os.environ.get("VAULT_ROOT", pathlib.Path.cwd()))
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = VAULT / "0-INBOX" / "temp" / "edition-spacing-fix"
ALLOWLIST = SKILL_DIR / "references" / "allowlist.txt"
DICT_PATHS = ("/usr/share/dict/words", "/usr/dict/words")
BASE = os.environ.get("WEBUDDHIST_API_BASE", "https://library.webuddhist.com").rstrip("/")

# Function words: a run-together word with one of these on either side is
# almost always two words ("ofthe", "mindto", "upholdit").
FUNC = set("""a i an the of to in on at by for from with as and or nor but so yet
my me mine you your yours us our we he him his she her it its they them their
is are was were be been am do does did has have had not no all this that these
those who whom whose which what when where may let can will shall such very
into onto upon over under through every each any some own one how why then than
there here now also only even just like if till until""".split())

PUNCT_NEEDS_SPACE = ",;:!?"
EM_DASH = "—"
ODD_SPACE = {"\u00a0": "NO-BREAK SPACE", "\t": "TAB", "\u200b": "ZERO WIDTH SPACE",
             "\u2009": "THIN SPACE", "\u202f": "NARROW NO-BREAK SPACE", "\ufeff": "BOM"}


# ---------------------------------------------------------------------------
# The backend's own span arithmetic, vendored so the simulation is the server's
# and not a re-reading of it.
#   webuddhist-library/openpecha-backend  database/span_database.py
#   commit 7fa2564 (2026-09-28): _adjust_continuous_for_insert,
#   _adjust_annotation_for_insert, _adjust_span_for_delete.
# A Segment line span is a "continuous" span; a TOC section span is an
# "annotation" span. Re-pin after any backend upgrade — see SKILL.md.
# ---------------------------------------------------------------------------

def adjust_continuous_for_insert(start, end, insert_pos, insert_len):
    if insert_pos == 0 and start == 0:
        return (start, end + insert_len)
    if insert_pos <= start:
        return (start + insert_len, end + insert_len)
    if insert_pos <= end:
        return (start, end + insert_len)
    return (start, end)


def adjust_annotation_for_insert(start, end, insert_pos, insert_len):
    if insert_pos <= start:
        return (start + insert_len, end + insert_len)
    if insert_pos < end:
        return (start, end + insert_len)
    return (start, end)


def adjust_span_for_delete(start, end, del_start, del_end):
    del_len = del_end - del_start
    if del_end <= start:
        return (start - del_len, end - del_len)
    if del_start >= end:
        return (start, end)
    if del_start <= start and del_end >= end:
        return None
    if del_start <= start < del_end < end:
        return (del_start, end - del_len)
    if start < del_start < end <= del_end:
        return (start, del_start)
    if start < del_start and del_end < end:
        return (start, end - del_len)
    return (start, end)


def apply_op_to_spans(spans, op, continuous):
    out = []
    for s in spans:
        if s is None:
            out.append(None)
        elif op["type"] == "insert":
            f = adjust_continuous_for_insert if continuous else adjust_annotation_for_insert
            out.append(f(s[0], s[1], op["position"], len(op["text"])))
        else:
            out.append(adjust_span_for_delete(s[0], s[1], op["start"], op["end"]))
    return out


def apply_op_to_text(text, op):
    if op["type"] == "insert":
        return text[:op["position"]] + op["text"] + text[op["position"]:]
    return text[:op["start"]] + text[op["end"]:]


def op_pos(op):
    return op["position"] if op["type"] == "insert" else op["start"]


# ---------------------------------------------------------------------------
# api
# ---------------------------------------------------------------------------

class ApiError(Exception):
    pass


def headers():
    h = {"Accept": "application/json", "X-Application": os.environ.get("WEBUDDHIST_APP") or "webuddhist"}
    key = os.environ.get("WEBUDDHIST_API_KEY")
    if key:
        h["X-API-Key"] = key
    return h


def call(method, path, body=None, timeout=120):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:800]
    except urllib.error.URLError as e:
        raise ApiError(f"network error {method} {path}: {e.reason}") from None


def get_ok(path):
    st, d = call("GET", path)
    if st != 200:
        sys.exit(f"GET {path} -> {st} {d}")
    return d


def live_content(eid):
    d = get_ok(f"/v2/editions/{eid}/content")
    return d if isinstance(d, str) else (d.get("content") or "")


def live_segments(eid):
    out, offset = [], 0
    while True:
        d = get_ok(f"/v2/editions/{eid}/segmentation/segments?limit=500&offset={offset}")
        items = d["items"] if isinstance(d, dict) else d
        out += items
        if not (isinstance(d, dict) and d.get("has_more")) or not items:
            return out
        offset += len(items)


def live_lines(segments):
    """[(ref, segment_id, line_index, start, end)] in content order."""
    rows = []
    for s in segments:
        lines = s.get("lines") or ([s["span"]] if s.get("span") else [])
        for i, ln in enumerate(lines):
            rows.append((s.get("reference"), s.get("id"), i, ln["start"], ln["end"]))
    return sorted(rows, key=lambda r: (r[3], r[4]))


def live_toc(eid):
    st, d = call("GET", f"/v2/editions/{eid}/table-of-contents")
    if st != 200:
        return []
    return d if isinstance(d, list) else [d]


def toc_sections(tocs):
    out = []

    def walk(secs, toc_id, depth):
        for s in secs:
            out.append({"toc_id": toc_id, "section_id": s.get("id"), "depth": depth,
                        "title": s.get("title") or {}, "span": s.get("span")})
            walk(s.get("subsections") or [], toc_id, depth + 1)

    for t in tocs:
        walk(t.get("sections") or [], t.get("id"), 0)
    return out


# ---------------------------------------------------------------------------
# vocabulary
# ---------------------------------------------------------------------------

SUFFIXES = [("ies", "y"), ("ied", "y"), ("iest", "y"), ("ier", "y"), ("ily", "y"),
            ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("d", ""), ("es", ""),
            ("s", ""), ("ly", ""), ("er", ""), ("er", "e"), ("est", ""), ("ness", ""),
            ("ment", ""), ("ful", ""), ("less", ""), ("ity", ""), ("ous", "")]


class Vocab:
    def __init__(self, extra_allow=()):
        self.words = set()
        for p in DICT_PATHS:
            if os.path.exists(p):
                self.words = {w.strip().lower() for w in open(p, encoding="utf-8", errors="ignore")}
                break
        self.allow = set(w.lower() for w in extra_allow)
        if ALLOWLIST.exists():
            for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    self.allow.add(line.lower())

    @property
    def available(self):
        return bool(self.words)

    def known(self, w):
        w = w.lower()
        if w in self.words or w in self.allow or w in FUNC:
            return True
        for suf, rep in SUFFIXES:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                base = w[: -len(suf)] + rep
                if base in self.words or base in self.allow:
                    return True
                if len(base) > 2 and base[-1] == base[-2] and base[:-1] in self.words:
                    return True
        return False

    def part_ok(self, p, corpus):
        """A half of a split: a function word, or a real word this text uses on
        its own elsewhere (or a long one). Names and mantra syllables split into
        rare dictionary scraps ("She|chen", "pad|am") that fail this."""
        if len(p) < 2:
            return False  # single letters: camel_join covers "whomI"
        if p in FUNC:
            return True
        return len(p) >= 3 and self.known(p) and (corpus.get(p, 0) >= 1 or len(p) >= 5)

    def best_split(self, token, corpus):
        """(k, strong) for the best two-word split of an unknown token, or None."""
        lw = token.lower()
        if len(lw) < 5 or lw in self.allow or self.known(lw):
            return None
        best = None
        for k in range(2, len(lw) - 1):
            a, b = lw[:k], lw[k:]
            if not (self.part_ok(a, corpus) and self.part_ok(b, corpus)):
                continue
            strong = (a in FUNC and len(a) >= 2) or (b in FUNC and len(b) >= 2)
            score = (strong, min(len(a), len(b)))
            if best is None or score > best[0]:
                best = (score, k, strong)
        return None if best is None else (best[1], best[2])


# ---------------------------------------------------------------------------
# detection — one line at a time, offsets local to the line
# ---------------------------------------------------------------------------

TOKEN = re.compile(r"[^\W\d_]+")


def word_counts(texts):
    out = {}
    for t in texts:
        for w in TOKEN.findall(t):
            out[w.lower()] = out.get(w.lower(), 0) + 1
    return out


def dominant_dash_style(texts):
    closed = sum(len(re.findall(rf"\w{EM_DASH}\w", t)) for t in texts)
    spaced = sum(len(re.findall(rf"\w {EM_DASH} \w", t)) for t in texts)
    return "spaced" if spaced > closed else "closed"


def english_line(line, vocab):
    """True when most of the line's words are English — not a mantra or a
    transliterated name list, where word_join would only produce noise."""
    toks = [t for t in TOKEN.findall(line) if len(t) >= 2]
    return bool(toks) and sum(vocab.known(t) for t in toks) / len(toks) >= 0.6


def detect(line, vocab, dash_style, corpus):
    """Raw hits: [(category, confidence, op_local)] where op_local uses line offsets."""
    hits = []
    n = len(line)
    # a one-letter word run into a capitalised one: "OĀryā", "IPray"
    for m in re.finditer(r"(?<![^\W\d_])[OIA](?=[^\W\d_])", line):
        nxt = line[m.end():m.end() + 2]
        if len(nxt) == 2 and nxt[0].isupper() and nxt[1].islower():
            hits.append(("camel_join", "high", {"type": "insert", "position": m.end(), "text": " "}))
    for i in range(1, n):
        a, b = line[i - 1], line[i]
        # lower→Upper inside a word: "whomI", "toBuddha", "ĀryāTārā"
        if a.isalpha() and b.isalpha() and a.islower() and b.isupper():
            hits.append(("camel_join", "high", {"type": "insert", "position": i, "text": " "}))
        # , ; : ! ? straight into a letter: "wheels,fire"
        elif a in PUNCT_NEEDS_SPACE and b.isalpha():
            hits.append(("punct_no_space", "high", {"type": "insert", "position": i, "text": " "}))
        # sentence period straight into a capitalised word: "degeneration.By"
        elif a == "." and b.isupper() and i >= 3 and line[i - 2].islower() and line[i - 3].isalpha():
            hits.append(("punct_no_space", "high", {"type": "insert", "position": i, "text": " "}))
    for m in re.finditer(r"(?<=\S) {2,}(?=\S)", line):
        hits.append(("double_space", "high", {"type": "delete", "start": m.start() + 1, "end": m.end()}))
    for m in re.finditer(r"(?<=\S) +(?=[,;:.!?](?:\s|$))", line):
        hits.append(("space_before_punct", "high", {"type": "delete", "start": m.start(), "end": m.end()}))
    for m in re.finditer(r"^\s+|\s+$", line):
        if 0 < m.end() - m.start() < n:
            hits.append(("edge_space", "review", {"type": "delete", "start": m.start(), "end": m.end()}))
    for i, ch in enumerate(line):
        if ch in ODD_SPACE:
            hits.append(("odd_space", "review", {"type": "delete", "start": i, "end": i + 1}))
            if ch not in ("\u200b", "\ufeff"):  # a visible gap: becomes a plain space
                hits.append(("odd_space", "review", {"type": "insert", "position": i, "text": " "}))
    if dash_style == "closed":
        for m in re.finditer(rf"(?<=\w)( +){EM_DASH}(?=\w)|(?<=\w){EM_DASH}( +)(?=\w)|(?<=\w)( +){EM_DASH}$", line):
            g = next(k for k in (1, 2, 3) if m.group(k))
            hits.append(("dash_spacing", "review", {"type": "delete", "start": m.start(g), "end": m.end(g)}))
    if vocab.available and english_line(line, vocab):
        for m in TOKEN.finditer(line):
            tok = m.group()
            if any(c.isupper() for c in tok[1:]):
                continue  # camel_join owns these
            sp = vocab.best_split(tok, corpus)
            if sp:
                k, strong = sp
                before = line[:m.start()].rstrip()
                if not strong and tok[0].isupper() and before and before[-1] not in ".!?:;\"“‘—(":
                    continue  # capitalised mid-sentence with no function-word half: a proper name
                hits.append(("word_join", "high" if strong else "review",
                             {"type": "insert", "position": m.start() + k, "text": " "}))
    return hits


def group_hits(line, hits):
    """Merge hits that touch the same stretch of non-space text into one issue.

    Returns [(lo, hi, categories, confidence, ops)] with line-local offsets;
    `line[lo:hi]` is the text shown and matched as `original`.
    """
    spans = []
    for cat, conf, op in hits:
        p = op_pos(op)
        q = op["end"] if op["type"] == "delete" else p
        lo, hi = p, q
        while lo > 0 and not line[lo - 1].isspace():
            lo -= 1
        while hi < len(line) and not line[hi].isspace():
            hi += 1
        if op["type"] == "delete":  # include the words either side of the removed space
            while lo > 0 and line[lo - 1].isspace():
                lo -= 1
            while lo > 0 and not line[lo - 1].isspace():
                lo -= 1
            while hi < len(line) and not line[hi].isspace():
                hi += 1
        spans.append([lo, hi, {cat}, conf, [op]])
    spans.sort(key=lambda s: (s[0], s[1]))
    merged = []
    for s in spans:
        if merged and s[0] < merged[-1][1]:
            m = merged[-1]
            m[1] = max(m[1], s[1])
            m[2] |= s[2]
            m[3] = "high" if (m[3] == "high" and s[3] == "high") else "review"
            m[4] += s[4]
        else:
            merged.append(s)
    out = []
    for lo, hi, cats, conf, ops in merged:
        uniq = {json.dumps({k: v for k, v in o.items() if not k.startswith("_")}, sort_keys=True): o for o in ops}
        out.append((lo, hi, sorted(cats), conf, list(uniq.values())))
    return out


def apply_local_ops(text, ops, offset=0):
    for op in ordered_ops(ops):
        o = dict(op)
        if o["type"] == "insert":
            o["position"] -= offset
        else:
            o["start"] -= offset
            o["end"] -= offset
        text = apply_op_to_text(text, o)
    return text


def diff_ops(original, proposed, base):
    """Insert/delete ops (absolute offsets) that turn original into proposed."""
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, original, proposed, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            ops.append({"type": "insert", "position": base + i1, "text": proposed[j1:j2]})
        elif tag == "delete":
            ops.append({"type": "delete", "start": base + i1, "end": base + i2})
        else:  # replace -> delete, then insert at the same point (ordered_ops keeps that order)
            ops.append({"type": "delete", "start": base + i1, "end": base + i2})
            ops.append({"type": "insert", "position": base + i1, "text": proposed[j1:j2]})
    return ops


def ordered_ops(ops):
    """Highest position first; at one position the delete goes before the insert,
    so a replace lands as "remove, then put the new text where it was"."""
    return sorted(ops, key=lambda o: (op_pos(o), 1 if o["type"] == "delete" else 0), reverse=True)


# ---------------------------------------------------------------------------
# mapping file
# ---------------------------------------------------------------------------

def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frontmatter(note):
    t = note.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    out = {}
    if m:
        for line in m.group(1).split("\n"):
            k = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if k:
                out[k.group(1)] = k.group(2).strip()
    return out


def map_paths(note_stem):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR / f"{note_stem}.spacing-map.json", OUT_DIR / f"{note_stem}.spacing-map.md"


def load_map(path):
    p = pathlib.Path(path)
    if not p.exists():
        sys.exit(f"no mapping at {p}")
    return p, json.loads(p.read_text(encoding="utf-8"))


def save_map(path, m):
    path = pathlib.Path(path)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    write_report(path, m)


def splice(i):
    lo = i["line_offset"]
    return i["line_before"][:lo] + i["proposed"] + i["line_before"][lo + len(i["original"]):]


def issue_key(i):
    return (i.get("segment"), i.get("line"), i.get("original"), i.get("occurrence", 0))


def write_report(json_path, m):
    md = pathlib.Path(json_path).with_suffix(".md")
    issues = m["issues"]
    count = lambda f: sum(1 for i in issues if f(i))
    L = [
        f"# Spacing map — {m['note_stem']}",
        "",
        f"Edition `{m['edition_id']}` on {m['api_base']} · scanned {m['scanned_at']} · "
        f"{m['segments']} segments, {m['lines']} lines, {m['content_length']} chars.",
        "",
        f"**{len(issues)} issues** — approved {count(lambda i: i['decision'] == 'approved')}, "
        f"rejected {count(lambda i: i['decision'] == 'rejected')}, "
        f"pending {count(lambda i: i['decision'] == 'pending')} · "
        f"fixed {count(lambda i: i['status'] == 'fixed')}, open {count(lambda i: i['status'] == 'open')}"
        + (f", gone {count(lambda i: i['status'] == 'gone')}" if count(lambda i: i['status'] == 'gone') else ""),
        "",
        "The JSON beside this file is the source of truth; this table is regenerated from it.",
        "Fixes are sent bottom-up (highest position first).",
        "",
        "| ID | Segment | Line | Category | Conf. | Found | Proposed | Decision | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    esc = lambda s: s.replace("|", "\\|").replace("\u00a0", "⍽")
    for i in issues:
        L.append(f"| {i['id']} | `^{i['segment']}` | {i['line']} | {', '.join(i['categories'])} | {i['confidence']} "
                 f"| `{esc(i['original'])}` | `{esc(i['proposed'])}` | {i['decision']} | {i['status']}"
                 + (f" {i['fixed_at'][:19]}" if i.get("fixed_at") else "") + " |")
    L += ["", "## In context", ""]
    for i in issues:
        L.append(f"- **{i['id']}** `^{i['segment']}` line {i['line']}: {esc(i['line_before'])}  ")
        L.append(f"  → {esc(i['line_after'])}" + (f"  \n  _{i['comment']}_" if i.get("comment") else ""))
    if m.get("toc_issues"):
        L += ["", "## Table-of-contents titles (not reachable by the content PATCH)", "",
              "| ID | Section | Found | Proposed | Status |", "|---|---|---|---|---|"]
        for t in m["toc_issues"]:
            L.append(f"| {t['id']} | `{t['section_id']}` | `{esc(t['original'])}` | `{esc(t['proposed'])}` | {t['status']} |")
        L += ["", "_" + m["toc_issues"][0]["fix_path"] + "_"]
    if m.get("title_issues"):
        L += ["", "## Text title", ""]
        for t in m["title_issues"]:
            L.append(f"- {t['id']} `{esc(t['original'])}` → `{esc(t['proposed'])}` — {t['status']} ({t['fix_path']})")
    md.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_scan(a):
    note = pathlib.Path(a.note).resolve()
    fm = frontmatter(note)
    eid = fm.get("edition_id")
    if not eid:
        sys.exit(f"{note.name}: no edition_id in frontmatter — nothing published to scan")
    content = live_content(eid)
    segments = live_segments(eid)
    rows = live_lines(segments)
    vocab = Vocab()
    if not vocab.available:
        print("warning: no system word list found — word_join detection is off")
    texts = [content[s:e] for _, _, _, s, e in rows]
    dash_style = dominant_dash_style(texts)
    corpus = word_counts(texts)

    found = []
    for ref, sid, li, s, e in rows:
        line = content[s:e]
        for lo, hi, cats, conf, ops in group_hits(line, detect(line, vocab, dash_style, corpus)):
            original = line[lo:hi]
            proposed = apply_local_ops(original, ops, offset=lo)
            found.append({"occurrence": line[:lo].count(original),
                "segment": ref, "segment_id": sid, "line": li, "line_offset": lo,
                "start": s + lo, "end": s + hi, "original": original, "proposed": proposed,
                "categories": cats, "confidence": conf,
                "line_before": line, "line_after": line[:lo] + proposed + line[hi:],
            })

    tocs_now = live_toc(eid)
    toc_found = []
    for sec in toc_sections(tocs_now):
        for lang, title in (sec["title"] or {}).items():
            for lo, hi, cats, conf, ops in group_hits(title, detect(title, vocab, dash_style, corpus)):
                original = title[lo:hi]
                toc_found.append({
                    "toc_id": sec["toc_id"], "section_id": sec["section_id"], "lang": lang,
                    "original": original, "proposed": apply_local_ops(original, ops, offset=lo),
                    "categories": cats, "title_before": title,
                    "title_after": title[:lo] + apply_local_ops(original, ops, offset=lo) + title[hi:],
                    "status": "manual",
                    "fix_path": "The API has no PATCH for a TOC section: fixing a title means "
                                "DELETE /v2/table-of-contents/{toc_id} and re-POST the corrected TOC "
                                "(segments and alignments are untouched). Needs its own confirmation.",
                })
    title_found = []
    tid = fm.get("text_id")
    if tid:
        st, t = call("GET", f"/v2/texts/{tid}")
        if st == 200 and isinstance(t, dict):
            for lang, title in (t.get("title") or {}).items():
                for lo, hi, cats, conf, ops in group_hits(title, detect(title, vocab, dash_style, corpus)):
                    original = title[lo:hi]
                    title_found.append({"lang": lang, "original": original,
                                        "proposed": apply_local_ops(original, ops, offset=lo),
                                        "categories": cats, "status": "manual",
                                        "fix_path": f"PATCH /v2/texts/{tid}"})

    json_path, _ = map_paths(note.stem)
    old = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else None
    prev = {issue_key(i): i for i in (old or {}).get("issues", [])}
    next_n = 1 + max([int(i["id"][1:]) for i in (old or {}).get("issues", [])] or [0])
    scan_id = now()
    issues, seen = [], set()
    for f in found:
        k = issue_key(f)
        seen.add(k)
        p = prev.get(k)
        if p and p["status"] != "fixed":
            f.update(id=p["id"], decision=p["decision"], status="open",
                     comment=p.get("comment"), fixed_at=None, ops_sent=None)
            if p.get("proposed_override"):
                f["proposed"] = p["proposed_override"]
                f["proposed_override"] = p["proposed_override"]
                f["line_after"] = splice(f)
        else:
            f.update(id=f"S{next_n:03d}", decision="pending", status="open",
                     comment=None, fixed_at=None, ops_sent=None)
            next_n += 1
        issues.append(f)
    for k, p in prev.items():  # keep history: fixed stays fixed, vanished open ones are "gone"
        if k not in seen:
            p = dict(p)
            if p["status"] == "open":
                p["status"] = "gone"
            issues.append(p)
    issues.sort(key=lambda i: (i["status"] != "open", i.get("start", 0)))
    issues.sort(key=lambda i: int(i["id"][1:]))

    m = {
        "note": str(note.relative_to(VAULT)) if note.is_relative_to(VAULT) else str(note),
        "note_stem": note.stem,
        "edition_id": eid, "text_id": tid, "api_base": BASE,
        "scan_id": scan_id, "scanned_at": scan_id,
        "scan_content_sha256": sha(content), "content_length": len(content),
        "segments": len(segments), "lines": len(rows), "dash_style": dash_style,
        "issues": issues,
        "toc_at_scan": tocs_now,
        "toc_issues": [dict(t, id=f"T{n:03d}") for n, t in enumerate(toc_found, 1)],
        "title_issues": [dict(t, id=f"X{n:03d}") for n, t in enumerate(title_found, 1)],
        "history": (old or {}).get("history", []) + [{"at": scan_id, "action": "scan",
                                                      "open": sum(1 for i in issues if i["status"] == "open")}],
    }
    (OUT_DIR / f"{note.stem}.scan-content.json").write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    save_map(json_path, m)
    op = [i for i in issues if i["status"] == "open"]
    print(f"edition {eid}: {len(segments)} segments, {len(rows)} lines, {len(content)} chars")
    print(f"open issues: {len(op)}  (high {sum(i['confidence'] == 'high' for i in op)}, "
          f"review {sum(i['confidence'] == 'review' for i in op)})  · TOC titles: {len(toc_found)} · text title: {len(title_found)}")
    print(f"mapping: {json_path}\nreview : {json_path.with_suffix('.md')}")


def parse_ids(vals, issues):
    ids = set()
    for v in vals or []:
        for part in v.split(","):
            part = part.strip()
            if not part:
                continue
            if part == "all":
                ids |= {i["id"] for i in issues if i["status"] == "open"}
            elif part in ("high", "review"):
                ids |= {i["id"] for i in issues if i["status"] == "open" and i["confidence"] == part}
            else:
                ids.add(part)
    unknown = ids - {i["id"] for i in issues}
    if unknown:
        sys.exit(f"unknown issue ids: {sorted(unknown)}")
    return ids


def cmd_decide(a):
    path, m = load_map(a.map)
    by_id = {i["id"]: i for i in m["issues"]}
    for spec in a.set or []:
        iid, _, text = spec.partition("=")
        i = by_id.get(iid.strip())
        if not i:
            sys.exit(f"unknown issue id in --set: {iid}")
        i["proposed"] = i["proposed_override"] = text
        i["line_after"] = splice(i)
    for iid in parse_ids(a.approve, m["issues"]):
        by_id[iid]["decision"] = "approved"
    for iid in parse_ids(a.reject, m["issues"]):
        by_id[iid]["decision"] = "rejected"
    for spec in a.comment or []:
        iid, _, text = spec.partition("=")
        by_id[iid.strip()]["comment"] = text
    m["history"].append({"at": now(), "action": "decide", "approve": a.approve, "reject": a.reject, "set": a.set})
    save_map(path, m)
    c = lambda d: sum(1 for i in m["issues"] if i["decision"] == d)
    print(f"approved {c('approved')}, rejected {c('rejected')}, pending {c('pending')}")


def cmd_add(a):
    """Record an issue by hand — a user report, or a join the detector cannot
    split correctly (e.g. a lost letter: "godsowered" -> "gods cowered")."""
    path, m = load_map(a.map)
    scan = json.loads((OUT_DIR / f"{m['note_stem']}.scan-content.json").read_text(encoding="utf-8"))
    rows = live_lines(live_segments(m["edition_id"]))
    row = next((r for r in rows if r[0] == a.segment and r[2] == a.line), None)
    if not row:
        sys.exit(f"no line {a.line} in segment ^{a.segment}")
    _, sid, li, s, e = row
    line = scan[s:e]
    if line.count(a.original) != 1:
        sys.exit(f"{a.original!r} occurs {line.count(a.original)} times in ^{a.segment}[{a.line}]: {line!r}")
    lo = line.index(a.original)
    next_n = 1 + max([int(i["id"][1:]) for i in m["issues"]] or [0])
    issue = {"occurrence": 0, "segment": a.segment, "segment_id": sid, "line": li, "line_offset": lo,
             "start": s + lo, "end": s + lo + len(a.original), "original": a.original,
             "proposed": a.proposed, "proposed_override": a.proposed, "categories": ["manual"],
             "confidence": "review", "line_before": line, "id": f"S{next_n:03d}",
             "decision": "pending", "status": "open", "comment": a.comment, "fixed_at": None, "ops_sent": None}
    issue["line_after"] = splice(issue)
    m["issues"].append(issue)
    m["issues"].sort(key=lambda i: int(i["id"][1:]))
    m["history"].append({"at": now(), "action": "add", "id": issue["id"]})
    save_map(path, m)
    print(f"added {issue['id']}: ^{a.segment}[{a.line}] {a.original!r} -> {a.proposed!r}")


def plan_ops(m, live):
    """Pending approved ops, validated against the live content, highest first."""
    scan = json.loads((OUT_DIR / f"{m['note_stem']}.scan-content.json").read_text(encoding="utf-8"))
    if sha(scan) != m["scan_content_sha256"]:
        sys.exit("ABORT: the saved scan content does not match the mapping — re-run scan")
    applied = [i for i in m["issues"] if i["status"] == "fixed" and i.get("fixed_in_scan") == m["scan_id"]]
    pending = [i for i in m["issues"] if i["status"] == "open" and i["decision"] == "approved"]
    expected_live = scan
    for i in sorted(applied, key=lambda i: i["fixed_seq"]):
        for op in i["ops_sent"]:
            expected_live = apply_op_to_text(expected_live, op)
    if live != expected_live:
        sys.exit("ABORT: the live content has changed since the scan (and not only by this mapping's "
                 "own fixes). Re-run scan to refresh offsets, then decide/apply again.")
    if applied and pending:
        lowest_applied = min(op_pos(op) for i in applied for op in i["ops_sent"])
        if max(i["end"] for i in pending) > lowest_applied:
            sys.exit("ABORT: some approved issues sit above positions already patched in this scan; "
                     "re-run scan to refresh offsets first.")
    for i in pending:
        if scan[i["start"]:i["end"]] != i["original"]:
            sys.exit(f"ABORT {i['id']}: live text at {i['start']}:{i['end']} is "
                     f"{scan[i['start']:i['end']]!r}, mapping says {i['original']!r}")
        i["_ops"] = diff_ops(i["original"], i["proposed"], i["start"])
        if not i["_ops"]:
            sys.exit(f"ABORT {i['id']}: proposed equals original")
    return pending


def simulate(live, rows, toc_spans, pending):
    """Replay the backend over the live spans; prove every line and TOC boundary."""
    line_spans = [(s, e) for _, _, _, s, e in rows]
    labels = [f"^{r}[{li}]" for r, _, li, _, _ in rows]
    # every op must sit strictly inside one line (insert) or within one line (delete)
    for i in pending:
        for op in i["_ops"]:
            p = op_pos(op)
            idx = next((k for k, (s, e) in enumerate(line_spans) if s <= p < e or (op["type"] == "insert" and s < p <= e)), None)
            if idx is None:
                sys.exit(f"ABORT {i['id']}: op at {p} is not inside any line span")
            s, e = line_spans[idx]
            if op["type"] == "insert" and not (s < p < e):
                sys.exit(f"ABORT {i['id']}: insert at {p} is on a line boundary ({labels[idx]} {s}:{e}); "
                         f"the backend would attach it to the wrong line")
            if op["type"] == "delete" and not (s <= op["start"] and op["end"] <= e and (op["end"] - op["start"]) < (e - s)):
                sys.exit(f"ABORT {i['id']}: delete {op['start']}:{op['end']} crosses or empties {labels[idx]}")
            op["_line"] = idx
    # expected text per line, built line-locally
    expected = [live[s:e] for s, e in line_spans]
    per_line = {}
    for i in pending:
        for op in i["_ops"]:
            per_line.setdefault(op["_line"], []).append(op)
    for idx, ops in per_line.items():
        s = line_spans[idx][0]
        t = expected[idx]
        for op in ordered_ops(ops):
            o = {k: v for k, v in op.items() if not k.startswith("_")}
            if o["type"] == "insert":
                o["position"] -= s
            else:
                o["start"] -= s
                o["end"] -= s
            t = apply_op_to_text(t, o)
        expected[idx] = t
    # replay
    all_ops = ordered_ops([op for i in pending for op in i["_ops"]])
    sim, spans, tspans = live, list(line_spans), list(toc_spans)
    for op in all_ops:
        o = {k: v for k, v in op.items() if not k.startswith("_")}
        spans = apply_op_to_spans(spans, o, continuous=True)
        tspans = apply_op_to_spans(tspans, o, continuous=False)
        sim = apply_op_to_text(sim, o)
    dropped = [labels[k] for k, s in enumerate(spans) if s is None]
    if dropped:
        sys.exit(f"ABORT: the backend would drop spans {dropped[:5]}")
    bad = [(labels[k], sim[s[0]:s[1]], expected[k]) for k, s in enumerate(spans) if sim[s[0]:s[1]] != expected[k]]
    if bad:
        for lbl, got, want in bad[:10]:
            print(f"    {lbl}: would select {got!r}, expected {want!r}")
        sys.exit(f"ABORT: {len(bad)} lines would not select their expected text")
    cov = sorted(spans)
    if cov[0][0] != 0 or cov[-1][1] != len(sim) or any(cov[k][1] != cov[k + 1][0] for k in range(len(cov) - 1)):
        sys.exit("ABORT: after replay the line spans no longer tile the content")
    bounds = {0, len(sim)} | {x for s in spans for x in s}
    tbad = [t for t in tspans if t is None or t[0] not in bounds or t[1] not in bounds]
    if tbad:
        sys.exit(f"ABORT: {len(tbad)} TOC section spans would stop landing on line boundaries")
    return all_ops, sim, spans


def cmd_apply(a):
    path, m = load_map(a.map)
    eid = m["edition_id"]
    live = live_content(eid)
    rows = live_lines(live_segments(eid))
    tspans = [(s["span"]["start"], s["span"]["end"]) for s in toc_sections(live_toc(eid)) if s.get("span")]
    pending = plan_ops(m, live)
    if not pending:
        print("nothing approved and open — nothing to send.")
        return
    all_ops, sim, spans = simulate(live, rows, tspans, pending)
    pending.sort(key=lambda i: i["start"], reverse=True)  # bottom-up
    print(f"== edition {eid} on {BASE} ==")
    print(f"  approved open issues : {len(pending)}  -> {len(all_ops)} PATCH calls, bottom-up "
          f"({op_pos(all_ops[0])} down to {op_pos(all_ops[-1])})")
    print(f"  content              : {len(live)} -> {len(sim)} chars ({len(sim) - len(live):+d})")
    print(f"  checks               : all {len(spans)} line spans replay onto their expected text ✓  "
          f"no span dropped ✓  TOC boundaries hold ✓")
    for i in pending:
        print(f"    {i['id']:5} ^{i['segment']}[{i['line']}]  {i['original']!r} -> {i['proposed']!r}")
    if not a.execute:
        print("\ndry run: nothing sent. Re-run with --execute after the human confirms.")
        return
    if not os.environ.get("WEBUDDHIST_API_KEY"):
        sys.exit("WEBUDDHIST_API_KEY is not set")
    print("\n== EXECUTE ==")
    seq = 1 + max([i.get("fixed_seq", 0) for i in m["issues"]] or [0])
    by_id = {i["id"]: i for i in m["issues"]}
    for i in pending:
        sent = []
        for op in ordered_ops(i["_ops"]):
            body = {k: v for k, v in op.items() if not k.startswith("_")}
            st, d = call("PATCH", f"/v2/editions/{eid}/content", body)
            if st not in (200, 204):
                if sent:  # a partly applied issue: record what landed, so the map stays truthful
                    by_id[i["id"]].update(status="partial", ops_sent=sent)
                    save_map(path, m)
                sys.exit(f"\n{i['id']} op {body} -> {st} {d}\nStopped. Everything above this issue is "
                         f"applied and recorded in the mapping; re-running apply resumes.")
            sent.append(body)
        rec = by_id[i["id"]]
        rec.update(status="fixed", fixed_at=now(), ops_sent=sent, fixed_in_scan=m["scan_id"], fixed_seq=seq)
        rec.pop("_ops", None)
        seq += 1
        save_map(path, m)  # after every issue, so an interruption leaves an honest record
        print(f"  fixed {i['id']:5} ^{i['segment']}[{i['line']}]  {i['original']!r} -> {i['proposed']!r}")
    for i in m["issues"]:
        i.pop("_ops", None)
    after = live_content(eid)
    after_rows = live_lines(live_segments(eid))
    ok_c, ok_s = after == sim, [(s, e) for *_, s, e in after_rows] == sorted(spans)
    m["history"].append({"at": now(), "action": "apply", "fixed": [i["id"] for i in pending],
                         "content_matches_prediction": ok_c, "spans_match_prediction": ok_s})
    save_map(path, m)
    print(f"\n  after: {len(after)} chars, {len(after_rows)} line spans")
    print(f"  content equals the prediction: {ok_c}")
    print(f"  spans equal the prediction   : {ok_s}")


def cmd_verify(a):
    path, m = load_map(a.map)
    eid = m["edition_id"]
    live = live_content(eid)
    segs = live_segments(eid)
    rows = live_lines(segs)
    by_line = {(r, li): live[s:e] for r, _, li, s, e in rows}
    fixed = [i for i in m["issues"] if i["status"] == "fixed"]
    bad = [i for i in fixed if by_line.get((i["segment"], i["line"])) != i["line_after"]
           and i["proposed"] not in (by_line.get((i["segment"], i["line"])) or "")]
    print(f"edition {eid}: {len(segs)} segments (mapping scanned {m['segments']}), "
          f"{len(rows)} lines (scanned {m['lines']}), {len(live)} chars")
    print(f"fixed issues confirmed live: {len(fixed) - len(bad)}/{len(fixed)}")
    for i in bad:
        print(f"  NOT LIVE {i['id']} ^{i['segment']}[{i['line']}]: {by_line.get((i['segment'], i['line']))!r}")
    vocab = Vocab()
    dash_style = m.get("dash_style", "closed")
    corpus = word_counts([live[s:e] for *_, s, e in rows])
    remaining = sum(len(group_hits(live[s:e], detect(live[s:e], vocab, dash_style, corpus))) for *_, s, e in rows)
    rejected = sum(1 for i in m["issues"] if i["decision"] == "rejected")
    print(f"detector hits still in the live edition: {remaining} (rejected in the mapping: {rejected})")
    m["history"].append({"at": now(), "action": "verify", "confirmed": len(fixed) - len(bad), "missing": [i["id"] for i in bad]})
    save_map(path, m)


def cmd_note(a):
    path, m = load_map(a.map)
    target = pathlib.Path(a.file) if a.file else VAULT / m["note"]
    text = target.read_text(encoding="utf-8")
    lines = text.split("\n")
    todo = [i for i in m["issues"] if i["status"] == "fixed" or (a.include_approved and i["decision"] == "approved")]
    done, manual, seen_lines = [], [], set()
    for i in todo:
        end_idx = next((k for k, ln in enumerate(lines) if re.search(rf"\s\^{re.escape(i['segment'])}\s*$", ln)), None)
        if end_idx is None:
            # A copy without block ids (e.g. a trilingual layout): match the whole
            # live line, only where it occurs exactly once in the file, and apply
            # every issue on that line together (right to left) in one replace.
            key = (i["segment"], i["line"])
            if key in seen_lines:
                continue
            seen_lines.add(key)
            group = sorted((j for j in todo if (j["segment"], j["line"]) == key),
                           key=lambda j: j["line_offset"], reverse=True)
            fixed_line = i["line_before"]
            for j in group:
                lo = j["line_offset"]
                fixed_line = fixed_line[:lo] + j["proposed"] + fixed_line[lo + len(j["original"]):]
            hits = [k for k, ln in enumerate(lines) if i["line_before"] in ln]
            if len(hits) == 1 and lines[hits[0]].count(i["line_before"]) == 1:
                lines[hits[0]] = lines[hits[0]].replace(i["line_before"], fixed_line, 1)
                done += group
            elif not hits and any(fixed_line in ln for ln in lines):
                continue  # already fixed in this file
            else:
                manual += [(j, f"no block id; whole line found {len(hits)} times") for j in group]
            continue
        start_idx = end_idx
        while start_idx > 0 and lines[start_idx - 1].strip() and not lines[start_idx - 1].startswith("![["):
            start_idx -= 1
        block = list(range(start_idx, end_idx + 1))
        cand = [k for k in block if i["original"] in lines[k]]
        pref = block[i["line"]] if i["line"] < len(block) else None
        if pref is not None and lines[pref].count(i["original"]) == 1:
            k = pref
        elif len(cand) == 1 and lines[cand[0]].count(i["original"]) == 1:
            k = cand[0]
        elif any(i["proposed"] in lines[k] for k in block):
            continue  # already fixed in this file
        else:
            manual.append((i, f"{len(cand)} candidate lines"))
            continue
        lines[k] = lines[k].replace(i["original"], i["proposed"], 1)
        done.append(i)
    # fixed TOC titles: the headings they were built from carry the same error
    for t in (x for x in m.get("toc_issues", []) if x["status"] == "fixed"):
        hits = [k for k, ln in enumerate(lines) if t["title_before"] in ln]
        if len(hits) == 1 and lines[hits[0]].count(t["original"]) == 1:
            lines[hits[0]] = lines[hits[0]].replace(t["original"], t["proposed"], 1)
            done.append(t)
        elif not hits and any(t["title_after"] in ln for ln in lines):
            continue  # already fixed in this file
        else:
            manual.append((t, f"title line found {len(hits)} times"))
    new = "\n".join(lines)
    diff = list(difflib.unified_diff(text.split("\n"), lines, lineterm="", n=0,
                                     fromfile=str(target.name), tofile=str(target.name)))
    print("\n".join(diff) if diff else "(no changes)")
    print(f"\n{len(done)} applied, {len(manual)} need a hand" + "".join(f"\n  {i['id']}: {why}" for i, why in manual))
    if a.write and diff:
        target.write_text(new, encoding="utf-8")
        for i in done:
            i.setdefault("note_fixed", []).append(str(target.relative_to(VAULT)) if target.is_relative_to(VAULT) else str(target))
        m["history"].append({"at": now(), "action": "note", "file": str(target.name), "ids": [i["id"] for i in done]})
        save_map(path, m)
        print(f"written: {target}")
    elif diff:
        print("\ndry run: file not written. Re-run with --write after the human confirms.")


def patch_frontmatter_id(path, key, old, new):
    t = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    if not m or f"\n{key}: {old}\n" not in f"\n{m.group(1)}\n":
        return False
    head = f"\n{m.group(1)}\n".replace(f"\n{key}: {old}\n", f"\n{key}: {new}\n", 1)[1:-1]
    path.write_text(f"---\n{head}\n---\n" + t[m.end():], encoding="utf-8")
    return True


def cmd_toc(a):
    """Rebuild a TOC whose titles need fixing: the content PATCH cannot reach a
    section title and the API has no TOC PATCH, so the TOC is re-posted.

    Spans are recalculated, not copied blindly: the TOC as it stood at scan time
    is replayed through every op this mapping sent (the backend's annotation
    arithmetic), and the result must equal the spans the backend holds now and
    land every boundary on a segment boundary. Titles change only where an
    approved T-issue says so. Dry run by default; --execute backs the live TOC
    up, DELETEs it, POSTs the rebuilt one, and records the new id.
    """
    path, m = load_map(a.map)
    eid = m["edition_id"]
    by_id = {t["id"]: t for t in m.get("toc_issues", [])}
    fix = set()
    for v in a.fix or []:
        fix |= {x.strip() for x in v.split(",") if x.strip()}
    if not fix or fix - set(by_id):
        sys.exit(f"--fix needs toc issue ids from the mapping: {sorted(by_id)}")
    tid = {by_id[x]["toc_id"] for x in fix}
    if len(tid) != 1:
        sys.exit("the chosen issues belong to more than one TOC — one TOC per run")
    tid = tid.pop()
    live = next((t for t in live_toc(eid) if t.get("id") == tid), None)
    if live is None:
        sys.exit(f"TOC {tid} is not on edition {eid} any more (already replaced?) — re-run scan")

    snap_all = json.loads(pathlib.Path(a.snapshot).read_text(encoding="utf-8")) if a.snapshot else m.get("toc_at_scan")
    snap = next((t for t in (snap_all or []) if t.get("id") == tid), None)
    if snap is None:
        sys.exit("no TOC snapshot from scan time in the mapping; pass --snapshot <the TOC JSON as it was then>")
    root_end = max(sec["span"]["end"] for sec in toc_sections([snap]) if sec.get("span"))
    if root_end > m["content_length"]:
        sys.exit("ABORT: the snapshot's spans run past the scanned content — wrong snapshot")

    flat_live, flat_snap = toc_sections([live]), toc_sections([snap])
    if [(x["section_id"], x["depth"]) for x in flat_live] != [(x["section_id"], x["depth"]) for x in flat_snap]:
        sys.exit("ABORT: the live TOC's structure differs from the snapshot's")
    sent = [op for i in sorted((i for i in m["issues"] if i["status"] == "fixed" and i.get("fixed_in_scan") == m["scan_id"]),
                               key=lambda i: i["fixed_seq"]) for op in i["ops_sent"]]
    spans = [(x["span"]["start"], x["span"]["end"]) for x in flat_snap]
    for op in sent:
        spans = apply_op_to_spans(spans, op, continuous=False)
    live_spans = [(x["span"]["start"], x["span"]["end"]) for x in flat_live]
    rows = live_lines(live_segments(eid))
    content_len = len(live_content(eid))
    seg_first, seg_last = {}, {}
    for ref, sid, li, s0, e0 in rows:
        seg_first.setdefault(sid, s0)
        seg_last[sid] = e0
    starts, ends = set(seg_first.values()), set(seg_last.values())
    problems = []
    for x, r, l in zip(flat_live, spans, live_spans):
        if r != l:
            problems.append(f"{x['section_id']}: replayed {r} != backend {l}")
        if r is None or r[0] not in starts or r[1] not in ends:
            problems.append(f"{x['section_id']}: {r} is not on segment boundaries")
    if any(r[1] > content_len for r in spans if r):
        problems.append("a span runs past the end of the content")
    if problems:
        sys.exit("ABORT: recalculated spans disagree:\n  " + "\n  ".join(problems[:10]))
    recalculated = {x["section_id"]: r for x, r in zip(flat_live, spans)}

    changes = []

    def rebuild(sec):
        title = dict(sec.get("title") or {})
        for iid in sorted(fix):
            t = by_id[iid]
            if t["section_id"] == sec.get("id"):
                cur = title.get(t["lang"], "")
                if cur.count(t["original"]) != 1:
                    sys.exit(f"ABORT {iid}: {t['original']!r} occurs {cur.count(t['original'])} times in {cur!r}")
                title[t["lang"]] = cur.replace(t["original"], t["proposed"], 1)
                changes.append((iid, cur, title[t["lang"]]))
        st, en = recalculated[sec["id"]]
        out = {"title": title, "span": {"start": st, "end": en}}
        if sec.get("summary"):
            out["summary"] = sec["summary"]
        subs = [rebuild(x) for x in sec.get("subsections") or []]
        if subs:
            out["subsections"] = subs
        return out

    payload = {"sections": [rebuild(x) for x in live["sections"]]}
    if live.get("metadata"):
        payload["metadata"] = live["metadata"]
    if len(changes) != len(fix):
        sys.exit("ABORT: not every chosen issue found its section")
    stamp = now().replace(":", "")[:17]
    backup = OUT_DIR / f"{m['note_stem']}.toc-{tid}.backup-{stamp}.json"
    newfile = OUT_DIR / f"{m['note_stem']}.toc-{tid}.rebuilt-{stamp}.json"
    print(f"== TOC {tid} on edition {eid} ({BASE}) ==")
    print(f"  sections      : {len(flat_live)} (structure unchanged)")
    print(f"  spans         : recalculated through {len(sent)} sent ops; equal to the backend's ✓  "
          f"on segment boundaries ✓  root 0..{content_len}")
    for iid, before, after in changes:
        print(f"  title {iid}  : {before!r}\n               -> {after!r}")
    if not a.execute:
        print("\ndry run: nothing sent. --execute backs up, DELETEs and re-POSTs this TOC.")
        return
    backup.write_text(json.dumps(live, ensure_ascii=False, indent=2), encoding="utf-8")
    newfile.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  backup : {backup}\n  payload: {newfile}")
    st, d = call("DELETE", f"/v2/table-of-contents/{tid}")
    if st not in (200, 204):
        sys.exit(f"DELETE -> {st} {d}\nNothing changed.")
    print(f"  DELETE {tid} -> {st}")
    st, d = call("POST", f"/v2/editions/{eid}/table-of-contents", payload)
    if st not in (200, 201):
        print(f"  POST -> {st} {d}")
        restore = {"sections": [rebuild_plain(x, recalculated) for x in live["sections"]]}
        st2, d2 = call("POST", f"/v2/editions/{eid}/table-of-contents", restore)
        sys.exit(f"POST of the fixed TOC failed; restore POST of the original titles -> {st2} {d2}\n"
                 f"backup: {backup}")
    new_id = d.get("id") if isinstance(d, dict) else d
    print(f"  POST -> {st}, new toc_id {new_id}")
    got = next((t for t in live_toc(eid) if t.get("id") == new_id), None)
    ok = got is not None and [(x["title"], x["span"]) for x in toc_sections([got])] == \
        [(x["title"], x["span"]) for x in toc_sections([{"sections": payload["sections"]}])]
    print(f"  read back equals the payload: {ok}")
    for iid in fix:
        by_id[iid].update(status="fixed", fixed_at=now(), old_toc_id=tid, new_toc_id=new_id)
    m["toc_id"] = new_id
    m["history"].append({"at": now(), "action": "toc", "fixed": sorted(fix), "old_toc_id": tid,
                         "new_toc_id": new_id, "read_back_ok": ok, "backup": backup.name})
    save_map(path, m)
    for f in [VAULT / m["note"]] + [pathlib.Path(x) for x in (a.also or [])]:
        if patch_frontmatter_id(f, "toc_id", tid, new_id):
            print(f"  PATCHED {f.name}: toc_id = {new_id}")
    for ledger in list(VAULT.glob("3-SKILLS/*/scripts/upload_ledger.json")) + list(VAULT.glob("4-SYSTEM/Skills/*/scripts/upload_ledger.json")):
        led = json.loads(ledger.read_text(encoding="utf-8"))
        ent = led.get(m["note_stem"])
        if isinstance(ent, dict) and ent.get("toc_id") == tid:
            ent["toc_id"] = new_id
            ent.setdefault("log", []).append({"step": "toc-replace", "old_toc_id": tid, "toc_id": new_id,
                                              "reason": f"edition-spacing-fix {', '.join(sorted(fix))}",
                                              "ts": datetime.datetime.now().isoformat(timespec="seconds")})
            ledger.write_text(json.dumps(led, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"  ledger {ledger.relative_to(VAULT)}: toc_id = {new_id}")


def rebuild_plain(sec, recalculated):
    st, en = recalculated[sec["id"]]
    out = {"title": sec["title"], "span": {"start": st, "end": en}}
    subs = [rebuild_plain(x, recalculated) for x in sec.get("subsections") or []]
    if subs:
        out["subsections"] = subs
    return out


def cmd_report(a):
    path, m = load_map(a.map)
    write_report(path, m)
    print(path.with_suffix(".md"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan"); p.add_argument("note"); p.set_defaults(f=cmd_scan)
    p = sub.add_parser("decide"); p.add_argument("map")
    p.add_argument("--approve", nargs="*", help="ids, comma lists, 'all', 'high' or 'review'")
    p.add_argument("--reject", nargs="*")
    p.add_argument("--set", nargs="*", help="ID=replacement text for the whole `original` snippet")
    p.add_argument("--comment", nargs="*", help="ID=free text")
    p.set_defaults(f=cmd_decide)
    p = sub.add_parser("add"); p.add_argument("map")
    p.add_argument("--segment", required=True); p.add_argument("--line", type=int, required=True)
    p.add_argument("--original", required=True); p.add_argument("--proposed", required=True)
    p.add_argument("--comment"); p.set_defaults(f=cmd_add)
    p = sub.add_parser("apply"); p.add_argument("map"); p.add_argument("--execute", action="store_true")
    p.set_defaults(f=cmd_apply)
    p = sub.add_parser("verify"); p.add_argument("map"); p.set_defaults(f=cmd_verify)
    p = sub.add_parser("note"); p.add_argument("map"); p.add_argument("--file")
    p.add_argument("--include-approved", action="store_true"); p.add_argument("--write", action="store_true")
    p.set_defaults(f=cmd_note)
    p = sub.add_parser("toc"); p.add_argument("map"); p.add_argument("--fix", nargs="+", required=True)
    p.add_argument("--snapshot", help="the TOC JSON as it was at scan time, if the mapping lacks one")
    p.add_argument("--also", nargs="*", help="other vault copies whose toc_id should follow")
    p.add_argument("--execute", action="store_true"); p.set_defaults(f=cmd_toc)
    p = sub.add_parser("report"); p.add_argument("map"); p.set_defaults(f=cmd_report)
    a = ap.parse_args()
    try:
        a.f(a)
    except ApiError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
