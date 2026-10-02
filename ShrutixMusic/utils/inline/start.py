import random

from pyrogram.types import InlineKeyboardButton

import config
from ShrutixMusic import nand

# Colored button styles (kurigram / pyrogram with ButtonStyle)
try:
    from pyrogram.enums import ButtonStyle
    _HAS_STYLE = True
    COLORS = (ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER)
except Exception:
    _HAS_STYLE = False
    COLORS = ()


def _btn(text, style=None, **kwargs):
    """Build button; attach style only if library supports it."""
    if _HAS_STYLE and style is not None:
        try:
            return InlineKeyboardButton(text=text, style=style, **kwargs)
        except TypeError:
            return InlineKeyboardButton(text=text, **kwargs)
    return InlineKeyboardButton(text=text, **kwargs)


def _styles(n):
    if not _HAS_STYLE or not COLORS:
        return [None] * n
    return [random.choice(COLORS) for _ in range(n)]


def _owner_btn(text, style=None):
    """Owner button – prefer user_id, fallback url if OWNER link known."""
    oid = getattr(config, "OWNER_ID", 0) or 0
    try:
        if oid:
            return _btn(text, style=style, user_id=int(oid))
    except Exception:
        pass
    # fallback: open support chat
    return _btn(text, style=style, url=config.SUPPORT_CHAT)


def start_panel(_):
    """Group /start – full buttons + premium colored emoji layout (Mahi style)."""
    s = _styles(10)
    add_url = f"https://t.me/{nand.username}?startgroup=true" if getattr(nand, "username", None) else config.SUPPORT_CHAT
    buttons = [
        # Full-width Add + Help (green style feel)
        [_btn("🟢 ➕  Add Me To Your Group", style=s[0], url=add_url)],
        [_btn("📖  Help & Commands", style=s[1], callback_data="settings_back_helper")],
        # 2x2 Owner / Channel
        [
            _owner_btn("👑  Owner", style=s[2]),
            _btn("📢  Update Channel", style=s[3], url=config.SUPPORT_CHANNEL),
        ],
        # 2x2 Support / Source
        [
            _btn("💬  Support Group", style=s[4], url=config.SUPPORT_CHAT),
            _btn("📦  Source Code", style=s[5], url=getattr(config, "UPSTREAM_REPO", "https://github.com/Kartiknishad36/Renu-music-")),
        ],
        # Extra features
        [
            _btn("🔁  Autoplay", style=s[6], callback_data="autoplay_help"),
            _btn("🏷️  TagAll", style=s[7], callback_data="tagall_help"),
        ],
        [
            _btn("⚙️  Settings", style=s[8], callback_data="settings_helper"),
            _btn("📊  Stats", style=s[9], callback_data="stats_overall"),
        ],
    ]
    return buttons


def private_panel(_):
    """Private /start – Mahi layout + premium colored emoji."""
    s = _styles(10)
    add_url = f"https://t.me/{nand.username}?startgroup=true" if getattr(nand, "username", None) else config.SUPPORT_CHAT
    buttons = [
        [_btn("🟢 ➕  Add Me In Your Group", style=s[0], url=add_url)],
        [_btn("📖  Help & Commands", style=s[1], callback_data="settings_back_helper")],
        [
            _owner_btn("👑  Owner", style=s[2]),
            _btn("📢  Update Channel", style=s[3], url=config.SUPPORT_CHANNEL),
        ],
        [
            _btn("💬  Support Group", style=s[4], url=config.SUPPORT_CHAT),
            _btn("📦  Source Code", style=s[5], url=getattr(config, "UPSTREAM_REPO", "https://github.com/Kartiknishad36/Renu-music-")),
        ],
        [
            _btn("🔁  Autoplay", style=s[6], callback_data="autoplay_help"),
            _btn("🏷️  TagAll", style=s[7], callback_data="tagall_help"),
        ],
        [
            _btn("⚙️  Settings", style=s[8], callback_data="settings_helper"),
            _btn("📊  Stats", style=s[9], callback_data="stats_overall"),
        ],
    ]
    return buttons
