import datetime
import logging
import sqlite3
from typing import Optional, Tuple

import discord
from discord.ext import commands

from ..vars import Data

logger = logging.getLogger(__name__)


def timedelta_to_str(td: datetime.timedelta):
    hours = int(td / datetime.timedelta(hours=1))
    minutes = int((td - hours * datetime.timedelta(hours=1)) /
                  datetime.timedelta(minutes=1))
    seconds = int((td - hours * datetime.timedelta(hours=1) -
                   minutes * datetime.timedelta(minutes=1)).seconds)

    return "{:02}:{:02}:{:02}".format(hours, minutes, seconds)


def is_commitable(member_id: int, channel: str, is_enter: bool = True) -> Optional[bool]:
    """入退室イベントが記録可能かを返す

    何らかの不具合で入室が記録されないまま退室履歴を記録すると、その後の入退室通知が行われなくなる\\
    そのため退室イベント発火時に直前の履歴が入室かどうかを調べ、入室じゃない場合に退室時の処理をスキップする\\
    同様の理由で入室イベント時にも直前の履歴が入室の場合は処理をスキップする

    Args:
        member_id (int): メンバーのID
        channel (str): チャンネル
        is_enter (bool): 入室イベントかどうか. Default is True

    Returns:
        bool: 入退室イベントが記録可能か
    """

    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()
    cur.execute("""SELECT is_entering FROM vc_access_history
                    WHERE user_id = :user_id
                    AND channel = :channel
                    ORDER BY access_datetime DESC
                    LIMIT 1""", {"user_id": member_id,
                                 "channel": channel})
    result = cur.fetchone()
    if result is None:
        return is_enter

    con.close()

    return not (bool(result[0]) is is_enter)


def is_already_entering(member_id: int, channel: str) -> bool:
    """すでにチャンネルへ入室済みか

    一度退出したチャンネルでの通話が終わる前に入室したとき、その入室記録を通知しない\\
    最後の通話記録の終了時間より後に退室記録が存在するかどうかを返す

    Args:
        member_id (int): 入室したメンバーのID
        channel (str): 入室したチャンネル

    Returns:
        bool: 退室記録が存在するか
    """
    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()
    cur.execute("""SELECT count(*) FROM vc_access_history
                    WHERE access_datetime > (SELECT end FROM access_time WHERE channel = :channel ORDER BY end DESC LIMIT 1)
                    AND user_id = :user_id
                    AND channel = :channel
                    AND is_entering = 0
                    LIMIT 1""", {"user_id": member_id,
                                 "channel": channel})
    is_exist = cur.fetchone()[0]
    con.close()

    return bool(is_exist)


def commit_history(member_id: int, channel: str, now: datetime.datetime, is_entering: bool) -> None:
    """入退室記録を追加する

    Args:
        member_id (int): メンバーのID
        channel (str): チャンネル名
        now (datetime.datetime): 記録時間
        is_entering (bool): 入室かどうか
    """
    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO vc_access_history(user_id, channel, access_datetime, is_entering) VALUES (?,?,?,?)",
        (member_id, channel, now.strftime("%Y-%m-%d %H:%M:%S.%f"), is_entering))
    con.commit()
    con.close()


def is_all_member_exited_from(channel: str) -> bool:
    """チャンネルから全員退室したか

    チャンネルに誰か入ってから全員抜けるまでを通話時間とする\\
    直近の通話記録の終了時間より後の入室記録と退室記録の数を比較して、一致するかどうかを返す\\
    入室記録と退出記録の数が同じとき、全員そのチャンネルから退出したと判断する


    Args:
        channel (str): チャンネル名

    Return:
        bool: 全員退出したか
    """
    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()
    cur.execute("""SELECT count(*) FROM vc_access_history
                    WHERE access_datetime > (SELECT end FROM access_time WHERE channel = :channel ORDER BY end DESC LIMIT 1)
                    AND channel = :channel
                    AND is_entering = 1""", {"channel": channel})
    enter_count = cur.fetchone()
    cur.execute("""SELECT count(*) FROM vc_access_history
                    WHERE access_datetime > (SELECT end FROM access_time WHERE channel = :channel ORDER BY end DESC LIMIT 1)
                    AND channel = :channel
                    AND is_entering = 0""", {"channel": channel})
    exit_count = cur.fetchone()
    con.close()

    return enter_count[0] == exit_count[0]


def commit_access_time(channel: str) -> Tuple[str, str]:
    """通話時間を記録して開始終了時間を返す

    入退室記録からそのチャンネルの最初の入室記録と最後の退出記録を通話時間を記録して、開始終了時間を返す

    Args:
        channel (str): チャンネル名
    Return:
        Tuple[str, str]: 入室時間と退出時間の文字列
    """
    con = sqlite3.connect(Data.DB_NAME)
    cur = con.cursor()
    cur.execute("""SELECT end FROM access_time WHERE channel = :channel ORDER BY end DESC LIMIT 1""", {
                "channel": channel})
    end = cur.fetchone()
    if end is None:
        end = "2000-01-01 00:00:00"
    else:
        end = end[0]

    cur.execute("""SELECT access_datetime FROM vc_access_history
                    WHERE access_datetime > :end
                    AND channel = :channel
                    AND is_entering = 1
                    ORDER BY access_datetime LIMIT 1""", {"channel": channel, "end": end})
    first_enter_time = cur.fetchone()[0]
    cur.execute("""SELECT access_datetime FROM vc_access_history
                    WHERE access_datetime > :end
                    AND channel = :channel
                    AND is_entering = 0
                    ORDER BY access_datetime DESC LIMIT 1""", {"channel": channel, "end": end})
    last_exit_time = cur.fetchone()[0]
    cur.execute("""INSERT INTO access_time(start, end, channel) VALUES (?,?,?)""",
                (first_enter_time, last_exit_time, channel))
    con.commit()
    con.close()

    return first_enter_time, last_exit_time


class VoiceNotificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.notify_channel_id = Data.NOTIFY_CHANNEL_ID
        self.server_id = Data.SERVER_ID

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__} is on ready.")

        self.notify_channel = self.bot.get_channel(self.notify_channel_id)
        self.guild = self.bot.get_guild(self.server_id)

        logger.debug(f"Notify Channel is {self.notify_channel}")
        logger.debug(f"Guild is {self.guild}")

    async def enter(self, member: discord.User, channel: discord.VoiceChannel, now: datetime.datetime):

        if not is_commitable(member.id, str(channel)):
            logger.info(
                f"""(Skipped) [VC UPDATE (Enter)]\tUser: {member}\tChannel:{channel}""")
            return

        logger.info(
            f"""[VC UPDATE (Enter)]\tUser: {member}\tChannel:{channel} """)

        commit_history(member.id, str(channel), now, True)

        if is_already_entering(member.id, str(channel)):
            return

        embed = discord.Embed(title="通話開始", description="",
                              color=discord.Colour.red())
        embed.add_field(name="`チャンネル`", value=f"{channel}")
        embed.add_field(name="`始めた人`", value=f"{member.display_name}さん")
        embed.add_field(
            name='`開始時間`', value=f'{now.strftime("%Y/%m/%d %H:%M:%S")}')
        embed.set_thumbnail(url=f"{member.display_avatar.url}")

        await self.notify_channel.send(embed=embed)

    async def exit(self, member: discord.User, channel: discord.VoiceChannel, now: datetime.datetime):

        if not is_commitable(member.id, str(channel), is_enter=False):
            logger.info(
                f"""(Skipped) [VC UPDATE (Exit)]\tUser: {member}\tChannel:{channel}""")
            return

        logger.info(
            f"""[VC UPDATE (Exit)]\tUser: {member}\tChannel:{channel}""")

        commit_history(member.id, str(channel), now, False)

        if is_all_member_exited_from(str(channel)):
            start, end = commit_access_time(str(channel))
            start_dt = datetime.datetime.strptime(
                start, "%Y-%m-%d %H:%M:%S.%f")
            end_dt = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M:%S.%f")

            elapsed_time = timedelta_to_str(end_dt - start_dt)

            embed = discord.Embed(
                title="通話終了", description="", color=discord.Colour.blue())
            embed.add_field(name="`チャンネル`", value=f"{channel}")
            embed.add_field(name='`通話時間`', value=f"{elapsed_time}")

            await self.notify_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.User, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return

        now: datetime.datetime = datetime.datetime.now(tz=Data.JST)

        # exit
        if before.channel is not None and \
                before.channel.guild == self.guild:
            await self.exit(member, before.channel, now)

        # enter
        if after.channel is not None and \
                after.channel.guild == self.guild:
            await self.enter(member, after.channel, now)
