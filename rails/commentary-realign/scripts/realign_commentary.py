#!/usr/bin/env python3
"""Re-align a commentary from one root text to another that contains it.

The library lets a commentary be aligned to one root text only. When the same
root passage also lives inside a second root text (the Praise to the Twenty-One
Taras recited three times inside the Zabtig Drolchok ritual), the commentary is
re-uploaded as a new commentary of the second root. This script builds that
copy from the existing alignment:

  1. read the commentary's transclusions of its current root (root_text:)
  2. match every transcluded root block to the new root by text similarity,
     keeping *every* block above the threshold (a passage repeated N times
     gives N targets)
  3. write a copy whose transclusions point at the new root — one line per
     target, written as one group so the parser aligns the commentary blocks
     under it to all of them — and whose frontmatter is re-pointed and
     cleared of the old live ids
  4. verify: the copy's alignment equals the old alignment mapped through the
     block map, and nothing but transclusion lines changed

Root blocks with no counterpart keep their transclusion of the old root. The
parser (4-SYSTEM/scripts/parser-commentary) reads a transclusion of any file
other than root_text as a scope break with no target, so the commentary on
them is left unaligned rather than paired with a same-numbered block.

Dry run by default: prints the block map and writes it to
0-INBOX/temp/commentary-realign/<stem>.mapping.json. Nothing in 1-SOURCES/
changes without --write.

Usage (from the vault root):
  python3 3-SKILLS/commentary-realign/scripts/realign_commentary.py "<commentary.md>" \\
      --new-root "<root.md>" --title "<new unique title>"                 # dry run
  ... --write                        # write the copy and verify it
  ... --write --delete-old           # and delete the old file if verification passed
  ... --map <overrides.json>         # {"<old ref>": ["<new ref>", ...] | []} replaces matches
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import pathlib
import re
import sys
import tempfile
import unicodedata

VAULT = pathlib.Path(os.environ.get("VAULT_ROOT", pathlib.Path.cwd()))
SKILL_DIR = pathlib.Path(__file__).resolve().parent
WORK_DIR = VAULT / "0-INBOX" / "temp" / "commentary-realign"

YAML_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
BLOCK_ID_RE = re.compile(r"\s*\^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*$")
TRANS_LINE_RE = re.compile(
    r"^(?P<indent>\s*)!\[\[(?P<file>[^\]#|]*)#\^(?P<ref>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    r"(?P<alias>\|[^\]]*)?\]\]\s*$")
SMALL_RE = re.compile(r"<small>.*?</small>", re.DOTALL)
TIB_TSHEG = "་"

# Keys that belong to the live copy of the old commentary and must not be
# carried over: a file carrying text_id is treated by commentary-upload as
# already uploaded.
LIVE_ID_KEYS = ("text_id", "edition_id", "toc_id", "aligned_to_edition_id")


def load_parser():
    for base in [VAULT / "4-SYSTEM" / "scripts", *SKILL_DIR.parents[:4]]:
        for p in sorted(base.rglob("parser-commentary/parser.py")):
            sys.path.insert(0, str(p.parent))
            import parser as parser_commentary  # noqa: E402
            return parser_commentary
    sys.exit("could not find parser-commentary/parser.py under 4-SYSTEM/scripts/")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def note_name(link):
    name = pathlib.Path(link.strip()).name
    if name and not name.endswith(".md"):
        name += ".md"
    return nfc(name)


def read_note(path):
    import yaml
    text = path.read_text(encoding="utf-8")
    m = YAML_RE.match(text)
    if not m:
        sys.exit(f"no frontmatter in {path}")
    return (yaml.safe_load(m.group(1)) or {}), text, m


def resolve(val, from_path):
    p = pathlib.Path(str(val))
    for base in [VAULT, from_path.parent, *from_path.parents]:
        if (base / p).exists():
            return (base / p).resolve()
    return None


def vault_rel(path):
    return nfc(str(path.resolve().relative_to(VAULT.resolve())))


def content_blocks(body):
    """{ref: text} for every non-heading block that ends in a block ID, in order."""
    out = {}
    for raw in re.split(r"\r?\n[ \t]*\r?\n", body.strip()):
        block = raw.strip()
        if not block or block.lstrip().startswith("#"):
            continue
        lines = block.split("\n")
        m = BLOCK_ID_RE.search(lines[-1])
        if not m:
            continue
        lines[-1] = lines[-1][: m.start()]
        out[m.group(1)] = "\n".join(lines)
    return out


def norm(text):
    """Tibetan letters and tshegs only: drops shad, spacing, yig mgo, <small>."""
    text = SMALL_RE.sub(" ", nfc(text))
    kept = []
    for ch in text:
        if "ཀ" <= ch <= "ྼ" or ch.isalnum():
            kept.append(ch)
        else:
            kept.append(TIB_TSHEG)
    return re.sub(f"{TIB_TSHEG}+", TIB_TSHEG, "".join(kept)).strip(TIB_TSHEG)


def score(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.real_quick_ratio() < 0.5 or sm.quick_ratio() < 0.5:
        return 0.0
    return sm.ratio()


def build_map(old_refs, old_blocks, new_blocks, threshold):
    new_norm = {r: norm(t) for r, t in new_blocks.items()}
    rows = {}
    for ref in old_refs:
        src = norm(old_blocks.get(ref, ""))
        if not src:
            rows[ref] = {"targets": [], "scores": {}, "best_rejected": None,
                         "note": "not a content block of the old root"}
            continue
        scored = sorted(((score(src, t), r) for r, t in new_norm.items() if t),
                        reverse=True)
        hits = [(s, r) for s, r in scored if s >= threshold]
        miss = next(((s, r) for s, r in scored if s < threshold), None)
        order = list(new_blocks)
        rows[ref] = {
            "targets": sorted((r for _, r in hits), key=order.index),
            "scores": {r: round(s, 3) for s, r in hits},
            "best_rejected": {"ref": miss[1], "score": round(miss[0], 3)} if miss else None,
        }
    return rows


def rewrite_body(body, old_root_name, new_root_link, mapping):
    """Replace each transclusion of the old root by its new-root targets."""
    out, changed, kept = [], 0, []
    for line in body.split("\n"):
        m = TRANS_LINE_RE.match(line)
        if m and note_name(m["file"]) == old_root_name:
            targets = mapping.get(m["ref"], [])
            if targets:
                out.append("\n\n".join(
                    f"{m['indent']}![[{new_root_link}#^{t}]]" for t in targets))
                changed += 1
                continue
            kept.append(m["ref"])
        out.append(line)
    return "\n".join(out), changed, kept


def yaml_scalar(value):
    s = str(value)
    if re.search(r"[:#\[\]{},&*!|>'\"%@`]|^\s|\s$|^[-?]", s):
        return json.dumps(s, ensure_ascii=False)
    return s


def edit_frontmatter(fm_text, sets, drops):
    """Line-level frontmatter edit that keeps every untouched line as it was."""
    lines = fm_text.split("\n")
    out, i = [], 0
    done = set()
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", lines[i])
        if m and (m.group(1) in drops or m.group(1) in sets):
            key = m.group(1)
            j = i + 1  # skip the value's continuation lines (lists, nested maps)
            while j < len(lines) and (lines[j].startswith((" ", "\t", "- ")) or not lines[j].strip()):
                j += 1
            if key in sets:
                out.append(f"{key}: {yaml_scalar(sets[key])}")
                done.add(key)
            i = j
            continue
        out.append(lines[i])
        i += 1
    for key, value in sets.items():
        if key not in done:
            out.append(f"{key}: {yaml_scalar(value)}")
    return "\n".join(out)


def alignment_pairs(parser, path):
    with tempfile.TemporaryDirectory() as tmp:
        parser._out_dir = lambda stem: pathlib.Path(tmp)
        _, out = parser.build_alignment(path)
    return {(a["source_segment_reference"], a["target_segment_reference"])
            for a in out["alignments"]}


def non_transclusion_lines(body):
    return [l for l in body.split("\n") if l.strip() and not TRANS_LINE_RE.match(l)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("commentary", type=pathlib.Path)
    ap.add_argument("--new-root", required=True, type=pathlib.Path)
    ap.add_argument("--title", help="new title, unique in its language on the library")
    ap.add_argument("--out", type=pathlib.Path, help="path of the copy (default: <stem>-<new root>.md)")
    ap.add_argument("--threshold", type=float, default=0.85)
    ap.add_argument("--map", type=pathlib.Path, help="JSON overrides {old_ref: [new_refs]}")
    ap.add_argument("--keep-alt-titles", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--delete-old", action="store_true")
    args = ap.parse_args(argv)

    old_path = args.commentary.resolve()
    fm, text, fm_match = read_note(old_path)
    if fm.get("file_type") != "commentary":
        sys.exit(f"{old_path.name}: file_type is {fm.get('file_type')!r}, expected commentary")
    old_root = resolve(fm.get("root_text", ""), old_path)
    new_root = args.new_root.resolve()
    if not old_root:
        sys.exit(f"root_text {fm.get('root_text')!r} does not resolve")
    if not new_root.exists():
        sys.exit(f"new root {args.new_root} does not exist")
    if old_root == new_root:
        sys.exit("the commentary is already aligned to this root")
    new_root_fm, new_root_text, nm = read_note(new_root)
    old_root_fm, old_root_text, om = read_note(old_root)
    old_blocks = content_blocks(old_root_text[om.end():])
    new_blocks = content_blocks(new_root_text[nm.end():])
    body = text[fm_match.end():]

    old_root_name = note_name(old_root.name)
    old_refs = list(dict.fromkeys(
        m["ref"] for l in body.split("\n")
        for m in [TRANS_LINE_RE.match(l)] if m and note_name(m["file"]) == old_root_name))
    if not old_refs:
        sys.exit(f"no transclusions of {old_root.name} in {old_path.name}")

    rows = build_map(old_refs, old_blocks, new_blocks, args.threshold)
    if args.map:
        for ref, targets in json.loads(args.map.read_text(encoding="utf-8")).items():
            bad = [t for t in targets if t not in new_blocks]
            if bad:
                sys.exit(f"--map {ref}: {bad} are not content blocks of {new_root.name}")
            rows.setdefault(ref, {"scores": {}, "best_rejected": None})
            rows[ref]["targets"], rows[ref]["override"] = list(targets), True
    mapping = {r: row["targets"] for r, row in rows.items()}

    # ---- report
    print(f"commentary : {vault_rel(old_path)}")
    print(f"old root   : {vault_rel(old_root)}  ({len(old_blocks)} blocks)")
    print(f"new root   : {vault_rel(new_root)}  ({len(new_blocks)} blocks)")
    print(f"threshold  : {args.threshold}\n")
    print(f"{'old ref':<8} {'n':>2}  targets (score)   | best rejected")
    close_calls = []
    for ref, row in rows.items():
        tg = ", ".join(f"{t}({row['scores'].get(t, 'map')})" for t in row["targets"]) or "— unmapped"
        br = row.get("best_rejected")
        brs = f"{br['ref']}({br['score']})" if br else ""
        flag = ""
        if row["targets"] and br and min(row["scores"].values() or [1]) - br["score"] < 0.15:
            flag = "  ⚠ close call"
            close_calls.append(ref)
        print(f"{ref:<8} {len(row['targets']):>2}  {tg:<40} | {brs}{flag}{'  (override)' if row.get('override') else ''}")
    unmapped = [r for r, t in mapping.items() if not t]
    counts = {}
    for t in mapping.values():
        counts[len(t)] = counts.get(len(t), 0) + 1
    print(f"\n{len(mapping)} old refs; targets per ref: {dict(sorted(counts.items()))}; "
          f"unmapped: {unmapped or 'none'}; close calls: {close_calls or 'none'}")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    map_path = WORK_DIR / f"{old_path.stem}.mapping.json"
    map_path.write_text(json.dumps(
        {"commentary": vault_rel(old_path), "old_root": vault_rel(old_root),
         "new_root": vault_rel(new_root), "threshold": args.threshold, "map": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"block map  : {vault_rel(map_path)}")

    # ---- the copy
    new_root_link = vault_rel(new_root)
    new_body, changed, kept = rewrite_body(body, old_root_name, new_root_link, mapping)
    order = list(new_blocks)
    all_targets = sorted({t for ts in mapping.values() for t in ts}, key=order.index)
    new_tid = new_root_fm.get("text_id")
    if not new_tid:
        print(f"  WARN {new_root.name} has no text_id: commentary_of left for the linter to fill")
    note = (f"Re-aligned copy for {new_root.stem}: the same commentary, whose root passages "
            f"recur in {new_root.stem}, with every transclusion of {old_root.stem} re-pointed "
            f"there by the commentary-realign skill. The original remains live as a commentary "
            f"of {old_root.stem} (text {fm.get('text_id', 'n/a')}).")
    desc = str(fm.get("source_description") or "").rstrip()
    if desc and not desc.endswith((".", "།", "。")):
        desc += "."
    sets = {
        "title": args.title or fm.get("title"),
        "root_text": new_root_link,
        "covers_verses": f"{all_targets[0]}–{all_targets[-1]}" if all_targets else "",
        "source_description": f"{desc} {note}".strip(),
        "realigned_from": vault_rel(old_path),
        "realigned_from_text_id": fm.get("text_id", ""),
        "realigned_from_edition_id": fm.get("edition_id", ""),
        "realigned_from_root_text": vault_rel(old_root),
    }
    if new_tid:
        sets["commentary_of"] = new_tid
    drops = set(LIVE_ID_KEYS) | (set() if args.keep_alt_titles else {"alt_titles"})
    new_fm = edit_frontmatter(fm_match.group(1), sets, drops)
    out_text = f"---\n{new_fm}\n---\n{new_body}"

    out_path = (args.out or old_path.with_name(f"{old_path.stem}-{new_root.stem.split('-', 1)[-1]}.md")).resolve()
    print(f"\ncopy       : {vault_rel(out_path)}")
    print(f"  transclusion lines re-pointed: {changed}; kept on old root (unaligned): {kept or 'none'}")
    print(f"  title      : {sets['title']}" + ("" if args.title else "   ⚠ unchanged — pass --title"))
    print(f"  dropped    : {sorted(k for k in drops if k in fm)}")
    print(f"  covers     : {sets['covers_verses']}")

    if not args.write:
        print("\nDRY RUN — nothing written. Review the block map, then re-run with --write.")
        return 0
    if not args.title:
        sys.exit("refusing to write without --title: the old title is already taken on the library")
    if out_path == old_path:
        sys.exit("--out must differ from the commentary: the original is needed for verification")
    if out_path.exists():
        sys.exit(f"{out_path.name} already exists — remove it or pass another --out")
    out_path.write_text(out_text, encoding="utf-8")
    print(f"  WROTE {vault_rel(out_path)}")

    # ---- verification
    parser = load_parser()
    problems = []
    if non_transclusion_lines(body) != non_transclusion_lines(new_body):
        problems.append("text other than transclusion lines changed")
    old_pairs = alignment_pairs(parser, old_path)
    expected = {(s, t2) for s, t in old_pairs for t2 in mapping.get(t, [])}
    actual = alignment_pairs(parser, out_path)
    if actual != expected:
        problems.append(f"alignment differs from the mapped old alignment: "
                        f"missing {sorted(expected - actual)[:6]}, extra {sorted(actual - expected)[:6]}")
    bad_targets = sorted({t for _, t in actual} - set(new_blocks))
    if bad_targets:
        problems.append(f"targets not content blocks of the new root: {bad_targets[:6]}")
    dropped_src = sorted({s for s, _ in old_pairs} - {s for s, _ in actual})
    print(f"\nverify: old {len(old_pairs)} pairs -> new {len(actual)} pairs "
          f"({len({s for s, _ in actual})} commentary blocks, {len({t for _, t in actual})} root blocks)")
    print(f"  commentary blocks now unaligned (their root block has no counterpart): {dropped_src or 'none'}")
    if problems:
        for p in problems:
            print(f"  FAIL {p}")
        print("  the old file was NOT deleted")
        return 1
    print("  OK  alignment = old alignment through the block map; only transclusion lines changed")

    if args.delete_old:
        delete_and_report(old_path, out_path)
    return 0


def delete_and_report(old_path, keep_path):
    old_path.unlink()
    print(f"  DELETED {vault_rel(old_path)}")
    # a link to the old file: [[stem#…]], [[stem|…]], [[stem]], or a path ending in stem.md
    link_re = re.compile(rf"{re.escape(nfc(old_path.stem))}(?:\.md|[#|\]])")
    refs = []
    for p in VAULT.rglob("*.md"):
        if ".git" in p.parts or p.resolve() == keep_path.resolve():
            continue
        try:
            if link_re.search(nfc(p.read_text(encoding="utf-8"))):
                refs.append(vault_rel(p))
        except (UnicodeDecodeError, OSError):
            pass
    print("  files still linking to the old file (update or re-point them):")
    for r in refs or ["none"]:
        print(f"    {r}")


if __name__ == "__main__":
    sys.exit(main())
