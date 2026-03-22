"""
QR-code-based Telegram login
==============================
No phone code needed — just scan the QR code with the Telegram app
already installed on your phone.

How to scan:
  Android:  Telegram → Settings (☰) → Devices → Scan QR code
  iPhone:   Telegram → Settings → Devices → Link Desktop Device
  Desktop:  Works even if you only open Telegram on your phone

Usage:
    python login_qr.py
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

try:
    import qrcode
except ImportError:
    print("[ERROR] Missing 'qrcode' library. Run:  pip install qrcode", file=sys.stderr)
    sys.exit(1)

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"[ERROR] {name} is missing or empty in .env", file=sys.stderr)
        sys.exit(1)
    return val


def print_qr(url: str) -> None:
    """Print a scannable QR code to the terminal."""
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    # print_ascii with invert=True gives a white-on-dark QR that most cameras read well
    qr.print_ascii(invert=True)


async def main() -> None:
    api_id       = int(_require("API_ID"))
    api_hash     = _require("API_HASH")
    session_file = _require("SESSION_FILE")

    session_dir  = os.path.dirname(session_file)
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)

    client = TelegramClient(session_file, api_id, api_hash)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already logged in as {me.username or me.first_name} (id={me.id}).")
        print("Nothing to do. You can start bot.py.")
        await client.disconnect()
        return

    print("=" * 60)
    print("  TELEGRAM QR LOGIN")
    print("=" * 60)
    print()
    print("  1. Open Telegram on your phone")
    print("  2. Go to:  Settings → Devices → Scan QR code")
    print("     (iPhone: Settings → Devices → Link Desktop Device)")
    print("  3. Point the camera at the QR code below")
    print()

    me = None
    while me is None:
        # Generate a fresh QR login token (valid for ~30 s)
        qr_login = await client.qr_login()

        print_qr(qr_login.url)
        print()
        print("Waiting for scan… (QR refreshes automatically if it expires)")
        print()

        try:
            # Wait up to 25 s for the user to scan
            await qr_login.wait(25)
            me = await client.get_me()

        except asyncio.TimeoutError:
            # QR expired — loop and print a new one
            print("QR code expired — generating a new one…\n")
            continue

        except SessionPasswordNeededError:
            # 2FA is enabled
            print()
            print("Two-step verification is enabled on this account.")
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
