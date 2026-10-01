# ShrutixMusic/plugins/admins/volume.py
"""
VOLUME CONTROL – Full Detail Edition
Commands:
  /volume          – Show current volume panel
  /volume [1-200]  – Set volume (percentage)
"""

import asyncio
from typing import Dict

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ShrutixMusic import nand
from ShrutixMusic.core.mongo import mongodb
from ShrutixMusic.utils.decorators.language import language
from config import BANNED_USERS

volumedb = mongodb.volume
_VOLUME_CACHE: Dict[int, int] = {}


def _bar(pct: int, width: int = 16) -> str:
    pct = max(0, min(200, pct))
    filled = int(width * min(pct, 100) / 100)
    extra = "🔥" if pct > 100 else ""
    return "█" * filled + "░" * (width - filled) + extra


async def get_volume(chat_id: int) -> int:
    if chat_id in _VOLUME_CACHE:
        return _VOLUME_CACHE[chat_id]
    data = await volumedb.find_one({"chat_id": chat_id})
    val = int(data["volume"]) if data and "volume" in data else 100
    _VOLUME_CACHE[chat_id] = val
    return val


async def set_volume(chat_id: int, value: int) -> int:
    value = max(1, min(200, int(value)))
    _VOLUME_CACHE[chat_id] = value
    await volumedb.update_one(
        {"chat_id": chat_id},
        {"$set": {"volume": value}},
        upsert=True,
    )
    return value


def _volume_text(chat_id: int, value: int) -> str:
    level = "Low" if value < 40 else "Normal" if value <= 100 else "High / Boost"
    return (
        f"╔══════════════════════╗\n"
        f"║   🔊  VOLUME PANEL  ║\n"
        f"╚══════════════════════╝\n\n"
        f"Current : **{value}%**\n"
        f"Bar     : `{_bar(value)}`\n"
        f"Level   : {level}\n\n"
        f"Use `/volume 1-200` to change.\n"
        f"Example: `/volume 80` or `/volume 150`"
    )


@nand.on_message(filters.command(["volume", "vol"]) & filters.group & ~BANNED_USERS)
@language
async def volume_cmd(client, message: Message, _):
    chat_id = message.chat.id
    current = await get_volume(chat_id)

    if len(message.command) == 1:
        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔉 50%", callback_data=f"volset {chat_id} 50"),
                    InlineKeyboardButton("🔊 100%", callback_data=f"volset {chat_id} 100"),
                ],
                [
                    InlineKeyboardButton("🔊 130%", callback_data=f"volset {chat_id} 130"),
                    InlineKeyboardButton("🔥 180%", callback_data=f"volset {chat_id} 180"),
                ],
                [InlineKeyboardButton("🗑 Close", callback_data="close")],
            ]
        )
        return await message.reply_text(_volume_text(chat_id, current), reply_markup=buttons)

    try:
        new_val = int(message.command[1])
    except ValueError:
        return await message.reply_text("» Volume must be a number between **1** and **200**.")

    if new_val < 1 or new_val > 200:
        return await message.reply_text("» Allowed range: **1 – 200**")

    status = await message.reply_text(
        f"⚙️ Setting volume to **{new_val}%**...\nPlease wait..."
    )
    await asyncio.sleep(0.4)
    applied = await set_volume(chat_id, new_val)

    try:
        from ShrutixMusic.core.call import Call
        if hasattr(Call, "change_volume"):
            await Call.change_volume(chat_id, applied)
    except Exception:
        pass

    await status.edit_text(
        f"✅ **Volume updated**\n\n"
        f"Old → New : {current}% → **{applied}%**\n"
        f"Bar       : `{_bar(applied)}`\n"
        f"Chat ID   : `{chat_id}`\n\n"
        f"Preference saved. It will be used for future streams in this chat."
    )


@nand.on_callback_query(filters.regex(r"^volset ") & ~BANNED_USERS)
async def volume_cb(client, CallbackQuery):
    try:
        _, chat_id_s, val_s = CallbackQuery.data.split(None, 2)
        chat_id = int(chat_id_s)
        val = int(val_s)
    except Exception:
        return await CallbackQuery.answer("Invalid data", show_alert=True)

    if CallbackQuery.message.chat.id != chat_id:
        return await CallbackQuery.answer("Wrong chat", show_alert=True)

    applied = await set_volume(chat_id, val)
    await CallbackQuery.answer(f"Volume set to {applied}%")
    try:
        await CallbackQuery.message.edit_text(_volume_text(chat_id, applied))
    except Exception:
        pass
