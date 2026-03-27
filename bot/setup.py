"""
Interactive setup script — creates .env file by prompting for tokens.
Run: python setup.py
"""

import os
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"

def main():
    print("=" * 40)
    print("  PA Bot Setup")
    print("=" * 40)
    print()

    if ENV_PATH.exists():
        ans = input(".env already exists. Overwrite? (y/n): ").strip().lower()
        if ans != "y":
            print("Cancelled.")
            return

    print("Paste each value and press Enter.")
    print("Press Enter to skip optional ones.\n")

    token = input("1. Telegram Bot Token (from @BotFather): ").strip()
    if not token:
        print("Bot token is required! Get one from @BotFather on Telegram.")
        return

    chat_id = input("2. Your Telegram Chat ID (from @userinfobot): ").strip()
    openai_key = input("3. OpenAI API Key (optional, for receipts): ").strip()
    news_key = input("4. NewsAPI Key (optional, for news): ").strip()
    schedule = input("5. Morning summary time in HH:MM UTC (default 07:00): ").strip() or "07:00"
    topics = input("6. News topics, comma-separated (default technology,AI,programming): ").strip() or "technology,AI,programming"

    contents = f"""TELEGRAM_BOT_TOKEN={token}
OWNER_CHAT_ID={chat_id}
OPENAI_API_KEY={openai_key}
NEWS_API_KEY={news_key}
SCHEDULE_TIME={schedule}
NEWS_TOPICS={topics}
"""

    ENV_PATH.write_text(contents)
    print(f"\n.env created at {ENV_PATH}")
    print("\nNow run:  python pa_bot.py")

if __name__ == "__main__":
    main()
