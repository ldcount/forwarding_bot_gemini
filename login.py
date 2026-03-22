"""
One-time Telegram login helper
==============================
Run this script once on the machine where the bot will live to create the
Telethon session file.  After that, start bot.py (or the systemd service).

Usage:
    python login.py
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"[ERROR] Required environment variable {name} is missing or empty.", file=sys.stderr)
        sys.exit(1)
    return val


async def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

    api_id = int(_require("API_ID"))
    api_hash = _require("API_HASH")
    phone = _require("PHONE_NUMBER")
    session_file = _require("SESSION_FILE")

    # Ensure the data directory exists
    session_dir = os.path.dirname(session_file)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    print(f"Session will be saved to: {session_file}.session")
    print(f"Phone number            : {phone}")
    print()

    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already logged in as {me.username or me.first_name} (id={me.id}).")
        print("Nothing to do. You can start bot.py.")
        await client.disconnect()
        return

    print("Requesting login code from Telegram…")
    await client.send_code_request(phone)

    code = input("Enter the code you received (digits only): ").strip()

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        password = input("Two-step verification is enabled. Enter your password: ").strip()
        await client.sign_in(password=password)

    me = await client.get_me()
    print()
    print(f"✓ Logged in successfully as {me.username or me.first_name} (id={me.id}).")
    print(f"✓ Session saved to {session_file}.session")
    print()
    print("You can now start the bot:  python bot.py")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
