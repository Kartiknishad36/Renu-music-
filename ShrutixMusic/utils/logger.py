# ShrutixMusic/utils/logger.py
"""
PREMIUM LOGGER – Full Detail + DP (Profile Photo)
Logs to LOGGER_ID with user profile photo, group photo, song thumbnail, full who/what/where/when UTC.
"""

import html
import os
import time
from datetime import datetime
from typing import Optional

from pyrogram.enums import ParseMode
from pyrogram.types import Message, User

from ShrutixMusic import nand
from ShrutixMusic.utils.database import is_on_off
from config import LOGGER_ID

_PHOTO_CACHE = "cache/log_photos"
os.makedirs(_PHOTO_CACHE, exist_ok=True)

DEDUPE_SECONDS = 8
_recent_logs = {}


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _already(key: str) -> bool:
    now = time.time()
    for k in [x for x, t in _recent_logs.items() if now - t > DEDUPE_SECONDS]:
        _recent_logs.pop(k, None)
    if key in _recent_logs:
        return True
    _recent_logs[key] = now
    return False


async def _download_user_photo(user: User) -> Optional[str]:
    if not user:
        return None
    try:
        if not user.photo:
            return None
        path = await nand.download_media(
            user.photo.big_file_id,
            file_name=f"{_PHOTO_CACHE}/u_{user.id}.jpg",
        )
        return path
    except Exception:
        try:
            async for photo in nand.get_chat_photos(user.id, limit=1):
                path = await nand.download_media(
                    photo.file_id,
                    file_name=f"{_PHOTO_CACHE}/u_{user.id}.jpg",
                )
                return path
        except Exception:
            return None
    return None


async def _send_log_photo(photo: Optional[str], caption: str, fallback_text: Optional[str] = None):
    if not LOGGER_ID:
        return
    caption = caption[:1020]
    try:
        if photo and os.path.isfile(str(photo)):
            await nand.send_photo(
                chat_id=LOGGER_ID,
                photo=photo,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
            return
    except Exception:
        pass
    try:
        await nand.send_message(
            chat_id=LOGGER_ID,
            text=fallback_text or caption,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def play_logs(message: Message, streamtype: str = "Unknown"):
    if not await is_on_off(2):
        return
    if not message or not message.from_user:
        return
    if message.chat and message.chat.id == LOGGER_ID:
        return

    user = message.from_user
    chat = message.chat
    query = ""
    try:
        if message.text and len(message.text.split(None, 1)) > 1:
            query = message.text.split(None, 1)[1][:120]
        elif message.command and len(message.command) > 1:
            query = " ".join(message.command[1:])[:120]
    except Exception:
        query = "N/A"

    dedupe_key = f"play:{chat.id if chat else 0}:{user.id}:{query[:30]}"
    if _already(dedupe_key):
        return

    uname = f"@{user.username}" if user.username else "No username"
    chat_title = html.escape(chat.title or "Private") if chat else "Private"
    chat_uname = f"@{chat.username}" if chat and chat.username else "No username"
    chat_id = chat.id if chat else 0

    caption = (
        f"<b>🎵 {nand.mention} ᴘʟᴀʏ ʟᴏɢ</b>\n"
        f"{'─'*22}\n\n"
        f"<b>👤 User</b>\n"
        f"├ Name : {user.mention}\n"
        f"├ ID   : <code>{user.id}</code>\n"
        f"└ User : {uname}\n\n"
        f"<b>📍 Group</b>\n"
        f"├ Title: {chat_title}\n"
        f"├ ID   : <code>{chat_id}</code>\n"
        f"└ Link : {chat_uname}\n\n"
        f"<b>🎶 Track</b>\n"
        f"├ Query : <code>{html.escape(query) or 'N/A'}</code>\n"
        f"└ Type  : <b>{html.escape(str(streamtype))}</b>\n\n"
        f"<b>🕐 Time</b> : <code>{_now()}</code>"
    )

    photo = await _download_user_photo(user)
    await _send_log_photo(photo, caption, fallback_text=caption)


async def song_play_log(
    chat_id: int,
    chat_title: str,
    user_id: int,
    user_name: str,
    title: str,
    duration: str,
    vidid: str = "",
    streamtype: str = "audio",
    thumb_path: Optional[str] = None,
):
    if not await is_on_off(2):
        return
    if chat_id == LOGGER_ID:
        return

    dedupe_key = f"song:{chat_id}:{vidid or title[:20]}"
    if _already(dedupe_key):
        return

    yt_link = (
        f"https://www.youtube.com/watch?v={vidid}"
        if vidid and len(str(vidid)) == 11
        else "N/A"
    )
    caption = (
        f"<b>🎧 {nand.mention} sᴏɴɢ ᴘʟᴀʏɪɴɢ</b>\n"
        f"{'─'*22}\n\n"
        f"<b>🎶 Song</b>\n"
        f"├ Title : <b>{html.escape(str(title)[:60])}</b>\n"
        f"├ Dur   : <code>{html.escape(str(duration))}</code>\n"
        f"├ Type  : {html.escape(str(streamtype))}\n"
        f"└ YT    : {yt_link}\n\n"
        f"<b>👤 Played By</b>\n"
        f"├ Name : {html.escape(str(user_name))}\n"
        f"└ ID   : <code>{user_id}</code>\n\n"
        f"<b>📍 Group</b>\n"
        f"├ Title: {html.escape(str(chat_title or chat_id))}\n"
        f"└ ID   : <code>{chat_id}</code>\n\n"
        f"<b>🕐 Time</b> : <code>{_now()}</code>"
    )

    photo = thumb_path
    if not photo or not os.path.isfile(str(photo)):
        try:
            user = await nand.get_users(user_id)
            photo = await _download_user_photo(user)
        except Exception:
            photo = None

    await _send_log_photo(photo, caption, fallback_text=caption)


async def start_log(message: Message, action: str = "started the bot"):
    if not await is_on_off(2):
        return
    if not message or not message.from_user:
        return

    user = message.from_user
    chat = message.chat
    uname = f"@{user.username}" if user.username else "No username"
    chat_info = "Private Chat"
    if chat and getattr(chat.type, "name", "") in ("GROUP", "SUPERGROUP"):
        chat_info = f"{html.escape(chat.title or '')} (<code>{chat.id}</code>)"

    caption = (
        f"<b>🚀 {nand.mention} sᴛᴀʀᴛ ʟᴏɢ</b>\n"
        f"{'─'*22}\n\n"
        f"<b>👤 User</b>\n"
        f"├ Name : {user.mention}\n"
        f"├ ID   : <code>{user.id}</code>\n"
        f"└ User : {uname}\n\n"
        f"<b>📍 Where</b> : {chat_info}\n"
        f"<b>📌 Action</b> : {html.escape(action)}\n"
        f"<b>🕐 Time</b>   : <code>{_now()}</code>"
    )

    photo = await _download_user_photo(user)
    await _send_log_photo(photo, caption, fallback_text=caption)


async def action_log(
    title: str,
    body: str,
    user: Optional[User] = None,
    photo_path: Optional[str] = None,
):
    if not LOGGER_ID:
        return
    caption = f"<b>{title}</b>\n{'─'*22}\n\n{body}\n\n<b>🕐</b> <code>{_now()}</code>"
    photo = photo_path
    if not photo and user:
        photo = await _download_user_photo(user)
    await _send_log_photo(photo, caption, fallback_text=caption)
