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
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.tl.functions.auth import ResendCodeRequest

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"[ERROR] Required environment variable {name} is missing or empty.", file=sys.stderr)
        sys.exit(1)
    return val


def _delivery_description(sent_code) -> str:
    """Return a human-readable description of how the code was sent."""
    type_name = type(sent_code.type).__name__
    descriptions = {
        "SentCodeTypeApp":          "📱  Telegram app (check the Telegram app on your phone or desktop)",
        "SentCodeTypeSms":          "💬  SMS to your phone number",
        "SentCodeTypeCall":         "📞  Voice call to your phone number",
        "SentCodeTypeFlashCall":    "📞  Flash call (missed call — the code is the last digits of the caller ID)",
        "SentCodeTypeMissedCall":   "📞  Missed call — the code is the last digits of the caller ID",
        "SentCodeTypeEmailCode":    "📧  E-mail",
        "SentCodeTypeFragment":     "🔒  Fragment (anonymous number)",
    }
    return descriptions.get(type_name, f"unknown delivery type: {type_name}")


async def main() -> None:
    logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

    api_id   = int(_require("API_ID"))
    api_hash = _require("API_HASH")
    phone    = _require("PHONE_NUMBER")
    session_file = _require("SESSION_FILE")

    print(phone)

    # Ensure the data directory exists
    session_dir = os.path.dirname(session_file)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    print(f"Session file : {session_file}.session")
    print(f"Phone number : {phone}")
    print()

    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already logged in as {me.username or me.first_name} (id={me.id}).")
        print("Nothing to do. You can start bot.py.")
        await client.disconnect()
        return

    # ------------------------------------------------------------------ #
    # Send code and tell the user exactly where to look for it            #
    # ------------------------------------------------------------------ #
    print("Requesting login code from Telegram…")
    sent = await client.send_code_request(phone)
    print(f"\n  Code sent via: {_delivery_description(sent)}\n")

    # Offer resend if the user didn't receive it
    print("If you didn't receive the code, press Enter without typing anything")
    print("and we will request a new code via the next delivery method (SMS/call).")
    print()

    code = input("Enter the 5-digit code (or press Enter to resend): ").strip()

    if not code:
        print("\nResending code via the next available method…")
        try:
            sent = await client(ResendCodeRequest(phone, sent.phone_code_hash))
            print(f"✉  New code sent via: {_delivery_description(sent)}\n")
        except Exception as e:
            print(f"[WARNING] Could not resend: {e}")
        code = input("Enter the 5-digit code: ").strip()

    # ------------------------------------------------------------------ #
    # Sign in                                                              #
    # ------------------------------------------------------------------ #
    try:
        await client.sign_in(phone, code)
    except PhoneCodeInvalidError:
        print("\n[ERROR] The code you entered is incorrect. Please run login.py again.")
        await client.disconnect()
        sys.exit(1)
    except PhoneCodeExpiredError:
        print("\n[ERROR] The code has expired. Please run login.py again.")
        await client.disconnect()
        sys.exit(1)
    except SessionPasswordNeededError:
        print("\nTwo-step verification is enabled on this account.")
        password = input("Enter your 2FA password: ").strip()
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
