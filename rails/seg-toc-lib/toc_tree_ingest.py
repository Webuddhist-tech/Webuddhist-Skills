#!/usr/bin/env python3
"""
toc_tree_ingest.py -- TOC Tree Ingestion Tool

Two modes:

  parse   Parse a toc-tree-*.md file into a JSON node list.

          python3 toc_tree_ingest.py parse \
              --input  0-INBOX/temp/TOC-X/toc-tree-X.md \
              --out    /tmp/toc-tree-X.json

  ingest  Insert ALL headings into the commentary in a single pass, in
          document order.

          python3 toc_tree_ingest.py ingest \
              --tree        /tmp/toc-tree-X.json \
              --commentary  1-SOURCES/Commentaries/commentaries_with_toc/X.toc.md \
              [--stamp-body-ids] [--title-style shad|raw] [--no-split-mid-block]

Tree lines
  * 2.1.3 title [[context]]       sa bcad node (decimal path)
  * I. མཆོད་བརྗོད། [[context]]     editorial frame node: front matter I, II, … and
  * a. བསྔོ་བ། [[context]]          back matter a, b, … (with children b.1, …),
  * b.1 མཛད་བྱང། [[context]]        IDs ^I-0, ^a-0, ^b-1-0 (annotation-conventions)

Placement (the convention of the human-edited vault files)
  The commentary is read as BLOCKS (paragraphs separated by a blank line). Each
  node's [[context]] is located in document order (canonical match: whitespace and
  shads ignored, so a context copied as "པའོ།།" still finds "པའོ། །"), and the
  heading is inserted at the START OF THE BLOCK that contains it. This is what
  stacks a parent's heading and its first child's heading on top of each other:
  the first child's opener "དང་པོ་ནི།" sits in the same block as the parent's
  division announcement, so both headings land before that block.
  When the context of a node that is NOT a first child (last segment ≠ 1) falls in
  the middle of a block, that block is split at the context (a new node always
  starts a new block); --no-split-mid-block reports it instead.

  reorder Put each parent's children in the order the TEXT treats them (when the tree
          follows the commentary's announcement but the explanation goes B, D, C, A),
          write the JSON (and --out-md the dkar chag). Titles unchanged; IDs keep the
          announced order (--renumber-reordered: renumber in text order). `ingest` does
          this by default before placing; --keep-tree-order turns it off.

Headings
  depth 1 → ##, each level adds one #; deeper than ###### keeps ###### and wraps
  the title in **bold** (annotation-conventions §2). --title-style shad (default)
  ends a title with "།" the way the vault writes headings ("…བསྟན་པ།").

Body IDs (--stamp-body-ids)
  Derived counters off the top-level labels, as annotation-conventions §3
  describes: every content block under "## … ^2-0" gets ^2-1, ^2-2, … (the counter
  runs through the whole top-level section, sub-headings included); front/back
  matter use their own label (^I-1, ^a-1, ^b-1); the "#" title gets ^0;
  transclusion lines never take an ID. The ## labels themselves are a human
  decision in a commentary — review them before stamping.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ANCHOR_LENGTH = 60       # chars from context used as primary anchor
CONTEXT_MAX = 200        # chars stored in JSON context field
FRONTMATTER_RE = re.compile(r"^---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n", re.DOTALL)
ID_RE = re.compile(r"\s*\^([A-Za-z0-9][A-Za-z0-9-]*)\s*$")
NODE_ID_RE = re.compile(r"(?:\d+|[IVX]+|[a-z])(?:\.\d+)*")
CANON_DROP = re.compile(r"[\s།༎༑༔]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def canon_map(s: str):
    """Canonical form (whitespace + shads removed) and, for each canonical char,
    its index in `s`."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if CANON_DROP.match(ch):
            continue
        out.append(ch)
        idx.append(i)
    return "".join(out), idx


def canon(s: str) -> str:
    return CANON_DROP.sub("", s)


def decimal_to_block_id(decimal_id: str) -> str:
    """'1.3.2.2' -> '^1-3-2-2-0';  'b.1' -> '^b-1-0';  'I' -> '^I-0'"""
    return "^" + "-".join(decimal_id.rstrip(".").split(".")) + "-0"


def format_title(label: str, style: str) -> str:
    t = label.strip()
    if style == "shad":
        t = t.rstrip("་").rstrip()
        if not re.search(r"[།༎]$", t):
            # after ཀ / ག the shad is written with a space before it ("…ག །" is
            # the verse form; a heading just takes the bare shad)
            t = t + "།"
    return t


def heading_line(node: dict, style: str) -> str:
    level = node["depth"] + 1
    title = format_title(node["label"], style)
    if level > 6:
        return f"###### **{title}** {node['block_id']}"
    return f"{'#' * level} {title} {node['block_id']}"


def parse_toc_line(line: str):
    """
    Parse one line of the toc-tree-*.md file:
        * N.N.N. label [[context]]   |   * I. label [[context]]   |   * b.1 label [[…]]
    """
    stripped = line.lstrip()
    if not stripped.startswith("* "):
        return None
    content = stripped[2:].strip()
    parts = content.split(None, 1)
    if not parts:
        return None
    raw_id = parts[0].rstrip(".")
    if not NODE_ID_RE.fullmatch(raw_id):
        return None
    rest = parts[1].strip() if len(parts) > 1 else ""
    if "[[" in rest:
        label_part, context_part = rest.split("[[", 1)
        label = label_part.strip()
        context = context_part.split("]]", 1)[0].strip()
        # a model sometimes writes a verse's line break as a literal "\n" (Tibetan text
        # never contains a backslash)
        context = context.replace("\\n", " ")
    else:
        label, context = rest.strip(), ""
    depth = raw_id.count(".") + 1
    return {
        "decimal_id":     raw_id,
        "depth":          depth,
        "frame":          not raw_id.split(".")[0].isdigit(),
        "label":          label,
        "block_id":       decimal_to_block_id(raw_id),
        "context":        context[:CONTEXT_MAX],
        "context_anchor": context[:ANCHOR_LENGTH].strip().rstrip("་"),
    }


# ---------------------------------------------------------------------------
# parse command
# ---------------------------------------------------------------------------

def cmd_parse(args):
    input_path = Path(args.input)
    out_path = Path(args.out)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    nodes = []
    with input_path.open(encoding="utf-8") as fh:
        for line in fh:
            node = parse_toc_line(line)
            if node:
                node["doc_order"] = len(nodes)
                nodes.append(node)
    if not nodes:
        print("ERROR: no nodes parsed — check input file format.", file=sys.stderr)
        sys.exit(1)
    max_depth = max(n["depth"] for n in nodes)
    output = {"source": str(input_path), "total_nodes": len(nodes),
              "max_depth": max_depth, "nodes": nodes}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)
    print(f"Parsed {len(nodes)} nodes ({sum(n['frame'] for n in nodes)} frame), max depth {max_depth}.")
    print(f"JSON cache written to: {out_path}")
    for d, c in sorted(Counter(n["depth"] for n in nodes).items()):
        print(f"  depth {d:2d}: {c} nodes")
    # two siblings with one title: almost always a miscounted ordinal (བཅོ་ལྔ་པ། twice)
    siblings = Counter((n["decimal_id"].rsplit(".", 1)[0] if "." in n["decimal_id"] else "",
                        canon(n["label"])) for n in nodes if not n["frame"])
    dups = [n for n in nodes if not n["frame"] and siblings[(
        n["decimal_id"].rsplit(".", 1)[0] if "." in n["decimal_id"] else "", canon(n["label"]))] > 1]
    if dups:
        print("\nWARNING — sibling headings with the same title (check the tree's numbering):")
        for n in dups:
            print(f"  [{n['decimal_id']}] {n['label']}")


# ---------------------------------------------------------------------------
# ingest command
# ---------------------------------------------------------------------------

def split_doc(text: str):
    m = FRONTMATTER_RE.match(text)
    fm = m.group(0) if m else ""
    body = text[m.end():] if m else text
    paras = [p.strip("\n") for p in re.split(r"\n[ \t]*\n", body) if p.strip()]
    return fm, paras


def is_heading(p: str) -> bool:
    return p.lstrip().startswith("#")


def content_canon(paras):
    return canon("".join(ID_RE.sub("", p) for p in paras
                         if not is_heading(p) and not p.lstrip().startswith("![[")))


def stamp_body_ids(paras):
    out, label, n = [], None, 0
    for p in paras:
        s = p.strip()
        if s.startswith("#"):
            lvl = len(s) - len(s.lstrip("#"))
            m = ID_RE.search(s)
            if lvl == 1:
                out.append(s if m else s + " ^0")
                continue
            if m and lvl == 2:
                label, n = m.group(1)[:-2] if m.group(1).endswith("-0") else m.group(1), 0
            out.append(p)
            continue
        # transclusions, blocks that already carry an ID, and footnote definitions
        # ("[^n]: …" — apparatus, not text) get no body ID; a text block that merely
        # opens with a footnote reference ("[^58]དེ་ལ་…") does
        if (s.startswith("![[") or re.match(r"\[\^[^\]]+\]:", s) or ID_RE.search(s.split("\n")[-1])
                or label is None):
            out.append(p)
            continue
        n += 1
        out.append(p.rstrip() + f" ^{label}-{n}")
    return out


# ---------------------------------------------------------------------------
# reorder siblings to the order the commentary actually treats them in
# ---------------------------------------------------------------------------

def content_stream(paras):
    """Canonical text of every content block, joined; plus (para, offset) per char."""
    chars, owner = [], []
    for pi, p in enumerate(paras):
        if is_heading(p) or p.lstrip().startswith("![["):
            continue
        cs, _ = canon_map(ID_RE.sub("", p))
        chars.append(cs)
        owner.extend((pi, j) for j in range(len(cs)))
    return "".join(chars), owner


def _find(stream, node, lo, hi):
    a = canon(node.get("context_anchor", ""))
    if not a or a == "?":
        return None
    for cand in (a, a[:max(12, len(a) // 2)]):
        k = stream.find(cand, lo, hi + len(cand))
        if 0 <= k < hi:
            return k
    return None


_ORD = ["དང་པོ", "གཉིས་པ", "གསུམ་པ", "བཞི་པ", "ལྔ་པ", "དྲུག་པ", "བདུན་པ", "བརྒྱད་པ", "དགུ་པ",
        "བཅུ་པ", "བཅུ་གཅིག་པ", "བཅུ་གཉིས་པ", "བཅུ་གསུམ་པ", "བཅུ་བཞི་པ", "བཅོ་ལྔ་པ", "བཅུ་དྲུག་པ",
        "བཅུ་བདུན་པ", "བཅོ་བརྒྱད་པ", "བཅུ་དགུ་པ", "ཉི་ཤུ་པ", "ཉེར་གཅིག་པ"]
_ORD_RE = re.compile(r"^(?:" + "|".join(sorted(map(re.escape, _ORD), key=len, reverse=True)) + r")(?=་|$)")


def opener_ordinal(node):
    """1 for a context opening 'དང་པོ…', 2 for 'གཉིས་པ…' … — the commentary's own count of
    which part this is; None when the context does not open with an ordinal."""
    m = _ORD_RE.match(canon(node.get("context_anchor", "")))
    return _ORD.index(m.group(0)) + 1 if m else None


def reorder_by_content(nodes, paras, renumber_ids=False):
    """
    A commentary sometimes announces its parts in one order (A, B, C, D) and then
    treats them in another (B, D, C, A). The tree follows the announcement; the
    headings must follow the text. For every parent, its children are first placed
    in the tree's order (each searched after the previous one, inside the parent's
    span). Only if that fails — a child cannot be found after its elder sibling, or
    the children's own opener ordinals disagree with the tree — are they re-sorted
    to the text's order. Titles never change; descendants move with their node;
    frame nodes (I, a, b …) never move. IDs: by default every node keeps the ID of
    the announced order (so 1.2 may come before 1.1 in the file); renumber_ids=True
    renumbers in the text's order instead.

    Returns (new node list, list of changes).
    """
    stream, _ = content_stream(paras)
    by_id = {n["decimal_id"]: n for n in nodes}
    kids = {}
    for n in nodes:
        if n["frame"]:
            continue
        parent = n["decimal_id"].rsplit(".", 1)[0] if "." in n["decimal_id"] else None
        kids.setdefault(parent if parent in by_id else None, []).append(n)
    changes = []

    def sequential(ch, lo, hi):
        pos, cur = {}, lo
        for c in ch:
            k = _find(stream, c, cur, hi)
            if k is None:
                return None
            pos[c["decimal_id"]] = k
            cur = k
        return pos

    def arrange(parent_id, lo, hi):
        ch = kids.get(parent_id, [])
        if not ch:
            return []
        # 1) tree order, each child searched after the one before it
        pos = sequential(ch, lo, hi)
        ords = [opener_ordinal(c) for c in ch]
        known = [o for o in ords if o is not None]
        # the commentary's own ordinals (དང་པོ་ནི། … གསུམ་པ་ནི།) out of step with the tree:
        # the tree's order is wrong even if a short repeated context happens to be found
        all_ord = len(known) == len(ch) and len(set(known)) == len(known)
        order = ch
        if pos is None or (all_ord and known != sorted(known)):
            # 2) text order. When every child opens with its own (distinct) ordinal,
            #    that ordinal is its place; otherwise — only if the tree order could not
            #    be placed at all — the first occurrence of each context in the span.
            by_ord = None
            if all_ord:
                cand = [c for _, c in sorted(zip(ords, ch), key=lambda t: t[0])]
                p2 = sequential(cand, lo, hi)
                if p2 is not None:
                    order, pos, by_ord = cand, p2, True
            if not by_ord and pos is not None:
                pass  # tree order places fine and the ordinals cannot settle it: keep it
            elif not by_ord:
                pos = {c["decimal_id"]: _find(stream, c, lo, hi) for c in ch}
                keyed, last = [], lo
                for i, c in enumerate(ch):
                    k = pos[c["decimal_id"]]
                    if k is not None:
                        last = k
                    keyed.append(((k if k is not None else last), i, c))
                order = [c for _, _, c in sorted(keyed, key=lambda t: (t[0], t[1]))]
            if [c["decimal_id"] for c in order] != [c["decimal_id"] for c in ch]:
                changes.append((parent_id or "(top)", [c["decimal_id"] for c in ch],
                                [c["decimal_id"] for c in order]))
        out = []
        found = [(pos[c["decimal_id"]], c) for c in order if pos.get(c["decimal_id"]) is not None]
        for c in order:
            k = pos.get(c["decimal_id"])
            if k is None:
                sub_lo, sub_hi = lo, hi
            else:
                later = [p for p, _ in found if p > k]
                sub_lo, sub_hi = k, (min(later) if later else hi)
            out.append((c, arrange(c["decimal_id"], sub_lo, sub_hi)))
        return out

    def renumber(items, prefix, acc):
        for i, (c, sub) in enumerate(items, 1):
            m = dict(c)
            m["first_in_text"] = (i == 1)       # stacks with its parent's heading
            if renumber_ids:
                new_id = f"{prefix}.{i}" if prefix else str(i)
            else:
                # keep the ID of the announced order: གཉིས་པ་… stays …-2-0 wherever it sits
                new_id = (f"{prefix}.{c['decimal_id'].rsplit('.', 1)[-1]}" if prefix
                          else c["decimal_id"])
            if new_id != c["decimal_id"]:
                m["tree_decimal_id"] = c["decimal_id"]
            m["decimal_id"] = new_id
            m["block_id"] = decimal_to_block_id(new_id)
            acc.append(m)
            renumber(sub, new_id, acc)
        return acc

    numbered = renumber(arrange(None, 0, len(stream)), "", [])
    first = next((i for i, n in enumerate(nodes) if not n["frame"]), len(nodes))
    front = [n for n in nodes[:first] if n["frame"]]
    back = [n for n in nodes[first:] if n["frame"]]
    new = front + numbered + back
    for i, n in enumerate(new):
        n["doc_order"] = i
    return new, changes


def tree_md(nodes):
    lines = ["## དཀར་ཆག / Table of Contents", ""]
    for n in nodes:
        d = n["decimal_id"]
        lab = d + ("." if "." not in d else "")
        lines.append("   " * (n["depth"] - 1) + f"* {lab} {n['label']} [[{n.get('context', '')}]]")
    return "\n".join(lines) + "\n"


def cmd_reorder(args):
    tree = json.loads(Path(args.tree).read_text(encoding="utf-8"))
    _, paras = split_doc(Path(args.commentary).read_text(encoding="utf-8"))
    nodes, changes = reorder_by_content(sorted(tree["nodes"], key=lambda n: n["doc_order"]), paras,
                                        renumber_ids=args.renumber_reordered)
    report_changes(changes, nodes)
    tree["nodes"] = nodes
    Path(args.out or args.tree).write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        Path(args.out_md).write_text(tree_md(nodes), encoding="utf-8")
        print(f"Reordered tree written to {args.out_md}")


def report_changes(changes, nodes):
    if not changes:
        print("Tree order matches the text — nothing reordered.")
        return
    print(f"REORDERED to the order of the text ({len(changes)} parent(s)):")
    for parent, old, new in changes:
        print(f"  under {parent}: tree {' '.join(old)}  →  text {' '.join(new)}")
    if not any("tree_decimal_id" in n for n in nodes):
        print("  NOTE: block IDs are kept from the announced order, so in the file these")
        print("  headings (and their ^…-0 IDs) now run out of numeric sequence, as listed above.")
        return
    moved = {i for _, o, nw in changes for i in o}
    ren = [n for n in nodes if "tree_decimal_id" in n]
    for n in ren:
        if n["tree_decimal_id"] in moved:
            sub = sum(1 for m in ren if m["tree_decimal_id"].startswith(n["tree_decimal_id"] + "."))
            print(f"    {n['tree_decimal_id']:>12s} → {n['decimal_id']:<12s} {n['label'][:50]}"
                  + (f"  (+{sub} below it renumbered with it)" if sub else ""))


def cmd_ingest(args):
    tree_path, commentary_path = Path(args.tree), Path(args.commentary)
    for pth in (tree_path, commentary_path):
        if not pth.exists():
            print(f"ERROR: not found: {pth}", file=sys.stderr)
            sys.exit(1)
    tree = json.loads(tree_path.read_text(encoding="utf-8"))
    nodes = sorted(tree["nodes"], key=lambda n: n["doc_order"])
    text = commentary_path.read_text(encoding="utf-8")
    fm, paras = split_doc(text)
    before = content_canon(paras)
    if args.reorder:
        nodes, changes = reorder_by_content(nodes, paras, renumber_ids=args.renumber_reordered)
        report_changes(changes, nodes)

    # canonical view of every block, for anchor search
    def views():
        return [canon_map(p) if not is_heading(p) else ("", []) for p in paras]

    existing = {m.group(1) for p in paras if is_heading(p) for m in [ID_RE.search(p)] if m}
    inserts = {}            # para index -> list of heading lines (doc order)
    not_found, mid_block, split_done = [], [], []
    cur = (0, 0)            # (block index, canonical offset) of the last placement
    v = views()

    for node in nodes:
        bid = node["block_id"]
        if bid.lstrip("^") in existing:
            continue
        anchor = canon(node.get("context_anchor", ""))
        if not anchor or anchor == "?":
            not_found.append((node["decimal_id"], node["label"], "empty context [[?]]"))
            continue
        hit = None
        for pi in range(cur[0], len(paras)):
            cs = v[pi][0]
            start = cur[1] if pi == cur[0] else 0
            k = cs.find(anchor, start)
            if k >= 0:
                hit = (pi, k)
                break
        if hit is None:
            # a shorter anchor tolerates a copying slip near the end of the context
            short = anchor[:max(12, len(anchor) // 2)]
            for pi in range(cur[0], len(paras)):
                start = cur[1] if pi == cur[0] else 0
                k = v[pi][0].find(short, start)
                if k >= 0:
                    hit = (pi, k)
                    break
        if hit is None:
            # the context may run across a block boundary (a short lead-in line, then
            # the quoted verse in the next block): search the joined canonical stream
            # and place the node in the block where the match starts
            joined, owner = [], []
            for pi in range(cur[0], len(paras)):
                start = cur[1] if pi == cur[0] else 0
                seg = v[pi][0][start:]
                joined.append(seg)
                owner.extend((pi, start + j) for j in range(len(seg)))
            k = "".join(joined).find(anchor)
            if k >= 0:
                hit = owner[k]
        if hit is None:
            not_found.append((node["decimal_id"], node["label"], f"context not found: {anchor[:40]!r}"))
            continue
        pi, k = hit
        last_seg = node["decimal_id"].split(".")[-1]
        # the child that comes first in the TEXT stacks with its parent's heading
        # (after a reorder that need not be the one numbered .1)
        first_child = node["depth"] > 1 and node.get("first_in_text", last_seg == "1")
        if k > 0 and not first_child and (args.split_frame_nodes or not node.get("frame")):
            prefix_txt = paras[pi][:v[pi][1][k]]
            if args.split_mid_block and prefix_txt.strip():
                # a new node starts a new block: cut the block at the context
                cut = v[pi][1][k]
                paras[pi:pi + 1] = [paras[pi][:cut].rstrip(), paras[pi][cut:].lstrip()]
                # shift pending inserts after pi
                inserts = {(i + 1 if i > pi else i): h for i, h in inserts.items()}
                v = views()
                pi, k = pi + 1, 0
                split_done.append(node["decimal_id"])
            else:
                mid_block.append((node["decimal_id"], node["label"], k))
        inserts.setdefault(pi, []).append(heading_line(node, args.title_style))
        cur = (pi, k)

    out = []
    for i, p in enumerate(paras):
        out.extend(inserts.get(i, []))
        out.append(p)
    if args.stamp_body_ids:
        out = stamp_body_ids(out)
    after = content_canon(out)
    if before != after:
        print("ABORT: ingest would change the commentary text — nothing written.", file=sys.stderr)
        sys.exit(3)
    commentary_path.write_text(fm + "\n" + "\n\n".join(out) + "\n", encoding="utf-8")

    n_ins = sum(len(h) for h in inserts.values())
    print("Summary")
    print(f"  Total nodes:            {len(nodes)}")
    print(f"  Inserted:               {n_ins}")
    print(f"  Already present:        {len(existing & {n['block_id'].lstrip('^') for n in nodes})}")
    print(f"  Blocks split at a node: {len(split_done)} {split_done if split_done else ''}")
    print(f"  Not found:              {len(not_found)}")
    if mid_block:
        print("\nMID-BLOCK (context not at a block start; heading placed before the block):")
        for d, lbl, k in mid_block:
            print(f"  [{d}] {lbl[:60]} (offset {k})")
    if not_found:
        print("\nNOT FOUND — insert manually then re-run to confirm:")
        for d, lbl, reason in not_found:
            print(f"  [{d}] {lbl[:70]}\n       {reason}")
    print("  Integrity: text unchanged ✓")
    print(f"\nCommentary updated: {commentary_path}")
    if getattr(args, "verify_against", None):
        # the strict gate (letters AND spacing) — the integrity check above ignores whitespace
        import subprocess
        v = subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve().parent / "verify_text.py"),
                            args.verify_against, str(commentary_path), "--fix"],
                           capture_output=True, text=True, encoding="utf-8")
        print(v.stdout.rstrip())
        if v.returncode != 0:
            print("✗ Strict text check FAILED — the letters differ from "
                  f"{args.verify_against}; the file is not approved", file=sys.stderr)
            sys.exit(4)
    if not_found:
        sys.exit(2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="TOC Tree Ingestion Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    p_parse = sub.add_parser("parse", help="Parse toc-tree-*.md to JSON")
    p_parse.add_argument("--input", required=True)
    p_parse.add_argument("--out", required=True)
    p_ing = sub.add_parser("ingest", help="Ingest all nodes into commentary")
    p_ing.add_argument("--tree", required=True)
    p_ing.add_argument("--commentary", required=True)
    p_ing.add_argument("--title-style", choices=["shad", "raw"], default="shad")
    p_ing.add_argument("--no-split-mid-block", dest="split_mid_block", action="store_false")
    p_ing.add_argument("--stamp-body-ids", action="store_true")
    p_ing.add_argument("--verify-against", metavar="SOURCE",
                       help="after writing, run the strict text gate (verify_text.py --fix) against "
                            "this source: letters and spacing; exit 4 if the letters differ. "
                            "Required by commentary-block-ids.")
    p_ing.add_argument("--split-frame-nodes", action="store_true",
                       help="a frame node (I, a, b …) whose context is mid-block cuts the block too")
    p_ing.add_argument("--keep-tree-order", dest="reorder", action="store_false",
                       help="do not reorder siblings to the order the text treats them in")
    p_ing.add_argument("--renumber-reordered", action="store_true",
                       help="give reordered siblings new IDs in text order (default: keep the announced IDs)")
    p_re = sub.add_parser("reorder", help="Reorder sibling nodes to the order of the text (JSON, optional .md)")
    p_re.add_argument("--tree", required=True)
    p_re.add_argument("--commentary", required=True)
    p_re.add_argument("--out", help="output JSON (default: overwrite --tree)")
    p_re.add_argument("--out-md", help="also write the reordered toc-tree .md")
    p_re.add_argument("--renumber-reordered", action="store_true",
                      help="renumber reordered siblings in text order (default: keep announced IDs)")
    args = parser.parse_args()
    {"parse": cmd_parse, "ingest": cmd_ingest, "reorder": cmd_reorder}[args.command](args)


if __name__ == "__main__":
    main()
