"""toc_tree_line.py — parse one node line of a toc-tree-*.md file.

Vendored verbatim from the retired toc-generate skill
(deprecated/toc-generate/scripts/toc_tree_ingest.py, parse_toc_line and its
helpers), so this skill does not depend on a deprecated sibling being installed.
The rails/seg-toc-lib parser of the same name reads a different line format
(a [[context]] quote, not a [[row]] pointer) and is not a drop-in replacement.
"""

import re



def decimal_to_block_id(decimal_id: str) -> str:
    """'1.3.2.2' -> '^1-3-2-2-0'"""
    segments = decimal_id.rstrip(".").split(".")
    return "^" + "-".join(segments) + "-0"


_TREE_LINE_RE = re.compile(
    r"^(?P<indent>[ \t]*)\*[ \t]+(?P<dec>\d+(?:\.\d+)*)\.?[ \t]+"
    r"(?P<label>.*?)(?:[ \t]*\[\[(?P<pointer>\d+|\?)\]\])?[ \t]*$"
)


def parse_toc_line(line: str):
    """
    Parse one line of the toc-tree-*.md file.

    Expected format (any leading whitespace) — the same format
    qc_tree_vs_source.py validates:
        * N.N.N Tibetan label [[123]]
        * N.N.N Tibetan label [[?]]

    Returns a dict or None if the line is not a node line.
    """
    if not line.lstrip().startswith("* "):
        return None

    m = _TREE_LINE_RE.match(line.rstrip("\n"))
    if not m:
        return None

    raw_id = m.group("dec")
    label = m.group("label").strip()
    pointer_raw = m.group("pointer")
    pointer = None if pointer_raw in (None, "?") else int(pointer_raw)
    depth = raw_id.count(".") + 1

    return {
        "decimal_id": raw_id,
        "depth": depth,
        "label": label,
        "block_id": decimal_to_block_id(raw_id),
        "pointer": pointer,
    }


