#!/usr/bin/env python3
"""
List Gemini models available to your API key that support generateContent.

Usage (from project root, venv activated; GEMINI_API_KEY is read from the vault-root .env):
    python 4-SYSTEM/Skills/commentary-resegment/scripts/list_models.py
"""
import os
from pathlib import Path
import sys


# ── Gemini API key ────────────────────────────────────────────────────────────
_KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _gemini_api_key():
    """
    The Gemini API key: from the environment if set, otherwise from the `.env`
    file at the vault root (a folder that contains 4-SYSTEM/), found by walking
    up from this script's own location, then from the current directory; the
    nearest vault root with a .env wins (so a benchmark copy inside the vault
    still uses the vault's own .env).
    Only GEMINI_API_KEY / GOOGLE_API_KEY are read; nothing else from .env is
    loaded, and the key is never printed or logged.
    """
    for n in _KEY_NAMES:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    roots = []          # every folder containing 4-SYSTEM/, nearest first
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        for d in (start, *start.parents):
            if (d / "4-SYSTEM").is_dir() and d not in roots:
                roots.append(d)
    for root in roots:
        envf = root / ".env"
        if not envf.is_file():
            continue
        try:
            lines = envf.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            continue
        found = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            if k.startswith("export "):
                k = k[len("export "):].strip()
            if k not in _KEY_NAMES:
                continue
            v = v.strip()
            if v[:1] in ("'", '"') and v[-1:] == v[:1] and len(v) >= 2:
                v = v[1:-1]
            else:
                v = v.split(" #", 1)[0].strip()
            if v:
                found[k] = v
        for n in _KEY_NAMES:
            if n in found:
                return found[n]
    return None


def main():
    api_key = _gemini_api_key()
    if not api_key:
        sys.exit("Error: no Gemini API key found.\n  Put GEMINI_API_KEY=your-key in the .env file at the vault root (next to 4-SYSTEM/),\n  or set GEMINI_API_KEY in the environment.")

    try:
        from google import genai
    except ImportError:
        sys.exit("Error: google-genai not installed. Run: pip install google-genai")

    client = genai.Client(api_key=api_key)

    rows = []
    for m in client.models.list():
        methods = getattr(m, "supported_actions", None) or \
                  getattr(m, "supported_generation_methods", None) or []
        if "generateContent" in methods:
            rows.append(m.name)

    if not rows:
        print("No models supporting generateContent were returned for this key.")
        return

    print("Models supporting generateContent:\n")
    for name in sorted(rows):
        print("  " + name.replace("models/", ""))
    print(f"\n{len(rows)} model(s). Pass one to resegment.py with --model <name>.")


if __name__ == "__main__":
    main()
