# ShrutixMusic/plugins/tools/lyrics.py
"""
LYRICS SYSTEM – Full Detail Edition
Commands:
  /lyrics [song name]          – Search & show lyrics
  /lyrics (reply to audio)     – Get lyrics of replied track
"""

import asyncio
import re
import time
from typing import Optional, Tuple

import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ShrutixMusic import nand
from ShrutixMusic.utils.decorators.language import language
from config import BANNED_USERS

LRCLIB_API = "https://lrclib.net/api/search"


def _clean_query(text: str) -> str:
    text = re.sub(r"[\(\[].*?[\)\]]", "", text)
    text = re.sub(r"(official|video|audio|lyrics|lyric|hd|hq|mv)", "", text, flags=re.I)
    return " ".join(text.split())[:80]


async def _fetch_lyrics(query: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                LRCLIB_API,
                params={"q": query},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    return None, None, None
                data = await resp.json()
                if not data:
                    return None, None, None

                best = None
                for item in data:
                    if item.get("plainLyrics") or item.get("syncedLyrics"):
                        best = item
                        break
                if not best:
                    best = data[0]

                title = best.get("trackName") or query
                artist = best.get("artistName") or "Unknown"
                lyrics = best.get("plainLyrics") or best.get("syncedLyrics")
                if not lyrics:
                    return title, artist, None
                lyrics = re.sub(r"\[\d{2}:\d{2}(\.\d{2,3})?\]", "", lyrics)
                lyrics = "\n".join(line.strip() for line in lyrics.splitlines() if line.strip())
                return title, artist, lyrics
    except asyncio.TimeoutError:
        return None, None, None
    except Exception:
        return None, None, None


@nand.on_message(filters.command(["lyrics", "lyric"]) & ~BANNED_USERS)
@language
async def lyrics_command(client, message: Message, _):
    query = None
    if message.reply_to_message:
        r = message.reply_to_message
        if r.audio:
            query = f"{r.audio.title or ''} {r.audio.performer or ''}".strip()
        elif r.document and r.document.file_name:
            query = r.document.file_name.rsplit(".", 1)[0]
        elif r.caption:
            query = r.caption
        elif r.text:
            query = r.text

    if not query and len(message.command) > 1:
        query = " ".join(message.command[1:])

    if not query or len(query.strip()) < 2:
        return await message.reply_text(
            "🎤 **Lyrics**\n\n"
            "Usage:\n"
            "• `/lyrics song name`\n"
            "• `/lyrics artist - song`\n"
            "• Reply to an audio file with `/lyrics`\n\n"
            "Example: `/lyrics Shape of You Ed Sheeran`"
        )

    query = _clean_query(query)
    status = await message.reply_text(
        f"🔍 **Searching lyrics...**\n\n"
        f"Query : `{query}`\n"
        f"Source: LRCLIB\n"
        f"Status: connecting..."
    )

    start_ts = time.time()
    await asyncio.sleep(0.6)
    try:
        await status.edit_text(
            f"🔍 **Searching lyrics...**\n\n"
            f"Query : `{query}`\n"
            f"Source: LRCLIB\n"
            f"Status: querying API... ({time.time()-start_ts:.1f}s)"
        )
    except Exception:
        pass

    title, artist, lyrics = await _fetch_lyrics(query)
    elapsed = time.time() - start_ts

    if not lyrics:
        try:
            await status.edit_text(
                f"❌ **Lyrics not found**\n\n"
                f"Query : `{query}`\n"
                f"Time  : {elapsed:.1f}s\n\n"
                f"Try a more precise name or different spelling."
            )
        except Exception:
            pass
        return

    header = (
        f"🎤 **{title}**\n"
        f"👤 {artist}\n"
        f"⏱ fetched in {elapsed:.1f}s\n"
        f"{'─'*24}\n\n"
    )
    max_body = 4000 - len(header)
    body = lyrics
    if len(body) > max_body:
        body = body[: max_body - 30] + "\n\n… (truncated)"

    full = header + body

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔎 Search again",
                    switch_inline_query_current_chat=f"lyrics {query}",
                )
            ],
            [InlineKeyboardButton("🗑 Close", callback_data="close")],
        ]
    )

    try:
        await status.edit_text(full, reply_markup=buttons)
    except Exception:
        await status.delete()
        await message.reply_text(full[:4000], reply_markup=buttons)
