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
| `SOURCE_CHAT`    | ✅       | —       | Source channel: `@username`, invite link, or numeric peer ID |
| `DESTINATIONS`   | ✅       | —       | Comma-separated destinations: `@group,@channel,-1001234567890` |
| `FORWARD_SILENT` | ❌       | `false` | Set to `true` to forward without notification sound |
| `LOG_LEVEL`      | ❌       | `INFO`  | Verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

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
venv/bin/pip install -r requirements.txt
```

### 4. Configure

```bash
cp .env.example .env
nano .env          # fill in all required values
```

---

## One-Time Login

The bot service itself is non-interactive. Run the login helper **once** on the
target machine to create the session file:

```bash
venv/bin/python login.py
```

Follow the prompts — enter the verification code sent to your Telegram app, and
your 2FA password if enabled. The session is saved to the path specified by
`SESSION_FILE`.

---

## Manual Foreground Run

```bash
venv/bin/python bot.py
```

Press **Ctrl-C** to stop. Logs go to stdout.

---

## systemd Installation

### 1. Edit the Service File

Open `forwarding_bot.service` and replace:

- `YOUR_LINUX_USER` — the OS user that will run the bot
- `/path/to/forwarding_bot_gemini` — absolute path to the project directory (×3)

### 2. Install and Enable

```bash
sudo cp forwarding_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable forwarding_bot
sudo systemctl start forwarding_bot
```

### 3. View Logs

```bash
sudo journalctl -u forwarding_bot -f
```

### 4. Common Commands

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
├── login.py                  # one-time interactive login helper
├── requirements.txt
├── .env                      # secrets — never commit
├── .env.example              # template
├── .gitignore
├── forwarding_bot.service    # systemd unit template
├── prd.md
├── README.md
└── venv/                     # virtualenv (not committed)
```
