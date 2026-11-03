#!/usr/bin/env python3
"""gm_translate_commentary.py — block-aligned Gemini translation of a COMMENTARY note.

A sibling of gm_translate.py for a different source shape. gm_translate.py
translates a line-by-line liturgy from the Tibetan root text; this script
translates a block-ID'd commentary (prose paragraphs, verse quotations,
headings at any depth, root-text transclusions, footnotes) from whatever
language the commentary is written in — e.g. the English commentary into
Traditional Chinese for Taiwan.

Same contract as the machine-translate skill:
  * Gemini returns STRUCTURED output — {"blocks": [{"id", "lines": [...]}]} under
    a response schema — so the response is split by block and by line without
    guessing. Ids must come back identical and in order.
  * Line parity: every block's line count must equal the source's (a verse keeps
    its lines; a paragraph stays one line). Footnote markers ([^n]) in a source
    block must all come back in its translation. A block that fails either
    check is re-run alone, up to --attempts times, and recorded with the failure
    flagged if it never passes — never padded or trimmed.
  * Script guard (--script traditional): output containing Simplified-only
    characters counts as a failed check and is re-run the same way.
  * Append-only ledger (<track>/work/<stem>.jsonl); the newest record per unit
    wins at render time, so any run resumes and any block can be redone with
    --force --only <ids>.
  * <track>/style.md is seeded once and then read back VERBATIM as the system
    prompt, followed by the fixed output contract. Edit the file, not the script.

Rendered output (translation-upload shape, as the other commentary tracks):
frontmatter; the H1 and every heading translated, keeping its block ID; each
body block as a transclusion of the SOURCE commentary's block, a blank line,
and the translation ending in the same ` ^id`. The source's root-text
transclusions are not carried over (this file aligns to the source commentary,
block for block). Footnote markers stay in place and the notes are translated
at the end; the parsers exclude both from the published edition.

Three kinds of unit, three passes (each resumable):
  (default)   body blocks, in batches of adjacent blocks with rolling context
  --headings  the H1 and all headings, in one call
  --notes     the footnote notes, in one call

Needs GEMINI_API_KEY in the environment (source ~/.zshrc). Stdlib only.

Usage (from the vault root):
  gm_translate_commentary.py --source <commentary.md> --list
  gm_translate_commentary.py --source <commentary.md> --dry-run --limit 3
  gm_translate_commentary.py --source <commentary.md> --limit 6          # pilot
  gm_translate_commentary.py --source <commentary.md>                    # all blocks
  gm_translate_commentary.py --source <commentary.md> --headings
  gm_translate_commentary.py --source <commentary.md> --notes
  gm_translate_commentary.py --source <commentary.md> --render-only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.1-pro-preview"
KEY_ENV = "GEMINI_API_KEY"
RATE_LIMIT_BACKOFF = [10, 20, 40, 60, 120, 180]
DAILY_LIMIT_RE = re.compile(r"per[\s_]*day|PerDay|daily", re.I)

BLOCK_ID_RE = re.compile(r"\s\^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s*$")
TRANSCLUSION_RE = re.compile(r"^\s*!\[\[.*\]\]\s*$")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]\s]+)\]:\s*(.*)$")
FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]\s]+\](?!:)")

# Characters written differently in Simplified Chinese. Any of these in the
# output means the model slipped out of Traditional script.
# 首 and 后 were removed: 首 is written the same in both scripts, and 后 is a
# Traditional character in its own right (王后, "queen"), not only the
# Simplified form of 後.
SIMPLIFIED_ONLY = set(
    "们这说来为与对于时会个无语经认显净观赞礼圣萨罗满养业灵门学应当从后种间乐愿诵谁点实证还见现发变并义过边头万恼归导众卫"
    "么国东车长马鸟鱼龙问间开关见贝页风飞饭钱铁银错钟书买卖读写让谈请讲论记设诸调谓识译议该详语误说课"
    "觉亲视览赏齿龄岁历压厅厉厌县园围图团圆场坏块坚坛声处备复够头夺奋奖妇妈娱婴宁宝实宫审宽宾对寻导寿将尔尘尝"
    "层属岂岭峡币师帐带帮广庄庆库应庙废开异弃张弥弯弹强归当录彻径忆忧怀态总恋恶悦悬惊惧惨惯愤忏戏战户扑执扩扫扬扰抚抢护报担拟拥择挂"
    "挡挤挥换损据掷摄摆摇携数断无旧时旷昼显晓晕暂术机杀杂权条来杨极构枪柜标栏树样桥梦检楼欢欧毁气汇汉污汤沟没沦沧泪泽洁浅浆测济浓涂涛润涨渊渐渔湾湿满滥滞滤灭灯灵灾炉点炼烂烛烟烦烧热爱爷牵犹状独狭狮猎献环现玛珑琐电画畅疗疮疯痒瘫盏盐监盖盘着睁矫矿码砖础确碍礼祸禅离种积称稳穷窃窍竞笔笼筑签简粮纠红约级纪纯纲纳纵纷纸纹线练组细织终绍经绑结绕绘给络绝统继绩绪续维绵综绿缓编缘缚缠缩网罗罚罢羡习联聪肃胁胆胜脉脑脚脱脸舍艰艺节苏苹范茎荐荡药莲获营萝萧葱蓝虑虚虫虽蚀补衬袭装见观规视览觉触誉计认讨让训议讯记讲许论讼设访证评识诉诊词译试诗诚话诞询该详诫语误诱说请诸读课谁调谅谈谊谋谓谜谢谨谱贝负贡财责贤败货质贩贪贫购贯贱贴贵贷贸费贺贼资赋赌赏赐赔赖赚赛赞赠赢赶趋跃践踪轨轩转轮软轰轻载较辅辆辈辉辑输辞辩边达迁过迈运还这进远违连迟适选逊递逻遗邓邮邻郑酱释针钓钢钥钱铁铃铜铭银铺链销锁锅锋错锦键锻镇镜长门闪闭问闯闲间闷闹闻阀阅队阳阴阵阶际陆陈险随隐难雾静韩页顶项顺须顽顾顿预领频题颜额风飘飞饥饮饰饱饲馆馈首驱驶驻驾验骂骑骗骤骨鲜鸣鸭鸿鹅鹤麦黄齐龟"
) - set("首后")

OUTPUT_CONTRACT = """

OUTPUT CONTRACT (strict; this is transport, not style):
- You receive a JSON object {"blocks": [{"id": ..., "lines": [...]}]}: the source lines of one or more consecutive units of the same text.
- Return a JSON object of exactly the same shape, with the SAME ids in the SAME order, and nothing else.
- For every unit, output EXACTLY as many lines as the source unit has. Line k of your output translates line k of the source and nothing else. Never merge, split, reorder, drop or add lines, and never leave a line empty.
- Keep every footnote marker such as [^3] exactly as written, attached to the word or phrase it follows in the source.
- A line is translation only: no line numbers, no source text, no notes of your own, no markdown."""

PARITY_CLAUSE = ("\n\nThis single unit has exactly {n} source line(s). Your \"lines\" array for it "
                 "must contain exactly {n} string(s), one per source line, in order.")
MARKER_CLAUSE = "\n\nThe source of this unit contains the footnote marker(s) {m}; each must appear exactly once in your translation."
SCRIPT_CLAUSE = ("\n\nYour previous answer used Simplified Chinese characters ({c}). Write ONLY Traditional "
                 "characters as used in Taiwan.")
HEADINGS_CLAUSE = ("\n\nThese units are the title and section headings of the text. Translate each as a short "
                   "heading: one line, no sentence-final punctuation, no numbering.")
NOTES_CLAUSE = "\n\nThese units are the translator's footnotes to the text. Translate each as one line."

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"blocks": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "lines": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "lines"]}}},
    "required": ["blocks"],
}
SAFETY_OFF = [{"category": c, "threshold": "BLOCK_NONE"} for c in (
    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT")]


class ApiStop(RuntimeError):
    pass


class BadResponse(RuntimeError):
    pass


# ---------------------------------------------------------------- source


def parse_source(path):
    """-> (frontmatter text, frontmatter dict, units).

    unit kinds: heading {id, level, lines:[text]}, block {id, lines, heading},
    note {id: 'fn-<n>', n, lines:[text]}. Transclusions are skipped (root-text
    navigation, not commentary content).
    """
    import yaml
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n", raw, re.S)
    fm_text, body = (m.group(1), raw[m.end():]) if m else ("", raw)
    fm = yaml.safe_load(fm_text) or {}
    units, buf, heading = [], [], None

    def flush():
        nonlocal buf
        lines = [l.strip() for l in buf if l.strip()]
        buf = []
        if not lines:
            return
        mm = BLOCK_ID_RE.search(lines[-1])
        if not mm:
            raise SystemExit(f"block without an ID in the source: {lines[0][:60]!r}")
        lines[-1] = lines[-1][: mm.start()].rstrip()
        units.append({"kind": "block", "id": mm.group(1), "lines": lines, "heading": heading})

    for line in body.split("\n"):
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("#"):
            flush()
            mm = BLOCK_ID_RE.search(s)
            text = s[: mm.start()].rstrip() if mm else s
            level = len(text) - len(text.lstrip("#"))
            text = text.lstrip("#").strip()
            heading = text if level >= 2 else heading
            units.append({"kind": "heading", "id": mm.group(1) if mm else "title",
                          "level": level, "lines": [text]})
            continue
        if TRANSCLUSION_RE.match(s):
            flush()
            continue
        fn = FOOTNOTE_DEF_RE.match(s)
        if fn:
            flush()
            units.append({"kind": "note", "id": f"fn-{fn.group(1)}", "n": fn.group(1), "lines": [fn.group(2)]})
            continue
        buf.append(line)
    flush()
    return fm_text, fm, units


# ---------------------------------------------------------------- ledger


def load_ledger(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def latest(ledger):
    out = {}
    for r in ledger:
        out[(r["kind"], r["id"])] = r
    return out


# ---------------------------------------------------------------- gemini


def build_request(units, context, args, extra=""):
    system = args.style.strip() + OUTPUT_CONTRACT + extra
    payload = json.dumps({"blocks": [{"id": u["id"], "lines": u["lines"]} for u in units]},
                         ensure_ascii=False, indent=1)
    user = ((context + "\n\n") if context else "") + \
        f"Translate the following unit(s) from {args.source_label} into {args.target_label}. Return JSON only.\n\n" + payload
    gen = {"responseMimeType": "application/json", "responseSchema": RESPONSE_SCHEMA}
    if args.temperature is not None:
        gen["temperature"] = args.temperature
    if args.thinking:
        gen["thinkingConfig"] = {"thinkingLevel": args.thinking}
    return {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen, "safetySettings": SAFETY_OFF}


def call_api(body, args, key):
    url = f"{API_BASE}/{args.model}:generateContent"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last = None
    for attempt in range(1, args.retries + 1):
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": key})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            cands = payload.get("candidates") or []
            if not cands:
                raise BadResponse(f"prompt blocked: {(payload.get('promptFeedback') or {}).get('blockReason')}")
            c = cands[0]
            finish = c.get("finishReason", "")
            text = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []) if "text" in p)
            um = payload.get("usageMetadata") or {}
            info = {"model_version": payload.get("modelVersion", args.model), "finish_reason": finish,
                    "usage": {"prompt_tokens": um.get("promptTokenCount"),
                              "output_tokens": um.get("candidatesTokenCount"),
                              "thinking_tokens": um.get("thoughtsTokenCount")},
                    "elapsed_s": round(time.time() - t0, 2)}
            if finish not in ("STOP", "") or not text.strip():
                raise BadResponse(f"finishReason={finish or '?'}, {len(text)} chars")
            return text, info
        except BadResponse:
            raise
        except urllib.error.HTTPError as exc:
            last = exc
            detail = exc.read().decode("utf-8", "replace")[:600]
            if exc.code == 429:
                if DAILY_LIMIT_RE.search(detail) and "minute" not in detail.lower():
                    raise ApiStop(f"daily quota spent: {detail[:200]} — finished units are saved; resume later")
                wait = RATE_LIMIT_BACKOFF[min(attempt - 1, len(RATE_LIMIT_BACKOFF) - 1)]
                print(f"    ! 429; waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if exc.code in (400, 401, 403, 404):
                raise ApiStop(f"HTTP {exc.code}: {detail}")
            time.sleep(2 ** attempt)
        except Exception as exc:  # noqa: BLE001 — network/parse failures, then back off
            last = exc
            time.sleep(2 ** attempt)
    raise ApiStop(f"generateContent failed after {args.retries} attempts: {last}")


def parse_response(text, units):
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    blocks = data.get("blocks") if isinstance(data, dict) else None
    if not isinstance(blocks, list) or [str(b.get("id")) for b in blocks] != [u["id"] for u in units]:
        return None
    out = {}
    for b in blocks:
        lines = [str(l).strip() for l in (b.get("lines") or []) if str(l).strip()]
        if not lines:
            return None
        out[str(b["id"])] = lines
    return out


def check(unit, lines, args):
    """-> dict of failed checks (empty when the translation is acceptable)."""
    fails = {}
    if len(lines) != len(unit["lines"]):
        fails["line_parity"] = f"{len(lines)} lines for {len(unit['lines'])}"
    want = sorted(FOOTNOTE_REF_RE.findall(" ".join(unit["lines"])))
    got = sorted(FOOTNOTE_REF_RE.findall(" ".join(lines)))
    if want != got:
        fails["footnote_markers"] = f"expected {want}, got {got}"
    if args.script == "traditional":
        bad = sorted({ch for ch in "".join(lines) if ch in SIMPLIFIED_ONLY})
        if bad:
            fails["simplified_chars"] = "".join(bad)
    banned = sorted({w for w in args.forbid if w and w in "".join(lines)})
    if banned:
        fails["forbidden"] = banned
    return fails


# ---------------------------------------------------------------- render


def render(out_md, src_path, fm, units, ledger, args):
    best = latest(ledger)
    stem = src_path.stem
    title_rec = best.get(("heading", next((u["id"] for u in units if u["kind"] == "heading" and u["level"] == 1), "")))
    title = title_rec["lines"][0] if title_rec else fm.get("title", "")
    n_blocks = sum(1 for u in units if u["kind"] == "block")
    done_blocks = sum(1 for u in units if u["kind"] == "block" and ("block", u["id"]) in best)
    n_heads = sum(1 for u in units if u["kind"] == "heading")
    done_heads = sum(1 for u in units if u["kind"] == "heading" and ("heading", u["id"]) in best)
    n_notes = sum(1 for u in units if u["kind"] == "note")
    done_notes = sum(1 for u in units if u["kind"] == "note" and ("note", u["id"]) in best)
    flagged = sorted(r["id"] for r in best.values() if r.get("failed_checks"))
    versions = sorted({r.get("model_version", "") for r in best.values() if r.get("model_version")})

    def q(s):
        return json.dumps(s, ensure_ascii=False)

    front = [
        "---",
        f"title: {q(title)}",
        f"track: Gemini zero-shot ({args.target_label})",
        f"title_original: {q(fm.get('title', ''))}",
        f"language: {args.language_name}",
        f"lang_tag: {args.lang_tag}",
        f"script: {q(args.script_label)}",
        "file_type: translation",
        "track_type: machine-baseline",
        f"root_text: {src_path.as_posix()}",
    ]
    if fm.get("text_id"):
        front += [f"translation_of: {fm['text_id']}", f"translation_of_text_id: {fm['text_id']}"]
    if fm.get("edition_id"):
        front.append(f"translation_of_edition_id: {fm['edition_id']}")
    for k in ("category_id", "license"):
        if fm.get(k):
            front.append(f"{k}: {fm[k]}")
    front += [
        f"translator: {q(', '.join(versions) or args.model)}",
        "source: https://ai.google.dev",
        "edition_type: critical",
        f"source_language: {args.source_label}",
        f"target_language: {q(args.target_label)}",
        f"generator: {q(', '.join(versions) or args.model)}",
        f"style: {(pathlib.Path(args.track) / 'style.md').as_posix()}",
        "rails_used: none",
        f"generated: {_dt.date.today().isoformat()}",
        f"blocks_translated: {done_blocks}",
        f"blocks_total: {n_blocks}",
        f"headings_translated: {done_heads}/{n_heads}",
        f"notes_translated: {done_notes}/{n_notes}",
        f"failed_checks: {q(flagged)}",
        "note: \"Machine baseline — not a rails-governed translation. Raw Gemini output, block-aligned to the source "
        "commentary; untranslated units are omitted. Never mark complete without human review.\"",
        "status: draft",
        "---",
        "",
    ]
    body = []
    for u in units:
        rec = best.get((u["kind"], u["id"]))
        if u["kind"] == "heading":
            text = rec["lines"][0] if rec else None
            if text is None:
                continue
            idpart = f" ^{u['id']}" if u["id"] != "title" else ""
            body += ["#" * u["level"] + " " + text + idpart, ""]
        elif u["kind"] == "block" and rec:
            lines = list(rec["lines"])
            lines[-1] = f"{lines[-1]} ^{u['id']}"
            body += [f"![[{stem}#^{u['id']}]]", ""] + lines + [""]
    notes = [f"[^{u['n']}]: {best[('note', u['id'])]['lines'][0]}" for u in units
             if u["kind"] == "note" and ("note", u["id"]) in best]
    if notes:
        body += notes + [""]
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(front + body), encoding="utf-8")
    return done_blocks, n_blocks, flagged


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="block-ID'd commentary note")
    ap.add_argument("--track", default="3-TRANSFORMATIONS/Translations/Gemini/zh-Hant-TW-commentaries",
                    help="output track folder ($TRANSFORMATIONS/Translations/<engine>/<track>/)")
    ap.add_argument("--source-label", default="English")
    ap.add_argument("--target-label", default="Traditional Chinese (Taiwan)")
    ap.add_argument("--language-name", default="Chinese")
    ap.add_argument("--lang-tag", default="zh")
    ap.add_argument("--script", choices=["traditional", "any"], default="traditional")
    ap.add_argument("--forbid", default="您", type=lambda v: [w for w in v.split(",") if w],
                    help="comma-separated strings the output must not contain (default: 您)")
    ap.add_argument("--script-label", default="Traditional Chinese (Taiwan)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--thinking", choices=["low", "medium", "high"], default=None)
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--headings", action="store_true", help="translate the H1 and all headings")
    ap.add_argument("--notes", action="store_true", help="translate the footnote notes")
    ap.add_argument("--only", default=None, help="comma-separated unit ids")
    ap.add_argument("--limit", type=int, default=None, help="translate at most N units this run")
    ap.add_argument("--force", action="store_true", help="redo units already in the ledger")
    ap.add_argument("--batch-units", type=int, default=4)
    ap.add_argument("--batch-chars", type=int, default=3500)
    ap.add_argument("--context-blocks", type=int, default=3)
    ap.add_argument("--attempts", type=int, default=3, help="solo re-runs for a unit that fails a check")
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args()

    src = pathlib.Path(args.source)
    fm_text, fm, units = parse_source(src)
    track = pathlib.Path(args.track)
    style_path = track / "style.md"
    ledger_path = track / "work" / f"{src.stem}-{args.lang_tag}.jsonl"
    out_md = track / f"{src.stem}-{args.lang_tag}.md"

    kind = "heading" if args.headings else "note" if args.notes else "block"
    pool = [u for u in units if u["kind"] == kind]
    if args.list:
        for k in ("heading", "block", "note"):
            us = [u for u in units if u["kind"] == k]
            print(f"{k:8} {len(us):4}  lines={sum(len(u['lines']) for u in us):4}  "
                  f"chars={sum(len(l) for u in us for l in u['lines'])}")
        print("multi-line blocks (verse):", sum(1 for u in units if u["kind"] == "block" and len(u["lines"]) > 1))
        return 0

    if not style_path.exists():
        sys.exit(f"no style file at {style_path} — write it first (it is the system prompt)")
    args.style = style_path.read_text(encoding="utf-8")
    ledger = load_ledger(ledger_path)

    if args.render_only:
        d, n, fl = render(out_md, src, fm, units, ledger, args)
        print(f"rendered {out_md}: {d}/{n} blocks, flagged {fl}")
        return 0

    done = {(r["kind"], r["id"]) for r in ledger}
    only = set(args.only.split(",")) if args.only else None
    todo = [u for u in pool if (only is None or u["id"] in only) and (args.force or (kind, u["id"]) not in done)]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        print("nothing to do")
        render(out_md, src, fm, units, ledger, args)
        return 0

    # batches: headings / notes go in one call; blocks by adjacent runs
    if kind != "block":
        batches = [todo]
    else:
        batches, cur, size = [], [], 0
        for u in todo:
            n = sum(len(l) for l in u["lines"])
            if cur and (len(cur) >= args.batch_units or size + n > args.batch_chars):
                batches.append(cur); cur, size = [], 0
            cur.append(u); size += n
        if cur:
            batches.append(cur)
    extra = HEADINGS_CLAUSE if kind == "heading" else NOTES_CLAUSE if kind == "note" else ""

    order = {u["id"]: i for i, u in enumerate(pool)}

    def context_for(batch):
        if kind != "block":
            return f"Work: {fm.get('title', '')} — {fm.get('subtitle', '')}".strip(" —")
        best = latest(ledger)
        first = order[batch[0]["id"]]
        prior = [u for u in pool[:first] if ("block", u["id"]) in best][-args.context_blocks:]
        parts = [f"Work: {fm.get('title', '')} — {fm.get('subtitle', '')}. "
                 f"Current section: {batch[0].get('heading') or ''}"]
        if prior:
            parts.append("Preceding passages already translated (keep terminology consistent with them):\n\n" +
                         "\n\n".join(f"[{u['id']}] {' / '.join(u['lines'])}\n=> {' / '.join(best[('block', u['id'])]['lines'])}"
                                     for u in prior))
        return "\n\n".join(parts)

    if args.dry_run:
        for b in batches[:2]:
            print(json.dumps(build_request(b, context_for(b), args, extra), ensure_ascii=False, indent=1)[:4000])
            print("-" * 60)
        print(f"dry run: {len(todo)} {kind}(s) in {len(batches)} call(s); nothing sent")
        return 0

    key = os.environ.get(KEY_ENV)
    if not key:
        sys.exit(f"{KEY_ENV} is not set (source ~/.zshrc)")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def record(u, lines, info, fails, attempts):
        rec = {"kind": kind, "id": u["id"], "src_lines": u["lines"], "lines": lines,
               "model": args.model, "model_version": info.get("model_version"),
               "thinking": args.thinking, "temperature": args.temperature,
               "failed_checks": fails, "attempts": attempts, "usage": info.get("usage"),
               "ts": _dt.datetime.now().isoformat(timespec="seconds")}
        ledger.append(rec)
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def solo(u, first_fails=None):
        fails, lines, info = first_fails or {}, None, {}
        for attempt in range(1, args.attempts + 1):
            clause = PARITY_CLAUSE.format(n=len(u["lines"]))
            marks = FOOTNOTE_REF_RE.findall(" ".join(u["lines"]))
            if marks:
                clause += MARKER_CLAUSE.format(m=", ".join(marks))
            if fails.get("simplified_chars"):
                clause += SCRIPT_CLAUSE.format(c=fails["simplified_chars"])
            if fails.get("forbidden"):
                clause += f"\n\nDo not use {', '.join(fails['forbidden'])} anywhere in your answer (see the style instruction)."
            try:
                text, info = call_api(build_request([u], context_for([u]), args, extra + clause), args, key)
            except BadResponse as exc:
                fails = {"bad_response": str(exc)}
                continue
            got = parse_response(text, [u])
            if not got:
                fails = {"bad_shape": "ids/shape mismatch"}
                continue
            lines = got[u["id"]]
            fails = check(u, lines, args)
            if not fails:
                return lines, info, {}, attempt
        return lines, info, fails, args.attempts

    t_start, n_ok, n_flag = time.time(), 0, 0
    try:
        for bi, batch in enumerate(batches, 1):
            ids = ",".join(u["id"] for u in batch)
            try:
                text, info = call_api(build_request(batch, context_for(batch), args, extra), args, key)
                got = parse_response(text, batch)
            except BadResponse as exc:
                print(f"  [{bi}/{len(batches)}] {ids}: {exc} — re-running singly", file=sys.stderr)
                got, info = None, {}
            for u in batch:
                lines = got.get(u["id"]) if got else None
                fails = check(u, lines, args) if lines else {"bad_shape": "batch rejected"}
                attempts = 0
                if fails:
                    lines, info_u, fails, attempts = solo(u, fails)
                    info = info_u or info
                if lines is None:
                    print(f"    ✗ {u['id']}: no usable translation ({fails}) — not recorded", file=sys.stderr)
                    n_flag += 1
                    continue
                record(u, lines, info, fails, attempts)
                if fails:
                    n_flag += 1
                    print(f"    ! {u['id']}: recorded with failed checks {fails}", file=sys.stderr)
                else:
                    n_ok += 1
            print(f"  [{bi}/{len(batches)}] {ids}  ok  ({round(time.time() - t_start)}s)")
    except ApiStop as exc:
        print(f"\nSTOP: {exc}", file=sys.stderr)
    d, n, fl = render(out_md, src, fm, units, ledger, args)
    print(f"\n{kind}s this run: {n_ok} clean, {n_flag} flagged. Blocks in file: {d}/{n}. Flagged overall: {fl}")
    print(f"output: {out_md}\nledger: {ledger_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
