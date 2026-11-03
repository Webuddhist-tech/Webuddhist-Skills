#!/usr/bin/env python3
"""84000 — converter for EPUBs published by 84000: Translating the Words of the Buddha.

Publisher : 84000 (read.84000.co / 84000.co/translation/tohNN)
Generated : 2026-10-19, from Toh 76 "Aśokadattā's Prophecy" (api.84000.co .../epub/toh76.epub)
Stdlib only: no bs4 / ebooklib needed.

Usage
-----
    python converters/84000.py path/to/tohNN.epub path/to/output.md [--labels]

What the EPUB looks like (84000 print edition)
----------------------------------------------
    text/title.xhtml, imprint.xhtml, disclaimer.xhtml   front matter  -> frontmatter
    text/toc.xhtml, logo.xhtml                          skipped
    text/main.xhtml                                     the whole text

main.xhtml is a flat run of section headings and numbered passages:

    h3/h4 .section-heading            Summary, Acknowledgments, Introduction,
                                      The Translation, Colophon (data-bm="tr. The Translation")
    div.passage > .passage-gutter     the 84000 passage label (s.1, ac.1, i.7, 1.1, c.1 ...)
              > .passage-content      p / h5 / blockquote / div.verse-group
    section.back-matter               Notes (div.endnote), Bibliography (div.bibl-entry),
                                      Glossary (div.passage.gloss-entry)

Mapping to markdown
-------------------
    section heading          ## Title ^<label>-0          (label from data-bm: "tr." -> ^tr-0)
    chapter-title passage    ### Title ^1-0               (h5.passage-heading)
    passage                  one markdown block ending ^<label>   ("i.7" -> ^i-7, "1.158" -> ^1-158)
                             paragraphs / verse lines joined with hard line breaks, so one
                             passage = one block = one transcludable ID
    blockquote passage       "> " lines, then the ID on its own line (Obsidian's rule for quotes)
    endnote reference        [^N]                         definitions under ## Notes as [^N]: ...
    glossary entry           ### term, then Tibetan / Wylie / Sanskrit lines and the definition
    <em> <b>                 *italic* / **bold**
    glossary links           plain text (the link target is a glossary entry, not a structure tag)
    external links           [text](url)

The ^label IDs are 84000's own passage numbers re-spelled as Obsidian block IDs. They are
INTAKE anchors: the vault annex decides the final addressing scheme, and `add-block-ids`
restamps them when the file is promoted into 1-SOURCES/. Do not cite them from a rail before then.

Mechanical changes only: soft hyphens and zero-width spaces/joiners (U+00AD, U+200B, U+200D,
which 84000 inserts inside Sanskrit compounds and before dashes) are removed, whitespace is normalised. Wording is never touched. After writing, the script
compares the words of the source with the words of the output and warns on any that were lost.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from html import unescape
from html.entities import name2codepoint
from pathlib import PurePosixPath

NS = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/",
      "c": "urn:oasis:names:tc:opendocument:xmlns:container"}
XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}
# soft hyphen, zero-width space / joiner: layout artefacts 84000 inserts inside compounds and before dashes
INVISIBLE = {0x00AD: None, 0x200B: None, 0x200D: None}


# ---------------------------------------------------------------- helpers

def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def classes(el) -> set[str]:
    return set((el.get("class") or "").split())


def parse_xhtml(raw: bytes) -> ET.Element:
    """Parse XHTML, turning HTML-only named entities (&nbsp; ...) into characters."""
    text = raw.decode("utf-8")

    def fix(m):
        name = m.group(1)
        if name in XML_ENTITIES:
            return m.group(0)
        return chr(name2codepoint[name]) if name in name2codepoint else m.group(0)

    text = re.sub(r"&([A-Za-z][A-Za-z0-9]*);", fix, text)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text)
    return ET.fromstring(text.encode("utf-8"))


def clean(s: str) -> str:
    """Remove soft hyphens, collapse whitespace."""
    return re.sub(r"\s+", " ", s.translate(INVISIBLE)).strip()


def text_of(el) -> str:
    return clean("".join(el.itertext()))


def find_all(el, tag=None, cls=None):
    for e in el.iter():
        if tag and local(e.tag) != tag:
            continue
        if cls and cls not in classes(e):
            continue
        yield e


def slug_id(label: str) -> str:
    """'i.7' -> 'i-7', '1.158' -> '1-158', 'tr.' -> 'tr'."""
    return re.sub(r"[^0-9A-Za-z]+", "-", label).strip("-")


def wrap(marker: str, s: str) -> str:
    """Wrap s in an emphasis marker, keeping edge whitespace outside it."""
    core = s.strip()
    if not core:
        return s
    lead = s[: len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    return f"{lead}{marker}{core}{marker}{trail}"


# ---------------------------------------------------------------- inline rendering

class Inline:
    """Render an element's inline content to markdown."""

    def __init__(self):
        self.italic_depth = 0
        self.note_refs: list[str] = []

    def render(self, el) -> str:
        out = [el.text or ""]
        for child in el:
            out.append(self.node(child))
            out.append(child.tail or "")
        return "".join(out).translate(INVISIBLE)

    def node(self, el) -> str:
        tag, cls = local(el.tag), classes(el)
        if tag == "br":
            return "  \n"
        if "inline-label" in cls or "passage-label" in cls:
            return ""
        if tag == "a":
            if "endnote-ref" in cls:
                n = text_of(el)
                self.note_refs.append(n)
                return f"[^{n}]"
            if "note-back" in cls:
                return ""
            inner = self.render(el)
            href = el.get("href", "")
            if "glossary-link" in cls or not href.startswith("http"):
                return inner
            href = href.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
            return f"[{inner.strip()}]({href})" if inner.strip() else ""
        if tag in ("em", "i"):
            if self.italic_depth:          # nested italic: render roman
                return self.render(el)
            self.italic_depth += 1
            try:
                return wrap("*", self.render(el))
            finally:
                self.italic_depth -= 1
        if tag in ("b", "strong"):
            return wrap("**", self.render(el))
        if tag == "sup":
            return f"<sup>{self.render(el)}</sup>"
        return self.render(el)             # span, small-caps, mention-work, anything else

    def line(self, el) -> str:
        return clean_inline(self.render(el))


def clean_inline(s: str) -> str:
    """Collapse whitespace but keep the '  \\n' hard breaks."""
    parts = s.translate(INVISIBLE).split("  \n")
    return "  \n".join(re.sub(r"\s+", " ", p).strip() for p in parts)


# ---------------------------------------------------------------- metadata

def read_metadata(z: zipfile.ZipFile, base: str) -> dict:
    meta: dict = {}
    opf = ET.fromstring(z.read(f"{base}/content.opf"))
    md = opf.find("opf:metadata", NS)
    meta["title"] = clean(md.findtext("dc:title", "", NS))
    meta["identifier"] = md.findtext("dc:identifier", "", NS)
    meta["publisher"] = clean(md.findtext("dc:publisher", "", NS))
    meta["language"] = md.findtext("dc:language", "", NS)
    for m in md.findall("opf:meta", NS):
        if m.get("property") == "dcterms:modified":
            meta["epub_modified"] = (m.text or "").strip()

    def page(name):
        try:
            return parse_xhtml(z.read(f"{base}/text/{name}.xhtml"))
        except KeyError:
            return None

    imp = page("imprint")
    if imp is not None:
        for p in find_all(imp, "p"):
            c = classes(p)
            t = text_of(p)
            if "title-tibetan" in c:
                meta["title_bo"] = t
            elif "imprint-wylie" in c:
                meta["title_wylie"] = t
            elif "imprint-title-en" in c:
                meta["title_en_full"] = t
            elif "imprint-title-sa" in c:
                meta["title_sa"] = t
            elif "imprint-toh" in c:
                m = re.search(r"Toh\s*([\w\-]+)", t)
                meta["toh"] = m.group(1) if m else t.strip("· ")
            elif "imprint-source" in c:
                meta["kangyur_reference"] = clean(" ".join(p.text.split()) if p.text else "")
                for a in find_all(p, "a", "src-link"):
                    meta["scholar_edition_url"] = a.get("href", "")
            elif "imprint-names" in c:
                meta["tibetan_translators"] = [n.strip() for n in t.split("·") if n.strip()]
    dis = page("disclaimer")
    if dis is not None:
        t = text_of(dis)
        m = re.search(r"https?://84000\.co/translation/\S+?(?=[.,;]?(?:\s|$))", t)
        if m:
            meta["source_url"] = m.group(0)
        m = re.search(r"generated at (.*?\d{4}) from the online version", t)
        if m:
            meta["print_generated"] = m.group(1)
    return meta


def yaml_str(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def build_frontmatter(meta: dict, epub_name: str) -> str:
    toh = meta.get("toh", "")
    src_desc = (f"84000 print-edition EPUB ({epub_name}) of Toh {toh}, converted by "
                f"epub-to-markdown/converters/84000.py").strip()
    rows = [
        ("title", meta.get("title", "")),
        ("title_en", meta.get("title_en_full", "")),
        ("title_bo", meta.get("title_bo", "")),
        ("title_wylie", meta.get("title_wylie", "")),
        ("title_sa", meta.get("title_sa", "")),
        ("author", ""),
        ("translator", ""),
        ("publisher", meta.get("publisher", "")),
        ("language", "English"),
        ("file_type", "translation"),
        ("lang_tag", "en"),
        ("root_text", ""),
        ("covers_verses", ""),
        ("source_description", src_desc),
        ("source_url", meta.get("source_url", "")),
        ("scholar_edition_url", meta.get("scholar_edition_url", "")),
        ("toh", toh),
        ("kangyur_reference", meta.get("kangyur_reference", "")),
        ("tibetan_translators", meta.get("tibetan_translators", [])),
        ("license", ""),
        ("epub_modified", meta.get("epub_modified", "")),
        ("print_generated", meta.get("print_generated", "")),
        ("verse_id_format", "chapter-verse"),
        ("status", "draft"),
    ]
    lines = ["---"]
    for k, v in rows:
        if isinstance(v, list):
            if v:
                lines.append(f"{k}:")
                lines += [f"  - {yaml_str(x)}" for x in v]
            else:
                lines.append(f"{k}: []")
        elif v == "":
            lines.append(f"{k}:")
        else:
            lines.append(f"{k}: {yaml_str(v)}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------- body

class Converter:
    def __init__(self, show_labels: bool):
        self.show_labels = show_labels
        self.inl = Inline()
        self.out: list[str] = []
        self.ids: list[str] = []
        self.counts = Counter()
        self.parent_label, self.sub_count = "section", 0

    # -- ids
    def block_id(self, label: str) -> str:
        i = slug_id(label)
        self.ids.append(i)
        return i

    # -- passages
    def passage(self, el):
        label = ""
        content = None
        for ch in el:
            if "passage-gutter" in classes(ch):
                label = text_of(ch)
            elif "passage-content" in classes(ch):
                content = ch
        if content is None:
            return
        if not label:
            lab = next(find_all(content, "span", "inline-label"), None)
            label = text_of(lab) if lab is not None else ""

        kids = list(content)
        # chapter-title passage: only h5 headings
        if kids and all(local(k.tag) == "h5" for k in kids):
            title = " ".join(self.inl.line(k) for k in kids)
            bid = self.block_id(label.rstrip(".") + "-0" if label else "title-0")
            self.out.append(f"### {title} ^{bid}")
            self.counts["passages"] += 1
            return

        lines: list[str] = []
        quoted = False
        for k in kids:
            tag, cls = local(k.tag), classes(k)
            if tag == "blockquote":
                quoted = True
                for sub in k:
                    lines += self.container_lines(sub)
                if not any(local(s.tag) in ("div", "p") for s in k):
                    lines.append(self.inl.line(k))
            else:
                lines += self.container_lines(k)
        lines = [l for l in lines if l.strip()]
        if self.show_labels and label and lines:
            lines[0] = f"**{label}** {lines[0]}"
        bid = self.block_id(label) if label else None
        if not lines:
            return
        self.counts["passages"] += 1
        if not bid:
            self.counts["passages_without_id"] += 1
        if quoted:
            body = "\n".join(f"> {l}" for l in lines)
            self.out.append(body + (f"\n\n^{bid}" if bid else ""))
        else:
            body = "  \n".join(lines)
            self.out.append(body + (f" ^{bid}" if bid else ""))

    def container_lines(self, el) -> list[str]:
        tag, cls = local(el.tag), classes(el)
        if tag == "div" and "verse-group" in cls:
            return [self.inl.line(p) for p in el]
        if tag == "p" or tag == "div":
            if tag == "div" and any(local(c.tag) in ("p", "div") for c in el):
                res: list[str] = []
                for c in el:
                    res += self.container_lines(c)
                return res
            return [self.inl.line(el)]
        if tag == "span" and "inline-label" in cls:
            return []
        return [self.inl.line(el)]

    # -- sections
    def section_heading(self, el):
        label_title = el.get("data-bm", "")
        m = re.match(r"^(\w{1,4})\.\s+(.*)$", label_title)      # "tr. The Translation"
        title = text_of(el)
        level = int(el.get("data-bm-level") or 1)
        if m and m.group(1).isdigit() and level >= 3:
            # a numbered list inside a section (e.g. "1. Identifying ..." in the Introduction):
            # its number must not collide with the translation's chapter 1, 2, ..., so it is
            # numbered by position under its parent like any other un-numbered sub-heading
            self.sub_count += 1
            bid = self.block_id(f"{self.parent_label}-{self.sub_count}-0")
            self.out.append(f"### {title} ^{bid}")
        elif m:
            self.parent_label, self.sub_count = m.group(1), 0
            bid = self.block_id(self.parent_label + "-0")
            self.out.append(f"## {title} ^{bid}")
        else:
            # un-numbered sub-heading (the groups inside Bibliography, the essay headings inside
            # a long Introduction): child of the last numbered section, one level deeper
            self.sub_count += 1
            bid = self.block_id(f"{self.parent_label}-{self.sub_count}-0")
            depth = 2 + int(el.get("data-bm-level") or 1)
            self.out.append(f"{'#' * min(depth, 6)} {title} ^{bid}")
        self.counts["sections"] += 1

    def endnote(self, el):
        num = ""
        parts = [el.text or ""]
        for ch in el:
            if "note-back" in classes(ch):
                num = text_of(ch).rstrip(".")
            else:
                parts.append(self.inl.node(ch))
            parts.append(ch.tail or "")
        body = clean_inline("".join(parts))
        self.out.append(f"[^{num}]: {body}")
        self.counts["endnotes"] += 1

    def bibl(self, el):
        self.out.append("- " + " ".join(self.inl.line(p) for p in el if local(p.tag) == "p"))
        self.counts["bibliography"] += 1

    def gloss(self, el):
        content = next(c for c in el if "passage-content" in classes(c))
        term = ""
        fields: dict[str, str] = {}            # gloss-tibetan / -wylie / -sanskrit / -pali / -chinese ...
        defs: list[str] = []
        for ch in content:
            c = classes(ch)
            if "gloss-term" in c:
                term = self.inl.line(ch)
            elif "gloss-def" in c:
                defs += [self.inl.line(p) for p in ch if local(p.tag) == "p"]
            else:
                for k in c:
                    if k.startswith("gloss-"):
                        fields[k[len("gloss-"):]] = self.inl.line(ch)
        n = self.counts["glossary"] + 1
        bid = self.block_id(f"g-{n}")
        block = [f"### {term} ^{bid}", ""]
        for key in fields:                     # source order: wylie, tibetan, sanskrit, pali, chinese ...
            if fields[key]:
                block.append(f"- {key.capitalize()}: {fields[key]}")
        block += [""] + defs if defs else []
        self.out.append("\n".join(block))
        self.counts["glossary"] += 1

    # -- walk
    def walk(self, body):
        for el in body:
            tag, cls = local(el.tag), classes(el)
            if "section-heading" in cls and tag.startswith("h"):
                self.section_heading(el)
            elif tag == "div" and "passage" in cls and "gloss-entry" in cls:
                self.gloss(el)
            elif tag == "div" and "passage" in cls:
                self.passage(el)
            elif tag == "div" and "endnote" in cls:
                self.endnote(el)
            elif tag == "div" and "bibl-entry" in cls:
                self.bibl(el)
            elif tag == "section":
                self.walk(el)
            else:
                t = text_of(el)
                if t:
                    sys.stderr.write(f"WARNING: unhandled <{tag} class='{' '.join(cls)}'>: {t[:70]!r}\n")
                    self.out.append(self.inl.line(el))


# ---------------------------------------------------------------- loss check

def words(s: str) -> Counter:
    # brackets and asterisks are stripped on BOTH sides: markdown markers sit inside words, and so
    # does the source's own "[ ]", so keeping them would split the same word differently each way
    s = re.sub(r"[\[\]*]", "", s.translate(INVISIBLE))
    return Counter(w.lower() for w in re.findall(r"\w+", s))


def source_words(body) -> Counter:
    """All visible words in body, excluding passage labels and footnote numerals
    (both are re-expressed as block IDs / [^N] markers, which strip_markup removes)."""
    skip = set()
    for e in body.iter():
        if classes(e) & {"passage-label", "endnote-ref", "note-back"}:
            skip.add(e)
    parts = []
    blocks = {"p", "div", "section", "blockquote", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br"}

    def rec(el):
        if el in skip:
            return
        sep = " " if local(el.tag) in blocks else ""      # inline tags must not split a word
        parts.append(sep + (el.text or ""))
        for ch in el:
            rec(ch)
            parts.append(ch.tail or "")
        parts.append(sep)

    rec(body)
    return words("".join(parts))


def strip_markup(md: str) -> str:
    md = re.sub(r"\^[0-9A-Za-z\-]+\s*$", "", md, flags=re.M)      # trailing block ids
    md = re.sub(r"\[\^[^\]]*\]", " ", md)                             # footnote refs / defs
    md = re.sub(r"\]\(<?https?://[^\s)]*(?:\([^\s)]*\)[^\s)]*)*>?\)", "", md)   # link targets
    md = re.sub(r"</?sup>", "", md)
    md = re.sub(r"[\[\]*]", "", md)    # markers that sit inside words must not split them
    return md


# ---------------------------------------------------------------- main entry

def convert_epub_to_markdown(epub_path: str, out_path: str, show_labels: bool = False) -> None:
    with zipfile.ZipFile(epub_path) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        rootfile = container.find(".//c:rootfile", NS).get("full-path")
        base = str(PurePosixPath(rootfile).parent)
        meta = read_metadata(z, base)
        body = parse_xhtml(z.read(f"{base}/text/main.xhtml")).find("{http://www.w3.org/1999/xhtml}body")

    conv = Converter(show_labels)
    conv.walk(body)

    md = build_frontmatter(meta, PurePosixPath(epub_path.replace("\\", "/")).name)
    body_md = ""
    for i, block in enumerate(conv.out):      # bibliography bullets form one tight list
        sep = "\n" if i and block.startswith("- ") and conv.out[i - 1].startswith("- ") else "\n\n"
        body_md += (sep if i else "") + block
    md += f"\n\n# {meta.get('title', '')}\n\n" + body_md + "\n"

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)

    # --- checks
    dupes = [i for i, n in Counter(conv.ids).items() if n > 1]
    missing = source_words(body) - words(strip_markup(md))
    print(f"wrote {out_path}")
    print("  " + ", ".join(f"{k}={v}" for k, v in conv.counts.items()))
    print(f"  block ids: {len(conv.ids)}  duplicates: {len(dupes)}")
    if dupes:
        print("  WARNING duplicate block ids: " + ", ".join(sorted(dupes)[:10]))
    if missing:
        print("  WARNING words in the source but not in the output: "
              + ", ".join(f"{w}×{n}" for w, n in missing.most_common(15)))
    else:
        print("  word check: every source word is present in the output")
    refs, defs = set(conv.inl.note_refs), set(re.findall(r"^\[\^([^\]]+)\]:", md, flags=re.M))
    if refs != defs:
        print(f"  WARNING footnotes: refs without defs {sorted(refs - defs)[:10]}, "
              f"defs without refs {sorted(defs - refs)[:10]}")


# ---------------------------------------------------------------- Tibetan source (Scholar's Edition)

TIBETAN = re.compile(r"[ༀ-࿿]")
TSHEG = "་"


def tibetan_text(el) -> str:
    """Text of a div.tibetan with 84000's display line-wraps undone.

    The EPUB hard-wraps the Tibetan with newlines. A wrap after a tsheg splits nothing in the
    text, so it is removed; a wrap anywhere else (after a shad) becomes one space.
    """
    raw = "".join(el.itertext()).translate(INVISIBLE)
    raw = re.sub(rf"{TSHEG}[ \t]*\n\s*", TSHEG, raw)
    return re.sub(r"\s+", " ", raw).strip()


def convert_scholar_tibetan(epub_path: str, out_path: str) -> None:
    """Extract the Tibetan source from an 84000 *Scholar's Edition* EPUB (tohNN-scholar.epub).

    In that edition every passage carries a div.tibetan-block (the Degé text, with folio
    references) beside its English. This writes the Tibetan alone, one block per passage, with the
    SAME block IDs as the English file converted by convert_epub_to_markdown(), so
    [[tohNN#^1-5]] and [[tohNN-bo#^1-5]] are the two sides of one passage.
    """
    with zipfile.ZipFile(epub_path) as z:
        container = ET.fromstring(z.read("META-INF/container.xml"))
        rootfile = container.find(".//c:rootfile", NS).get("full-path")
        base = str(PurePosixPath(rootfile).parent)
        meta = read_metadata(z, base)
        body = parse_xhtml(z.read(f"{base}/text/main.xhtml")).find("{http://www.w3.org/1999/xhtml}body")

    blocks: list[str] = []
    ids: list[str] = []
    src_chars: Counter = Counter()
    for passage in find_all(body, "div", "passage"):
        if "gloss-entry" in classes(passage):
            continue
        content = next((c for c in passage if "passage-content" in classes(c)), None)
        gutter = next((c for c in passage if "passage-gutter" in classes(c)), None)
        if content is None:
            continue
        label = text_of(gutter) if gutter is not None else ""
        has_heading = any(local(k.tag) == "h5" for k in content)
        lines = []
        for tb in find_all(content, "div", "tibetan-block"):
            folio = next((text_of(d) for d in tb if "folio-ref" in classes(d)), "")
            txt = next((tibetan_text(d) for d in tb if "tibetan" in classes(d)), "")
            if not txt:
                continue
            src_chars.update(TIBETAN.findall(txt))
            if folio and not txt.startswith("[F."):
                txt = f"[{folio}] {txt}"
            lines.append(txt)
        if not lines:
            continue
        if has_heading:        # same rule as the English converter, so the IDs line up
            bid = slug_id(label.rstrip(".") + "-0") if label else "title-0"
        elif label:
            bid = slug_id(label)
        else:
            sys.stderr.write(f"WARNING: Tibetan block without a passage number skipped: {lines[0][:40]!r}\n")
            continue
        ids.append(bid)
        blocks.append("  \n".join(lines) + f" ^{bid}")

    title_bo = meta.get("title_bo", "")
    rows = [
        ("title", title_bo), ("title_wylie", meta.get("title_wylie", "")),
        ("title_sa", meta.get("title_sa", "")), ("title_en", meta.get("title_en_full", "")),
        ("author", ""), ("language", "Tibetan"), ("file_type", "root-text"), ("lang_tag", "bo"),
        ("source_description", f"Tibetan source (Degé Kangyur) as printed in the 84000 Scholar's "
                               f"Edition EPUB ({PurePosixPath(epub_path.replace(chr(92), '/')).name}) "
                               f"of Toh {meta.get('toh', '')}, extracted by epub-to-markdown/converters/84000.py"),
        ("source_url", meta.get("source_url", "")), ("toh", meta.get("toh", "")),
        ("kangyur_reference", meta.get("kangyur_reference", "")),
        ("tibetan_translators", meta.get("tibetan_translators", [])),
        ("license", ""), ("epub_modified", meta.get("epub_modified", "")),
        ("verse_id_format", "chapter-verse"), ("status", "draft"),
    ]
    fm = ["---"]
    for k, v in rows:
        if isinstance(v, list):
            fm += [f"{k}:"] + [f"  - {yaml_str(x)}" for x in v] if v else [f"{k}: []"]
        else:
            fm.append(f"{k}: {yaml_str(v)}" if v != "" else f"{k}:")
    fm.append("---")
    md = "\n".join(fm) + f"\n\n# {title_bo or meta.get('title', '')}\n\n" + "\n\n".join(blocks) + "\n"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)

    out_chars = Counter(TIBETAN.findall(re.sub(r"\^[0-9A-Za-z\-]+\s*$", "", md, flags=re.M)))
    # the YAML title_bo / title_wylie duplicate a few characters, so compare "at least" the source
    lost = src_chars - out_chars
    dupes = [i for i, n in Counter(ids).items() if n > 1]
    print(f"wrote {out_path}")
    print(f"  tibetan blocks={len(blocks)}  tibetan characters={sum(src_chars.values())}  duplicate ids={len(dupes)}")
    print("  character check: " + ("every source Tibetan character is present in the output" if not lost
          else "WARNING lost: " + ", ".join(f"{c}×{n}" for c, n in lost.most_common(10))))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    if "--tibetan" in sys.argv or args[0].endswith("-scholar.epub"):
        convert_scholar_tibetan(args[0], args[1])
    else:
        convert_epub_to_markdown(args[0], args[1], show_labels="--labels" in sys.argv)
