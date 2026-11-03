---
updated: 2026-10-26
owner: Evan (Product Owner) — but designed so anyone on the team can maintain it
---

# Discord Feedback Digest — Maintainer Runbook

Automated daily digest of the WeBuddhist Discord **#ux-feedback** channel (App only). It pulls new messages + screenshots, has Kimi read them, and writes a prioritized, deduped digest into the App feedback folder. This file is for whoever needs to run, change, or fix it — no prior context required.

## What it produces

Each run creates a dated folder at:

```
20_PRODUCTS/26_Webuddhist/Feedback/UX Feedback Digest <YYYY-MM-DD>/
  ├── Digest.md       # clustered, deduped, prioritized action items (Dev / Design / Localization → feature subsections, screenshots inline)
  ├── Thread.md       # readable transcript with screenshots
  └── screenshots/    # every image from that run
```

## How it runs

It's a **GitHub Action** in this repo (`webuddhist-knowledge`). Nothing runs on anyone's laptop. Two Python scripts, no agent: the fetch script talks to Discord, then the digest script makes **one Kimi API call** and renders the Markdown.

- **Manual:** GitHub → **Actions** tab → **"Discord Feedback Digest"** → **Run workflow**. Leave the `hours` box **blank** to process everything since the last run (recommended). Put a number only to force a fixed look-back window (e.g. `72` = last 3 days). Use **Run workflow**, not **Re-run** on an old run.
- **Scheduled:** the workflow is manual-only. To make it daily, add a `schedule:` cron trigger to the workflow.

## The files (what to edit for what)

| File | What it controls |
|---|---|
| `digest-prompt.md` (skill folder) | **The triage rules**: how feedback is read, clustered and prioritised, the lanes, the feature names, and the JSON the model returns. Sent verbatim as the system prompt. **Edit this to change what the digest says.** |
| `scripts/discord-feedback-digest.py` | **The layout**: how the JSON becomes `Digest.md` / `Thread.md` (feature subsections, inline screenshots, thumbnail size), which screenshots go to the model, and the API call. |
| `scripts/discord-feedback-fetch.py` | The fetch logic (pulls messages, downloads + downscales screenshots, tracks the watermark). |
| `.github/workflows/feedback-digest.yml` (from `templates/feedback-digest.yml`) | The runner: model, channel, where output is committed. |
| `SKILL.md` (skill folder) | Overview for people and agents. If the repo keeps a second copy (e.g. `.claude/skills/` plus a vault skills folder), keep them identical — better, install one copy from Webuddhist-Skills. |
| `SETUP.md` (skill folder) | One-time Discord bot setup (only needed if the bot is ever recreated). |
| `scripts/.discord-feedback-state.json` | The **watermark** — the ID of the last message processed. Committed each run so the next run continues from there. Don't hand-edit unless you mean to. |

## Common changes

**Change what the digest says** (priorities, lanes, feature list) → edit `digest-prompt.md`.

**Change how it looks** (headings, image size, images per item) → the constants and `render_*` functions at the top of `scripts/discord-feedback-digest.py`.

**Change the model** → set the repo variable `KIMI_MODEL` (default `kimi-k3.1-pro`). Its base URL is `KIMI_BASE_URL` (default `https://api.moonshot.ai/v1`; use `https://api.moonshot.cn/v1` for a China-region key).

**Lower the cost** → `--max-vision` on the digest script caps how many screenshots the model sees (default 80, and only vague messages' screenshots qualify). The fetch script downscales screenshots (`--max-image-edge`, default 1280px).

**Change the channel** → the `--channel` argument in `feedback-digest.yml`. Get a new ID by right-clicking the channel in Discord with Developer Mode on → Copy Channel ID.

**Change where digests are saved** → `OUT_DIR` and the `git add` line in `feedback-digest.yml`. Update both.

## Secrets (need repo admin)

Set in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | What it is | How to regenerate |
|---|---|---|
| `DISCORD_BOT_TOKEN` | The Discord bot's token | Discord Developer Portal → your app → Bot → Reset Token. Then update this secret. |
| `WEBUDDHIST_FEEDBACK_DIGEST` | Kimi / Moonshot API key | platform.kimi.ai → API keys. Set with: `printf %s "sk-..." \| gh secret set WEBUDDHIST_FEEDBACK_DIGEST --repo WeBuddhist/webuddhist-knowledge` (the `printf %s` avoids a trailing newline, which causes auth errors). |

## Troubleshooting (errors we've actually hit)

| Error in the run | Cause | Fix |
|---|---|---|
| `! [rejected] HEAD -> main (fetch first)` | Someone pushed to main mid-run, or an old run was **Re-run** (it replays its old commit) | Fixed: the workflow checks out the branch tip and rebases before pushing, with retries. Use **Run workflow** for new digests. |
| `KIMI_API_KEY is not set` | Secret missing/empty | Re-set `WEBUDDHIST_FEEDBACK_DIGEST` with the `printf %s … \| gh secret set` command above. |
| `Kimi API 401` | Bad or expired key | Regenerate on platform.kimi.ai and re-set the secret. |
| `Kimi API 404` / model not found | Model ID retired | Check platform.kimi.ai/docs/models and set the `KIMI_MODEL` repo variable. |
| `content filter rejected the batch` | Kimi's moderation flagged some message or screenshot | Handled automatically: the flagged messages are isolated and listed under **⚠️ Not triaged** in the digest. Only a total failure (`rejects the batch even text-only`) stops the run. |
| `Model hit max_tokens` | Very large window, or too much reasoning | Set the repo variable `KIMI_MAX_TOKENS` higher (default 64000), keep `KIMI_REASONING_EFFORT` at `low`, or run smaller windows. |
| Digest has screenshots but no text | Discord **Message Content Intent** is off | Discord Developer Portal → Bot → enable Message Content Intent. |
| Run pulls 0 messages | Channel was quiet, or watermark already current | Normal. Force a window with the `hours` input if you want a backfill. |

## How it stays duplicate-free

The fetch uses a **watermark** (last processed message ID, in `scripts/.discord-feedback-state.json`), committed back after each successful run. So whether it runs daily, skips a weekend, or is triggered twice, it only ever processes messages newer than the last digest — no overlaps, no gaps. The watermark only advances after the digest commits successfully, so a failed run safely re-processes the same window next time.

## Don't run two copies at once

If you ever run the fetch on a Mac *and* the Action is live, the two watermarks diverge and you'll get duplicate or skipped digests. Pick one (the Action). `SKILL.md` shows the local commands for one-off runs.
