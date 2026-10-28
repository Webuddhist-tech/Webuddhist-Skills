#!/usr/bin/env python3
"""
Run commentary-resegment's LLM phase with Claude subagents instead of Gemini.

    # 1. write one prompt file per window (exact SYSTEM_PROMPT + user prompt the script sends)
    python3 claude_reseg_shim.py dump  <input.md> --commentary-id <id> [--script PATH]
    #    → 0-INBOX/temp/RESEG-<id>/claude/window-NNNN.prompt.md
    # 2. a Claude subagent per window reads the prompt file and writes the raw JSON reply to
    #    0-INBOX/temp/RESEG-<id>/claude/window-NNNN.response.json
    # 3. stage the replies exactly as the script would, then run resegment.py --apply-only
    python3 claude_reseg_shim.py stage <input.md> --commentary-id <id> [--script PATH]

The script's own windowing, parsing, staging format, combine/validate/apply and
integrity check are reused unchanged — only the model call is swapped.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

DEFAULT_SCRIPT = str(Path(__file__).resolve().parent / 'resegment.py')   # the skill's own script


def load(script):
    spec = importlib.util.spec_from_file_location('reseg', script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['dump', 'stage'])
    ap.add_argument('input')
    ap.add_argument('--commentary-id', required=True)
    ap.add_argument('--script', default=DEFAULT_SCRIPT)
    ap.add_argument('--window-size', type=int)
    ap.add_argument('--overlap', type=int)
    a = ap.parse_args()
    m = load(a.script)
    ws = a.window_size or m.DEFAULT_WINDOW_SIZE
    ov = a.overlap or m.DEFAULT_OVERLAP
    fm, blocks = m.parse_file(Path(a.input))
    wins = m.make_windows(blocks, ws, ov)
    root = Path('.').resolve()
    cdir = root / m.TEMP_BASE / f'RESEG-{a.commentary_id}' / 'claude'
    sdir = root / m.TEMP_BASE / f'RESEG-{a.commentary_id}' / 'windows'
    cdir.mkdir(parents=True, exist_ok=True)
    if a.mode == 'dump':
        for w in wins:
            user = m.USER_PROMPT_TEMPLATE.format(blocks_text=m.format_window(w))
            (cdir / f"window-{w['idx']:04d}.prompt.md").write_text(
                '=== SYSTEM PROMPT ===\n' + m.SYSTEM_PROMPT + '\n=== USER PROMPT ===\n' + user,
                encoding='utf-8')
        print(f'{len(blocks)} blocks → {len(wins)} windows; prompts in {cdir}')
    else:
        for w in wins:
            r = cdir / f"window-{w['idx']:04d}.response.json"
            if not r.exists():
                print(f'missing response for window {w["idx"]}')
                continue
            raw = r.read_text(encoding='utf-8').strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            try:
                ops = json.loads(raw)
                if not isinstance(ops, list):
                    ops = []
            except json.JSONDecodeError as e:
                print(f'window {w["idx"]}: JSON error {e} — treating as []')
                ops = []
            m.save_window_result(sdir, w, ops)
            print(f'window {w["idx"]}: {len(ops)} op(s) staged')


if __name__ == '__main__':
    main()
