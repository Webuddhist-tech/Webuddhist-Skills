#!/usr/bin/env python3
"""
check_termbase_consistency.py
==============================

Validates that a translation output actually uses the rendering locked in its
track's termbase.md, verse by verse, instead of drifting to a synonym.

Why this exists
----------------
Nothing in the normal generation path enforces vocabulary consistency across
verses: each verse (or each chunk, if using a batch/API translation script)
is generated more or less independently. A term correctly rendered in verse
1-1 can silently drift to a different French word by verse 1-30 with nothing
flagging it. This script is the mechanical check that catches that drift,
so it doesn't have to rely on a human re-reading 900+ verses by eye.

Method
------
1. Parse the track's termbase.md table into {bo_lemma: locked_fr_rendering}.
   A row's source-lemma column may list several bo variants separated by
   " / "; each variant is registered separately, pointing to the same
   rendering. The rendering column may carry a parenthetical gloss, e.g.
   "bodhicitta (l'esprit d'eveil)" or "voeu (samvara)" -- both the head word
   and the glossed alternative are extracted as acceptable surface forms,
   since either may legitimately appear depending on sentence position.

2. For each verse rail under 2-RAILS/Verses/<id>.md in scope, read the
   frontmatter concepts_in_verse: list (and, as a fallback signal,
   concepts_in_commentary:) to get the bo lemmas the rail says are load-
   bearing for that verse. Only lemmas that also exist in the termbase are
   checked -- the termbase is deliberately partial (built verse-by-verse as
   rails are produced), so a concept with no termbase entry yet is skipped,
   not flagged as an error.

3. Parse the translation output file into verse_id -> text blocks, splitting
   on the trailing Obsidian block identifier (^chapter-verse). Any footnote
   referenced from within a verse's text has its body appended to that
   verse's checked text, so a term glossed only in a footnote still counts
   as covered.

4. For each (verse, expected termbase lemma) pair, check whether any of the
   lemma's registered French surface forms appears in that verse's
   translated text, in two tiers:
     - EXACT  : the literal surface form (accent/case-insensitive) appears.
     - LOOSE  : an article-stripped, crudely-depluralized version of the
       form appears -- catches ordinary French inflection (le Sugata vs
       les Sugatas, du corps vs au corps) so it isn't reported as drift.
   Anything that matches neither tier is a MISSING and is worth a human
   look -- it may be a legitimate paraphrase choice, or it may be real
   vocabulary drift.

Grade-file mode (no verse rails needed)
---------------------------------------
    python check_termbase_consistency.py \\
        --grade-file  <keywords>/bo_en_keyword_general.json \\
        --translation 3-TRANSFORMATIONS/Translations/en-general/<text>-en-general.md \\
        --strict-diacritics

Usage
-----
    python check_termbase_consistency.py \\
        --termbase "3-TRANSFORMATIONS/Translations/fr-scholarly/termbase.md" \\
        --translation "3-TRANSFORMATIONS/Translations/fr-scholarly/BCA-Chapitre1-Vers1-9-pilote.md" \\
        --rails-dir "2-RAILS/Verses" \\
        --verses 1-1 1-2 1-3 1-4 1-5 1-6 1-7 1-8 1-9

Omit --verses to check every verse rail found in --rails-dir that also
appears as a block in --translation.

Run from the vault root (bodhisattvachartavatara-rails/).
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path


# Set by --strict-diacritics. Off (the historical default) folds accents, which
# suits French ("éveil" = "eveil"). For a termbase that locks IAST spellings
# (Tara vs Tārā, hum vs HŪṂ) folding would hide exactly the drift to catch.
STRICT_DIACRITICS = False


def normalize(s: str) -> str:
    """Lowercase, collapse whitespace/apostrophe variants; strip accents unless
    --strict-diacritics."""
    s = s.strip().lower()
    s = s.replace("\u2019", "'")
    if not STRICT_DIACRITICS:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
    else:
        s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s)
    return s


_ARTICLE_WORD_RE = re.compile(
    r"\b(l|le|la|les|un|une|des|du|aux|au|d|de|ce|cet|cette|ces|the|a|an)\b"
)


def loose_form(s: str) -> str:
    """Article-insensitive, crudely depluralized form of a phrase, used only
    as an advisory LOOSE match tier -- the exact tier (plain normalize())
    always runs first and is the authoritative signal."""
    s = normalize(s)
    s = _ARTICLE_WORD_RE.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\b(\w{4,})s\b", r"\1", s)
    # crude English stemming for the advisory tier: blazing/blaze, endowed/endow
    s = re.sub(r"\b(\w{3,}?)(?:ing|ed|e)\b", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def match_tier(form: str, haystack_norm: str, haystack_loose: str) -> str:
    """Return 'exact', 'loose', or 'none' for whether `form` is attested in
    the translated text."""
    if normalize(form) in haystack_norm:
        return "exact"
    lf = loose_form(form)
    if lf and lf in haystack_loose:
        return "loose"
    return "none"


TERMBASE_ROW_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")


def extract_surface_forms(rendering_cell: str) -> list:
    # "world(s)" -> "world" / "worlds" (an optional plural, not a gloss)
    rendering_cell = re.sub(r"(\w+)\(s\)", r"\1 / \1s", rendering_cell)
    forms = []
    for alt in re.split(r"\s*/\s*", rendering_cell):
        alt = alt.strip()
        m = re.match(r"^(.+?)\s*\((.+)\)\s*$", alt)
        if m:
            forms.append(m.group(1).strip())
            forms.append(m.group(2).strip())
        else:
            forms.append(alt)
    return [f for f in forms if f]


_SEP_ROW_RE = re.compile(r"^\|[\s:|-]+\|$")


def parse_termbase(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    termbase = {}
    lines = text.split("\n")
    for i, line in enumerate(lines):
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if _SEP_ROW_RE.match(nxt):      # table header row
            continue
        m = TERMBASE_ROW_RE.match(line.strip())
        if not m:
            continue
        col1, col2, _col3 = m.groups()
        if col1.lower().startswith("lemme source") or set(col1) <= {"-", " "}:
            continue
        forms = extract_surface_forms(col2)
        if not forms:
            continue
        for bo_variant in re.split(r"\s*/\s*", col1):
            bo_variant = bo_variant.strip()
            if bo_variant:
                termbase[bo_variant] = forms
    return termbase


CONCEPT_LIST_RE = re.compile(
    r"^(concepts_in_verse|concepts_in_commentary):\s*\[(.*)\]\s*$"
)


def parse_rail_concepts(path: Path) -> list:
    lemmas = []
    text = path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not fm_match:
        return lemmas
    fm = fm_match.group(1)
    for line in fm.split("\n"):
        m = CONCEPT_LIST_RE.match(line.strip())
        if not m:
            continue
        body = m.group(2)
        entries = re.split(r"\)\s*,\s*", body)
        for entry in entries:
            entry = entry.strip().rstrip(",")
            gm = re.match(r"^(.+?)\s*\(", entry)
            if gm:
                bo_part = gm.group(1).strip()
            else:
                bo_part = entry.strip().rstrip(")").strip()
            for bo_variant in re.split(r"\s*/\s*", bo_part):
                bo_variant = bo_variant.strip()
                if bo_variant:
                    lemmas.append(bo_variant)
    return lemmas


BLOCK_ID_RE = re.compile(r"(?<!\S)\^((?:\w[\w\-]*)?\d)\s*$")   # ^0 ^1-5 ^I-1 ^a-1
FOOTNOTE_DEF_RE = re.compile(r"^\[\^(\d+)\]:\s*(.*)$")
FOOTNOTE_REF_RE = re.compile(r"\[\^(\d+)\]")


def split_translation_by_verse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    body = text[fm_match.end():] if fm_match else text

    footnotes = {}
    for raw_line in body.split("\n"):
        fm = FOOTNOTE_DEF_RE.match(raw_line.strip())
        if fm:
            footnotes[fm.group(1)] = fm.group(2)

    blocks = {}
    acc = []
    for raw_line in body.split("\n"):
        line = raw_line.rstrip()
        if FOOTNOTE_DEF_RE.match(line.strip()):
            continue
        if line.strip().startswith("![["):     # transclusion of the source block
            continue
        m = BLOCK_ID_RE.search(line)
        if m:
            content = line[: m.start()].rstrip()
            if content:
                acc.append(content)
            verse_id = m.group(1)
            verse_text = "\n".join(acc)
            ref_ids = FOOTNOTE_REF_RE.findall(verse_text)
            referenced_notes = " ".join(
                footnotes[n] for n in ref_ids if n in footnotes
            )
            blocks[verse_id] = (verse_text + " " + referenced_notes).strip()
            acc = []
        else:
            acc.append(line)
    return blocks


def run(termbase_path, translation_path, rails_dir, verses):
    termbase = parse_termbase(termbase_path)
    verse_blocks = split_translation_by_verse(translation_path)

    if verses:
        target_verses = verses
    else:
        target_verses = sorted(
            (p.stem for p in rails_dir.glob("*.md")
             if re.match(r"^\d+-\d+$", p.stem) and p.stem in verse_blocks),
            key=lambda s: tuple(int(x) for x in s.split("-"))
        )

    print(f"Termbase   : {termbase_path}  ({len(termbase)} bo lemmas registered)")
    print(f"Translation: {translation_path}  ({len(verse_blocks)} verse blocks found)")
    print(f"Rails dir  : {rails_dir}")
    print(f"Checking verses: {', '.join(target_verses)}")
    print()

    total_checks = 0
    total_hits = 0
    total_loose = 0
    misses = []

    header = f"{'verse':<8} {'bo term':<28} {'expected (fr)':<32} {'result'}"
    print(header)
    print("-" * len(header))

    for vid in target_verses:
        rail_path = rails_dir / f"{vid}.md"
        if not rail_path.exists():
            print(f"{vid:<8} (no rail file found, skipped)")
            continue
        lemmas = parse_rail_concepts(rail_path)
        verse_text = verse_blocks.get(vid, "")
        norm_verse_text = normalize(verse_text)
        loose_verse_text = loose_form(verse_text)

        if not verse_text:
            print(f"{vid:<8} (no matching block in translation output, skipped)")
            continue

        checked_any = False
        for lemma in lemmas:
            if lemma not in termbase:
                continue
            checked_any = True
            forms = termbase[lemma]
            total_checks += 1
            tiers = [match_tier(f, norm_verse_text, loose_verse_text) for f in forms]
            display_term = (lemma[:26] + "...") if len(lemma) > 27 else lemma
            expected = " / ".join(forms)
            expected_display = (expected[:30] + "...") if len(expected) > 31 else expected
            if "exact" in tiers:
                total_hits += 1
                print(f"{vid:<8} {display_term:<28} {expected_display:<32} OK")
            elif "loose" in tiers:
                total_hits += 1
                total_loose += 1
                print(f"{vid:<8} {display_term:<28} {expected_display:<32} OK (loose match -- verify inflection)")
            else:
                misses.append((vid, lemma, forms))
                print(f"{vid:<8} {display_term:<28} {expected_display:<32} MISSING")
        if not checked_any:
            print(f"{vid:<8} (no rail concepts with a termbase entry yet)")

    print()
    n_miss = total_checks - total_hits
    print(f"Summary: {total_hits}/{total_checks} expected renderings found "
          f"({total_loose} via loose/inflected match, "
          f"{n_miss} possible drift/miss{'es' if n_miss != 1 else ''}).")

    if misses:
        print("\nDetail on misses (verify by eye -- may be legitimate French "
              "paraphrase, or may be real drift):")
        for vid, lemma, forms in misses:
            snippet = verse_blocks.get(vid, "").strip().replace("\n", " ")
            if len(snippet) > 140:
                snippet = snippet[:140] + "..."
            print(f"  [{vid}] {lemma} -> expected one of: {forms}")
            print(f"          text: {snippet}")

    return 1 if misses else 0


def _verse_sort_key(vid):
    return [(0, int(x)) if x.isdigit() else (1, x) for x in re.split(r"-", vid)]


def run_grade_file(grade_path, translation_path, verses, grade_name=None, lang="en"):
    """Grade-file mode: the expectations are the per-verse keyword lists that
    graded-translate Phase 1 writes (bo_<tgt>_keyword_<grade>.json). No verse
    rails or termbase.md needed. A keyword whose Tibetan is contained in a
    longer locked phrase expected in the same verse (a title inside the
    Sanskrit title line, "Tara" inside "the Blessed Tārā") is COVERED when
    that phrase is present."""
    import json
    grade = json.loads(Path(grade_path).read_text(encoding="utf-8"))
    verse_blocks = split_translation_by_verse(translation_path)
    target = verses or sorted(
        (v for v in grade if v in verse_blocks and grade[v].get("keywords")),
        key=_verse_sort_key)

    print(f"Grade file : {grade_path}  ({len(grade)} verses)")
    print(f"Translation: {translation_path}  ({len(verse_blocks)} verse blocks found)")
    print(f"Diacritics : {'strict' if STRICT_DIACRITICS else 'folded (use --strict-diacritics for IAST termbases)'}")
    print()
    header = f"{'verse':<8} {'bo term':<24} {'expected':<32} result"
    print(header); print("-" * len(header))

    checks = hits = loose = covered = 0
    misses = []
    for vid in target:
        text = verse_blocks.get(vid, "")
        if not text:
            print(f"{vid:<8} (no matching block in translation output, skipped)")
            continue
        kws = {}
        for kw in grade.get(vid, {}).get("keywords", []):
            en = kw.get(lang) or ""
            if not en or (grade_name and kw.get("grade") not in (None, grade_name)):
                continue
            kws.setdefault((kw.get("term") or kw.get("key"), en), kw.get("bo") or "")
        n_text, l_text = normalize(text), loose_form(text)
        tiers = {k: [match_tier(f, n_text, l_text) for f in extract_surface_forms(re.sub(r"^the\s+", "", k[1], flags=re.I))]
                 for k in kws}
        for (term, en), bo in kws.items():
            checks += 1
            tr = tiers[(term, en)]
            bo_disp = (bo[:22] + "…") if len(bo) > 23 else bo
            en_disp = (en[:30] + "…") if len(en) > 31 else en
            if "exact" in tr:
                hits += 1; res = "OK"
            elif "loose" in tr:
                hits += 1; loose += 1; res = "OK (loose match -- verify inflection)"
            else:
                cover = [k2 for k2, b2 in kws.items() if k2 != (term, en) and bo and b2 and bo != b2
                         and any(part.strip() and part.strip() in b2 for part in bo.split("/"))
                         and "exact" in tiers[k2]]
                if cover:
                    hits += 1; covered += 1; res = f"COVERED by '{cover[0][1]}'"
                else:
                    res = "MISSING"; misses.append((vid, term, bo, en))
            print(f"{vid:<8} {bo_disp:<24} {en_disp:<32} {res}")

    print()
    n_miss = checks - hits
    print(f"Summary: {hits}/{checks} locked renderings found ({loose} loose, {covered} covered by a longer "
          f"locked phrase, {n_miss} possible drift/miss{'es' if n_miss != 1 else ''}).")
    if misses:
        print("\nMisses (verify by eye):")
        for vid, term, bo, en in misses:
            snippet = verse_blocks.get(vid, "").strip().replace("\n", " / ")
            print(f"  [{vid}] {term} ({bo}) -> expected '{en}'\n          text: {snippet[:160]}")
    return 1 if misses else 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--termbase", type=Path, help="termbase.md table (rails mode)")
    p.add_argument("--translation", required=True, type=Path)
    p.add_argument("--rails-dir", type=Path, help="2-RAILS/Verses (rails mode)")
    p.add_argument("--grade-file", type=Path,
                   help="graded-translate Phase 1 grade file (bo_<tgt>_keyword_<grade>.json): "
                        "use its per-verse keywords as the expectation instead of verse rails")
    p.add_argument("--grade", default=None, help="only check keywords of this grade (grade-file mode)")
    p.add_argument("--lang", default="en",
                   help="grade-file mode: keyword field holding the locked rendering (en, zh, hi, …); default en")
    p.add_argument("--strict-diacritics", action="store_true",
                   help="do not fold accents: Tara != Tārā, hum != HŪṂ (use for IAST termbases)")
    p.add_argument(
        "--verses", nargs="*", default=None,
        help="Specific verse IDs to check (e.g. 1-1 1-2). "
             "Default: every verse rail that also has a block "
             "in --translation.",
    )
    args = p.parse_args(argv)
    global STRICT_DIACRITICS
    STRICT_DIACRITICS = args.strict_diacritics
    if args.grade_file:
        return run_grade_file(args.grade_file, args.translation, args.verses, args.grade, args.lang)
    if not (args.termbase and args.rails_dir):
        p.error("rails mode needs --termbase and --rails-dir (or use --grade-file)")
    return run(args.termbase, args.translation, args.rails_dir, args.verses)


if __name__ == "__main__":
    raise SystemExit(main())
