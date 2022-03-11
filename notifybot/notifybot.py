import datetime
import logging
import os
import re
import sqlite3
import traceback

import aiohttp
import discord
from discord.ext import commands

from .cogs import HeatMapCog, VoiceNotificationCog
from .vars import Data

logger = logging.getLogger(__name__)


class NotifyBot(commands.Bot):
    """Bot本体

    全体のエラーをdiscordのerrorチャンネルに通知する

    """
    async def on_error(self, event_method: str, *args, **kwargs):
        if Data.ERROR_NOTIFY_INCOMING_WEBHOOK_URL is None:
            await super().on_error(event_method, *args, **kwargs)
            return
        now = datetime.datetime.now(tz=Data.JST).strftime("%Y-%m-%d %H:%M:%S")
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                Data.ERROR_NOTIFY_INCOMING_WEBHOOK_URL, session=session)
            await webhook.send("[{}] Exception is occured in {} ```{}```".format(now, event_method, traceback.format_exc()))
        await super().on_error(event_method, *args, **kwargs)

    async def on_command_error(self, ctx: discord.ext.commands.Context, ex: Exception):
        if Data.ERROR_NOTIFY_INCOMING_WEBHOOK_URL is None:
            await super().on_command_error(ctx, ex)
            return
        now = datetime.datetime.now(tz=Data.JST).strftime("%Y-%m-%d %H:%M:%S")
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(
                Data.ERROR_NOTIFY_INCOMING_WEBHOOK_URL, session=session)
            ex_str = "".join(traceback.format_exception(
                type(ex), ex, ex.__traceback__))
            await webhook.send("[{}] Command Exception is occured in {} ```{}```".format(now, ctx.command, ex_str))

        await super().on_command_error(ctx, ex)


async def db_init(notify_channel):
    """データベースの初期化"""

    TIME_FIELD_PATTERN = r"(\d{2}):(\d{2}):(\d{2})"
    if os.path.exists(Data.DB_NAME):
        logger.info("DB exists.")
        return

    time_field_pattern = re.compile(TIME_FIELD_PATTERN)

    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()

    cur.execute(f"""CREATE TABLE {Data.VC_HISTORY_TABLE_NAME}
                    (user_id int unsigned not null, channel text unsigned not null, access_datetime datetime not null, is_entering boolean)""")
    cur.execute(f"""CREATE TABLE {Data.ACCESS_TIME_TABLE}
                    (start datetime not null, end datetime not null, channel text unsigned not null)""")

    con.commit()
    con.close()

    logger.info("DB is initialized.")


def main():
    intents = discord.Intents.default()
    intents.members = True
    intents.reactions = True

    bot = NotifyBot(intents=intents)

    @bot.event
    async def on_ready():
        await db_init(bot.get_channel(Data.NOTIFY_CHANNEL_ID))

    bot.add_cog(VoiceNotificationCog(bot))
    bot.add_cog(HeatMapCog(bot))
    bot.run(Data.TOKEN)
