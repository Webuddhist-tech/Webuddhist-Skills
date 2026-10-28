#!/usr/bin/env python3
"""
Generic Claude stand-in (used when the skill is run with Claude agents instead of Gemini) for the skills' Gemini `_generate()` calls.

Runs a skill script with `get_client()` and `_generate()` replaced:
  - each model call N is written to <dir>/call-NNN.prompt.md (system + user prompt);
  - if <dir>/call-NNN.response.txt exists, its text is returned as the model reply;
  - otherwise the run stops (exit 3) after writing the prompt, so a Claude subagent
    can answer it; re-run the same command to continue.

    python3 claude_generate_shim.py --dir <calls-dir> -- <script.py> [script args...]

Works for scripts whose model calls go through a module-level
`_generate(client, model, user_prompt, ...)` and whose system prompt is a module
constant named *SYSTEM_PROMPT (resegment.py, qc_check.py, commentary-resegment).
"""
import argparse
import importlib.util
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('script')
    ap.add_argument('args', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('skillmod', a.script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys_prompts = [getattr(mod, n) for n in dir(mod) if n.endswith('SYSTEM_PROMPT')]
    counter = {'n': 0}

    def fake_generate(client, model, user_prompt, *args, **kw):
        n = counter['n']
        counter['n'] += 1
        resp = d / f'call-{n:03d}.response.txt'
        prompt = d / f'call-{n:03d}.prompt.md'
        if resp.exists():
            return resp.read_text(encoding='utf-8').strip()
        prompt.write_text('=== SYSTEM PROMPT ===\n' + '\n'.join(sys_prompts) +
                          '\n=== USER PROMPT ===\n' + user_prompt, encoding='utf-8')
        print(f'[claude-shim] prompt written: {prompt} — answer it in {resp.name}, then re-run.')
        sys.exit(3)

    mod.get_client = lambda: None
    mod._generate = fake_generate
    sys.argv = [a.script] + [x for x in a.args if x != '--']
    mod.main()


if __name__ == '__main__':
    main()
