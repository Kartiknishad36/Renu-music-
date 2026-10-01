# ShrutixMusic/plugins/tools/tagall.py
"""
Premium TagAll system for groups.
Commands:
  /tagall [message]     – Tag everyone with optional custom text
  /tagstop / cancel     – Stop ongoing tagall
  /tagspam [text]       – Spam tag with text (admin only)
  /tagbomb [count]      – Bomb tag N times (max 5)
"""
import asyncio
import time
from typing import List

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter, ChatType
from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ShrutixMusic import nand
from ShrutixMusic.misc import SUDOERS
from config import BANNED_USERS

# In-memory stop flags per chat
_TAG_RUNNING: dict = {}
_TAG_STOP: dict = {}


def _is_admin_or_sudo(message: Message) -> bool:
    if message.from_user and message.from_user.id in SUDOERS:
        return True
    return False


async def _get_members(chat_id: int) -> List:
    members = []
    try:
        async for member in nand.get_chat_members(chat_id, filter=ChatMembersFilter.SEARCH):
            if member.user and not member.user.is_bot and not member.user.is_deleted:
                members.append(member.user)
    except Exception:
        pass
    return members


def _progress_bar(done: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "░" * width
    filled = int(width * done / total)
    return "█" * filled + "░" * (width - filled)


@nand.on_message(
    filters.command(["tagall", "all", "mentionall"]) & filters.group & ~BANNED_USERS
)
async def tagall_cmd(client, message: Message):
    if not message.from_user:
        return
    chat_id = message.chat.id

    # Admin check
    try:
        member = await nand.get_chat_member(chat_id, message.from_user.id)
        if member.status not in ("administrator", "creator") and message.from_user.id not in SUDOERS:
            return await message.reply_text("🔒 Only admins can use /tagall.")
    except Exception:
        return await message.reply_text("🔒 Unable to verify admin rights.")

    if _TAG_RUNNING.get(chat_id):
        return await message.reply_text(
            "⚠️ TagAll is already running in this chat.\nUse /tagstop to cancel."
        )

    custom = message.text.split(None, 1)[1] if len(message.command) > 1 else "👋 Hello everyone!"

    status = await message.reply_text("🔎 Collecting members…")
    members = await _get_members(chat_id)
    if not members:
        return await status.edit_text("❌ No members found to tag.")

    total = len(members)
    _TAG_RUNNING[chat_id] = True
    _TAG_STOP[chat_id] = False

    stop_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛑 STOP TagAll", callback_data=f"tagstop_{chat_id}")]]
    )

    await status.edit_text(
        f"🏷️ **TagAll Started**\n"
        f"👥 Members : `{total}`\n"
        f"📝 Message : {custom[:80]}\n\n"
        f"Progress : {_progress_bar(0, total)} 0/{total}",
        reply_markup=stop_kb,
    )

    tagged = 0
    start_ts = time.time()
    batch = []
    BATCH_SIZE = 5

    for user in members:
        if _TAG_STOP.get(chat_id):
            break
        mention = user.mention if user.username is None else f"@{user.username}"
        batch.append(mention)
        if len(batch) >= BATCH_SIZE:
            text = f"{custom}\n\n" + " ".join(batch)
            try:
                await nand.send_message(chat_id, text)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await nand.send_message(chat_id, text)
                except Exception:
                    pass
            except Exception:
                pass
            tagged += len(batch)
            batch = []
            elapsed = int(time.time() - start_ts)
            eta = int((elapsed / max(tagged, 1)) * (total - tagged)) if tagged else 0
            try:
                await status.edit_text(
                    f"🏷️ **TagAll Running**\n"
                    f"👥 Members : `{total}`\n"
                    f"✅ Tagged  : `{tagged}`\n"
                    f"⏱ Elapsed : `{elapsed}s` | ETA : `{eta}s`\n\n"
                    f"Progress : {_progress_bar(tagged, total)} {tagged}/{total}",
                    reply_markup=stop_kb,
                )
            except Exception:
                pass
            await asyncio.sleep(1.2)

    if batch and not _TAG_STOP.get(chat_id):
        text = f"{custom}\n\n" + " ".join(batch)
        try:
            await nand.send_message(chat_id, text)
            tagged += len(batch)
        except Exception:
            pass

    _TAG_RUNNING[chat_id] = False
    _TAG_STOP.pop(chat_id, None)

    elapsed = int(time.time() - start_ts)
    if _TAG_STOP.get(chat_id) is None and tagged >= total:
        final = (
            f"✅ **TagAll Completed**\n\n"
            f"👥 Total members : `{total}`\n"
            f"✅ Tagged        : `{tagged}`\n"
            f"⏱ Time taken    : `{elapsed}s`"
        )
    else:
        final = (
            f"🛑 **TagAll Stopped**\n\n"
            f"👥 Total members : `{total}`\n"
            f"✅ Tagged before stop : `{tagged}`\n"
            f"⏱ Time taken    : `{elapsed}s`"
        )
    try:
        await status.edit_text(final)
    except Exception:
        await message.reply_text(final)


@nand.on_message(
    filters.command(["tagstop", "stoptag", "cancel"]) & filters.group & ~BANNED_USERS
)
async def tagstop_cmd(client, message: Message):
    chat_id = message.chat.id
    if not _TAG_RUNNING.get(chat_id):
        return await message.reply_text("ℹ️ No TagAll is currently running.")
    _TAG_STOP[chat_id] = True
    await message.reply_text("🛑 Stopping TagAll… please wait.")


@nand.on_callback_query(filters.regex(r"^tagstop_(-?\d+)$") & ~BANNED_USERS)
async def tagstop_cb(client, CallbackQuery):
    chat_id = int(CallbackQuery.matches[0].group(1))
    if CallbackQuery.message.chat.id != chat_id:
        return await CallbackQuery.answer("Wrong chat.", show_alert=True)
    if not _TAG_RUNNING.get(chat_id):
        return await CallbackQuery.answer("Already finished.", show_alert=False)
    _TAG_STOP[chat_id] = True
    await CallbackQuery.answer("🛑 Stopping…", show_alert=False)
    try:
        await CallbackQuery.message.edit_text("🛑 TagAll stop requested…")
    except Exception:
        pass


@nand.on_message(
    filters.command(["tagspam"]) & filters.group & ~BANNED_USERS
)
async def tagspam_cmd(client, message: Message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    try:
        member = await nand.get_chat_member(chat_id, message.from_user.id)
        if member.status not in ("administrator", "creator") and message.from_user.id not in SUDOERS:
            return await message.reply_text("🔒 Only admins can use /tagspam.")
    except Exception:
        return

    text = message.text.split(None, 1)[1] if len(message.command) > 1 else "🔥 Spam Tag"
    members = await _get_members(chat_id)
    if not members:
        return await message.reply_text("No members found.")

    # Limit spam to first 20 for safety
    members = members[:20]
    status = await message.reply_text(f"🚀 TagSpam started for {len(members)} members…")
    for user in members:
        mention = user.mention
        try:
            await nand.send_message(chat_id, f"{text}\n{mention}")
            await asyncio.sleep(0.8)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
    await status.edit_text(f"✅ TagSpam finished ({len(members)} tags).")


@nand.on_message(
    filters.command(["tagbomb"]) & filters.group & ~BANNED_USERS
)
async def tagbomb_cmd(client, message: Message):
    if not message.from_user:
        return
    chat_id = message.chat.id
    try:
        member = await nand.get_chat_member(chat_id, message.from_user.id)
        if member.status not in ("administrator", "creator") and message.from_user.id not in SUDOERS:
            return await message.reply_text("🔒 Only admins.")
    except Exception:
        return

    count = 3
    if len(message.command) > 1 and message.command[1].isdigit():
        count = min(int(message.command[1]), 5)

    text = "💣 TagBomb!"
    members = await _get_members(chat_id)
    if not members:
        return await message.reply_text("No members.")
    # small random sample
    import random
    sample = random.sample(members, min(10, len(members)))
    status = await message.reply_text(f"💣 TagBomb x{count} started…")
    for _ in range(count):
        mentions = " ".join(u.mention for u in sample)
        try:
            await nand.send_message(chat_id, f"{text}\n{mentions}")
            await asyncio.sleep(1.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
    await status.edit_text(f"✅ TagBomb completed ({count} rounds).")


@nand.on_callback_query(filters.regex(r"^tagall_help$") & ~BANNED_USERS)
async def tagall_help_cb(client, CallbackQuery):
    text = (
        "🏷️ **TagAll Commands**\n\n"
        "`/tagall [msg]` – Tag everyone\n"
        "`/tagstop` – Stop ongoing tag\n"
        "`/tagspam [text]` – Quick spam tag (20 max)\n"
        "`/tagbomb [1-5]` – Bomb tag rounds\n\n"
        "⚠️ Admin only. Use responsibly."
    )
    await CallbackQuery.answer()
    await CallbackQuery.message.reply_text(text)


@nand.on_callback_query(filters.regex(r"^autoplay_help$") & ~BANNED_USERS)
async def autoplay_help_cb(client, CallbackQuery):
    text = (
        "🔁 **Autoplay**\n\n"
        "When enabled, the bot automatically finds and plays a related song "
        "when the queue becomes empty.\n\n"
        "Use `/autoplay` in a group to toggle."
    )
    await CallbackQuery.answer()
    await CallbackQuery.message.reply_text(text)
