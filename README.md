# Telegram Forwarding Bot

A lightweight Python service that monitors one Telegram source channel and
forwards every new message and album to one or more configured destinations,
using a Telegram **user-account session** (not a bot token). Built with
[Telethon](https://docs.telethon.dev/).

---

## What It Does

- Listens to a configured Telegram source chat using your personal user account.
- Forwards every single message and every media album to all configured destinations.
- Preserves Telegram's native forwarding (no re-upload, no content modification).
- Handles FloodWait, forwarding restrictions, and per-destination RPC errors
  gracefully without crashing.
- Runs as a `systemd` service with automatic restart on failure.

---

## Telegram-Side Setup

1. Go to <https://my.telegram.org/apps>.
2. Log in with your Telegram phone number.
3. Create a new application (any name/platform is fine).
4. Copy the **App api_id** and **App api_hash** values into `.env`.

---

## Environment Variables

| Variable         | Required | Default | Description |
|------------------|----------|---------|-------------|
| `API_ID`         | ✅       | —       | Telegram API ID from my.telegram.org |
| `API_HASH`       | ✅       | —       | Telegram API hash from my.telegram.org |
| `PHONE_NUMBER`   | ✅       | —       | Your phone number in international format (`+12025551234`) |
| `SESSION_FILE`   | ✅       | —       | Path (without `.session`) for the session file, e.g. `data/telegram_forwarder` |
| `SOURCE_CHAT`    | ✅       | —       | Source channel: `@username`, invite link, or numeric peer ID (see note below) |
| `DESTINATIONS`   | ✅       | —       | Comma-separated destinations: `@group,@channel,-1001234567890` |
| `FORWARD_SILENT` | ❌       | `false` | Set to `true` to forward without notification sound |
| `LOG_LEVEL`      | ❌       | `INFO`  | Verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### SOURCE_CHAT and DESTINATIONS — accepted formats

| Format | Example | Notes |
|--------|---------|-------|
| `@username` | `@mychannel` | Works for public channels/groups |
| Invite link | `https://t.me/+AbcXyz` | Works for private channels |
| Numeric ID with `-100` prefix | `-1001898815959` | As returned by most ID bots |
| Bare numeric ID | `1898815959` | As returned by some ID bots (bot auto-converts) |

> **Important:** The logged-in account must be a **member** of the source channel.
> If it is not a member, entity resolution will fail at startup.

---

## Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd forwarding_bot_gemini
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

### 3. Install Dependencies

```bash
# Linux / macOS
venv/bin/pip install -r requirements.txt

# Windows
venv\Scripts\pip install -r requirements.txt
```

### 4. Configure

```bash
cp .env.example .env
nano .env   # or open in any editor — fill in all required values
```

---

## One-Time Login (QR Code — recommended)

The bot service is non-interactive. Authenticate once using the QR login helper:

```bash
# Linux / macOS
venv/bin/python login_qr.py

# Windows
venv\Scripts\python login_qr.py
```

A QR code will appear in the terminal. Scan it with the Telegram app already
installed on your phone:

- **Android:** Telegram → ☰ Menu → **Settings → Devices → Scan QR code**
- **iPhone:** Telegram → **Settings → Devices → Link Desktop Device**

The QR code auto-refreshes every 25 seconds. If 2FA is enabled, the script
will prompt for your password after the scan.

Once done, the session is saved to the path in `SESSION_FILE` and the bot is
ready to run.

### Alternative: phone-code login

If QR login is not suitable, `login.py` requests a code via the Telegram app
or SMS. Note: code delivery depends on your network and account configuration.

```bash
venv/bin/python login.py   # or venv\Scripts\python login.py on Windows
```

---

## Manual Foreground Run

```bash
# Linux / macOS
venv/bin/python bot.py

# Windows
venv\Scripts\python bot.py
```

Press **Ctrl-C** to stop. All logs go to stdout.

---

## systemd Installation (Linux VPS)

### 1. Edit the Service File

Open `forwarding_bot.service` and replace the three placeholders:

- `YOUR_LINUX_USER` — the OS user that will run the bot
- `/path/to/forwarding_bot_gemini` — absolute path to the project directory

### 2. Install and Enable

```bash
sudo cp forwarding_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable forwarding_bot
sudo systemctl start forwarding_bot
```

### 3. Common Commands

| Action  | Command |
|---------|---------|
| Start   | `sudo systemctl start forwarding_bot` |
| Stop    | `sudo systemctl stop forwarding_bot` |
| Restart | `sudo systemctl restart forwarding_bot` |
| Status  | `sudo systemctl status forwarding_bot` |
| Logs    | `sudo journalctl -u forwarding_bot -f` |

---

## Project Structure

```
forwarding_bot_gemini/
├── bot.py                    # main service (run under systemd)
├── login_qr.py               # one-time QR-code login helper (recommended)
├── login.py                  # one-time phone-code login helper (alternative)
├── login_pyrogram.py         # alternative login via Pyrogram library
├── requirements.txt
├── .env                      # secrets — never commit
├── .env.example              # template
├── .gitignore
├── forwarding_bot.service    # systemd unit template
├── prd.md
├── README.md
└── venv/                     # virtualenv (not committed)
```
