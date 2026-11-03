# Discord bot setup — UX feedback digest

One-time setup. ~10 minutes. You only do this once; after that the skill runs on the token.

You need two things by the end: a **bot token** (stored in `~/.zshrc`) and the **channel ID** of your UX feedback channel.

---

## 1. Create the application

1. Go to https://discord.com/developers/applications
2. **New Application** (top right) → name it `WeBuddhist Feedback Bot` → **Create**.

## 2. Add a bot + grab the token

1. Left sidebar → **Bot**.
2. Under **Privileged Gateway Intents**, turn ON **Message Content Intent**. *(Required — without it Discord returns empty message text, even over the REST API. It's free for bots in fewer than 100 servers.)*
3. Click **Reset Token** → **Yes** → **Copy**. This is your `DISCORD_BOT_TOKEN`.
   - Treat it like a password. If it leaks, come back here and Reset Token again.

Store it on your Mac so the script and Claude Code can read it:

```bash
echo 'export DISCORD_BOT_TOKEN="paste-your-token-here"' >> ~/.zshrc
source ~/.zshrc
```

*(Same place you keep `OPENAI_API_KEY`.)*

## 3. Invite the bot to your server

The bot only needs to **read**, not post.

1. Left sidebar → **Installation** (or **OAuth2 → URL Generator** on older portals).
2. Scopes: check **bot**.
3. Bot Permissions: check **View Channels** and **Read Message History** only.
4. Copy the generated URL, open it in a browser, pick your WeBuddhist server, **Authorize**.

> You need **Manage Server** permission on the Discord server to add a bot. If you don't have it, send the invite URL to whoever does.

Make sure the bot can actually see the feedback channel: if the channel is private, right-click it → **Edit Channel → Permissions** → add the bot (or its role) with View Channel + Read Message History.

## 4. Get the channel ID

1. Discord → **User Settings → Advanced** → turn on **Developer Mode**.
2. Right-click your UX feedback channel → **Copy Channel ID**.

That long number is your `--channel` value. Keep it handy — the skill will ask for it the first time, or you can hardcode it in your scheduled command.

---

## Quick test (run on your Mac, in Terminal or Claude Code)

```bash
cd ~/WeBuddhist/product-owner
python3 scripts/discord-feedback-fetch.py --channel YOUR_CHANNEL_ID --hours 168 --out /tmp/feedback-test
```

`--hours 168` looks back a week so you actually catch something on the first run.

- **Works:** prints message + image counts and writes `/tmp/feedback-test/messages.json`. You're done — tell Claude "run the discord feedback digest."
- **401 Unauthorized:** token is wrong or not exported. Re-check step 2 and `source ~/.zshrc`.
- **403 Forbidden:** bot isn't in the server or can't see the channel. Re-check steps 3–4.
- **Empty content but images present:** Message Content Intent is off. Re-check step 2.

First run needs `requests`: `pip3 install requests` if it's missing.
