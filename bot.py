"""
Telegram Forwarding Bot
=======================
Continuously monitors a Telegram source chat and forwards every new
message / album to all configured destinations.

Run as a systemd service (see forwarding_bot.service).
For the one-time interactive login, use login.py instead.
"""

import asyncio
import logging
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import (
    ChatForwardsRestrictedError,
    FloodWaitError,
    RPCError,
    SessionPasswordNeededError,
    UnauthorizedError,
)
from telethon.tl.types import Message

# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------

load_dotenv()


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        logging.critical("Required environment variable %s is missing or empty.", name)
        sys.exit(1)
    return val


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def load_config() -> dict:
    cfg = {
        "api_id": int(_require("API_ID")),
        "api_hash": _require("API_HASH"),
        "phone": _require("PHONE_NUMBER"),
        "session_file": _require("SESSION_FILE"),
        "source_chat": _require("SOURCE_CHAT"),
        "destinations_raw": _require("DESTINATIONS"),
        "forward_silent": _optional("FORWARD_SILENT", "false").lower() == "true",
        "log_level": _optional("LOG_LEVEL", "INFO").upper(),
    }
    cfg["destinations"] = [d.strip() for d in cfg["destinations_raw"].split(",") if d.strip()]
    if not cfg["destinations"]:
        logging.critical("DESTINATIONS is set but contains no valid entries.")
        sys.exit(1)
    return cfg


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(level: str) -> None:
    numeric = getattr(logging, level, logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------------------
# Forward helper with FloodWait / error handling
# ---------------------------------------------------------------------------

MAX_FLOOD_RETRIES = 5


async def forward_to(client: TelegramClient, dest_entity, messages, silent: bool) -> bool:
    """Forward *messages* to *dest_entity*. Returns True on success."""
    for attempt in range(1, MAX_FLOOD_RETRIES + 1):
        try:
            await client.forward_messages(
                entity=dest_entity,
                messages=messages,
                silent=silent,
            )
            return True
        except FloodWaitError as e:
            if attempt == MAX_FLOOD_RETRIES:
                logging.error(
                    "FloodWait: hit retry limit (%d) for destination %s. Giving up.",
                    MAX_FLOOD_RETRIES,
                    dest_entity,
                )
                return False
            logging.warning(
                "FloodWait: sleeping %d s (attempt %d/%d) for destination %s.",
                e.seconds,
                attempt,
                MAX_FLOOD_RETRIES,
                dest_entity,
            )
            await asyncio.sleep(e.seconds + 1)
        except ChatForwardsRestrictedError:
            logging.warning(
                "Forward restricted by Telegram for destination %s — skipping.",
                dest_entity,
            )
            return False
        except RPCError as e:
            logging.error(
                "RPC error forwarding to %s (attempt %d/%d): %s",
                dest_entity,
                attempt,
                MAX_FLOOD_RETRIES,
                e,
            )
            return False
    return False


# ---------------------------------------------------------------------------
# Album / media-group buffering
# ---------------------------------------------------------------------------

ALBUM_TIMEOUT = 1.2  # seconds — Telegram groups arrive within ~1 s


class AlbumBuffer:
    """Collect messages belonging to the same grouped_id, then forward them all."""

    def __init__(self, client: TelegramClient, dest_entities: list, silent: bool):
        self._client = client
        self._dests = dest_entities
        self._silent = silent
        self._buffers: dict[int, list[Message]] = defaultdict(list)
        self._tasks: dict[int, asyncio.TimerHandle] = {}

    def add(self, message: Message) -> None:
        gid = message.grouped_id
        self._buffers[gid].append(message)
        # Reset / start the flush timer
        handle = self._tasks.get(gid)
        if handle:
            handle.cancel()
        loop = asyncio.get_event_loop()
        self._tasks[gid] = loop.call_later(
            ALBUM_TIMEOUT, lambda g=gid: asyncio.ensure_future(self._flush(g))
        )

    async def _flush(self, grouped_id: int) -> None:
        messages = self._buffers.pop(grouped_id, [])
        self._tasks.pop(grouped_id, None)
        if not messages:
            return
        # Sort by message id so they go in order
        messages.sort(key=lambda m: m.id)
        logging.info(
            "Forwarding album (grouped_id=%d, %d items) to %d destination(s).",
            grouped_id,
            len(messages),
            len(self._dests),
        )
        for dest in self._dests:
            ok = await forward_to(self._client, dest, messages, self._silent)
            if ok:
                logging.info("Album forwarded → %s", dest)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    cfg = load_config()
    setup_logging(cfg["log_level"])

    logging.info("=== Telegram Forwarding Bot starting ===")
    logging.info("Session file : %s", cfg["session_file"])
    logging.info("Source chat  : %s", cfg["source_chat"])
    logging.info("Destinations : %s", ", ".join(cfg["destinations"]))
    logging.info("Silent mode  : %s", cfg["forward_silent"])

    client = TelegramClient(cfg["session_file"], cfg["api_id"], cfg["api_hash"])

    await client.connect()

    # --- FR5 / NFR: authorisation check ---
    if not await client.is_user_authorized():
        logging.critical(
            "Session is not authorised. Run  python login.py  to complete the "
            "one-time login, then restart this service."
        )
        await client.disconnect()
        sys.exit(1)

    me = await client.get_me()
    logging.info("Logged in as %s (id=%s)", me.username or me.first_name, me.id)

    # --- FR5: resolve source and destination entities at startup ---
    try:
        source_entity = await client.get_entity(cfg["source_chat"])
        logging.info("Source resolved: %s (id=%s)", source_entity.title if hasattr(source_entity, "title") else source_entity, source_entity.id)
    except Exception as e:
        logging.critical("Cannot resolve SOURCE_CHAT '%s': %s", cfg["source_chat"], e)
        await client.disconnect()
        sys.exit(1)

    dest_entities = []
    for dest_str in cfg["destinations"]:
        try:
            entity = await client.get_entity(dest_str)
            dest_entities.append(entity)
            logging.info(
                "Destination resolved: %s (id=%s)",
                entity.title if hasattr(entity, "title") else entity,
                entity.id,
            )
        except Exception as e:
            logging.critical("Cannot resolve destination '%s': %s", dest_str, e)
            await client.disconnect()
            sys.exit(1)

    logging.info("Startup OK — listening for new messages.")

    album_buffer = AlbumBuffer(client, dest_entities, cfg["forward_silent"])

    @client.on(events.NewMessage(chats=source_entity))
    async def handler(event: events.NewMessage.Event) -> None:
        msg: Message = event.message
        logging.debug("New message id=%s grouped_id=%s", msg.id, msg.grouped_id)

        if msg.grouped_id:
            # Part of an album — buffer it
            album_buffer.add(msg)
            return

        # Single message — forward immediately
        logging.info("Forwarding message id=%s to %d destination(s).", msg.id, len(dest_entities))
        for dest in dest_entities:
            ok = await forward_to(client, dest, [msg], cfg["forward_silent"])
            if ok:
                logging.info("Message %s forwarded → %s", msg.id, dest)

    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        logging.info("Client disconnected. Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Interrupted by user.")
