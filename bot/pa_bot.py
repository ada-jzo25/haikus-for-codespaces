"""
Personal Assistant Telegram Bot
================================
Features:
1. Quick notes — save and retrieve notes
2. Daily reminders — scheduled morning messages
3. Receipt scanning — photo → extracted expense data (via OpenAI GPT-4o)
4. News summary — daily brief from NewsAPI
5. Expense analysis — spending breakdown by category and time period

Run: python pa_bot.py
"""

import os
import json
import logging
import base64
import datetime
from pathlib import Path
from io import BytesIO

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "07:00")
NEWS_TOPICS = os.getenv("NEWS_TOPICS", "technology,AI,programming")

DATA_DIR = Path(__file__).parent / "data"
NOTES_FILE = DATA_DIR / "notes.json"
EXPENSES_FILE = DATA_DIR / "expenses.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _ensure_data():
    DATA_DIR.mkdir(exist_ok=True)
    for fpath, default in [
        (NOTES_FILE, []),
        (EXPENSES_FILE, []),
        (REMINDERS_FILE, []),
    ]:
        if not fpath.exists():
            fpath.write_text(json.dumps(default, indent=2))


def _load(fpath: Path) -> list:
    return json.loads(fpath.read_text())


def _save(fpath: Path, data: list):
    fpath.write_text(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Auth decorator — restrict to owner
# ---------------------------------------------------------------------------

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if OWNER_CHAT_ID and str(update.effective_chat.id) != OWNER_CHAT_ID:
            await update.message.reply_text("Sorry, this bot is private.")
            return
        return await func(update, context)
    return wrapper


# ---------------------------------------------------------------------------
# /start & /help
# ---------------------------------------------------------------------------

@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your Personal Assistant bot.\n\n"
        "Here's what I can do:\n"
        "/note <text> — Save a quick note\n"
        "/notes — View all saved notes\n"
        "/delnote <number> — Delete a note by number\n"
        "/remind <HH:MM> <text> — Set a daily reminder\n"
        "/reminders — View all reminders\n"
        "/delremind <number> — Delete a reminder\n"
        "/expenses — View expense summary\n"
        "/spent <period> — Spending analysis (week/month/all)\n"
        "/news — Get a news summary now\n"
        "/help — Show this message\n\n"
        "Send me a photo of a receipt to log an expense!\n"
        "Send any text without a command to save it as a quick note."
    )


@owner_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


# ---------------------------------------------------------------------------
# Feature 1: Quick Notes
# ---------------------------------------------------------------------------

@owner_only
async def cmd_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Usage: /note <your note text>")
        return

    notes = _load(NOTES_FILE)
    notes.append({
        "text": text,
        "date": datetime.datetime.now().isoformat(),
    })
    _save(NOTES_FILE, notes)
    await update.message.reply_text(f"Noted! ({len(notes)} notes saved)")


@owner_only
async def cmd_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = _load(NOTES_FILE)
    if not notes:
        await update.message.reply_text("No notes saved yet. Use /note <text> to add one.")
        return

    lines = []
    for i, n in enumerate(notes, 1):
        dt = n["date"][:10]
        lines.append(f"{i}. [{dt}] {n['text']}")
    await update.message.reply_text("Your notes:\n\n" + "\n".join(lines))


@owner_only
async def cmd_delnote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delnote <number>")
        return
    try:
        idx = int(context.args[0]) - 1
        notes = _load(NOTES_FILE)
        removed = notes.pop(idx)
        _save(NOTES_FILE, notes)
        await update.message.reply_text(f"Deleted: {removed['text']}")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid note number. Use /notes to see the list.")


@owner_only
async def plain_text_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any plain text message (not a command) is saved as a quick note."""
    text = update.message.text
    if not text:
        return
    notes = _load(NOTES_FILE)
    notes.append({
        "text": text,
        "date": datetime.datetime.now().isoformat(),
    })
    _save(NOTES_FILE, notes)
    await update.message.reply_text(f"Saved as note! ({len(notes)} total)\nUse /notes to view all.")


# ---------------------------------------------------------------------------
# Feature 2: Daily Reminders
# ---------------------------------------------------------------------------

@owner_only
async def cmd_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /remind <HH:MM> <reminder text>\n"
            "Example: /remind 08:30 Take vitamins"
        )
        return

    time_str = context.args[0]
    try:
        datetime.datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await update.message.reply_text("Invalid time format. Use HH:MM (24-hour).")
        return

    text = " ".join(context.args[1:])
    reminders = _load(REMINDERS_FILE)
    reminders.append({"time": time_str, "text": text})
    _save(REMINDERS_FILE, reminders)
    await update.message.reply_text(f"Reminder set for {time_str} UTC: {text}")


@owner_only
async def cmd_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = _load(REMINDERS_FILE)
    if not reminders:
        await update.message.reply_text("No reminders set. Use /remind HH:MM <text>")
        return

    lines = [f"{i}. {r['time']} — {r['text']}" for i, r in enumerate(reminders, 1)]
    await update.message.reply_text("Your reminders:\n\n" + "\n".join(lines))


@owner_only
async def cmd_delremind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /delremind <number>")
        return
    try:
        idx = int(context.args[0]) - 1
        reminders = _load(REMINDERS_FILE)
        removed = reminders.pop(idx)
        _save(REMINDERS_FILE, reminders)
        await update.message.reply_text(f"Deleted reminder: {removed['time']} — {removed['text']}")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid number. Use /reminders to see the list.")


async def _send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Job callback — runs every minute, sends reminders whose time matches."""
    if not OWNER_CHAT_ID:
        return
    now = datetime.datetime.utcnow().strftime("%H:%M")
    reminders = _load(REMINDERS_FILE)
    for r in reminders:
        if r["time"] == now:
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=f"Reminder: {r['text']}",
            )


async def _morning_schedule(context: ContextTypes.DEFAULT_TYPE):
    """Send a morning summary at the configured time."""
    if not OWNER_CHAT_ID:
        return

    now_str = datetime.datetime.utcnow().strftime("%H:%M")
    if now_str != SCHEDULE_TIME:
        return

    parts = [f"Good morning! Here's your summary for {datetime.date.today():%B %d, %Y}:\n"]

    # Reminders for today
    reminders = _load(REMINDERS_FILE)
    if reminders:
        parts.append("Today's reminders:")
        for r in reminders:
            parts.append(f"  {r['time']} — {r['text']}")
    else:
        parts.append("No reminders set.")

    # Recent expenses (last 7 days)
    expenses = _load(EXPENSES_FILE)
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    recent = [e for e in expenses if e.get("date", "") >= week_ago]
    if recent:
        total = sum(e.get("amount", 0) for e in recent)
        parts.append(f"\nSpent this week: ${total:.2f} across {len(recent)} expenses")

    # Note count
    notes = _load(NOTES_FILE)
    if notes:
        parts.append(f"\nYou have {len(notes)} saved notes.")

    await context.bot.send_message(
        chat_id=int(OWNER_CHAT_ID),
        text="\n".join(parts),
    )


# ---------------------------------------------------------------------------
# Feature 3: Receipt Scanning (GPT-4o Vision)
# ---------------------------------------------------------------------------

@owner_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """When a photo is sent, try to extract receipt info via OpenAI GPT-4o."""
    if not OPENAI_API_KEY:
        await update.message.reply_text(
            "Receipt scanning requires an OpenAI API key.\n"
            "Set OPENAI_API_KEY in your .env file."
        )
        return

    await update.message.reply_text("Analyzing receipt...")

    photo = update.message.photo[-1]  # highest resolution
    file = await photo.get_file()
    img_bytes = BytesIO()
    await file.download_to_memory(img_bytes)
    b64_image = base64.b64encode(img_bytes.getvalue()).decode()

    import aiohttp
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract receipt information from this image. "
                                "Return ONLY valid JSON with these fields:\n"
                                '{"store": "...", "date": "YYYY-MM-DD", '
                                '"items": [{"name": "...", "price": 0.00}], '
                                '"total": 0.00, "category": "..."}\n'
                                "Category should be one of: food, transport, "
                                "shopping, entertainment, health, utilities, other.\n"
                                "If you can't read the receipt, return "
                                '{"error": "Could not read receipt"}'
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 1000,
        }
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        async with session.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            if resp.status != 200:
                err = await resp.text()
                await update.message.reply_text(f"OpenAI API error: {err[:200]}")
                return
            result = await resp.json()

    content = result["choices"][0]["message"]["content"]
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        receipt = json.loads(content)
    except json.JSONDecodeError:
        await update.message.reply_text(
            f"Couldn't parse receipt data. Raw response:\n{content[:500]}"
        )
        return

    if "error" in receipt:
        await update.message.reply_text(f"Receipt scan failed: {receipt['error']}")
        return

    # Save expense
    expense = {
        "store": receipt.get("store", "Unknown"),
        "date": receipt.get("date", datetime.date.today().isoformat()),
        "total": float(receipt.get("total", 0)),
        "category": receipt.get("category", "other"),
        "items": receipt.get("items", []),
    }
    expenses = _load(EXPENSES_FILE)
    expenses.append(expense)
    _save(EXPENSES_FILE, expenses)

    items_text = "\n".join(
        f"  - {it['name']}: ${it['price']:.2f}" for it in expense["items"]
    ) if expense["items"] else "  (no items parsed)"

    await update.message.reply_text(
        f"Receipt logged!\n\n"
        f"Store: {expense['store']}\n"
        f"Date: {expense['date']}\n"
        f"Category: {expense['category']}\n"
        f"Items:\n{items_text}\n"
        f"Total: ${expense['total']:.2f}\n\n"
        f"Use /expenses or /spent week to see your spending."
    )


# ---------------------------------------------------------------------------
# Feature 4: News Summary
# ---------------------------------------------------------------------------

@owner_only
async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not NEWS_API_KEY:
        await update.message.reply_text(
            "News requires a NewsAPI key. Get one free at https://newsapi.org\n"
            "Then set NEWS_API_KEY in your .env file."
        )
        return

    await update.message.reply_text("Fetching news...")

    import aiohttp
    topics = NEWS_TOPICS.replace(",", " OR ")
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={topics}&sortBy=publishedAt&pageSize=5&language=en"
        f"&apiKey={NEWS_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await update.message.reply_text("Failed to fetch news.")
                return
            data = await resp.json()

    articles = data.get("articles", [])
    if not articles:
        await update.message.reply_text("No news articles found for your topics.")
        return

    lines = [f"News Summary ({NEWS_TOPICS}):\n"]
    for i, a in enumerate(articles[:5], 1):
        title = a.get("title", "No title")
        source = a.get("source", {}).get("name", "")
        url = a.get("url", "")
        desc = a.get("description", "")
        if desc and len(desc) > 120:
            desc = desc[:120] + "..."
        lines.append(f"{i}. {title}\n   {source}\n   {desc}\n   {url}\n")

    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Feature 5: Expense Analysis
# ---------------------------------------------------------------------------

@owner_only
async def cmd_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expenses = _load(EXPENSES_FILE)
    if not expenses:
        await update.message.reply_text(
            "No expenses logged yet. Send me a receipt photo to get started!"
        )
        return

    # Show last 10
    recent = expenses[-10:]
    lines = ["Recent expenses:\n"]
    for e in recent:
        lines.append(
            f"  {e['date']} | {e['store']} | {e['category']} | ${e['total']:.2f}"
        )
    total = sum(e.get("total", 0) for e in expenses)
    lines.append(f"\nAll-time total: ${total:.2f} ({len(expenses)} expenses)")
    await update.message.reply_text("\n".join(lines))


@owner_only
async def cmd_spent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    period = context.args[0].lower() if context.args else "week"
    expenses = _load(EXPENSES_FILE)
    if not expenses:
        await update.message.reply_text("No expenses logged yet.")
        return

    today = datetime.date.today()
    if period == "week":
        cutoff = (today - datetime.timedelta(days=7)).isoformat()
        label = "this week"
    elif period == "month":
        cutoff = today.replace(day=1).isoformat()
        label = "this month"
    else:
        cutoff = "0000-00-00"
        label = "all time"

    filtered = [e for e in expenses if e.get("date", "") >= cutoff]
    if not filtered:
        await update.message.reply_text(f"No expenses found for {label}.")
        return

    # Group by category
    by_cat = {}
    for e in filtered:
        cat = e.get("category", "other")
        by_cat[cat] = by_cat.get(cat, 0) + e.get("total", 0)

    total = sum(by_cat.values())
    lines = [f"Spending {label}: ${total:.2f}\n\nBy category:"]
    for cat, amount in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = (amount / total * 100) if total else 0
        bar = "█" * int(pct / 5)
        lines.append(f"  {cat:<15} ${amount:>8.2f}  {pct:>5.1f}%  {bar}")

    lines.append(f"\n{len(filtered)} expenses in period")
    await update.message.reply_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not TOKEN:
        print("ERROR: Set TELEGRAM_BOT_TOKEN in .env file")
        print("Get a token from @BotFather on Telegram")
        return

    _ensure_data()

    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("note", cmd_note))
    app.add_handler(CommandHandler("notes", cmd_notes))
    app.add_handler(CommandHandler("delnote", cmd_delnote))
    app.add_handler(CommandHandler("remind", cmd_remind))
    app.add_handler(CommandHandler("reminders", cmd_reminders))
    app.add_handler(CommandHandler("delremind", cmd_delremind))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("expenses", cmd_expenses))
    app.add_handler(CommandHandler("spent", cmd_spent))

    # Photos → receipt scanning
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Plain text → quick notes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_note))

    # Scheduled jobs — check every 60 seconds
    job_queue = app.job_queue
    job_queue.run_repeating(_send_reminders, interval=60, first=10)
    job_queue.run_repeating(_morning_schedule, interval=60, first=10)

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
