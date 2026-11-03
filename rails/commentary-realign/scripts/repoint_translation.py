#!/usr/bin/env python3
"""Re-point a translation of a commentary at the commentary's re-aligned copy.

A translation of a commentary is uploaded with translation-upload as a
translation *of that commentary*: its blocks carry the commentary's block IDs,
each block transcludes its source block (``![[<commentary>#^X]]``), and the
library aligns it to the commentary segment for segment. It reaches the root
text only through the commentary. So when the commentary is re-aligned to a new
root (realign_commentary.py) and re-uploaded, each translation follows it: a
copy of the translation whose source transclusions point at the re-aligned
commentary and whose frontmatter names it as root_text, cleared of the old live
ids and the old translation_of link (the translation linter fills translation_of
from the re-aligned commentary's text_id once that is uploaded).

Checks: only transclusion lines change; the translation's block IDs equal the
source commentary's content block IDs one for one (translation-upload aligns by
identity); every block has its source transclusion.

Dry run by default.

Usage (from the vault root):
  python3 3-SKILLS/commentary-realign/scripts/repoint_translation.py "<translation.md>" \\
      --source "<re-aligned commentary.md>" --title "<new unique title>"   # dry run
  ... --write [--delete-old]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from realign_commentary import (  # noqa: E402
    LIVE_ID_KEYS, TRANS_LINE_RE, content_blocks, delete_and_report, edit_frontmatter,
    non_transclusion_lines, note_name, read_note, vault_rel,
)

TRANSLATION_KEYS = ("translation_of", "translation_of_text_id", "translation_of_edition_id")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("translation", type=pathlib.Path)
    ap.add_argument("--source", required=True, type=pathlib.Path,
                    help="the re-aligned commentary (written by realign_commentary.py)")
    ap.add_argument("--title", help="new title, unique in its language on the library")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--delete-old", action="store_true")
    args = ap.parse_args(argv)

    old_path = args.translation.resolve()
    src_path = args.source.resolve()
    fm, text, fm_match = read_note(old_path)
    src_fm, src_text, src_m = read_note(src_path)
    if fm.get("file_type") != "translation":
        sys.exit(f"{old_path.name}: file_type is {fm.get('file_type')!r}, expected translation")
    if not src_fm.get("realigned_from"):
        sys.exit(f"{src_path.name} has no realigned_from: run realign_commentary.py on it first")

    # the names the translation may use for its source: the old commentary or the copy
    src_names = {note_name(src_fm["realigned_from"]), note_name(src_path.name)}
    body = text[fm_match.end():]
    out_lines, seen, other = [], [], []
    for line in body.split("\n"):
        m = TRANS_LINE_RE.match(line)
        if m and note_name(m["file"]) in src_names:
            # keep the link style the file already uses (short name or full path)
            link = src_path.stem if "/" not in m["file"] else vault_rel(src_path)
            out_lines.append(f"{m['indent']}![[{link}#^{m['ref']}]]")
            seen.append(m["ref"])
            continue
        if m:
            other.append(f"{m['file']}#^{m['ref']}")
        out_lines.append(line)
    new_body = "\n".join(out_lines)

    tr_ids = list(content_blocks(body))
    src_ids = list(content_blocks(src_text[src_m.end():]))
    problems = []
    if tr_ids != src_ids:
        problems.append(f"block IDs differ from the source commentary: "
                        f"only here {sorted(set(tr_ids) - set(src_ids))[:6]}, "
                        f"only in source {sorted(set(src_ids) - set(tr_ids))[:6]}"
                        + ("" if set(tr_ids) != set(src_ids) else ", same set in a different order"))
    if sorted(seen) != sorted(tr_ids):
        problems.append(f"blocks without their source transclusion: {sorted(set(tr_ids) - set(seen))[:6]}; "
                        f"transclusions without a block: {sorted(set(seen) - set(tr_ids))[:6]}")
    if other:
        problems.append(f"transclusions of other files: {other[:6]}")
    if non_transclusion_lines(body) != non_transclusion_lines(new_body):
        problems.append("text other than transclusion lines would change")

    sets = {
        "title": args.title or fm.get("title"),
        "root_text": vault_rel(src_path),
        "realigned_from": vault_rel(old_path),
        "realigned_from_text_id": fm.get("text_id", ""),
        "realigned_from_edition_id": fm.get("edition_id", ""),
        "realigned_from_translation_of": fm.get("translation_of_text_id") or fm.get("translation_of", ""),
    }
    if "title_original" in fm:
        sets["title_original"] = src_fm.get("title")
    drops = set(LIVE_ID_KEYS) | set(TRANSLATION_KEYS) | {"alt_titles"}
    new_fm = edit_frontmatter(fm_match.group(1), sets, drops)
    out_text = f"---\n{new_fm}\n---\n{new_body}"

    old_src_stem = pathlib.Path(src_fm["realigned_from"]).stem
    tail = (old_path.stem[len(old_src_stem):] if old_path.stem.startswith(old_src_stem)
            else f"-{old_path.stem}")
    out_path = (args.out or old_path.with_name(f"{src_path.stem}{tail}.md")).resolve()

    print(f"translation: {vault_rel(old_path)}  ({len(tr_ids)} blocks)")
    print(f"source     : {vault_rel(src_path)}  ({len(src_ids)} blocks)")
    print(f"copy       : {vault_rel(out_path)}")
    print(f"  source transclusions re-pointed: {len(seen)}")
    print(f"  title      : {sets['title']}" + ("" if args.title else "   ⚠ unchanged — pass --title"))
    print(f"  root_text  : {sets['root_text']}")
    print(f"  dropped    : {sorted(k for k in drops if k in fm)}")
    for p in problems:
        print(f"  FAIL {p}")
    if problems:
        return 1
    print("  OK  block IDs identical to the source; every block transcludes its source block; "
          "only transclusion lines change")
    if not args.write:
        print("\nDRY RUN — nothing written. Re-run with --write.")
        return 0
    if not args.title:
        sys.exit("refusing to write without --title: the old title is already taken on the library")
    if out_path == old_path or out_path.exists():
        sys.exit(f"{out_path.name}: must be a new file")
    out_path.write_text(out_text, encoding="utf-8")
    print(f"  WROTE {vault_rel(out_path)}")
    if args.delete_old:
        delete_and_report(old_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
