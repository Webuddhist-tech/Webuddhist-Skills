"""Functional-unit layout for Tibetan verse commentaries (segment_commentary.py --units).

Human-edited commentary files in the rails vaults do not cut prose into ~40-syllable
sentences. They cut a verse commentary into its *functional units*:

  OPENER       the division announcement(s) and/or the lemma opener that
               introduces the next quoted root verse:
                 "<topic> ལ་གསུམ། A། B། C་འོ། །དང་པོ་ནི།"   (enumeration + first opener)
                 "གཉིས་པ་<title>་ནི།"                         (sibling opener)
  ROOT QUOTE   the quoted root stanza (or the one/two/five pādas quoted), one block
  EXPLANATION  the whole gloss that follows ("ཞེས་པ་སྟེ། …") up to the next opener,
               quote or heading — internal sentence ends are NOT block boundaries

plus the frame: the namo homage line, the author's own verses, the dedication
verses (each stanza a block) and the colophon (one block).

This module takes the structural-mode blocks (every candidate boundary already cut)
and *only merges* them back into units, except for two kinds of extra cut it may
add: a root-verse quotation found inside a prose block (when --root is given), and
the namo homage line. Every merge re-reads the original source text between the
blocks, so the source's own whitespace (e.g. "། །") is preserved exactly.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

TSHEG = "་"
SHAD = "།"
NYIS_SHAD = "༎"
SHAD_CLUSTER_RE = re.compile(r"[།༎](?:[\s་]*[།༎])*")
WS_RE = re.compile(r"\s+")

NUM = r"(?:གཉིས|གསུམ|བཞི|ལྔ|དྲུག|བདུན|བརྒྱད|དགུ|བཅུ(?:་(?:གཅིག|གཉིས|གསུམ|བཞི|ལྔ|དྲུག|བདུན|བརྒྱད|དགུ))?|ཉི་ཤུ)"
ORD = (r"(?:དང་པོ|གཉིས་པ|གསུམ་པ|བཞི་པ|ལྔ་པ|དྲུག་པ|བདུན་པ|བརྒྱད་པ|དགུ་པ|བཅུ་པ|"
       r"བཅུ་གཅིག་པ|བཅུ་གཉིས་པ|བཅུ་གསུམ་པ|བཅུ་བཞི་པ|བཅོ་ལྔ་པ|བཅུ་དྲུག་པ|བཅུ་བདུན་པ|"
       r"བཅོ་བརྒྱད་པ|བཅུ་དགུ་པ|ཉི་ཤུ་པ)")
# a block that opens a node: "(གཉིས་པ་" / "དང་པོ་ནི" / "གསུམ་པ་ལ་"
OPENER_RE = re.compile(r"^\(?" + ORD + r"[་\s)]")
FIRST_OPENER_RE = re.compile(r"^\(?དང་པོ[་\s)]")
# a division announcement anywhere in the block: "…ལ་གསུམ།", "…དང་གཉིས།", "ལ་དྲུག །"
ENUM_RE = re.compile(r"(?:ལ|དང|ལས|སྟེ)[་\s]*" + NUM + r"(?:[་\s]*(?:ཡོད[་\s]*(?:དེ|པ)?[་\s]*)?[།༎]|\s)")
NAMO_RE = re.compile(r"^(?:ན་མོ|ནཱ་མོ|ན་མཿ|ན་མ་)")
LEMMA_RE = re.compile(r"(?:ནི|ན)[\s་]*[།༎]\s*$")      # "…ནི།" introduces a quoted lemma
QUOTE_CLOSE_RE = re.compile(r"^\s*(?:ཞེས|ཅེས|ཤེས)[་\s]")
# a finished sentence: final particle in -o ("…པའོ། །", "…སོ།", "…ཏོ།")
SENT_END_RE = re.compile(r"ོ[\s་]*[།༎][\s།༎]*$")
# a short question that asks about the sentence just closed: "…ལོ། །གང་ལ་ན།"
INTERROG_RE = re.compile(r"^\(?(?:གང་ལ|གང་གི|གང་དུ|གང་ཞེ|ཅི|ཅིའི|ཇི|སུ|དེ་ཅི|དེ་ཡང་གང)[^།༎]{0,40}?"
                         r"(?:ན|ཅེ་ན|ཞེ་ན|སྙམ་ན)[་\s]*[།༎]")
# v1.1 (--enum-chain broad): a block whose LAST sentence closes on a count or on a
# "from these / of these" particle also announces children:
#   "… ཕྱག་འཚལ་བ་གཉིས།"  "… གཉིས་ལས།"  "… བཞི་ལས།"  "… ཡོད་པ་ལས།"  "… མཛད་པ་ལ།"
ENUM_END_RE = re.compile(r"(?:" + NUM + r"(?:[་\s]*(?:ལས|ཡོད(?:་པ)?(?:་ལས)?|སོ|སྟེ|ཏེ))?|ལས|[^་\s།]་ལ)[་\s]*[།༎]\s*$")
# v1.3 (--colophon-guard): a "ཞེས/ཅེས …" block that names the author / the act of
# composing starts the colophon — it is not a quotative continuation
COLOPHON_RE = re.compile(r"(?:འདི་ནི|འདི་ཡང|མིང་པས|མིང་གིས|(?:པས|ཡིས|ཀྱིས|གྱིས|གིས|ས)[་\s]*(?:སོ|སྦྱར|བྲིས|སྨྲས|གསུངས|བགྱིས|བཀོད|མཛད))")
# frame lead-ins that always start their own block: the author's "it is said:"
# before the closing verses
FRAME_LEADIN_RE = re.compile(r"^(?:སྨྲས་པ|སྨྲས་པ་ནི|བརྗོད་པ)[་\s]*[།༎]")


def canon(s: str) -> str:
    """Letters only: drop whitespace, tsheg, shads, brackets — for fuzzy quote matching."""
    return re.sub(r"[\s་།༎༑༔()\[\]]", "", s)


def syl(s: str) -> int:
    return len(re.findall(r"[ཀ-ྼ]+", s))


def clause_units(text: str):
    """(start, end) spans of shad-terminated clauses in `text` (tail kept with last)."""
    spans, last = [], 0
    for m in SHAD_CLUSTER_RE.finditer(text):
        if text[last:m.end()].strip():
            spans.append((last, m.end()))
        last = m.end()
    if text[last:].strip():
        if spans:
            spans[-1] = (spans[-1][0], len(text))
        else:
            spans.append((last, len(text)))
    return spans


# ── root text ────────────────────────────────────────────────────────────────

def load_root_padas(path: str | Path):
    """Return the root text's pādas in order as (canonical string, solo, first) triples;
    solo = the pāda is a whole root block by itself (e.g. an opening homage line);
    first = the pāda opens its root block (a stanza's first line)."""
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    padas = []
    for para in re.split(r"\n\s*\n", text):
        s = para.strip()
        if not s or s.startswith("#") or s.startswith("!["):
            continue
        s = re.sub(r"\s*\^[\w-]+\s*$", "", s)
        cl = [canon(s[a:b]) for a, b in clause_units(s)]
        cl = [c for c in cl if len(c) >= 6]
        for k, c in enumerate(cl):
            padas.append((c, len(cl) == 1, k == 0))
    return padas


class RootMatcher:
    def __init__(self, padas, threshold=0.8):
        self.padas = [p if isinstance(p, str) else p[0] for p in padas]
        self.solo = [False if isinstance(p, str) else p[1] for p in padas]
        self.first = [False if isinstance(p, str) or len(p) < 3 else p[2] for p in padas]
        self.t = threshold

    def match(self, unit_text: str):
        """Index of the best-matching root pāda, or None."""
        c = canon(unit_text)
        if len(c) < 8:
            return None
        best, best_r = None, 0.0
        for i, p in enumerate(self.padas):
            if abs(len(p) - len(c)) > max(6, 0.35 * len(p)):
                continue
            r = SequenceMatcher(None, c, p, autojunk=False).ratio()
            if r > best_r:
                best, best_r = i, r
        return best if best_r >= self.t else None


# ── span bookkeeping ─────────────────────────────────────────────────────────

def realign(pieces, body):
    """Map each piece (whitespace may differ) to its (start, end) span in `body`."""
    spans, pos = [], 0
    for piece in pieces:
        sq = WS_RE.sub("", piece)
        # skip whitespace in body
        while pos < len(body) and body[pos].isspace():
            pos += 1
        start, k = pos, 0
        while k < len(sq):
            if pos >= len(body):
                raise ValueError("realign: ran past end of body")
            ch = body[pos]
            if ch.isspace():
                pos += 1
                continue
            if ch != sq[k]:
                raise ValueError(f"realign mismatch at body {pos}: {body[pos:pos+20]!r} vs {sq[k:k+20]!r}")
            pos += 1
            k += 1
        spans.append((start, pos))
    return spans


# ── unitize ──────────────────────────────────────────────────────────────────

def unitize(blocks, body, root: RootMatcher | None = None, max_syl: int = 300, report=None,
            enum_chain: str = "strict", quotes: str = "separate", colophon_guard: bool = False,
            stanza_breaks: bool = False):
    """blocks: list of (kind, text) with kind in {'H','V','P'} in document order,
    covering `body` (the source text without frontmatter) completely.
    Returns a list of block strings for output."""
    report = report if report is not None else []
    texts = [t for _, t in blocks]
    spans = realign(texts, body)
    items = [{"kind": k, "s": s, "e": e} for (k, _), (s, e) in zip(blocks, spans)]

    def text_of(it):
        return body[it["s"]:it["e"]]

    # 1. split root-verse quotations and the namo line out of prose blocks
    out = []
    for it in items:
        if it["kind"] == "V" and stanza_breaks and root is not None:
            # a detected stanza that runs into the first line of the next root
            # stanza (the scanner paired a closing sentence with the next quote)
            # is cut there
            t = text_of(it)
            us = clause_units(t)
            at = [us[i][0] for i in range(1, len(us))
                  if (m := root.match(t[us[i][0]:us[i][1]])) is not None and root.first[m]
                  and not LEMMA_RE.search(t[us[i - 1][0]:us[i - 1][1]])]
            for x, y in zip([0] + at, at + [len(t)]):
                piece = {"kind": "V", "s": it["s"] + x, "e": it["s"] + y, "stanza": x in at}
                pu = clause_units(t[x:y])
                if at and x == 0 and all(root.match(t[x:y][a:b]) is None for a, b in pu):
                    # the sentence the scanner paired with the quote is the end of
                    # the explanation before it: it goes back there
                    piece.update(kind="P", join=True)
                out.append(piece)
            if at:
                report.append({"trigger": "stanza-break", "syllables": 0, "flag": "",
                               "preview": t[at[0]:at[0] + 80].strip()})
            continue
        if it["kind"] != "P":
            out.append(it)
            continue
        t = text_of(it)
        cuts = []  # (rel_start, rel_end, kind)
        m = NAMO_RE.match(t.lstrip())
        if m:
            us = clause_units(t)
            if len(us) > 1:
                cuts.append((0, us[0][1], "P"))
        breaks = []   # v1.4 (--stanza-breaks): positions where a quoted stanza begins
        if root is not None:
            us = clause_units(t)
            idx = [root.match(t[a:b]) for a, b in us]
            if stanza_breaks:
                # a quoted first line of a root stanza starts a new block when it
                # follows a finished sentence ("…པའོ། །"); after a lead-in "…ནི།" or
                # inside a sentence ("… ལ།", "… སྟེ།") it stays where it is
                for i in range(1, len(us)):
                    if (idx[i] is not None and root.first[idx[i]]
                            and SENT_END_RE.search(t[us[i - 1][0]:us[i - 1][1]])):
                        breaks.append(us[i][0])
                        report.append({"trigger": "stanza-break", "syllables": 0, "flag": "",
                                       "preview": t[us[i][0]:us[i][1]].strip()[:80]})
            # what precedes this prose block (for a quote that opens the block)
            prev_txt = text_of(out[-1]) if out and out[-1]["kind"] == "P" else ""
            prev_is_lemma = (not prev_txt) or bool(LEMMA_RE.search(prev_txt))
            # a block that itself opens with a stanza's first line starts a unit too
            if (stanza_breaks and us and idx[0] is not None and root.first[idx[0]]
                    and (not prev_txt or SENT_END_RE.search(prev_txt))):
                breaks.insert(0, 0)
            # last root pāda of an immediately preceding verse block (to continue it)
            prev_root = None
            if out and out[-1]["kind"] == "V":
                pv = text_of(out[-1])
                pu = clause_units(pv)
                prev_root = root.match(pv[pu[-1][0]:pu[-1][1]]) if pu else None
            i = 0
            while i < len(us):
                if idx[i] is None:
                    i += 1
                    continue
                j = i + 1
                while j < len(us) and idx[j] is not None and idx[j] == idx[j - 1] + 1:
                    j += 1
                run_len = j - i
                # A lemma quotation is introduced ("…ནི།" or a block/heading start)
                # and closed (block end or "ཞེས/ཅེས …"). Pādas quoted inside a gloss
                # are not cut out.
                opens = (prev_is_lemma if i == 0 else bool(LEMMA_RE.search(t[us[i - 1][0]:us[i - 1][1]])))
                closes = (j == len(us)) or bool(QUOTE_CLOSE_RE.match(t[us[j][0]:]))
                # one pāda alone is cut only when it is a whole root block by itself;
                # glossators who quote pāda-by-pāda keep lemma and gloss together
                whole = run_len >= 2 or root.solo[idx[i]]
                # the rest of a root verse whose first pādas were already peeled
                # out as a stanza (e.g. a 5-pāda verse cut 4 + 1)
                continues = i == 0 and prev_root is not None and idx[i] == prev_root + 1
                if (opens and closes and whole) or continues:
                    cuts.append((us[i][0], us[j - 1][1], "V"))
                    report.append({"trigger": "root-quote", "syllables": syl(t[us[i][0]:us[j-1][1]]),
                                   "flag": "", "preview": t[us[i][0]:us[j-1][1]].strip()[:80]})
                i = j
        if not cuts and not breaks:
            out.append(it)
            continue
        cuts.sort()
        pieces, pos = [], 0
        for a, b, k in cuts:
            if a < pos:
                continue
            if t[pos:a].strip():
                pieces.append(("P", pos, a))
            pieces.append((k, a, b))
            pos = b
        if t[pos:].strip():
            pieces.append(("P", pos, len(t)))
        for k, a, b in pieces:
            # a prose piece is cut again at every stanza break inside it; a piece
            # (prose or verse) that begins at a break is marked so no later merge
            # joins it to the block before
            cut_at = [x for x in breaks if a < x < b] if k == "P" else []
            for x, y in zip([a] + cut_at, cut_at + [b]):
                if t[x:y].strip():
                    out.append({"kind": k, "s": it["s"] + x, "e": it["s"] + y,
                                "stanza": x in breaks})
    items = out

    # 2. a short verse fragment (≤2 pādas) that continues the preceding verse in the
    #    root order is the same quotation (e.g. a 5-pāda root verse cut 4+1)
    if root is not None:
        merged = []
        for it in items:
            if (it["kind"] == "V" and merged and merged[-1]["kind"] == "V"):
                prev_units = clause_units(text_of(merged[-1]))
                cur_units = clause_units(text_of(it))
                if len(cur_units) <= 2:
                    a = root.match(text_of(merged[-1])[prev_units[-1][0]:prev_units[-1][1]])
                    b = root.match(text_of(it)[cur_units[0][0]:cur_units[0][1]])
                    if a is not None and b is not None and b == a + 1:
                        merged[-1] = {"kind": "V", "s": merged[-1]["s"], "e": it["e"]}
                        continue
            merged.append(it)
        items = merged

    # 2b. with a root text, a ≤2-pāda "stanza" that is not a root quotation is a
    #     false stanza detection inside prose (two uniform clauses ending "། །")
    if root is not None:
        for it in items:
            if it["kind"] == "V":
                us = clause_units(text_of(it))
                if len(us) <= 2 and all(root.match(text_of(it)[a:b]) is None for a, b in us):
                    it["kind"] = "P"
                    report.append({"trigger": "verse-demoted", "syllables": syl(text_of(it)),
                                   "flag": "", "preview": text_of(it).strip()[:80]})

    # 2c. v1.2 (--quotes inline): editors who keep the quoted root verse inside the
    #     explanation — a verse block made of root pādas is turned back into prose
    #     and joined to the block before and the block after it
    if quotes == "inline" and root is not None:
        for n, it in enumerate(items):
            if it["kind"] == "V":
                us = clause_units(text_of(it))
                if any(root.match(text_of(it)[a:b]) is not None for a, b in us):
                    it["kind"] = "Q"
                    # --stanza-breaks: a quote that opens a stanza stays inline with its
                    # explanation but does not join the block before (unless "…ནི།")
                    first = root.match(text_of(it)[us[0][0]:us[0][1]]) if us else None
                    prev = text_of(items[n - 1]) if n and items[n - 1]["kind"] == "P" else ""
                    if (stanza_breaks and first is not None and root.first[first]
                            and (it.get("stanza") or not prev or SENT_END_RE.search(prev))):
                        it["stanza"] = True
                    report.append({"trigger": "quote-inline", "syllables": syl(text_of(it)),
                                   "flag": "", "preview": text_of(it).strip()[:80]})

    # 3. merge prose into functional units
    units = []
    force_next = False
    for it in items:
        if it.get("join") and units and units[-1]["kind"] == "P":
            cur = units[-1]
            cur.setdefault("parts", [(cur["s"], cur["e"])])
            cur["parts"].append((it["s"], it["e"]))
            cur["e"] = it["e"]
            cur["last"] = it["s"]
            continue
        if it["kind"] == "Q":
            it = dict(it, kind="P")
            if units and units[-1]["kind"] == "P" and not it.get("stanza"):
                cur = units[-1]
                if "parts" not in cur:
                    cur["parts"] = [(cur["s"], cur["e"])]
                cur["parts"].append((it["s"], it["e"]))
                cur["e"] = it["e"]
                cur["last"] = it["s"]
            else:
                units.append(dict(it))
            force_next = True
            continue
        if (force_next and it["kind"] == "P" and units and units[-1]["kind"] == "P"
                and not it.get("stanza")):
            force_next = False
            t0 = text_of(it).lstrip()
            if not (OPENER_RE.match(t0) or FRAME_LEADIN_RE.match(t0) or NAMO_RE.match(t0)):
                cur = units[-1]
                cur.setdefault("parts", [(cur["s"], cur["e"])])
                cur["parts"].append((it["s"], it["e"]))
                cur["e"] = it["e"]
                cur["last"] = it["s"]
                continue
        force_next = False
        if (it["kind"] in ("H", "V") or not units or units[-1]["kind"] in ("H", "V")
                or it.get("stanza")):
            units.append(dict(it))
            continue
        t = text_of(it).lstrip()
        cur = units[-1]
        cur_text = body[cur["s"]:cur["e"]]
        # Merge only on a positive linguistic signal; every other structural
        # cut is kept (semantic merges are commentary-resegment's job).
        if NAMO_RE.match(t) or FRAME_LEADIN_RE.match(t) or NAMO_RE.match(cur_text.lstrip()):
            merge = False
        elif FIRST_OPENER_RE.match(t) and (
                ENUM_RE.search(body[cur.get("last", cur["s"]):cur["e"]])
                or (enum_chain == "broad" and ENUM_END_RE.search(body[cur.get("last", cur["s"]):cur["e"]]))):
            merge = True          # "…ལ་གསུམ། A B C་འོ། །" + "དང་པོ་ནི།" — one opener unit
        elif (colophon_guard and QUOTE_CLOSE_RE.match(t) and it["s"] > 0.8 * len(body)
              and COLOPHON_RE.search(t[:300])):
            merge = False         # "ཞེས་ <work> འདི་ནི། … གྱིས་ … སྦྱར་བའོ།" — the colophon starts here
        elif INTERROG_RE.match(t):
            merge = True          # "ཕྱག་འཚལ་ལོ། །" + "གང་ལ་ན། …" — the question continues it
        elif QUOTE_CLOSE_RE.match(t):
            merge = True          # "ཞེས/ཅེས …" quotes the words just before it
        else:
            merge = False
        new_unit = not merge
        if new_unit:
            units.append(dict(it))
        else:
            if "parts" not in cur:
                cur["parts"] = [(cur["s"], cur["e"])]
            cur["parts"].append((it["s"], it["e"]))
            cur["e"] = it["e"]
            cur["last"] = it["s"]

    # 4. safety valve: an over-long prose unit falls back to its structural cuts,
    #    greedily re-grouped so each piece stays under max_syl
    final = []
    for u in units:
        if u["kind"] == "P" and max_syl and "parts" in u and syl(body[u["s"]:u["e"]]) > max_syl:
            subs = u["parts"]
            start, end = subs[0]
            for a, b in subs[1:]:
                if syl(body[start:b]) > max_syl:
                    final.append({"kind": "P", "s": start, "e": end})
                    start = a
                end = b
            final.append({"kind": "P", "s": start, "e": end})
            report.append({"trigger": "unit-over-cap", "syllables": syl(body[u["s"]:u["e"]]),
                           "flag": "STAGE2_REVIEW", "preview": body[u["s"]:u["s"] + 80].strip()})
        else:
            final.append(u)

    blocks_out = []
    for u in final:
        t = body[u["s"]:u["e"]].strip()
        if u["kind"] == "V":
            us = clause_units(t)
            t = "\n".join(t[a:b].strip() for a, b in us)
        blocks_out.append(t)
    return blocks_out
