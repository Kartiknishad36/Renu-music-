import asyncio
import importlib
import sys
import traceback

from pyrogram import idle
from pytgcalls.exceptions import NoActiveGroupCall

import config
from ShrutixMusic import LOGGER, nand, userbot
from ShrutixMusic.core.call import Shruti
from ShrutixMusic.misc import sudo
from ShrutixMusic.plugins import ALL_MODULES
from ShrutixMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

# Start health HTTP early (same process backup if start script health dies)
try:
    from health_server import start_health_server

    start_health_server()
except Exception as e:
    print(f"[health] skip: {e}")


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error("Assistant STRING session missing — set STRING1 in env")
        # Do not hard-exit forever; allow restart loop to retry after env fix
        await asyncio.sleep(30)
        return

    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception:
        pass

    await nand.start()
    for all_module in ALL_MODULES:
        importlib.import_module("ShrutixMusic.plugins" + all_module)
    LOGGER("ShrutixMusic.plugins").info("Successfully Imported Modules...")
    await userbot.start()
    await Shruti.start()

    # Log-group VC optional — NEVER exit bot if VC is off
    try:
        await Shruti.stream_call("https://te.legra.ph/file/29f784eb49d230ab62e9e.mp4")
    except NoActiveGroupCall:
        LOGGER("ShrutixMusic").warning(
            "Log group videochat is OFF — bot continues without test stream."
        )
    except Exception as e:
        LOGGER("ShrutixMusic").warning(f"stream_call skip: {e}")

    await Shruti.decorators()
    LOGGER("ShrutixMusic").info(
        "Renu Music Bot Started Successfully.\n"
        "Owner: Kartik Nishad\n"
        "Waah!"
    )
    await idle()
    await nand.stop()
    await userbot.stop()
    LOGGER("ShrutixMusic").info("Stopping Renu Music Bot...")


def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init())
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
        # non-zero so start script restarts
        sys.exit(1)


if __name__ == "__main__":
    main()
