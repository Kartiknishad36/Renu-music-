# ShrutixMusic/plugins/bot/group_logs.py
"""
GROUP MEMBERSHIP LOGGER – Full Detail + DP / Group Photo
When bot is ADDED → photo + full group info + who added
When bot is REMOVED → photo + full info + who removed
"""

import html
import os
import time
from datetime import datetime

from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode

import config
from ShrutixMusic import nand
from ShrutixMusic.utils.database import (
    delete_chat_link,
    get_chat_link,
    remove_served_chat,
    save_chat_link,
)

NOT_APPLICABLE = "Not Applicable"
OUT_OF_CHAT = (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED)
GROUP_TYPES = (ChatType.GROUP, ChatType.SUPERGROUP)
DEDUPE_SECONDS = 30
_PHOTO_CACHE = "cache/log_photos"
os.makedirs(_PHOTO_CACHE, exist_ok=True)

_recent = {}


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _already_logged(chat_id, kind):
    now = time.time()
    for key in [k for k, t in _recent.items() if now - t > DEDUPE_SECONDS]:
        _recent.pop(key, None)
    key = (chat_id, kind)
    if key in _recent:
        return True
    _recent[key] = now
    return False


def _who(user):
    if not user:
        return NOT_APPLICABLE, NOT_APPLICABLE, None
    try:
        mention = user.mention
    except Exception:
        mention = html.escape(str(getattr(user, "first_name", "") or user.id))
    return mention, f"<code>{user.id}</code>", user


def _link_text(link):
    return html.escape(link) if link else NOT_APPLICABLE


def _can_invite(member):
    rights = getattr(member, "privileges", None)
    return (
        member is not None
        and member.status == ChatMemberStatus.ADMINISTRATOR
        and rights is not None
        and bool(getattr(rights, "can_invite_users", False))
    )


async def _current_link(chat, member):
    if getattr(chat, "username", None):
        return f"https://t.me/{chat.username}"
    if _can_invite(member):
        try:
            full = await nand.get_chat(chat.id)
            return full.invite_link or None
        except Exception:
            return None
    return None


async def _get_chat_photo(chat_id):
    try:
        chat = await nand.get_chat(chat_id)
        if not chat.photo:
            return None
        return await nand.download_media(
            chat.photo.big_file_id,
            file_name=f"{_PHOTO_CACHE}/g_{chat_id}.jpg",
        )
    except Exception:
        return None


async def _get_user_photo(user):
    if not user or not getattr(user, "photo", None):
        return None
    try:
        return await nand.download_media(
            user.photo.big_file_id,
            file_name=f"{_PHOTO_CACHE}/u_{user.id}.jpg",
        )
    except Exception:
        return None


async def _send_log(text, photo=None):
    if not config.LOGGER_ID:
        return
    text = text[:1020]
    try:
        if photo and os.path.isfile(str(photo)):
            await nand.send_photo(
                config.LOGGER_ID,
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
            return
    except Exception as ex:
        print(ex)
    try:
        await nand.send_message(
            config.LOGGER_ID, text, disable_web_page_preview=True, parse_mode=ParseMode.HTML
        )
    except Exception as ex:
        print(ex)


async def _on_added(update, member):
    chat = update.chat
    link = await _current_link(chat, member)
    if link:
        try:
            await save_chat_link(chat.id, link)
        except Exception as ex:
            print(ex)

    adder, adder_id, adder_user = _who(update.from_user)
    members_count = getattr(chat, "members_count", None) or "N/A"
    uname = f"@{chat.username}" if chat.username else "No username"

    text = (
        f"<b>➕ {nand.mention} ᴀᴅᴅᴇᴅ ɪɴ ᴀ ɴᴇᴡ ɢʀᴏᴜᴘ</b>\n"
        f"{'─'*22}\n\n"
        f"<b>📍 Group</b>\n"
        f"├ Title : {html.escape(chat.title or NOT_APPLICABLE)}\n"
        f"├ ID    : <code>{chat.id}</code>\n"
        f"├ User  : {uname}\n"
        f"├ Members: <code>{members_count}</code>\n"
        f"└ Link  : {_link_text(link)}\n\n"
        f"<b>👤 Added By</b>\n"
        f"├ Name : {adder}\n"
        f"└ ID   : {adder_id}\n\n"
        f"<b>🕐 Time</b> : <code>{_now()}</code>"
    )

    photo = await _get_chat_photo(chat.id)
    if not photo and adder_user:
        photo = await _get_user_photo(adder_user)

    await _send_log(text, photo=photo)


async def _on_removed(update):
    chat = update.chat
    link = None
    if getattr(chat, "username", None):
        link = f"https://t.me/{chat.username}"
    if not link:
        try:
            link = await get_chat_link(chat.id)
        except Exception:
            link = None

    actor = update.from_user
    if actor and actor.id == nand.id:
        remover, remover_id, remover_user = "ʙᴏᴛ ɪᴛsᴇʟғ (ʟᴇғᴛ ᴛʜᴇ ɢʀᴏᴜᴘ)", NOT_APPLICABLE, None
    else:
        remover, remover_id, remover_user = _who(actor)

    uname = f"@{chat.username}" if chat.username else "No username"
    text = (
        f"<b>➖ {nand.mention} ʀᴇᴍᴏᴠᴇᴅ ғʀᴏᴍ ᴀ ɢʀᴏᴜᴘ</b>\n"
        f"{'─'*22}\n\n"
        f"<b>📍 Group</b>\n"
        f"├ Title : {html.escape(chat.title or NOT_APPLICABLE)}\n"
        f"├ ID    : <code>{chat.id}</code>\n"
        f"├ User  : {uname}\n"
        f"└ Link  : {_link_text(link)}\n\n"
        f"<b>👤 Removed By</b>\n"
        f"├ Name : {remover}\n"
        f"└ ID   : {remover_id}\n\n"
        f"<b>🕐 Time</b> : <code>{_now()}</code>"
    )

    photo = await _get_chat_photo(chat.id)
    if not photo and remover_user:
        photo = await _get_user_photo(remover_user)

    await _send_log(text, photo=photo)

    for cleanup in (delete_chat_link, remove_served_chat):
        try:
            await cleanup(chat.id)
        except Exception as ex:
            print(ex)


async def _refresh_link(update, member):
    if not _can_invite(member):
        return
    link = await _current_link(update.chat, member)
    if link:
        await save_chat_link(update.chat.id, link)


@nand.on_chat_member_updated()
async def bot_membership_changed(client, update):
    try:
        new = update.new_chat_member
        old = update.old_chat_member
        member = new or old
        if not member or not member.user or member.user.id != nand.id:
            return
        if update.chat.type not in GROUP_TYPES:
            return
        was_in = old is not None and old.status not in OUT_OF_CHAT
        now_in = new is not None and new.status not in OUT_OF_CHAT
        if now_in and not was_in:
            if not _already_logged(update.chat.id, "added"):
                await _on_added(update, new)
        elif was_in and not now_in:
            if not _already_logged(update.chat.id, "removed"):
                await _on_removed(update)
        elif now_in:
            await _refresh_link(update, new)
    except Exception as ex:
        print(ex)
