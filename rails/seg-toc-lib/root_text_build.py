#!/usr/bin/env python3
"""
Root-text workflow library — one subcommand per step skill (4-SYSTEM/Skills/root-text-*):
lay out a Tibetan root text (treatise, praise, ritual, prayer, letter) the way the vault's
processed root texts are laid out: verse texts as stanzas, prose texts as paragraphs with
their verse passages as stanzas.

    root-text-classify    python root_text_build.py classify   <source.md>
    root-text-segment     python root_text_build.py segment    <source.md> <workdir>
                                     [--form auto|verse|prose] [--front-title <title>]
                                     [--body-title <title>]
    root-text-toc-ingest  python root_text_build.py toc-ingest <workdir> --tree <anchored tree.md>
    root-text-group       python root_text_build.py group-split <workdir> [--max-lines 750]
                          (subagents: Skills/root-text-group/prompts/*-grouping.md)
                          python root_text_build.py group-join  <workdir>
    root-text-block-ids   python root_text_build.py finish     <workdir>  # → final-free.md / final-prose.md

    (prepare <source> <workdir> [--tree T] = segment + toc-ingest in one call)

classify  content first, title second: commentary (glosses another text) / verse / mixed /
          prose. Verse share counts only metrical lines (a clause with the same syllable
          count as a neighbour); a commentary word in the title does not make a verse text
          a commentary ("…ཚད་མ་རྣམ་འགྲེལ།", "བྱང་ཆུབ་སེམས་ཀྱི་འགྲེལ་པ།"). Exit 0 for
          verse, mixed and prose (segment picks the form); 1 for a commentary, which goes to
          commentary-pipeline.
segment / toc-ingest (one routine, `prepare`; toc-ingest re-derives the units from the
          source with the settings segment stored in state.json, so its output is exactly
          what one call with --tree gives)
          1. units. verse form: pādas — a pāda ends at a shad (།) or tsheg-shad (༔) cluster
             before the next syllable; footnote markers [^n] stay on the line they follow.
             prose form: sentences — a sentence ends at a final verb (…འོ། …སོ། …ཏོ། …ནོ།
             …ཤོག …ཅིག …ཞེ་ན།); verse passages inside (4+ lines of one metre, each closed by
             "། །") stay pāda by pāda.
             Raw paragraph breaks are kept: the printed edition's paragraphs follow the
             sense, so a unit always ends at one and no block may run across one (marked ¶
             in group-in.md; finish refuses a grouping that crosses it). A paragraph that
             ends mid-sentence (no shad, or a connective: …ཏེ། …ནས། …དང་།) is not kept but
             listed in breaks-review.md. Headings may still fall inside a paragraph.
          2. frame, by pattern only (added only when present):
             Sanskrit (or Chinese: རྒྱའི་སྐད་དུ།) title + Tibetan title + homage, or the
             title repeated + homage → ## <front-title> ^I-0
             the closing matter → ## མཇུག་བྱང། ^a-0, with one sub-section per colophon in
             text order (as the commentary skill does): author's (… མཛད་པ་རྫོགས་སོ།) →
             ### མཛད་བྱང། ^a-1-0, translators' (… ལོ་ཙཱ་བ … བསྒྱུར …) → ### འགྱུར་བྱང། ^a-2-0
             The title line becomes "# <title> ^0". With front matter and no TOC parts,
             the body gets "## <body-title> ^1-0" (default གཞུང་དངོས།).
          3. body headings (toc-ingest): the top-level nodes (1., 2. …, II.) of an anchored
             tree from root-text-toc-extract; no tree = no body headings.
          4. grouping input, one version: verse form → free (stanzas by sense,
             root-text-group/prompts/stanza-grouping.md); prose form → prose (paragraphs and
             stanzas, root-text-group/prompts/prose-grouping.md).
group-split / group-join  cut a long group-in.md into parts at a heading or ¶ (where no
          block may cross anyway) for parallel subagents; join their groups-<v>-partN.json.
finish    applies groups-<version>.json → final-<version>.md, stamps
          block IDs, verifies the text is unchanged. Prose sentences of one block are joined
          on one line; verse lines keep one pāda per line.
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def vault_root():
    for d in (HERE, *HERE.parents):
        if (d / "4-SYSTEM").is_dir():
            return d
    sys.exit("cannot find the vault root (a folder containing 4-SYSTEM/)")


ING = HERE / "toc_tree_ingest.py"          # shared with commentary-toc-ingest
GROUP_PROMPTS = "4-SYSTEM/Skills/root-text-group/prompts"
PY = sys.executable
FN = r"\[\^\d+\]"
END = re.compile(r"[།༔](?:[ \t]*(?:" + FN + r")?[ \t]*[།༔])*(?:" + FN + r")*[ \t]*(?=[ཀ-ྼ༄])")
NOTES = re.compile(r"(?m)^\[\^\d+\]:")
# "…མཛད་པ་རྫོགས་སོ།", and the title between: "…མཛད་པའི་<title>་རྫོགས་སོ།" / "…མཛད་པ་<title>་རྫོགས་སོ།"
AUTHOR = re.compile(r"མཛད་པ(?:་|འི་)?(?:རྫོགས|ཡིན|ལགས)|མཛད་པ(?:འི)?་[^།]{0,300}?རྫོགས|[གཀ]ྱིས་སྦྱར་བ|བརྩམས་པ་རྫོགས")
TRANSLATOR = re.compile(r"ལོ་ཙཱ་བ|བསྒྱུར་(?:ཅིང|ཞིང|ནས|ཏེ|བ)|ཞུས་ཏེ|གཏན་ལ་ཕབ|འགྱུར་བཅོས")
FRAME_SECTIONS = ("^I-0", "^a-")       # front matter; the closing matter and its sub-sections
COLOPHON_TITLE = {"author": "མཛད་བྱང།", "translators": "འགྱུར་བྱང།"}
COMM_TITLE = re.compile(r"འགྲེལ|རྣམ་པར་བཤད|རྣམ་བཤད|ཊཱི་ཀཱ|ཊཱི་ཀ|བཤད་སྦྱར|དཀའ་འགྲེལ")
SRC_LANG = re.compile(r"རྒྱ་གར་སྐད་དུ|རྒྱའི་སྐད་དུ|རྒྱ་ནག་སྐད་དུ")
# a clause closed the way verse lines are: "། །", "ག །", "༔"
DOUBLE = re.compile(r"(?:།[\s་]*(?:" + FN + r")?\s*།|[གཀཤ]\s+།|༔)[\s།༔]*(?:" + FN + r")*\s*$")
# a finite ending closes a prose sentence: …འོ། …སོ། …ཏོ། …ནོ། …ཤོག …ཅིག …ཞེ་ན།
FINAL = re.compile(r"(?:འོ|(?<![ཀ-ྼ])[སཏནརལདངག]ོ|ཤོག|[ཅཤ]ིག|[ཞཅཤ]ེ་ན|"
                   # the -o particle repeating a final བ / མ: "…འགྲུབ་བོ།" "…འཚམ་མོ།"
                   r"བ་[བཔ]ོ|མ་མོ)[\s་]*$")
SENT_MAX = 200          # syllables: a longer run is cut at the next clause end
VERSE_MIN = 4           # lines of one metre, each closed by "། །", make a verse passage
# a raw paragraph that ends on one of these has stopped mid-sentence: its break is not kept
# as fixed but listed for review ("…བསལ་ཏེ། །", "…ཞལ་ནས།", "…དང་།")
CONNECTIVE = {"ཏེ", "སྟེ", "དེ", "ནས", "ཞིང", "ཅིང", "ཤིང", "དང", "ཀྱང", "ཡང", "པས", "བས", "ཀྱིས",
              "གྱིས", "ཀྱི", "གྱི", "ལས", "ཞེས", "ཅེས", "ཤེས", "པའི", "བའི", "མའི"}


def norm(s):
    """For matching colophon wording: no footnote markers, no editorial parentheses,
    the non-breaking tsheg as a tsheg ("…མཛད་པ་)རྫོགས", "ལོ་ཙཱ༌[^11]བ")."""
    return re.sub(r"[()\s]", "", re.sub(FN, "", s)).replace("༌", "་")


def is_author(s):
    return bool(AUTHOR.search(norm(s)))


def is_translator(s):
    return bool(TRANSLATOR.search(norm(s)))


def syl(s):
    return len(re.findall(r"[ཀ-ྼ]+", re.sub(FN, "", s)))


def squeeze(s):
    return re.sub(r"\s+", "", s)


def no_headings(s):
    return squeeze(re.sub(r"(?m)^#.*$", "", s))


def split_doc(text):
    fm = ""
    m = re.match(r"^---\n.*?\n---\n", text, flags=re.S)
    if m:
        fm, text = m.group(0), text[m.end():]
    n = NOTES.search(text)
    body, notes = (text[:n.start()], text[n.start():]) if n else (text, "")
    return fm, body, notes


def pada_spans(run, start=0, end=None, cuts=frozenset()):
    """Clauses of run[start:end]; a kept raw paragraph break (an offset in cuts) always
    ends one."""
    end = len(run) if end is None else end
    spans, pos = [], start
    for m in END.finditer(run, start, end):
        spans.append((pos, m.end()))
        pos = m.end()
    if run[pos:end].strip():
        spans.append((pos, end))
    out = []
    for x, y in spans:
        for c in sorted(c for c in cuts if x < c < y):
            out.append((x, c))
            x = c
        out.append((x, y))
    return out


def raw_paragraphs(lines):
    """The body as one run (paragraphs joined by a space, as before) and its raw paragraph
    breaks. The printed edition's paragraphs follow the sense (565 Nalanda files: page
    breaks fall inside paragraphs 95% of the time, paragraphs end at a sentence or verse
    line 99%), so each break is kept — unless the paragraph ends mid-sentence (no shad, or
    a connective): those are listed for review instead.
    Returns run, kept break offsets (start of the next paragraph), doubtful breaks."""
    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n[ \t]*\n", "\n".join(lines))]
    paras = [p for p in paras if p]
    run, kept, doubtful = "", set(), []
    for k, p in enumerate(paras):
        if k:
            prev = re.sub(FN, "", paras[k - 1]).replace("༌", "་").rstrip()
            core_end = re.sub(r"[།༔\s]+$", "", prev).rstrip("་")
            last = re.split(r"[་\s]", core_end)[-1] if core_end else ""
            if re.search(r"[།༔]$", prev) and last not in CONNECTIVE:
                kept.add(len(run) + 1)
            else:
                doubtful.append((len(run) + 1, paras[k - 1][-40:], p[:30]))
            run += " "
        run += p
    return run, kept, doubtful


# ── classify ─────────────────────────────────────────────────────────────────

def measure(text):
    """(kind, title, gloss markers per 1000 syllables, metrical share) of a source file."""
    fm, body, _ = split_doc(text)
    first = next((l for l in body.splitlines() if l.strip()), "")
    title = re.sub(r"^#+\s*", "", first)
    t = re.sub(FN, "", body).replace("༌", "་")
    n = syl(t) or 1
    gloss = len(re.findall(r"ཞེས་པ་(?:ནི|སྟེ|ལ)|ཞེས་བྱ་བ་(?:ནི|ལ)", t)) / n * 1000
    lens = [syl(c) for c in re.split(r"[།༔]+", t) if syl(c)]
    # metrical: a clause of 5+ syllables with the same count as a neighbour
    verse = sum(m for k, m in enumerate(lens) if m >= 5 and m in
                [lens[j] for j in (k - 1, k + 1) if 0 <= j < len(lens)]) / n
    # a verse text stays verse unless it glosses heavily: one "ཞེས་པ་" in a short prayer
    # is not a commentary
    if (gloss >= 1.0 and verse < 0.6) or gloss >= 3.0 or (COMM_TITLE.search(title) and verse < 0.6):
        kind = "commentary"
    elif verse >= 0.6:
        kind = "verse"
    else:
        kind = "prose" if verse < 0.3 else "mixed"
    return kind, title, gloss, verse


def classify(src):
    kind, title, gloss, verse = measure(src.read_text(encoding="utf-8"))
    print(f"{src.name}: {kind}  (title: {title[:60]} · gloss markers {gloss:.2f}/1000 syl · "
          f"metrical share {verse:.0%})")
    if kind == "commentary":
        print("  → a commentary: use commentary-pipeline, not the root-text skills")
    elif kind in ("prose", "mixed"):
        print("  → prose form: paragraphs, with its verse passages as stanzas (prepare --form prose)")
    elif COMM_TITLE.search(title):
        print("  → the title reads like a commentary, but the text is verse: laid out as verse")
    return 1 if kind == "commentary" else 0


# ── prepare ──────────────────────────────────────────────────────────────────

def core(s):
    """Tibetan letters and tshegs only, for comparing a title with its repetition."""
    return re.sub(r"[^ཀ-ྼ་]", "", re.sub(FN, "", s).replace("༌", "་")).strip("་")


def prose_units(run, a, b, cuts=frozenset()):
    """Prose body → units: sentences (S) and, inside them, verse passages pāda by pāda (V).
    A kept raw paragraph break ends a sentence. Returns texts, types, end offsets."""
    spans = pada_spans(run, a, b, cuts)
    lens = [syl(run[x:y]) for x, y in spans]
    clean = [re.sub(r"[།༔\s]+$", "", re.sub(FN, "", run[x:y])).replace("༌", "་").strip() for x, y in spans]
    # a clause opening with "ཞེས" closes a quotation: prose, never a verse line
    dbl = [bool(DOUBLE.search(run[x:y])) and not c.startswith("ཞེས") for (x, y), c in zip(spans, clean)]
    final = [bool(FINAL.search(c)) for c in clean]
    isv = [False] * len(spans)
    # long metres drift with Sanskrit names: exact up to 9 syllables, ±1 up to 12, ±2 above
    tol = lambda m: 0 if m <= 9 else (1 if m <= 12 else 2)
    i = 0
    while i < len(spans):
        j = i
        while j < len(spans) and 5 <= lens[i] <= 25 and dbl[j]:
            ref = sorted(lens[i:j])[(j - i - 1) // 2] if j > i else lens[i]   # lines so far
            if abs(lens[j] - ref) > tol(ref):
                break
            j += 1
        # a run of rubrics of similar length ("…བྱའོ། །" "…ཕྱག་རྒྱའོ། །") is prose: in a
        # loose (long-metre) run, at most a third of the lines may end on a final verb
        loose = tol(sorted(lens[i:j])[(j - i) // 2]) > 0 if j > i else False
        # …unless the final verbs are a homage or praise refrain ("…ལ་ཕྱག་འཚལ་ལོ། །" on every
        # line); parallel prose lists ("…ནི་རྣམ་པར་སྣང་མཛད་ཀྱིའོ།") share endings too, so
        # only these refrains count
        ends = Counter(" ".join(re.findall(r"[ཀ-ྼ]+", clean[k])[-2:]) for k in range(i, j) if final[k])
        top = ends.most_common(1)[0] if ends else ("", 0)
        refrain = bool(re.search(r"ཕྱག|འཚལ|བསྟོད|འདུད", top[0])) and top[1] * 2 >= sum(final[i:j])
        if j - i >= VERSE_MIN and not (loose and not refrain and sum(final[i:j]) * 3 > j - i):
            isv[i:j] = [True] * (j - i)
        i = max(j, i + 1)
    # a line right after (or between) verse lines, closed like verse and one syllable off
    # the metre — a contraction: "…བདག་མཆིའོ། །" is 6 in a 7-syllable passage — belongs to
    # the passage; a quotation close ("…ཞེས་སོ།") never does
    for k in range(1, len(spans)):
        if isv[k] or not dbl[k] or not isv[k - 1] or "ཞེས" in run[spans[k][0]:spans[k][1]]:
            continue
        if abs(lens[k] - lens[k - 1]) <= 1:
            isv[k] = True
    # a line closed like verse with verse on both sides is verse, whatever its length (a
    # damaged or irregular pāda would otherwise split its stanza)
    for k in range(1, len(spans) - 1):
        if not isv[k] and dbl[k] and isv[k - 1] and isv[k + 1]:
            isv[k] = True
    units, types, start, size = [], [], None, 0
    for k, (x, y) in enumerate(spans):
        if isv[k]:
            if start is not None:
                units.append((start, x))
                types.append("S")
                start, size = None, 0
            units.append((x, y))
            types.append("V")
            continue
        start = x if start is None else start
        size += lens[k]
        seg = re.sub(r"[།༔\s]+$", "", re.sub(FN, "", run[x:y])).replace("༌", "་")
        if FINAL.search(seg) or size >= SENT_MAX or y in cuts:
            units.append((start, y))
            types.append("S")
            start, size = None, 0
    if start is not None:
        units.append((start, b))
        types.append("S")
    return [run[x:y].strip() for x, y in units], types, [y for _, y in units]


def prepare(src, work, tree, front_title, body_title, form="auto"):
    work.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    if form == "auto":
        form = "verse" if measure(text)[0] == "verse" else "prose"
    fm, body, notes = split_doc(text)
    lines = body.strip("\n").split("\n")
    title_line = lines[0].strip() if lines and lines[0].lstrip().startswith("#") else None
    # one run; unit boundaries are re-derived, but the raw paragraph breaks are kept
    run, cuts, doubtful = raw_paragraphs(lines[1:] if title_line else lines)
    report = []

    # 1–2a. front matter: source-language title / Tibetan title / homage — or, without the
    #       language labels, the title repeated and the homage
    front, pos = [], 0
    i = run.find("བོད་སྐད་དུ")
    hom_re = re.compile(r"ཕྱག་འཚལ་ལོ")
    if SRC_LANG.search(run[:200]) and 0 < i < 600:
        h = hom_re.search(run, i)
        if h and h.start() - i < 600:
            hcuts = [m.end() for m in END.finditer(run, i, h.start())]
            hom = hcuts[-1] if hcuts else h.start()
            m = END.search(run, h.end())
            pos = m.end() if m else len(run)
            front = [run[:i].strip(), run[i:hom].strip(), run[hom:pos].strip()]
            lang = "Chinese" if "རྒྱ་གར་སྐད" not in run[:200] else "Sanskrit"
            report.append(f"front matter ({lang} title, Tibetan title, homage)")
    elif title_line:
        # leading clauses that repeat the title or pay homage (a prose text may put the
        # homage before the title); the opening marks (༄༅། །) join the next clause. In a
        # verse text a lone homage is usually the first pāda of the first stanza: only the
        # title repetition counts there.
        t_core = core(re.sub(r"བཞུགས(?:་སོ)?", "", title_line)).split("་")
        segs, p0 = [], 0
        for m in END.finditer(run):
            if m.end() > 400 or len(segs) >= 3:
                break
            if core(run[p0:m.end()]):
                segs.append((p0, m.end()))
                p0 = m.end()
        kinds = []
        for x, y in segs:
            c = core(run[x:y]).split("་")
            if len(t_core) >= 3 and c[:3] == t_core[:3]:
                kinds.append("title")
            elif hom_re.search(run[x:y]) and form == "prose" and syl(run[x:y]) <= 20:
                kinds.append("homage")
            else:
                break
        if "title" in kinds or ("homage" in kinds and form == "prose"):
            n_front = len(kinds)
            pos = segs[n_front - 1][1]
            front = [run[x:y].strip() for x, y in segs[:n_front]]
            report.append(f"front matter ({', '.join(kinds)})")

    # 2b. colophons: the tail of the text that is out of metre or worded as a colophon
    spans = pada_spans(run, pos, cuts=cuts)
    metre = Counter(syl(run[a:b]) for a, b in spans).most_common(1)[0][0] if spans else 0
    k = len(spans)
    floor = max(0, len(spans) - 30) if form == "prose" else 0   # prose: the last 30 clauses
    while k > floor:
        seg = run[spans[k - 1][0]:spans[k - 1][1]]
        # colophon region: colophon wording, a line out of metre, or prose — a clause that
        # ends on a single shad ("…དང་།") where a pāda ends on "། །" / "ག །" / "༔"
        prose = not re.search(r"(?:།[\s་]*(?:" + FN + r")?[\s]*།|ག\s+།|༔)[\s།༔]*(?:" + FN + r")*\s*$", seg)
        if is_author(seg) or is_translator(seg) or abs(syl(seg) - metre) > 2 or prose:
            k -= 1
        else:
            break
    # a colophon starts at its own wording: closing verses in another metre (a dedication
    # in 9- or 11-syllable lines after 7-syllable verse) stay in the body
    while k < len(spans) and not (is_author(run[spans[k][0]:spans[k][1]])
                                  or is_translator(run[spans[k][0]:spans[k][1]])):
        k += 1
    if k >= len(spans):
        # verse after the colophon — a translator's dedication ("…ཞི་བར་ཤོག") — stops the
        # walk back; look for colophon wording among the last lines instead
        k = next((j for j in range(max(0, len(spans) - 16), len(spans))
                  if is_author(run[spans[j][0]:spans[j][1]]) or is_translator(run[spans[j][0]:spans[j][1]])),
                 len(spans))
    tail = run[spans[k][0]:].strip() if k < len(spans) else ""
    if tail and not (is_author(tail) or is_translator(tail)):
        k, tail = len(spans), ""                 # out-of-metre lines, but no colophon
    colophons = []
    if tail:
        # the author's colophon ends with the first clause that completes its wording
        ends = [m.end() for m in END.finditer(tail)] + [len(tail)]
        cut = next((e for e in ends if is_author(tail[:e])), None)
        if cut is not None:
            colophons.append(("author", tail[:cut].strip()))
            rest = tail[cut:].strip()
        else:
            rest = tail
        if rest and is_translator(rest):
            colophons.append(("translators", rest))
        elif rest:
            colophons[-1:] = [(colophons[-1][0], colophons[-1][1] + " " + rest)] if colophons else \
                [("author", rest)]
        report += ["author's colophon" if kind == "author" else "translators' colophon"
                   for kind, _ in colophons]
    if form == "prose":
        padas, types, ends = prose_units(run, pos, spans[k][0] if k < len(spans) else len(run), cuts)
    else:
        padas = [run[a:b].strip() for a, b in spans[:k]]
        types = ["P"] * len(padas)
        ends = [b for _, b in spans[:k]]
    # body units followed by a kept raw paragraph break: no block may run across one
    breaks = [i for i, e in enumerate(ends[:-1], 1) if e in cuts]
    body_end = ends[-1] if ends else pos
    flagged = [d for d in doubtful if pos < d[0] < body_end]
    if flagged:
        (work / "breaks-review.md").write_text(
            "# Raw paragraph breaks that end mid-sentence — not kept, check by hand\n\n"
            + "\n".join(f"- …{a} ‖ {b}…" for _, a, b in flagged) + "\n", encoding="utf-8")
    report.append(f"raw paragraph breaks kept: {len(breaks)}"
                  + (f", {len(flagged)} flagged (breaks-review.md)" if flagged else ""))

    out = []
    if title_line:
        out.append(re.sub(r"^#+\s*", "# ", title_line).rstrip() + " ^0")
    else:
        report.append("no title line found — add '# <title> ^0' by hand")
    if front:
        out += [f"## {front_title} ^I-0"] + front
    if padas and not tree:
        # the body needs its own heading, or its blocks would be counted as front matter
        # (^I-4 …) or get no section number; with a tree, its first part takes this role
        out.append(f"## {body_title} ^1-0")
        report.append(f"body heading '{body_title}' added (no TOC parts)")
    out += padas
    if colophons:
        # the closing matter as in the commentary skill: ## མཇུག་བྱང། ^a-0, one ### per
        # colophon in text order (^a-1-0, ^a-2-0)
        out.append("## མཇུག་བྱང། ^a-0")
        for i, (kind, c) in enumerate(colophons, 1):
            out += [f"### {COLOPHON_TITLE[kind]} ^a-{i}-0", c]
    prepared = work / "prepared.md"
    res = fm + "\n\n".join(out) + "\n" + ("\n" + notes if notes else "")
    assert no_headings(res) == no_headings(text), "text changed — nothing written"
    prepared.write_text(res, encoding="utf-8")

    # 3. body headings: top-level tree nodes only
    nf = "no tree"
    if tree:
        tl = tree.read_text(encoding="utf-8").splitlines()
        # top-level nodes only — but a tree with a single numbered top node (one rite
        # section, one chapter) would give a single heading: its children count too
        child = len([l for l in tl if re.match(r"^\* \d+\. ", l)]) == 1
        keep = [l for l in tl if l.startswith("## ") or not l.strip() or re.match(r"^\* (?:\d+|II)\.? ", l)
                or (child and re.match(r"^\s+\* \d+\.\d+ ", l))]
        tmd, tjs = work / "tree-top.md", work / "tree-top.json"
        tmd.write_text("\n".join(keep) + "\n", encoding="utf-8")
        subprocess.run([PY, "-X", "utf8", str(ING), "parse", "--input", str(tmd), "--out", str(tjs)],
                       check=True, capture_output=True)
        r = subprocess.run([PY, "-X", "utf8", str(ING), "ingest", "--tree", str(tjs), "--commentary",
                            str(prepared), "--split-frame-nodes"], capture_output=True, text=True,
                           encoding="utf-8")
        assert "Integrity: text unchanged" in r.stdout, r.stdout + r.stderr
        m = re.search(r"Not found:\s+(\d+)", r.stdout)
        nf = f"{m.group(1) if m else '?'} not placed"
        # the front-matter section holds only its frame blocks: the author's own opening
        # verses belong to the body, so the first body heading moves up to meet them
        if front:
            t = prepared.read_text(encoding="utf-8")
            f2, b2, n2 = split_doc(t)
            bl = [x.strip() for x in re.split(r"\n\s*\n", b2) if x.strip()]
            fi = next(j for j, x in enumerate(bl) if x.startswith("## ") and "^I-0" in x)
            nxt = next((j for j in range(fi + 1, len(bl)) if bl[j].startswith("#")), None)
            gap = nxt - (fi + 1 + len(front)) if nxt is not None else 0
            if gap > 0 and not any(s in bl[nxt] for s in FRAME_SECTIONS):
                bl.insert(fi + 1 + len(front), bl.pop(nxt))
                prepared.write_text(f2 + "\n\n".join(bl) + "\n" + ("\n" + n2 if n2 else ""), encoding="utf-8")
                report.append(f"first body heading moved up {gap} pāda(s) to follow the front matter")

    # 4. grouping input — one version: free (verse) or prose
    translated = "རྒྱ་གར་སྐད་དུ" in run[:300]
    modes = ["prose"] if form == "prose" else ["free"]
    t = split_doc(prepared.read_text(encoding="utf-8"))[1]
    lst, n, sec = [], 0, None
    for b in [x.strip() for x in re.split(r"\n\s*\n", t) if x.strip()]:
        if b.startswith("#"):
            sec = b
            lst.append("\n" + b)
        elif sec and any(s in sec for s in FRAME_SECTIONS):
            lst.append("[frame] " + b)
        else:
            n += 1
            lst.append(f"{types[n - 1]}{n}  {b}")
            if n in breaks:
                lst.append("¶")          # a paragraph break of the printed edition: blocks stop here
    (work / "group-in.md").write_text("\n".join(lst).strip() + "\n", encoding="utf-8")
    assert n == len(types), "unit count changed between prepare steps"
    json.dump({"source": str(src), "form": form, "modes": modes, "translated": translated,
               "front": bool(front), "tree": str(tree) if tree else None, "types": "".join(types),
               "breaks": breaks, "front_title": front_title, "body_title": body_title},
              open(work / "state.json", "w", encoding="utf-8"), ensure_ascii=False)
    steps = []
    if "free" in modes:
        steps.append(f"free → run {GROUP_PROMPTS}/stanza-grouping.md → groups-free.json")
    if "prose" in modes:
        steps.append(f"prose → run {GROUP_PROMPTS}/prose-grouping.md → groups-prose.json")
    if form == "prose":
        passages = len(re.findall(r"V+", "".join(types)))
        units = (f"prose: {types.count('S')} sentences, {types.count('V')} verse lines in "
                 f"{passages} passage(s)")
    else:
        units = f"pādas {n} · metre {metre} syllables"
    print(f"{units} · {', '.join(report) or 'no frame elements'} · "
          f"body headings: {nf} · {'translated from Sanskrit' if translated else 'not translated'} · "
          f"versions: {' + '.join(steps)}")
    for h in re.findall(r"(?m)^#.*$", prepared.read_text(encoding="utf-8")):
        print("   " + h)


# ── finish ───────────────────────────────────────────────────────────────────

def finish(work):
    state = json.loads((work / "state.json").read_text(encoding="utf-8"))
    for mode in state.get("modes", ["free"]):
        g = work / f"groups-{mode}.json"
        if not g.exists():
            prompt = "prose-grouping.md" if mode == "prose" else "stanza-grouping.md"
            sys.exit(f"{g} is missing — run {GROUP_PROMPTS}/{prompt} first (version '{mode}'; "
                     f"for a split input: group-join)")
        build(work, g, work / f"final-{mode}.md", state.get("types"), state.get("breaks", []))


def build(work, groups_path, final, types=None, breaks=()):
    prepared = work / "prepared.md"
    text = prepared.read_text(encoding="utf-8")
    fm, body, notes = split_doc(text)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    groups = json.loads(groups_path.read_text(encoding="utf-8"))["stanzas"]
    ends = {z for _, z in groups}
    kind =lambda i: types[i - 1] if types else "P"
    for a, z in groups:
        assert len({kind(i) for i in range(a, z + 1)}) == 1, \
            f"block [{a}, {z}] mixes prose sentences and verse lines"
    crossing = [(a, z) for a, z in groups if any(a <= b < z for b in breaks)]
    assert not crossing, f"block(s) {crossing} run across a raw paragraph break (¶ in group-in.md)"
    out, cur, n, sec = [], [], 0, None
    for b in blocks:
        if b.startswith("#"):
            assert not cur, f"a stanza crosses the heading {b}"
            sec = b
            out.append(b)
        elif sec and any(s in sec for s in FRAME_SECTIONS):
            out.append(b)
        else:
            n += 1
            cur.append(b)
            if n in ends:
                # a prose paragraph runs on one line; verse keeps one pāda per line
                out.append((" " if kind(n) == "S" else "\n").join(cur))
                cur = []
    assert not cur and [i for a, z in groups for i in range(a, z + 1)] == list(range(1, n + 1)), \
        f"{groups_path.name} must cover every pāda once, in order"
    res = fm + "\n\n".join(out) + "\n" + ("\n" + notes if notes else "")
    assert squeeze(res) == squeeze(text), "text changed — nothing written"
    final.write_text(res, encoding="utf-8")
    # block IDs: stamp against the tree's JSON if there is one, else a frame-only tree
    tjs = work / "tree-top.json"
    if not tjs.exists():
        tjs.write_text(json.dumps({"source": "", "total_nodes": 0, "max_depth": 0, "nodes": []}), encoding="utf-8")
    r = subprocess.run([PY, "-X", "utf8", str(ING), "ingest", "--tree", str(tjs), "--commentary", str(final),
                        "--stamp-body-ids"], capture_output=True, text=True, encoding="utf-8")
    assert "Integrity: text unchanged" in r.stdout, r.stdout + r.stderr
    # the strict gate: letters AND spacing against the source (the checks above ignore
    # whitespace); joining a paragraph's sentences must not add a space the source lacks
    source = json.loads((work / "state.json").read_text(encoding="utf-8"))["source"]
    v = subprocess.run([PY, "-X", "utf8", str(HERE / "verify_text.py"), source, str(final), "--fix"],
                       capture_output=True, text=True, encoding="utf-8")
    assert v.returncode == 0, v.stdout + v.stderr
    print("   " + v.stdout.strip().splitlines()[-1])
    sizes = [z - a + 1 for a, z in groups]
    if types and "S" in types:
        para = [z - a + 1 for a, z in groups if kind(a) == "S"]
        st = [z - a + 1 for a, z in groups if kind(a) != "S"]
        print(f"{final}: {len(para)} paragraphs (sentences per paragraph: "
              + ", ".join(f"{s} ×{para.count(s)}" for s in sorted(set(para))) + f") · {len(st)} stanzas"
              + (" (" + ", ".join(f"{s} lines ×{st.count(s)}" for s in sorted(set(st))) + ")" if st else ""))
        return
    print(f"{final}: {len(groups)} stanzas — " + ", ".join(f"{s} lines ×{sizes.count(s)}" for s in sorted(set(sizes))))


# ── toc-ingest / group-split / group-join ────────────────────────────────────

def toc_ingest(work, tree):
    """Put the anchored tree's headings into the segmented text: re-derive the units from
    the source with the settings segment stored, now with the tree."""
    state = json.loads((work / "state.json").read_text(encoding="utf-8"))
    prepare(Path(state["source"]), work, tree, state.get("front_title", "ཀླད་ཀྱི་དོན།"),
            state.get("body_title", "གཞུང་དངོས།"), state["form"])


def group_split(work, max_lines=750):
    """group-in.md → group-in-partN.md, cut only before a heading or after a ¶ line, each
    part at least max_lines − 150 lines (a part with no units joins the one before)."""
    mode = json.loads((work / "state.json").read_text(encoding="utf-8"))["modes"][0]
    lines = (work / "group-in.md").read_text(encoding="utf-8").split("\n")
    if len(lines) <= max_lines:
        print(f"{len(lines)} lines — no split needed: one subagent on group-in.md → groups-{mode}.json")
        return
    parts, cur = [], []
    for l in lines:
        if l.startswith("##") and len(cur) >= max_lines - 150:
            parts.append(cur)
            cur = []
        cur.append(l)
        if l.startswith("¶") and len(cur) >= max_lines - 150:
            parts.append(cur)
            cur = []
    if cur:
        parts.append(cur)
    unit = re.compile(r"[PSV](\d+)  ")
    merged = []
    for p in parts:
        if merged and not any(unit.match(l) for l in p):
            merged[-1] += p
        else:
            merged.append(p)
    for old in work.glob("group-in-part*.md"):
        old.unlink()
    for k, p in enumerate(merged, 1):
        nums = [int(m.group(1)) for l in p for m in [unit.match(l)] if m]
        (work / f"group-in-part{k}.md").write_text("\n".join(p).strip() + "\n", encoding="utf-8")
        print(f"group-in-part{k}.md: units {nums[0]}–{nums[-1]} → groups-{mode}-part{k}.json")


def group_join(work):
    mode = json.loads((work / "state.json").read_text(encoding="utf-8"))["modes"][0]
    parts = sorted(work.glob(f"groups-{mode}-part*.json"),
                   key=lambda p: int(re.search(r"part(\d+)", p.name).group(1)))
    if not parts:
        sys.exit(f"no groups-{mode}-part*.json in {work}")
    stanzas, notes = [], {}
    for p in parts:
        j = json.loads(p.read_text(encoding="utf-8"))
        stanzas += j["stanzas"]
        notes.update({str(k): v for k, v in j.get("notes", {}).items()})
    (work / f"groups-{mode}.json").write_text(json.dumps({"stanzas": stanzas, "notes": notes},
                                                         ensure_ascii=False), encoding="utf-8")
    print(f"groups-{mode}.json: {len(stanzas)} blocks from {len(parts)} parts")


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if not a:
        sys.exit(__doc__)
    if a[0] == "classify":
        sys.exit(classify(Path(a[1])))
    elif a[0] in ("segment", "prepare"):
        t = opt("--tree") if a[0] == "prepare" else None
        prepare(Path(a[1]), Path(a[2]), Path(t) if t else None,
                opt("--front-title", "ཀླད་ཀྱི་དོན།"), opt("--body-title", "གཞུང་དངོས།"),
                opt("--form", "auto"))
    elif a[0] == "toc-ingest":
        if not opt("--tree"):
            sys.exit("toc-ingest needs --tree <anchored tree.md> (no tree: skip this step)")
        toc_ingest(Path(a[1]), Path(opt("--tree")))
    elif a[0] == "group-split":
        group_split(Path(a[1]), int(opt("--max-lines", 750)))
    elif a[0] == "group-join":
        group_join(Path(a[1]))
    elif a[0] == "finish":
        finish(Path(a[1]))
    else:
        sys.exit(__doc__)
