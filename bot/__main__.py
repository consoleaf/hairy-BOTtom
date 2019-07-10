import asyncio
import os
import json
import sys
import time
import threading
import discord
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
        self.discord_check.start()

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
        data = re.match(r"!([^ ]+)(.*)", message.content)
        if data[1].lower() == "add_streamer":
            streamer_name = data[2].strip()
            await self.add_streamer(streamer_name, message.channel.id, message.channel.guild.id)
            await message.channel.send("{0} is added to the streamers list!".format(streamer_name))
            return
        if data[1].lower() == "cat":
            url = "..gif"
            while re.match(r".*\.(.+)", url)[1] == "gif":
                resp = urllib.request.urlopen("http://aws.random.cat/meow")
                url = json.loads(resp.read())["file"]
            emoji = ":heart_eyes_cat:"
            # if message.guild.id == 569460226676228096:
            #     emoji = ":nyvenaWelp:"
            embed = discord.Embed(title="Cat pic for ya! {emoji}".format(emoji=emoji))
            embed.set_image(url=url)
            await message.channel.send(embed=embed)
        if data[1].lower() == "dog":
            url = "..gif"
            while re.match(r".*\.(.+)", url)[1] == "gif":
                resp = urllib.request.urlopen("http://aws.random.dog/woof")
                url = json.loads(resp.read())["file"]
            emoji = ":heart_eyes_cat:"
            # if message.guild.id == 569460226676228096:
            #     emoji = ":nyvenaWelp:"
            embed = discord.Embed(title="Cat pic for ya! {emoji}".format(emoji=emoji))
            embed.set_image(url=url)
            await message.channel.send(embed=embed)
        if data[1].lower() == "thirst":
            embed = discord.Embed(title="Ya naughty!")
            await message.channel.send(embed=embed)

    @orm.db_session
    def count_chars(self, message):
        user = User.get(uid=str(message.author.id))
        if user is None:
            user = User(uid=str(message.author.id), char_count=0)
        prev_lvl = 0
        if user.char_count - 5 > 0:
            prev_lvl = int(math.log10(user.char_count - 5))
        user.char_count += min(len(message.content), 100)
        if user.uid == "373594474154033153" and user.char_count > 20:
            prev_lvl = 1
            user.char_count = 10
        new_lvl = int(math.log10(user.char_count - 5))
        orm.commit()

        print("{0} characters total. Level: {1}".format(user.char_count, new_lvl))

        if prev_lvl != new_lvl:
            return new_lvl
        return None

    @orm.db_session
    async def add_streamer(self, streamer_name, channel_id, guild_id):
        if Streamer.exists(login=streamer_name):
            return
        Streamer(login=streamer_name, channel_id=str(channel_id), guild_id=str(guild_id))

    async def alert_live(self, streamer):
        channel = client.get_channel(int(streamer.channel_id))
        await channel.send("hey, {mention}, {0} is now live! Come see: https://twitch.tv/{0}"
                           .format(streamer.login, mention="dumbo gulphole"))
        pass

    # noinspection PyCallingNonCallable
    @tasks.loop(seconds=30.0)
    async def discord_check(self):
        print("Clock ticked! Time to check the streamers!")

        @orm.db_session
        def get_streamers():
            for streamer_ in Streamer.select():
                orm.commit()
                yield streamer_

        @orm.db_session
        async def f():
            if respData["data"]:
                if respData["data"][0]["type"] == "live" and not streamer.online:
                    print("Streamer is live!")
                    await client.alert_live(streamer)
                    streamer.online = True
                else:
                    if respData["data"][0]["type"] != "live":
                        print("Streamer is not live")
                        streamer.online = False
                    print("Streamer is still live")
            else:
                print("Streamer is not live")
                streamer.online = False

        try:
            for streamer in get_streamers():
                print("Checking {0}...".format(streamer.login))
                headers = {
                    "Client-ID": "7i5krka1pcikxak6y74sk77fpmj89y"
                }
                url = "https://api.twitch.tv/helix/streams?user_login={0.login}&first=1".format(streamer)
                req = urllib.request.Request(url, headers=headers)
                resp = urllib.request.urlopen(req)
                respData = json.loads(resp.read())
                await f()
        except Exception as e:
            print(e, file=sys.stderr)

    @discord_check.before_loop
    async def before_discord_checker(self):
        print("waiting for bot to start...")
        await self.wait_until_ready()

    @discord_check.after_loop
    async def after_discord_checker(self):
        print("Stopping discord checker...")


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
        if os.path.exists("db.sqlite"):
            os.rename("db.sqlite", os.path.join(os.getcwd(), "db.sqlite"))
        db.bind(provider="sqlite", filename=os.path.join(os.getcwd(), "db.sqlite"), create_db=True)
        db.generate_mapping(create_tables=True)

        client.run(credentials.token)
    except KeyboardInterrupt as e:
        print("Bot is stopping...")
