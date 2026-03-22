"""
Pyrogram-based one-time login helper
=====================================
Alternative to login.py (Telethon). Uses Pyrogram's MTProto implementation.

Usage:
    pip install pyrogram tgcrypto
    python login_pyrogram.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import (
    AuthKeyUnregistered,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    SessionPasswordNeeded,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
)

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"[ERROR] {name} is missing or empty in .env", file=sys.stderr)
        sys.exit(1)
    return val


async def main() -> None:
    api_id       = int(_require("API_ID"))
    api_hash     = _require("API_HASH")
    phone        = _require("PHONE_NUMBER")
    session_file = _require("SESSION_FILE")

    # Use a sibling session name so it doesn't clash with the Telethon session
    pyrogram_session = session_file + "_pyrogram"

    session_dir = os.path.dirname(session_file)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    print(f"Phone        : {phone}")
    print(f"Session file : {pyrogram_session}.session")
    print()

    app = Client(
        name=pyrogram_session,
        api_id=api_id,
        api_hash=api_hash,
    )

    await app.connect()

    # ------------------------------------------------------------------ #
    # Check if already authorized                                          #
    # ------------------------------------------------------------------ #
    already_authorized = False
    try:
        me = await app.get_me()
        already_authorized = True
    except (AuthKeyUnregistered, Exception):
        already_authorized = False

    if already_authorized:
        print(f"Already logged in as {me.username or me.first_name} (id={me.id}).")
        print("Nothing to do. You can start bot.py.")
        await app.disconnect()
        return

    # ------------------------------------------------------------------ #
    # Send login code                                                      #
    # ------------------------------------------------------------------ #
    print("Requesting login code from Telegram via Pyrogram…")
    try:
        sent = await app.send_code(phone)
    except PhoneNumberInvalid:
        print("[ERROR] Phone number is invalid. Check PHONE_NUMBER in .env (must include +).")
        await app.disconnect()
        sys.exit(1)
    except PhoneNumberUnoccupied:
        print("[ERROR] This phone number has no Telegram account.")
        await app.disconnect()
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to send code: {e}")
        await app.disconnect()
        sys.exit(1)

    type_map = {
        "app":        "📱  Telegram app — open Telegram on your phone/desktop and check the chat named 'Telegram'",
        "sms":        "💬  SMS — check your text messages",
        "call":       "📞  Voice call to your phone",
        "flash_call": "📞  Flash call (missed call — code = last digits of caller ID)",
    }
    code_type = sent.type.value if hasattr(sent.type, "value") else str(sent.type)
    delivery  = type_map.get(code_type, f"method: {code_type}")
    print(f"\n✉  Code sent via: {delivery}\n")

    # ------------------------------------------------------------------ #
    # Optionally resend via SMS/call                                       #
    # ------------------------------------------------------------------ #
    print("If you did NOT receive the code, press Enter without typing anything")
    print("to request a resend via SMS or voice call instead.")
    print()
    code = input("Enter the 5-digit code: ").strip()

    if not code:
        print("\nResending code via next available method…")
        try:
            sent = await app.resend_code(phone, sent.phone_code_hash)
            code_type2 = sent.type.value if hasattr(sent.type, "value") else str(sent.type)
            print(f"✉  New code sent via: {type_map.get(code_type2, code_type2)}\n")
        except Exception as e:
            print(f"[WARNING] Resend failed: {e}")
        code = input("Enter the 5-digit code: ").strip()

    # ------------------------------------------------------------------ #
    # Sign in                                                              #
    # ------------------------------------------------------------------ #
    try:
        await app.sign_in(phone, sent.phone_code_hash, code)
    except PhoneCodeInvalid:
        print("\n[ERROR] Incorrect code. Please run this script again.")
        await app.disconnect()
        sys.exit(1)
    except PhoneCodeExpired:
        print("\n[ERROR] Code expired. Please run this script again.")
        await app.disconnect()
        sys.exit(1)
    except SessionPasswordNeeded:
        print("\nTwo-step verification is enabled on this account.")
        password = input("Enter your 2FA password: ").strip()
        await app.check_password(password)

    me = await app.get_me()
    print()
    print(f"✓ Logged in as {me.username or me.first_name} (id={me.id})")
    print(f"✓ Pyrogram session saved to {pyrogram_session}.session")

    await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
