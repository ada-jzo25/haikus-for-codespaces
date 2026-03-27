# Personal Assistant Telegram Bot — Phone-Only Setup Guide

## Overview

A personal Telegram bot that acts as your daily assistant:
- **Quick Notes** — send any text to save it
- **Daily Reminders** — set timed reminders
- **Receipt Scanning** — photo → expense log (via GPT-4o Vision)
- **News Summary** — on-demand news briefs
- **Expense Analysis** — spending breakdowns by category/period

---

## Step 1: Get a Telegram Bot Token

1. Open Telegram on your phone
2. Search for **@BotFather** and start a chat
3. Send `/newbot`
4. Choose a **name** (e.g., "My PA Bot")
5. Choose a **username** ending in `bot` (e.g., `mypa_2024_bot`)
6. BotFather will reply with your **token** — copy it! It looks like: `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## Step 2: Get Your Telegram Chat ID

1. Search for **@userinfobot** on Telegram and start a chat
2. It will reply with your **user ID** (a number like `123456789`)
3. Save this — it restricts the bot to only respond to you

## Step 3: Get API Keys (Optional)

### For receipt scanning (GPT-4o Vision):
- Go to https://platform.openai.com/api-keys
- Create a new API key
- You need some credits ($5 minimum)

### For news summaries:
- Go to https://newsapi.org/register
- Sign up for a free account
- Copy your API key from the dashboard

## Step 4: Set Up the Environment

### Option A: GitHub Codespaces (Recommended — 60 free hrs/month)

1. Fork or open this repo in GitHub on your phone's browser
2. Tap the green **Code** button → **Codespaces** → **Create codespace**
3. Wait for it to load (it opens a VS Code editor in your browser)
4. Open the terminal (tap the ☰ menu → Terminal → New Terminal)
5. Run these commands:

```bash
cd bot
cp .env.example .env
```

6. Edit `.env` and fill in your tokens:
```bash
# In the Codespaces terminal:
nano .env
# Or use the file explorer to edit .env
```

7. Install dependencies and run:
```bash
pip install -r requirements.txt
python pa_bot.py
```

### Option B: Termux on Android

1. Install **Termux** from F-Droid (not Play Store)
2. Run:
```bash
pkg update && pkg install python git
git clone <your-repo-url>
cd haikus-for-codespaces/bot
cp .env.example .env
nano .env   # fill in your tokens
pip install -r requirements.txt
python pa_bot.py
```

### Option C: Google Cloud Shell

1. Go to https://shell.cloud.google.com on your phone
2. Clone the repo and follow the same steps as above

## Step 5: Test Your Bot

1. Open Telegram and find your bot by its username
2. Send `/start` — you should see the welcome message
3. Try these:
   - Send any text → saved as a note
   - `/notes` → view your notes
   - `/note Buy groceries` → save a specific note
   - `/remind 14:00 Call dentist` → set a reminder
   - Send a receipt photo → expense gets logged
   - `/spent week` → see weekly spending
   - `/news` → get a news summary

## Step 6: Keep It Running

### On Codespaces:
- The bot runs while your Codespace is active
- Codespaces auto-stop after 30 min of inactivity
- To keep it running longer, interact with it periodically

### For 24/7 uptime (free options):
1. **Render.com** — free web service tier (spins down after inactivity)
2. **Railway.app** — $5 free credits/month
3. **Oracle Cloud Free Tier** — always-free VM (requires setup)

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and help |
| `/help` | Show all commands |
| `/note <text>` | Save a quick note |
| `/notes` | View all saved notes |
| `/delnote <n>` | Delete note by number |
| `/remind HH:MM <text>` | Set a daily reminder (UTC) |
| `/reminders` | View all reminders |
| `/delremind <n>` | Delete a reminder |
| `/news` | Get news summary |
| `/expenses` | View recent expenses |
| `/spent week` | This week's spending |
| `/spent month` | This month's spending |
| `/spent all` | All-time spending |
| *Send photo* | Scan receipt & log expense |
| *Send text* | Auto-saved as note |

## Architecture

```
bot/
├── pa_bot.py          # Single-file bot (all features)
├── requirements.txt   # Python dependencies
├── .env.example       # Template for secrets
├── .env               # Your actual secrets (gitignored)
├── data/              # Auto-created JSON data store
│   ├── notes.json
│   ├── expenses.json
│   └── reminders.json
└── SETUP_GUIDE.md     # This file
```

## Tips for Phone-Only Development

- **Codespaces** is the smoothest experience on a phone browser
- Use **landscape mode** for the terminal
- **Termux:Widget** can add a home screen shortcut to start the bot
- Keep Claude Pro / ChatGPT Plus open in another tab for debugging help
- Use Claude for code logic questions, ChatGPT for vision/image tasks
