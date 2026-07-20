"""
Telegram delivery layer for the pure-Python path (main.py).
Not used when running the n8n hybrid - n8n's Telegram node replaces this.
"""
import asyncio
import logging
import re
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import RetryAfter, TelegramError
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, PRIORITY
from modules.state import log_alert

log = logging.getLogger(__name__)
_bot = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env")
        _bot = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot


def _escape_md(text: str) -> str:
    chars = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(f"([{re.escape(chars)}])", r"\\\1", text)


async def _send(text: str, parse_mode=ParseMode.MARKDOWN_V2):
    bot = get_bot()
    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=False,
        )
    except RetryAfter as e:
        log.warning("Telegram rate limit: sleeping %ds", e.retry_after)
        await asyncio.sleep(e.retry_after + 1)
        await _send(text, parse_mode)
    except TelegramError as e:
        log.error("Telegram send failed: %s", e)


def send_alert(module: str, priority: str, title: str, body: str = "", url: str = "", action: str = ""):
    emoji = PRIORITY.get(priority, "⚪")
    parts = [f"{emoji} *{_escape_md(priority)}* \\| {_escape_md(module)}"]
    parts.append(f"\n*{_escape_md(title)}*")
    if body:
        if len(body) > 600:
            body = body[:597] + "..."
        parts.append(f"\n{_escape_md(body)}")
    if action:
        parts.append(f"\n\n📝 *Angle:* {_escape_md(action)}")
    if url:
        parts.append(f"\n\n[Source]({url})")
    text = "".join(parts)
    asyncio.run(_send(text))
    log_alert(module, priority, title)


def send_digest(title: str, body: str):
    text = f"📊 {title}\n\n{body}"
    if len(text) > 4000:
        text = text[:3997] + "..."
    asyncio.run(_send(text, parse_mode=None))
