---
name: discord-feedback-digest
description: Pull messages and screenshots from the WeBuddhist Discord UX-feedback channel and write a prioritized, deduped digest (lanes Dev / Design / Localization, each split into product-feature subsections, with the screenshots embedded under each item) plus a readable thread file, into the repo's Feedback folder. Use whenever the product owner says "run the feedback digest", "summarise the Discord feedback", "what came into the UX channel", or "catch me up on Discord feedback". Normally runs as the "Discord Feedback Digest" GitHub Action; the same two scripts run locally too.
profile: any
supersedes:
  - webuddhist-knowledge/.claude/skills/discord-feedback-digest/SKILL.md
  - webuddhist-knowledge/80_SYSTEM/82_Skills/UX/discord-feedback-digest/SKILL.md
updated: 2026-10-26
---

# discord-feedback-digest

> **Single source of truth.** This folder defines how the digest works. The triage rules (how feedback is read, clustered and prioritised, and the lanes and feature names) live in `digest-prompt.md`, which is sent to the model as its system prompt. The page layout lives in `scripts/discord-feedback-digest.py`. See `README.md` in this folder for the maintainer runbook.

## What travels with this skill

| File | Install to (in the host repo) |
|---|---|
| `SKILL.md`, `digest-prompt.md`, `README.md`, `SETUP.md` | the skill folder (e.g. `.claude/skills/discord-feedback-digest/`) |
| `scripts/discord-feedback-fetch.py`, `scripts/discord-feedback-digest.py` | `scripts/` at the repo root (the watermark `scripts/.discord-feedback-state.json` is written next to the fetch script) |
| `templates/feedback-digest.yml` | `.github/workflows/feedback-digest.yml` — set the `--channel` IDs and `OUT_DIR` for the host repo |

The digest script finds `digest-prompt.md` in the skill folder (the folder above `scripts/`, then `80_SYSTEM/82_Skills/UX/discord-feedback-digest/` or `.claude/skills/discord-feedback-digest/` at the repo root); pass `--prompt <file>` or set `DIGEST_PROMPT_FILE` if it lives elsewhere.

Turn raw Discord UX feedback (text + screenshots) into two durable files: a **prioritised, deduped digest** that design and dev can act on, and a **clean readable thread**. There is no agent in the loop, just two scripts:

1. **Fetch** — `scripts/discord-feedback-fetch.py` pulls new messages and downloads and downscales the screenshots into a staging folder. No LLM.
2. **Digest** — `scripts/discord-feedback-digest.py` makes **one Kimi API call** (`kimi-k3.1-pro`, vision). It sends the full transcript plus only the screenshots whose message text is vague (selective OCR). The model returns JSON, and the script renders `Digest.md`, `Thread.md` and `screenshots/`.

## How to run

**Normally: the GitHub Action.** GitHub → Actions → **Discord Feedback Digest** → **Run workflow**, or:

```bash
gh workflow run feedback-digest.yml
```

Leave `hours` blank to process everything since the last run. Use **Run workflow**, not **Re-run** on an old run.

**Locally (same scripts):** needs `DISCORD_BOT_TOKEN` and `KIMI_API_KEY` in the env, plus `pip install requests pillow`.

```bash
python3 scripts/discord-feedback-fetch.py --channel 1488485129058783272 --since-last --out .wb-feedback/<YYYY-MM-DD>
python3 scripts/discord-feedback-digest.py --stage .wb-feedback/<YYYY-MM-DD> \
  --out "20_PRODUCTS/26_Webuddhist/Feedback/UX Feedback Digest <YYYY-MM-DD>" --date <YYYY-MM-DD>
```

Don't run both locally and in CI: they share the watermark (`scripts/.discord-feedback-state.json`), which CI commits back. Use `--no-save-state` on the fetch for throwaway tests, and `--dry-run` on the digest to see the exact request without calling the API.

## Output

```
20_PRODUCTS/26_Webuddhist/Feedback/UX Feedback Digest <YYYY-MM-DD>/
  ├── Digest.md       # lanes → feature subsections → items, screenshots inline
  ├── Thread.md       # readable transcript, every screenshot where it was sent
  └── screenshots/
```

**`Digest.md`** reads on one page in Obsidian, so you never have to click through to see a screenshot:

```markdown
## 🛠 Dev

### Notifications

- [ ] 🔴 **Reminder fires in every language** — same "Day 5" reminder in en/bo/zh at once · 3 reporters (kun, Harshal, Jay Liao) `[l10n]`
  ![Notification shade, three languages|250](screenshots/<file>) ![…|250](screenshots/<file>)

### Practice Timer & Meditation
...
## 🎨 Design
## 🌐 Localization
## 🤔 Needs clarification / not actionable yet
```

- **Lanes** (H2): Dev, Design, Localization, Needs clarification. Each item sits in one primary lane.
- **Features** (H3) group the items inside each lane, e.g. Notifications, Events, Prayer Requests, Accumulation & Mala. The preferred list is in `digest-prompt.md`. Features are ordered by their most urgent item.
- **Items**: one per underlying problem, deduped with a reporter count, and sorted 🔴 P0 → 🟠 P1 → 🟡 P2. Already-fixed items render as `[x]`.
- **Screenshots**: those from the messages an item cites are embedded right under it at 250px (up to 4, with a "+N more in Thread" link). The model's one-line read of a screenshot becomes its alt text.
- **Tags**: `[multi-platform?]`, `[l10n]`, `[self-fix]`. They're greppable.

**`Thread.md`** is a back-link to the digest, then who said what in order (same-author bursts collapsed), each screenshot inline at 250px with its caption when the model read it. It has no JSON, timestamps or IDs.

## Pitfalls

- **Message Content Intent off** → text comes back empty while images still download. Fix it in the Discord Developer Portal → Bot (see `SETUP.md`).
- **"Re-run" on an old Actions run** replays that run's commit. The workflow now checks out the branch tip, so it's safe, but "Run workflow" is the intended trigger.
- **Model returned no items / bad JSON**: the raw reply is saved to `<stage>/model-response.json` on the runner. Re-render without paying again with `--response <file>`.
- **Kimi content filter** (`400 … considered high risk`): Moonshot's moderation sometimes rejects a batch. The script then bisects it with small probe calls, leaves out only the flagged messages or screenshots, and lists them under **⚠️ Not triaged** at the bottom of the digest so nothing is silently dropped.
- **Max tokens**: a month-long backfill can produce a big reply. If the run says "hit max_tokens", set the repo variable `KIMI_MAX_TOKENS` higher (default 64000). Reasoning counts toward it, which is why `KIMI_REASONING_EFFORT` defaults to `low`.
- **Auto-filing tickets**: this skill triages; it does not file. Hand off via `github-issue` only when Evan asks.
- **Secrets**: never write the bot token or Kimi key into any vault file.
- **Channel scope**: the UX feedback channel only. If feedback spans App and Connect, the item says which.

## What to return when done

Counts (messages / screenshots), the date, a link to `Digest.md`, and the P0 items with any urgent flag. Skip the full list; it's in the digest.
