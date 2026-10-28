# Reference copy — the heading branch, as applied 2026-09-20.
#
# NOT a drop-in file. tools/parser/parser.py in
# webuddhist-library-data-pipeline is canonical; the vault copies are forks
# (see the FORK(liturgy-rails) markers there). Copy the SHAPE of these three
# functions, not the file.
#
# Extracted verbatim from:
#   bodhisattvacharyavatara-rails/4-SYSTEM/scripts/parser-root-text/parser.py
#   bodhisattvacharyavatara-rails/4-SYSTEM/scripts/parser-commentary/parser_commentary.py

# ============ root-text parser: _build_content_and_segmentation ============
def _build_content_and_segmentation(blocks, doc_default):
    """Returns (content, segments, headings).

    `headings` is the TOC's raw material — one entry per heading block, each
    carrying the offset in the heading-free content at which that heading's
    body starts. Headings contribute nothing to `content` or `segments`.
    """
    parts = []
    seg_list = []
    headings = []
    pos = 0

    for block_num, block in enumerate(blocks, start=1):
        ref = block["ref"]
        raw_lines = block["lines"]
        is_header = block["is_header"]

        content_lines = [l for l in raw_lines if not TRANSCLUSION_RE.match(l)]
        # Pure transclusion block — silently skip, used for alignment only
        if not any(l.strip() for l in content_lines):
            continue

        if not ref:
            print(f"  WARN block {block_num}: no reference marker — skipped", file=sys.stderr)
            continue

        ref_no_caret = ref[1:] if ref.startswith("^") else ref

        if is_header:
            # Recorded for the TOC, then dropped: `pos` is not advanced and no
            # segment is appended, so the heading leaves no trace in the
            # uploaded content or segmentation. `pos` is where this heading's
            # body begins, which becomes the TOC section's span start.
            text = raw_lines[0].lstrip('#').strip()
            ref_idx = text.rfind(ref)
            if ref_idx != -1:
                text = text[:ref_idx].rstrip()
            if not text:
                continue
            headings.append({"reference": ref_no_caret, "title": text, "pos": pos})
        else:
            line_spans = []
            for raw_line in content_lines:
                text = raw_line.rstrip()
                # Strip a trailing block-id marker (e.g. "^1-2") from every
                # line, not just the segment's own closing reference line —
                # per-line anchors used for finer-grained IDs must not leak
                # into the joined edition content.
                m = REF_RE.search(text)
                if m:
                    text = text[:m.start()].rstrip()
                if not text:
                    continue
                start = pos
                parts.append(text)
                pos += len(text)
                line_spans.append({"start": start, "end": start + len(text)})
            seg_type = _infer_segment_type(ref_no_caret, doc_default)
            seg_list.append({"lines": line_spans, "type": seg_type, "reference": ref_no_caret})

    return "".join(parts), seg_list, headings

# ============ root-text parser: build_edition return ============
def build_edition(source_path, lint_path):
    fm, body = _read_source(source_path)
    blocks = _extract_blocks(body)

    file_type = fm.get("file_type", "")
    if file_type == "translation":
        root_text_val = fm.get("root_text")
        root_file_type = None
        if root_text_val:
            resolved_root = _resolve_root_text_path(str(root_text_val), source_path)
            if resolved_root:
                try:
                    root_fm, _ = _read_source(resolved_root)
                    root_file_type = root_fm.get("file_type", "")
                except (ValueError, OSError):
                    pass
        doc_default = "paragraph" if root_file_type == "commentary" else "verse"
    else:
        doc_default = "paragraph" if fm.get("commentary_of") else "verse"

    content_str, seg_list, headings = _build_content_and_segmentation(blocks, doc_default)

    edition_type = fm.get("edition_type", "critical")
    source_url = (
        fm.get("source") or fm.get("gretil_url") or fm.get("dsbc_url")
        or fm.get("suttacentral_id") or ""
    )
    metadata = {"type": edition_type, "source": source_url}

    out = {
        "metadata": metadata,
        "content": content_str,
        "segmentation": {"segments": seg_list},
    }

    stem = source_path.stem
    out_path = OUTPUT_DIR / f"{stem}.edition.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    # `_headings` is handed to build_toc in memory and is deliberately absent
    # from the written payload — it is TOC input, not edition data.
    return out_path, {**out, "_headings": headings}

# ============ root-text parser: build_toc ============
def build_toc(source_path, edition_result):
    fm, body = _read_source(source_path)
    lang_tag = fm.get("lang_tag") or "en"

    content = edition_result["content"]
    segments = edition_result["segmentation"]["segments"]
    content_len = len(content)
    header_levels = _extract_header_levels(body)

    # Headings are no longer in the content or the segmentation, so the TOC is
    # built from what build_edition recorded on the way past. Each heading's
    # `pos` is where its body starts in the heading-free content, which serves
    # as both this section's span start and the previous section's span end —
    # there is no longer a heading occupying characters in between.
    headings = edition_result.get("_headings")
    if headings is None:
        # An edition.json read back from disk has no headings recorded; fall
        # back to the pre-2026-09-20 layout where they were title segments.
        headings = [
            {"reference": seg.get("reference", ""),
             "title": content[seg["lines"][0]["start"]:seg["lines"][0]["end"]],
             "pos": seg["lines"][0]["end"]}
            for seg in segments if seg.get("type") == "title"
        ]

    title_nodes = []
    for h in headings:
        title_nodes.append({
            "level": header_levels.get(h["reference"], 1),
            "span_start": h["pos"],
            "title": _wylie_to_unicode(h["title"], lang_tag),
            "ref": h["reference"],
        })

    for i, node in enumerate(title_nodes):
        span_end = content_len
        for j in range(i + 1, len(title_nodes)):
            if title_nodes[j]["level"] <= node["level"]:
                span_end = title_nodes[j]["span_start"]
                break
        node["span_end"] = span_end

# ============ commentary parser: the _strip_verse_ids heading remap ============
    # Heading offsets live in the same coordinate space and must move with it.
    # Each heading's `pos` is a segment-line boundary by construction (it is
    # the end of whatever block preceded it, or 0), so it is always a key in
    # `mapping` — assert rather than silently guess if that ever stops holding.
    for h in headings:
        assert h["pos"] in mapping, f"heading {h['reference']} at {h['pos']} is not a line boundary"
        h["pos"] = mapping[h["pos"]]

    return new_content, new_seg_list, headings
