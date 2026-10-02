import random
import time

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from py_yt import VideosSearch

import config
from ShrutixMusic import nand
from ShrutixMusic.misc import _boot_
from ShrutixMusic.plugins.sudo.sudoers import sudoers_list
from ShrutixMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
)
from ShrutixMusic.utils.decorators.language import LanguageStart
from ShrutixMusic.utils.formatters import get_readable_time
from ShrutixMusic.utils.logger import start_log
from ShrutixMusic.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string

MESSAGE_EFFECTS = [
    5107584321108051014,
    5159385139981059251,
    5104841245755180586,
    5046509860389126442,
]


@nand.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    effect_id = random.choice(MESSAGE_EFFECTS)
    name = message.text.split(None, 1)[1] if len(message.text.split()) > 1 else ""
    if name[0:4] == "help":
        keyboard = help_pannel(_)
        return await message.reply_photo(
            photo=config.START_IMG_URL,
            caption=_["help_1"].format(config.SUPPORT_CHAT),
            reply_markup=keyboard,
            effect_id=effect_id,
        )
    if name[0:3] == "sud":
        await sudoers_list(client=client, message=message, _=_)
        await start_log(message, action="checked sudolist")
        return
    if name[0:3] == "inf":
        m = await message.reply_text("🔎")
        query = (str(name)).replace("info_", "", 1)
        query = f"https://www.youtube.com/watch?v={query}"
        results = VideosSearch(query, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration = result["duration"]
            views = result["viewCount"]["short"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            channellink = result["channel"]["link"]
            channel = result["channel"]["name"]
            link = result["link"]
            published = result["publishedTime"]
        searched_text = _["start_6"].format(
            title, duration, views, published, channellink, channel, nand.mention
        )
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text=_["S_B_8"], url=link),
                    InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT),
                ],
            ]
        )
        await m.delete()
        await nand.send_photo(
            chat_id=message.chat.id,
            photo=thumbnail,
            caption=searched_text,
            reply_markup=key,
        )
        await start_log(message, action="checked track info")
        return
    out = private_panel(_)
    try:
        await message.reply_photo(
            photo=config.START_IMG_URL,
            caption=_["start_2"].format(message.from_user.mention, nand.mention),
            reply_markup=InlineKeyboardMarkup(out),
            effect_id=effect_id,
        )
    except Exception:
        await message.reply_text(
            _["start_2"].format(message.from_user.mention, nand.mention),
            reply_markup=InlineKeyboardMarkup(out),
        )
    await start_log(message, action="started the bot")


@nand.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    caption = _["start_1"].format(nand.mention, get_readable_time(uptime))
    markup = InlineKeyboardMarkup(out)
    try:
        await message.reply_photo(
            photo=config.START_IMG_URL,
            caption=caption,
            reply_markup=markup,
        )
    except Exception:
        await message.reply_text(caption, reply_markup=markup)
    try:
        await start_log(message, action="started the bot in group")
    except Exception:
        pass
    return await add_served_chat(message.chat.id)


@nand.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except Exception:
                    pass
            if member.id == nand.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await nand.leave_chat(message.chat.id)
                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            nand.mention,
                            f"https://t.me/{nand.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await nand.leave_chat(message.chat.id)

                out = start_panel(_)
                caption = _["start_3"].format(
                    message.from_user.first_name,
                    nand.mention,
                    message.chat.title,
                    nand.mention,
                )
                markup = InlineKeyboardMarkup(out)
                try:
                    await message.reply_photo(
                        photo=config.START_IMG_URL,
                        caption=caption,
                        reply_markup=markup,
                    )
                except Exception:
                    await message.reply_text(caption, reply_markup=markup)
                await add_served_chat(message.chat.id)
                await message.stop_propagation()
        except Exception as ex:
            print(ex)
