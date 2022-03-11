import datetime
import io
import logging
import sqlite3
from collections import defaultdict

import discord
import matplotlib.pyplot as plt
import pandas as pd
from discord.commands import Option
from discord.ext import commands
from ..libs import heatmap
from ..vars import Data

logger = logging.getLogger(__name__)

FILENAME = "kusa.png"

SECONDS_OF_24HOURS = 86400


class HeatMapCog(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        self.bot = bot
        self.server_id = Data.SERVER_ID

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.info(f"{self.__class__.__name__} is on ready.")
        self.guild = self.bot.get_guild(self.server_id)

    def create_heatmap_file(self, series: pd.Series) -> discord.File:
        end_date = datetime.datetime.now().date()
        hm = heatmap.HeatMap(series, end_date=end_date)
        fig, ax = plt.subplots()
        hm.plot(vmin=0, vmax=max(series), linewidth=1, ax=ax)
        fig.set_figheight(4)
        fig.set_figwidth(16)
        format = "png"
        sio = io.BytesIO()
        plt.savefig(sio, format=format)
        sio.seek(0)
        return discord.File(sio, filename=FILENAME)

    def aggregate_access_time(self, channel: str = None) -> pd.Series:
        con = sqlite3.connect(
            Data.DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        sqlite3.dbapi2.converters['DATETIME'] = sqlite3.dbapi2.converters['TIMESTAMP']
        cur = con.cursor()
        dt_dict: defaultdict = defaultdict(int)
        query = f"""SELECT start, end FROM {Data.ACCESS_TIME_TABLE}"""
        query_kwargs = {}
        if channel is not None:
            query += "\nWHERE channel = :channel"
            query_kwargs["channel"] = channel

        for start, end in cur.execute(query, query_kwargs):
            dt_dict[start.date()] += (end - start).total_seconds() / \
                SECONDS_OF_24HOURS

        index = pd.DatetimeIndex(dt_dict.keys())
        series = pd.Series(list(dt_dict.values()), index=index)

        return series

    @commands.slash_command(description="通話時間の可視化")
    async def kusa(self,
                   ctx,
                   channel: Option(discord.VoiceChannel, description="通話時間の可視化をするチャンネル (オプション)", name="チャンネル", required=False)) -> None:
        if ctx.guild != self.guild:
            return

        content = ""

        if channel:
            series = self.aggregate_access_time(channel.name)
            content = channel.name
        else:
            series = self.aggregate_access_time()

        if len(series) == 0:
            await ctx.respond(content="データが見つかりませんでした")
            return

        await ctx.respond(content=content, file=self.create_heatmap_file(series))
