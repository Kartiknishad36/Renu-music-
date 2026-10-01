# ShrutixMusic/plugins/admins/group.py
"""Full Group Management – ban/unban/kick/mute/unmute/tmute/promote/demote/purge/pin/warn"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import ChatAdminRequired, FloodWait, PeerIdInvalid, RightForbidden, UserAdminInvalid
from pyrogram.types import ChatPermissions, Message, User

from ShrutixMusic import nand
from ShrutixMusic.misc import SUDOERS
from ShrutixMusic.utils.decorators.language import language
from config import BANNED_USERS, LOGGER_ID

_WARN_DB: dict = {}
_MUTE_TIMERS: dict = {}
_PURGE_STOP: dict = {}
MAX_WARNS = 3
PURGE_BATCH_SLEEP = 0.35
TMUTE_MIN_SECONDS = 5
TMUTE_MAX_SECONDS = 86400 * 7


def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _progress(done: int, total: int, width: int = 14) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * done / total))
    return "█" * filled + "░" * (width - filled)


def _eta(done: int, total: int, start_ts: float) -> str:
    if done <= 0:
        return "calculating..."
    elapsed = time.time() - start_ts
    rate = done / elapsed if elapsed > 0 else 0.01
    remaining = (total - done) / rate
    if remaining < 60:
        return f"{int(remaining)}s"
    return f"{int(remaining // 60)}m {int(remaining % 60)}s"


async def _extract_user(message: Message) -> Optional[User]:
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
    if not message.command or len(message.command) < 2:
        return None
    arg = message.command[1]
    try:
        if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
            return await nand.get_users(int(arg))
        return await nand.get_users(arg)
    except (PeerIdInvalid, IndexError, KeyError, ValueError):
        return None


async def _is_admin(chat_id: int, user_id: int) -> bool:
    if user_id in SUDOERS:
        return True
    try:
        member = await nand.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def _bot_can_restrict(chat_id: int) -> bool:
    try:
        me = await nand.get_chat_member(chat_id, "me")
        return bool(me.privileges and me.privileges.can_restrict_members)
    except Exception:
        return False


async def _bot_can_promote(chat_id: int) -> bool:
    try:
        me = await nand.get_chat_member(chat_id, "me")
        return bool(me.privileges and me.privileges.can_promote_members)
    except Exception:
        return False


async def _bot_can_delete(chat_id: int) -> bool:
    try:
        me = await nand.get_chat_member(chat_id, "me")
        return bool(me.privileges and me.privileges.can_delete_messages)
    except Exception:
        return False


async def _log_action(chat_id: int, text: str):
    try:
        if LOGGER_ID:
            await nand.send_message(LOGGER_ID, text, disable_web_page_preview=True)
    except Exception:
        pass


def _reason_from_cmd(message: Message, start_index: int = 2) -> str:
    if len(message.command) > start_index:
        return " ".join(message.command[start_index:])[:200]
    return "No reason provided"


@nand.on_message(filters.command(["ban", "dban"]) & filters.group & ~BANNED_USERS)
@language
async def ban_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.\nExample: `/ban @username spam`")
    if user.id in SUDOERS or await _is_admin(message.chat.id, user.id):
        return await message.reply_text("» Cannot ban an admin/sudo.")
    reason = _reason_from_cmd(message, 2 if not message.reply_to_message else 1)
    try:
        await nand.ban_chat_member(message.chat.id, user.id)
        text = (
            f"╔══════════════════════╗\n║   🔨  USER BANNED   ║\n╚══════════════════════╝\n\n"
            f"👤 User      : {user.mention} (`{user.id}`)\n"
            f"👮 By        : {message.from_user.mention}\n"
            f"📝 Reason    : {reason}\n"
            f"🕐 Time      : `{_now()}`\n"
            f"📍 Chat      : {message.chat.title}"
        )
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except FloodWait as e:
        await asyncio.sleep(e.value + 0.5)
        return await message.reply_text(f"» FloodWait {e.value}s – try again.")
    except (ChatAdminRequired, RightForbidden, UserAdminInvalid) as e:
        await message.reply_text(f"» Permission error: `{e}`")
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["unban"]) & filters.group & ~BANNED_USERS)
@language
async def unban_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    try:
        await nand.unban_chat_member(message.chat.id, user.id)
        text = f"✅ **User Unbanned**\n\n👤 {user.mention} (`{user.id}`)\n👮 By: {message.from_user.mention}\n🕐 `{_now()}`"
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["kick", "dkick"]) & filters.group & ~BANNED_USERS)
@language
async def kick_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    if user.id in SUDOERS or await _is_admin(message.chat.id, user.id):
        return await message.reply_text("» Cannot kick an admin/sudo.")
    reason = _reason_from_cmd(message, 2 if not message.reply_to_message else 1)
    try:
        await nand.ban_chat_member(message.chat.id, user.id)
        await asyncio.sleep(0.8)
        await nand.unban_chat_member(message.chat.id, user.id)
        text = (
            f"╔══════════════════════╗\n║   👢  USER KICKED   ║\n╚══════════════════════╝\n\n"
            f"👤 User   : {user.mention} (`{user.id}`)\n"
            f"👮 By     : {message.from_user.mention}\n"
            f"📝 Reason : {reason}\n"
            f"🕐 Time   : `{_now()}`"
        )
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["mute", "dmute"]) & filters.group & ~BANNED_USERS)
@language
async def mute_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    if user.id in SUDOERS or await _is_admin(message.chat.id, user.id):
        return await message.reply_text("» Cannot mute an admin/sudo.")
    reason = _reason_from_cmd(message, 2 if not message.reply_to_message else 1)
    try:
        await nand.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=False))
        text = (
            f"╔══════════════════════╗\n║   🔇  USER MUTED    ║\n╚══════════════════════╝\n\n"
            f"👤 User   : {user.mention} (`{user.id}`)\n"
            f"👮 By     : {message.from_user.mention}\n"
            f"📝 Reason : {reason}\n"
            f"⏳ Until  : Forever\n"
            f"🕐 Time   : `{_now()}`"
        )
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["unmute"]) & filters.group & ~BANNED_USERS)
@language
async def unmute_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    key = (message.chat.id, user.id)
    if key in _MUTE_TIMERS:
        _MUTE_TIMERS[key].cancel()
        del _MUTE_TIMERS[key]
    try:
        await nand.restrict_chat_member(
            message.chat.id, user.id,
            ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                            can_send_other_messages=True, can_add_web_page_previews=True),
        )
        text = f"🔊 **User Unmuted**\n\n👤 {user.mention} (`{user.id}`)\n👮 By: {message.from_user.mention}\n🕐 `{_now()}`"
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["tmute", "tempmute"]) & filters.group & ~BANNED_USERS)
@language
async def tmute_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_restrict(message.chat.id):
        return await message.reply_text("» I need **Restrict Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text(
            f"» Usage: `/tmute @user 60 reason` or reply `/tmute 120 reason`\n"
            f"Seconds range: {TMUTE_MIN_SECONDS} – {TMUTE_MAX_SECONDS}"
        )
    if user.id in SUDOERS or await _is_admin(message.chat.id, user.id):
        return await message.reply_text("» Cannot mute an admin/sudo.")
    seconds = None
    reason_start = 2
    if message.reply_to_message:
        if len(message.command) < 2:
            return await message.reply_text("» Give duration in seconds.\nExample: `/tmute 300`")
        try:
            seconds = int(message.command[1])
            reason_start = 2
        except ValueError:
            return await message.reply_text("» Duration must be a number (seconds).")
    else:
        if len(message.command) < 3:
            return await message.reply_text("» Usage: `/tmute @user 60 reason`")
        try:
            seconds = int(message.command[2])
            reason_start = 3
        except ValueError:
            return await message.reply_text("» Duration must be a number (seconds).")
    if seconds < TMUTE_MIN_SECONDS or seconds > TMUTE_MAX_SECONDS:
        return await message.reply_text(
            f"» Duration must be between **{TMUTE_MIN_SECONDS}s** and **{TMUTE_MAX_SECONDS}s**."
        )
    reason = _reason_from_cmd(message, reason_start)
    until = datetime.utcnow() + timedelta(seconds=seconds)
    try:
        await nand.restrict_chat_member(
            message.chat.id, user.id, ChatPermissions(can_send_messages=False), until_date=until
        )
    except Exception as e:
        return await message.reply_text(f"» Failed to mute: `{e}`")
    key = (message.chat.id, user.id)
    if key in _MUTE_TIMERS:
        _MUTE_TIMERS[key].cancel()

    async def _auto_unmute():
        try:
            await asyncio.sleep(seconds)
            await nand.restrict_chat_member(
                message.chat.id, user.id,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                can_send_other_messages=True, can_add_web_page_previews=True),
            )
            await nand.send_message(message.chat.id, f"🔊 Auto-unmuted {user.mention} after **{seconds}s**.")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            _MUTE_TIMERS.pop(key, None)

    _MUTE_TIMERS[key] = asyncio.create_task(_auto_unmute())
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    duration_str = (f"{hours}h " if hours else "") + (f"{mins}m " if mins else "") + f"{secs}s"
    text = (
        f"╔══════════════════════╗\n║  ⏳  TEMP MUTED     ║\n╚══════════════════════╝\n\n"
        f"👤 User     : {user.mention} (`{user.id}`)\n"
        f"👮 By       : {message.from_user.mention}\n"
        f"📝 Reason   : {reason}\n"
        f"⏱ Duration : **{duration_str}** ({seconds} seconds)\n"
        f"🔓 Unmute at: `{until.strftime('%Y-%m-%d %H:%M:%S UTC')}`\n"
        f"🕐 Now      : `{_now()}`\n\n"
        f"Bot will auto-unmute after exact {seconds} seconds."
    )
    await message.reply_text(text)
    await _log_action(message.chat.id, text)


@nand.on_message(filters.command(["promote"]) & filters.group & ~BANNED_USERS)
@language
async def promote_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_promote(message.chat.id):
        return await message.reply_text("» I need **Promote Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    title = "Admin"
    if message.reply_to_message and len(message.command) > 1:
        title = " ".join(message.command[1:])[:16]
    elif not message.reply_to_message and len(message.command) > 2:
        title = " ".join(message.command[2:])[:16]
    try:
        await nand.promote_chat_member(
            message.chat.id, user.id,
            can_manage_chat=True, can_delete_messages=True, can_manage_video_chats=True,
            can_restrict_members=True, can_change_info=False, can_invite_users=True,
            can_pin_messages=True, can_promote_members=False,
        )
        try:
            await nand.set_administrator_title(message.chat.id, user.id, title)
        except Exception:
            pass
        text = (
            f"╔══════════════════════╗\n║  ⬆️  USER PROMOTED  ║\n╚══════════════════════╝\n\n"
            f"👤 User  : {user.mention} (`{user.id}`)\n"
            f"🏷 Title : `{title}`\n"
            f"👮 By    : {message.from_user.mention}\n"
            f"🕐 `{_now()}`"
        )
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["demote"]) & filters.group & ~BANNED_USERS)
@language
async def demote_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_promote(message.chat.id):
        return await message.reply_text("» I need **Promote Members** permission.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    if user.id in SUDOERS:
        return await message.reply_text("» Cannot demote a sudo user.")
    try:
        await nand.promote_chat_member(
            message.chat.id, user.id,
            can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
            can_restrict_members=False, can_change_info=False, can_invite_users=False,
            can_pin_messages=False, can_promote_members=False,
        )
        text = f"⬇️ **User Demoted**\n\n👤 {user.mention} (`{user.id}`)\n👮 By: {message.from_user.mention}\n🕐 `{_now()}`"
        await message.reply_text(text)
        await _log_action(message.chat.id, text)
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["purge"]) & filters.group & ~BANNED_USERS)
@language
async def purge_messages(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not await _bot_can_delete(message.chat.id):
        return await message.reply_text("» I need **Delete Messages** permission.")
    if not message.reply_to_message:
        return await message.reply_text("» Reply to the message from which you want to start deleting.")
    chat_id = message.chat.id
    start_id = message.reply_to_message.id
    end_id = message.id
    if end_id <= start_id:
        return await message.reply_text("» Nothing to purge.")
    total = end_id - start_id + 1
    _PURGE_STOP[chat_id] = False
    start_ts = time.time()
    deleted = 0
    failed = 0
    status = await message.reply_text(
        f"🗑 **Purge started**\n\nTotal: **{total}**\nProgress: `{_progress(0, total)}` 0%\nETA: calculating..."
    )
    current = end_id
    while current >= start_id:
        if _PURGE_STOP.get(chat_id):
            break
        try:
            await nand.delete_messages(chat_id, current)
            deleted += 1
        except FloodWait as e:
            await asyncio.sleep(e.value + 0.3)
            try:
                await nand.delete_messages(chat_id, current)
                deleted += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        current -= 1
        done = deleted + failed
        if done % 8 == 0 or current < start_id:
            pct = int(100 * done / total) if total else 100
            try:
                await status.edit_text(
                    f"🗑 **Purging...**\n\nProgress: `{_progress(done, total)}` **{pct}%**\n"
                    f"Deleted : **{deleted}**\nFailed  : **{failed}**\n"
                    f"ETA     : {_eta(done, total, start_ts)}\nElapsed : {int(time.time() - start_ts)}s"
                )
            except Exception:
                pass
            await asyncio.sleep(PURGE_BATCH_SLEEP)
    elapsed = int(time.time() - start_ts)
    try:
        speed = f"{deleted / elapsed:.1f} msg/s" if elapsed else "Done."
        await status.edit_text(
            f"✅ **Purge completed**\n\nDeleted : **{deleted}**\nFailed  : **{failed}**\n"
            f"Total   : **{total}**\nTime    : **{elapsed}s**\nSpeed   : **{speed}**"
        )
    except Exception:
        pass
    _PURGE_STOP.pop(chat_id, None)


@nand.on_message(filters.command(["del", "delete"]) & filters.group & ~BANNED_USERS)
@language
async def delete_msg(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not message.reply_to_message:
        return await message.reply_text("» Reply to the message you want to delete.")
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["pin"]) & filters.group & ~BANNED_USERS)
@language
async def pin_msg(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    if not message.reply_to_message:
        return await message.reply_text("» Reply to the message you want to pin.")
    try:
        await message.reply_to_message.pin(disable_notification=False)
        await message.reply_text(f"📌 Pinned by {message.from_user.mention}\n🕐 `{_now()}`")
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["unpin"]) & filters.group & ~BANNED_USERS)
@language
async def unpin_msg(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    try:
        if message.reply_to_message:
            await message.reply_to_message.unpin()
        else:
            await nand.unpin_chat_message(message.chat.id)
        await message.reply_text(f"📌 Unpinned by {message.from_user.mention}")
    except Exception as e:
        await message.reply_text(f"» Failed: `{e}`")


@nand.on_message(filters.command(["warn"]) & filters.group & ~BANNED_USERS)
@language
async def warn_user(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    if user.id in SUDOERS or await _is_admin(message.chat.id, user.id):
        return await message.reply_text("» Cannot warn an admin/sudo.")
    reason = _reason_from_cmd(message, 2 if not message.reply_to_message else 1)
    chat_id = message.chat.id
    if chat_id not in _WARN_DB:
        _WARN_DB[chat_id] = {}
    count = _WARN_DB[chat_id].get(user.id, 0) + 1
    _WARN_DB[chat_id][user.id] = count
    text = (
        f"⚠️ **Warning #{count}/{MAX_WARNS}**\n\n"
        f"👤 User   : {user.mention} (`{user.id}`)\n"
        f"👮 By     : {message.from_user.mention}\n"
        f"📝 Reason : {reason}\n"
        f"🕐 `{_now()}`\n"
    )
    if count >= MAX_WARNS:
        text += f"\n🔨 **Max warns reached → Auto-banning...**"
        await message.reply_text(text)
        try:
            await nand.ban_chat_member(chat_id, user.id)
            _WARN_DB[chat_id][user.id] = 0
            await message.reply_text(f"🔨 {user.mention} banned after {MAX_WARNS} warns.")
        except Exception as e:
            await message.reply_text(f"» Ban failed: `{e}`")
    else:
        text += f"\nRemaining warns before ban: **{MAX_WARNS - count}**"
        await message.reply_text(text)
    await _log_action(chat_id, text)


@nand.on_message(filters.command(["warns"]) & filters.group & ~BANNED_USERS)
@language
async def check_warns(client, message: Message, _):
    user = await _extract_user(message)
    if not user:
        user = message.from_user
    count = _WARN_DB.get(message.chat.id, {}).get(user.id, 0)
    await message.reply_text(f"⚠️ Warns for {user.mention}: **{count}/{MAX_WARNS}**")


@nand.on_message(filters.command(["resetwarns", "rmwarns"]) & filters.group & ~BANNED_USERS)
@language
async def reset_warns(client, message: Message, _):
    if not await _is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("» Only admins can use this command.")
    user = await _extract_user(message)
    if not user:
        return await message.reply_text("» Reply to a user or give username/user_id.")
    if message.chat.id in _WARN_DB:
        _WARN_DB[message.chat.id][user.id] = 0
    await message.reply_text(f"✅ Warns reset for {user.mention}.")


@nand.on_callback_query(filters.regex("^tagall_help$") & ~BANNED_USERS)
async def tagall_help_cb(client, CallbackQuery):
    await CallbackQuery.answer()
    await CallbackQuery.message.reply_text(
        "**🏷️ TagAll Commands**\n\n"
        "`/tagall [msg]` – Tag all with progress + ETA + STOP\n"
        "`/tagstop` / `/cancel` – Stop\n"
        "`/tagspam [text]` – Quick spam\n"
        "`/tagbomb [1-5]` – Bomb rounds\n\nAdmin only."
    )


@nand.on_callback_query(filters.regex("^autoplay_help$") & ~BANNED_USERS)
async def autoplay_help_cb(client, CallbackQuery):
    await CallbackQuery.answer()
    await CallbackQuery.message.reply_text(
        "**🔁 Autoplay**\n\nWhen ON, bot auto-plays related tracks when queue ends.\nUse `/autoplay` to toggle."
    )
