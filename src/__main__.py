import asyncio
import json
import time
import threading
import discord
import asyncpg
from discord.ext import tasks, commands
import credentials
import re
from pony import orm
import math
import urllib.request

db = orm.Database()


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)

    async def on_ready(self):
        print("Logged on as {0}!".format(self.user))

    async def on_message(self, message):
        """

        :type message: discord.message.Message
        """

        # If self's message, just leave.
        if message.author == self.user:
            return

        # If command, execute it.
        if re.match(r"!.*", message.content):
            await self.command(message)

        print("Message from {0.author}: {0.content}.".format(message))
        level = self.count_chars(message)
        if level:
            await message.channel.send("{0}, you leveled up to level {1}!".format(message.author.mention, level))

    async def command(self, message):
        data = re.match(r"!([^ ]+) (.*)", message.content)
        if data[1] == "add_streamer":
            streamer_name = data[2].strip()
            await self.add_streamer(streamer_name, message.channel.id, message.channel.guild.id)
            await message.channel.send("{0} is added to the streamers list!".format(streamer_name))

    @orm.db_session
    def count_chars(self, message):
        user = User.get(uid=str(message.author.id))
        if user is None:
            user = User(uid=str(message.author.id), char_count=0)
        prev_lvl = 0
        if user.char_count > 0:
            prev_lvl = int(math.log10(user.char_count))
        user.char_count += min(len(message.content), 100)
        new_lvl = int(math.log10(user.char_count))
        orm.commit()
        if prev_lvl != new_lvl:
            return new_lvl
        return None

    @orm.db_session
    async def add_streamer(self, streamer_name, channel_id, guild_id):
        if Streamer.exists(login=streamer_name):
            return
        Streamer(login=streamer_name, channel_id=str(channel_id), guild_id=str(guild_id))


class User(db.Entity):
    uid = orm.Required(str, unique=True)
    char_count = orm.Required(int)


class Streamer(db.Entity):
    login = orm.Required(str, unique=True)
    online = orm.Required(bool, default=False)
    channel_id = orm.Required(str)
    guild_id = orm.Required(str)


client = MyClient()

if __name__ == "__main__":
    try:
        # orm.set_sql_debug(True)
        db.bind(provider="sqlite", filename="db.sqlite", create_db=True)
        db.generate_mapping(create_tables=True)

        client.run(credentials.token)
    except KeyboardInterrupt as e:
        print("Bot is stopping...")
