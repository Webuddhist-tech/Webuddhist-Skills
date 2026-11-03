"""The human row pairing of an md_rows work, row by row of its own text.

A pair is two docs whose row N goes with row N (`pair.own_side`,
`pair.target_side`). Usually `own_side` is the work's `text` itself, or a
letter-identical copy, so text row N is paired with target-side row N.

`own_side` may also be a *different cut of the same text* (the Diamond Sūtra:
the display Tibetan is the Tibetan side of the Sanskrit pair with its empty
rows dropped and one row cut in three). Its rows are then carried onto the
text's rows by letters (the concordance, as for every other cut — D2): text
row k is paired with the target-side rows of the own-side rows that fall in
it. Rows are never merged or split. The two cuts must hold the same letters.

`pair_corrections` re-pair a row of `own_side` (`row` = its row number there,
which is the text's row number when the two are the same cut).
"""
from concordance import Concordance
from project import is_letter


def _letters(t):
    return "".join(c for c in t if is_letter(c))


def pair_map(text_rows, own_rows, tgt_rows, corrections=None, min_overlap=3):
    """text_rows / own_rows / tgt_rows: [(row:int, text)].
    Returns ({text row: {"own": [own rows], "human": [target rows as paired],
    "rows": [target rows after corrections], "corrections": [the corrections
    applied]}}, [correction rows that name no own-side row], stats)."""
    tl = {int(r): t for r, t in text_rows if _letters(t)}
    ol = {int(r): t for r, t in own_rows if _letters(t)}
    stats = {"own_side": "same cut"}
    if set(tl) == set(ol) and all(_letters(tl[k]) == _letters(ol[k]) for k in tl):
        own_of = {k: [k] for k in tl}
    else:
        conc = Concordance([(str(k), t) for k, t in tl.items()], list(ol.items()), min_overlap=min_overlap)
        st = conc.stats
        if st["copy_only"] or st["replaced"] or st["ratio"] < 0.99:
            raise ValueError(f"pair.own_side is not the same text as text (concordance {st})")
        own_of = {k: [] for k in tl}
        for r in ol:
            for d in conc.row(r)["targets"]:
                own_of[int(d)].append(r)
        stats = {"own_side": "another cut of the same text, carried by letters", "concordance": st}
    tg = {int(r) for r, t in tgt_rows if _letters(t)}
    corr = {int(c["row"]): c for c in corrections or []}
    used, out = set(), {}
    for k, owns in own_of.items():
        human, rows, applied = [r for r in owns if r in tg], [], []
        for r in owns:
            if r in corr:
                used.add(r)
                applied.append(corr[r])
                rows += [int(x) for x in corr[r].get("target_side_rows") or [] if int(x) not in rows]
            elif r in tg and r not in rows:
                rows.append(r)
        out[k] = {"own": owns, "human": human, "rows": rows, "corrections": applied}
    return out, sorted(set(corr) - used), stats
