import asyncio
import time
import aiosqlite
import random
import json
import discord
import util
import logging
from discord.ext import commands
from urllib.request import urlopen
from main import global_cooldown

logger = logging.getLogger("bot_logger")

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Links your handle")
    @global_cooldown()
    async def register(self, ctx, handle: str):
        if not isinstance(handle, str):
            await ctx.send("Invalid handle.")
            return
            
        b = await util.handle_exists_on_cf(handle)
        if not b:
            await ctx.send("Invalid handle.")
            return
        # check that it is not in the database already (for this server)
        if await util.handle_exists(ctx.guild.id, ctx.author.id, handle):
            await ctx.send("Handle taken in this server.")
            return
        # check that user does not already have a handle
        if await util.handle_linked(ctx.guild.id, ctx.author.id):
            await ctx.send("You already linked a handle (use unlink if you wish to remove it).")
            return
        # now give them the verification challenge
        ret = await validate_handle(ctx, ctx.guild.id, ctx.author.id, handle)
        if ret == 1:
            await ctx.send(f"Handle set to {handle}.")
        elif ret == 2:
            await ctx.send("Verification failed.")
        elif ret == 3:
            await ctx.send("Handle has been taken (;-; are you trying to break me).")
        elif ret == 4:
            await ctx.send("You already linked a handle (during verification, is this a test?).")
        else:
            await ctx.send("Some error (maybe CF is down).")

    @commands.command(help="Unlinks your handle")
    @global_cooldown()
    async def unlink(self, ctx):
        if not await util.handle_linked(ctx.guild.id, ctx.author.id):
            await ctx.send("You have not linked a handle.")
            return
        embed = discord.Embed(title="Confirm", description="Are you sure? This action cannot be undone. React with :white_check_mark: within 60 seconds to confirm.", color=discord.Color.blue())
        message = await ctx.send(embed=embed)
        await asyncio.sleep(60)
        message = await ctx.channel.fetch_message(message.id)
        bad = True
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅":
                reactors = [user.id async for user in reaction.users()]
                if ctx.author.id in reactors:
                    bad = False
                break

        if bad:
            embed.description = "Account not unlinked."
            await message.edit(embed=embed)
            return
        else:
            await unlink(ctx.guild.id, ctx.author.id)
            embed.description = "Account unlinked."
            await message.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(Register(bot))

async def validate_handle(ctx, server_id: int, user_id: int, handle: str):
    # 1 - ok
    # 2 - didn't receive
    # 3 - handle exists
    # 4 - you have a handle
    # 5 - some other error

    if util.problems is None:
        try:
            await util.get_problems()    
        except Exception as e:
            logger.error(f"Failed to get problems: {e}")
            return 5

    problem = util.problems[random.randint(0, len(util.problems) - 1)]
    t = time.time()
    await ctx.send(f"Submit a compilation error to the following problem in the next 60 seconds:\nhttps://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}")

    await asyncio.sleep(60)
    if not await got_submission(handle, problem, t):
        return 2
    async with aiosqlite.connect(util.path + "bot_data.db") as db:
        try:
            await db.execute("BEGIN TRANSACTION")

            async with db.execute('SELECT handle FROM users WHERE server_id = ? AND handle = ?', (server_id, handle)) as cursor:
                existing_handle = await cursor.fetchone()

            if existing_handle:
                await db.rollback()
                return 3

            async with db.execute('SELECT handle FROM users WHERE server_id = ? AND user_id = ?', (server_id, user_id)) as cursor:
                linked_handle = await cursor.fetchone()

            if linked_handle:
                await db.rollback()
                return 4

            history = "[]"
            rating_history = "[1500]"
            await db.execute(
                'INSERT INTO users (server_id, user_id, handle, rating, history, rating_history) VALUES (?, ?, ?, ?, ?, ?)',
                (server_id, user_id, handle, 1500, history, rating_history)
            )

            await db.commit()
            return 1
        except Exception as e:
            await db.rollback()
            logger.error(f"Transaction failed: {e}")
            return 5

async def got_submission(handle: str, problem, t):
    try:

        URL = f"https://codeforces.com/api/contest.status?contestId={problem['contestId']}&asManager=false&from=1&count=10&handle={handle}"
        response = urlopen(URL)
        response_data = json.loads(response.read())

        if response_data["status"] != "OK":
            return False

        for o in response_data["result"]:
            if o["problem"]["index"] == problem["index"] and o["verdict"] == "COMPILATION_ERROR" and o["contestId"] == problem["contestId"]:
                return o["creationTimeSeconds"] > t

    except Exception as e:
        logger.error(f"Error getting submission: {e}")
        return False

async def unlink(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(util.path + "bot_data.db") as db:
            await db.execute("DELETE FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")