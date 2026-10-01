import random

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton

import config
from ShrutixMusic import nand

COLORS = (ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER)


def _random_styles(count, blanks=0):
    blanks = min(blanks, count)
    blank_at = set(random.sample(range(count), blanks)) if blanks else set()
    colored = [i for i in range(count) if i not in blank_at]
    while True:
        picks = {i: random.choice(COLORS) for i in colored}
        if len(colored) < 3 or len(set(picks.values())) > 1:
            break
    return [picks.get(i, ButtonStyle.DEFAULT) for i in range(count)]


def start_panel(_):
    """Group start panel – premium multi-button layout with emoji colors."""
    s = _random_styles(8, 1)
    buttons = [
        # Full-width Add Me
        [
            InlineKeyboardButton(
                text="➕  " + _["S_B_3"],
                url=f"https://t.me/{nand.username}?startgroup=true",
                style=s[0],
            )
        ],
        # Help & Commands full-width
        [
            InlineKeyboardButton(
                text="📖  " + _["S_B_4"],
                callback_data="settings_back_helper",
                style=s[1],
            )
        ],
        # 2x2 row
        [
            InlineKeyboardButton(
                text="👑  " + _["S_B_5"],
                user_id=config.OWNER_ID,
                style=s[2],
            ),
            InlineKeyboardButton(
                text="📢  " + _["S_B_6"],
                url=config.SUPPORT_CHANNEL,
                style=s[3],
            ),
        ],
        [
            InlineKeyboardButton(
                text="💬  " + _["S_B_2"],
                url=config.SUPPORT_CHAT,
                style=s[4],
            ),
            InlineKeyboardButton(
                text="📦  " + _["S_B_7"],
                url=config.UPSTREAM_REPO if hasattr(config, "UPSTREAM_REPO") else "https://github.com/Kartiknishad36/Renu-music-",
                style=s[5],
            ),
        ],
        # Extra useful buttons
        [
            InlineKeyboardButton(
                text="🎵  Autoplay",
                callback_data="autoplay_help",
                style=s[6],
            ),
            InlineKeyboardButton(
                text="🏷️  TagAll",
                callback_data="tagall_help",
                style=s[7],
            ),
        ],
    ]
    return buttons


def private_panel(_):
    """Private /start panel – Mahi-style + extra command buttons."""
    s = _random_styles(10, 1)
    buttons = [
        # Full-width Add Me
        [
            InlineKeyboardButton(
                text="➕  " + _["S_B_3"],
                url=f"https://t.me/{nand.username}?startgroup=true",
                style=s[0],
            )
        ],
        # Full-width Help
        [
            InlineKeyboardButton(
                text="📖  " + _["S_B_4"],
                callback_data="settings_back_helper",
                style=s[1],
            )
        ],
        # 2x2 Owner / Channel / Support / Source
        [
            InlineKeyboardButton(
                text="👑  " + _["S_B_5"],
                user_id=config.OWNER_ID,
                style=s[2],
            ),
            InlineKeyboardButton(
                text="📢  " + _["S_B_6"],
                url=config.SUPPORT_CHANNEL,
                style=s[3],
            ),
        ],
        [
            InlineKeyboardButton(
                text="💬  " + _["S_B_2"],
                url=config.SUPPORT_CHAT,
                style=s[4],
            ),
            InlineKeyboardButton(
                text="📦  " + _["S_B_7"],
                url=getattr(config, "UPSTREAM_REPO", "https://github.com/Kartiknishad36/Renu-music-"),
                style=s[5],
            ),
        ],
        # Extra feature buttons
        [
            InlineKeyboardButton(
                text="🔁  Autoplay",
                callback_data="autoplay_help",
                style=s[6],
            ),
            InlineKeyboardButton(
                text="🏷️  TagAll",
                callback_data="tagall_help",
                style=s[7],
            ),
        ],
        [
            InlineKeyboardButton(
                text="⚙️  Settings",
                callback_data="settings_helper",
                style=s[8],
            ),
            InlineKeyboardButton(
                text="📊  Stats",
                callback_data="stats_overall",
                style=s[9],
            ),
        ],
    ]
    return buttons
