"""Shared helpers for keyword-standardize (stdlib only)."""
import json, re
from pathlib import Path

SOURCE_LABELS = {
    "classical":  "classical canon (CBETA)",
    "standard":   "standard Buddhist term",
    "mt":         "machine draft",
    "recitation": "modern mantra recitation",
    "attested":   "attested human translation",
    "related":    "related-language word list",
    "kept":       "kept as in the English",
    "new":        "new (no source had it)",
}
TRUST = ["attested", "classical", "related", "standard", "recitation", "kept", "mt", "new"]
_ID = re.compile(r"(?<!\S)\^([\w][\w\-]*)\s*$")


def blocks(path, prefix=""):
    """{block_id: text} for a block-ID'd markdown file. Skips frontmatter and
    transclusion lines; strips `prefix` from IDs (reference files use ^zhc-1-1)."""
    if not path:
        return {}
    t = Path(path).read_text(encoding="utf-8")
    if t.startswith("---"):
        parts = t.split("\n---\n", 1)
        t = parts[1] if len(parts) == 2 else t
    out = {}
    for b in re.split(r"\n\s*\n", t):
        lines = [l for l in b.strip().splitlines() if not l.lstrip().startswith("![[")]
        b = "\n".join(lines).strip()
        m = _ID.search(b)
        if not m:
            continue
        vid = m.group(1)
        if prefix and vid.startswith(prefix):
            vid = vid[len(prefix):]
        out[vid] = b[: m.start()].strip()
    return out


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def forms(bo):
    return [f.strip() for f in (bo or "").split("/") if f.strip()]


def clean_bo(s):
    return re.sub(r"[\s།༄༅༎༑]+", "", s or "")


def source_label(codes, overrides=None):
    """Display string for source codes, most trusted first. `overrides` (the
    decisions file's _meta.source_labels) names them for one text, e.g.
    {"classical": "classical canon (CBETA T1108)", "mt": "DharmaMitra zh draft"}."""
    labels = {**SOURCE_LABELS, **(overrides or {})}
    if isinstance(codes, str):
        codes = [codes]
    bad = [c for c in codes if c not in SOURCE_LABELS]
    if bad:
        raise SystemExit(f"unknown source code(s) {bad}; use {sorted(SOURCE_LABELS)}")
    codes = sorted(codes, key=TRUST.index)
    return " + ".join(labels[c] for c in codes)
