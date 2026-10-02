# ShrutixMusic/plugins/tools/tagall.py
"""TagAll – /tagall /tagstop /tagspam /tagbomb (admin only)"""
import asyncio
import random
import time
from typing import List

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ShrutixMusic import nand
from ShrutixMusic.misc import SUDOERS
from config import BANNED_USERS

_TAG_RUNNING: dict = {}
_TAG_STOP: dict = {}


async def _get_members(chat_id: int) -> List:
    members = []
    try:
        async for member in nand.get_chat_members(chat_id):
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


async def _ensure_admin(message: Message) -> bool:
    if not message.from_user:
        return False
    if message.from_user.id in SUDOERS:
        return True
    try:
        member = await nand.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


@nand.on_message(filters.command(["tagall", "all", "mentionall"]) & filters.group & ~BANNED_USERS)
async def tagall_cmd(client, message: Message):
    if not await _ensure_admin(message):
        return await message.reply_text("🔒 Only admins can use /tagall.")

    chat_id = message.chat.id
    if _TAG_RUNNING.get(chat_id):
        return await message.reply_text("⚠️ TagAll already running.\nUse /tagstop to cancel.")

    custom = message.text.split(None, 1)[1] if len(message.command) > 1 else "👋 Hello everyone!"
    status = await message.reply_text("🔎 Collecting members…")
    members = await _get_members(chat_id)
    if not members:
        return await status.edit_text("❌ No members found to tag.")

    total = len(members)
    _TAG_RUNNING[chat_id] = True
    _TAG_STOP[chat_id] = False
    stop_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 STOP TagAll", callback_data=f"tagstop_{chat_id}")]])

    await status.edit_text(
        f"🏷️ **TagAll Started**\n👥 Members : `{total}`\n📝 Message : {custom[:80]}\n\n"
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
        mention = user.mention
        batch.append(mention)
        if len(batch) >= BATCH_SIZE:
            text = f"{custom}\n\n" + " ".join(batch)
            try:
                await nand.send_message(chat_id, text)
            except FloodWait as e:
                await asyncio.sleep(e.value + 0.5)
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
                    f"🏷️ **TagAll Running**\n👥 Members : `{total}`\n✅ Tagged  : `{tagged}`\n"
                    f"⏱ Elapsed : `{elapsed}s` | ETA : `{eta}s`\n\n"
                    f"Progress : {_progress_bar(tagged, total)} {tagged}/{total}",
                    reply_markup=stop_kb,
                )
            except Exception:
                pass
            await asyncio.sleep(1.2)

    if batch and not _TAG_STOP.get(chat_id):
        try:
            await nand.send_message(chat_id, f"{custom}\n\n" + " ".join(batch))
            tagged += len(batch)
        except Exception:
            pass

    stopped = bool(_TAG_STOP.get(chat_id))
    _TAG_RUNNING[chat_id] = False
    _TAG_STOP.pop(chat_id, None)
    elapsed = int(time.time() - start_ts)
    if stopped:
        final = f"🛑 **TagAll Stopped**\n\n👥 Total : `{total}`\n✅ Tagged : `{tagged}`\n⏱ Time : `{elapsed}s`"
    else:
        final = f"✅ **TagAll Completed**\n\n👥 Total : `{total}`\n✅ Tagged : `{tagged}`\n⏱ Time : `{elapsed}s`"
    try:
        await status.edit_text(final)
    except Exception:
        await message.reply_text(final)


@nand.on_message(filters.command(["tagstop", "stoptag", "cancel"]) & filters.group & ~BANNED_USERS)
async def tagstop_cmd(client, message: Message):
    chat_id = message.chat.id
    if not _TAG_RUNNING.get(chat_id):
        return await message.reply_text("ℹ️ No TagAll is currently running.")
    _TAG_STOP[chat_id] = True
    await message.reply_text("🛑 Stopping TagAll…")


@nand.on_callback_query(filters.regex(r"^tagstop_(-?\d+)$") & ~BANNED_USERS)
async def tagstop_cb(client, CallbackQuery):
    chat_id = int(CallbackQuery.matches[0].group(1))
    if CallbackQuery.message.chat.id != chat_id:
        return await CallbackQuery.answer("Wrong chat.", show_alert=True)
    if not _TAG_RUNNING.get(chat_id):
        return await CallbackQuery.answer("Already finished.")
    _TAG_STOP[chat_id] = True
    await CallbackQuery.answer("🛑 Stopping…")


@nand.on_message(filters.command(["tagspam"]) & filters.group & ~BANNED_USERS)
async def tagspam_cmd(client, message: Message):
    if not await _ensure_admin(message):
        return await message.reply_text("🔒 Only admins can use /tagspam.")
    text = message.text.split(None, 1)[1] if len(message.command) > 1 else "🔥 Spam Tag"
    members = (await _get_members(message.chat.id))[:20]
    if not members:
        return await message.reply_text("No members found.")
    status = await message.reply_text(f"🚀 TagSpam for {len(members)} members…")
    for user in members:
        try:
            await nand.send_message(message.chat.id, f"{text}\n{user.mention}")
            await asyncio.sleep(0.8)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
    await status.edit_text(f"✅ TagSpam finished ({len(members)} tags).")


@nand.on_message(filters.command(["tagbomb"]) & filters.group & ~BANNED_USERS)
async def tagbomb_cmd(client, message: Message):
    if not await _ensure_admin(message):
        return await message.reply_text("🔒 Only admins.")
    count = 3
    if len(message.command) > 1 and message.command[1].isdigit():
        count = min(int(message.command[1]), 5)
    members = await _get_members(message.chat.id)
    if not members:
        return await message.reply_text("No members.")
    sample = random.sample(members, min(10, len(members)))
    status = await message.reply_text(f"💣 TagBomb x{count}…")
    for _ in range(count):
        mentions = " ".join(u.mention for u in sample)
        try:
            await nand.send_message(message.chat.id, f"💣 TagBomb!\n{mentions}")
            await asyncio.sleep(1.5)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            pass
    await status.edit_text(f"✅ TagBomb completed ({count} rounds).")
