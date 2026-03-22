# Product Requirements Document

## Product Name

Telegram Forwarding Bot

## Objective

Build a Python service that listens to new messages from one specific Telegram channel, using a Telegram user account session, and forwards those messages to one or more configured Telegram destinations such as a group, channel, or specific users.

The tool must be deployable on a Linux VPS and runnable as a `systemd` service.

## Problem Statement

The operator needs an automated relay that forwards every new post from a source Telegram channel to a defined set of Telegram recipients. The source channel is not owned by the operator, but the operator’s Telegram user account does have access to it. A normal Telegram bot token is not sufficient for this use case because the source channel cannot be assumed to add the bot as an administrator or member.

## Users

- Primary user: VPS operator / Telegram account owner
- Secondary user: future coding agent or developer maintaining the project

## Core Use Case

1. The operator creates Telegram API credentials at `my.telegram.org`.
2. The operator configures the project via `.env`.
3. The service starts under `systemd`.
4. The service monitors one configured source channel.
5. Each new message or album is forwarded to all configured destinations.

## Functional Requirements

### FR1. Source Monitoring

- The system must monitor exactly one configured Telegram source chat.
- The source chat may be identified by username, invite link, or numeric peer ID.
- The source must be accessible to the logged-in Telegram user account.

### FR2. Destination Forwarding

- The system must forward incoming posts to one or more configured destinations.
- Destinations may be usernames, invite links, or numeric peer IDs.
- Destinations may include Telegram groups, channels, or individual Telegram users.
- The system must support multiple destinations from a single configuration value.

### FR3. Message Types

- The system must forward standard single messages.
- The system must forward Telegram albums/media groups as grouped forwards.
- The system must preserve Telegram’s native forwarding behavior instead of re-uploading or re-creating content.

### FR4. Login Flow

- The login flow uses **QR code authentication** via `login_qr.py`.
- The operator runs `python login_qr.py` once on the target machine.
- A QR code is printed to the terminal and must be scanned using the Telegram app:
  - Android: Settings → Devices → Scan QR code
  - iOS: Settings → Devices → Link Desktop Device
- The QR code auto-refreshes every 25 seconds if not scanned in time.
- If two-step verification (2FA) is enabled, the script prompts for the password after the scan.
- On success, a Telethon session file is saved to the path configured in `SESSION_FILE`.
- Phone-code delivery (`login.py`) is also included as an alternative but phone-code delivery may be unavailable depending on network or account configuration.
- QR login does not require SMS delivery and works without receiving any code.

### FR5. Runtime Validation

- The runtime command must refuse to start if the session is not authorized.
- The runtime command must refuse to start if required forwarding configuration is missing.
- The system must resolve the source chat and all destinations during startup and fail fast if any are invalid or unreachable.

### FR6. Logging

- The system must log startup, login success, and forwarding activity.
- The system must log forwarding failures with enough detail to diagnose the failed destination.
- The system must log Telegram rate-limit delays such as flood waits.
- Logging must go to stdout/stderr so `systemd`/`journalctl` can capture it.

### FR7. Service Operation

- The application must run continuously until disconnected or stopped.
- The project must include a ready-to-use `systemd` service file.
- The service must restart automatically on failure.

## Non-Functional Requirements

### NFR1. Language and Runtime

- Python 3.11+ compatible, preferably Python 3.12
- Use a dedicated virtual environment inside the project directory

### NFR2. Dependencies

- Use a Telegram client library of your choice.
- Keep dependencies minimal and production-appropriate

### NFR3. Project Layout

- Initialize a local git repository
- Include a `.gitignore`

### NFR4. Configuration

- Configuration must be supplied through environment variables and `.env`
- The project must include `.env.example`
- Relative file paths in config should resolve from the project root

### NFR5. Safety and Compliance

- The system must not attempt to bypass Telegram forwarding restrictions or protected-content restrictions
- If Telegram rejects a forward due to platform restrictions, the system must log the event and continue

## Required Configuration

The coding agent should implement support for these environment variables:

- `API_ID`
- `API_HASH`
- `PHONE_NUMBER`
- `SESSION_FILE`
- `SOURCE_CHAT`
- `DESTINATIONS`
- `FORWARD_SILENT`
- `LOG_LEVEL`

### Configuration Notes

- `DESTINATIONS` should be a comma-separated list
- `SESSION_FILE` should represent the session path without requiring the user to manually manage the `.session` suffix
- `FORWARD_SILENT` should default to `false`
- `LOG_LEVEL` should default to `INFO`

## Error Handling Requirements

- Handle invalid or missing environment variables with explicit errors
- Handle unauthorized session state with an actionable message
- Handle entity-resolution failures at startup
- Handle Telegram `FloodWait` responses by sleeping and retrying a limited number of times
- Handle destination-specific RPC failures without crashing the whole service
- Handle forwarding-restricted messages without retry loops

## Deployment Requirements

The project must include:

- `requirements.txt`
- `.gitignore`
- `.env.example`
- `README.md`
- `prd.md`

## README Requirements

The README must document:

- what the tool does
- required Telegram-side setup at `my.telegram.org`
- environment variables
- virtualenv setup
- dependency installation
- one-time login procedure
- manual foreground run
- `systemd` installation and management

## Out of Scope

- QR login
- Message filtering by keyword, author, or media type
- Content transformation or rewriting
- Database persistence
- Web dashboard
- Automatic destination management via UI
- Any mechanism intended to bypass Telegram restrictions
