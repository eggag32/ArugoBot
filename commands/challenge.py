import discord
import asyncio
import time
import util
import aiosqlite
import json
import logging
from exceptions import DatabaseError
from main import global_cooldown
from discord.ext import commands

logger = logging.getLogger("bot_logger")
active_chal = set()

class Challenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.egg = bot.egg    

    @commands.command(help="Get a challenge")
    @global_cooldown()
    async def challenge(self, ctx, 
                        problem: str = commands.param(description=": Problem for the challenge (e.g. 1000A)"),
                        length: int = commands.param(description=": Length of the challenge in minutes (40/60/80)"),
                        users: commands.Greedy[discord.Member] = commands.param(description=": Participants other than you (e.g. @eggag32 @eggag33) (optional)")):
        user_list = None
        try:
            if not isinstance(problem, str):
                await ctx.send("Problem must be a string.")
                return
            if not isinstance(length, int):
                await ctx.send("Invalid length. Valid lengths are 40, 60, and 80 minutes.")
                return
            if not isinstance(users, list):
                await ctx.send("Users must be a list.")
                return
            if not all(isinstance(user, discord.Member) for user in users):
                await ctx.send("Some inputs were not valid members.")
                return

            if not (length == 40 or length == 60 or length == 80):
                await ctx.send("Invalid length. Valid lengths are 40, 60, and 80 minutes.")
                return
            if not problem in util.problem_dict:
                await ctx.send("Invalid problem. Make sure it is in the correct format (concatenation of contest ID and problem index, for example 1000A).")
                return

            user_list = [member.id for member in users]
            user_list.append(ctx.author.id)
            user_list = list(set(user_list))

            global active_chal
            for id in user_list:
                if (id, ctx.guild.id) in active_chal:
                    await ctx.send("One or more users are already in a challenge.")
                    return

            if len(user_list) > 5:
                await ctx.send("Too many users (limit is 5).")
                return

            for id in user_list:
                if not await util.handle_linked(ctx.guild.id, id):
                    await ctx.send("One or more users have not linked a handle.")
                    return
            # for each user check that it is not in their history
            for id in user_list:
                s = await util.get_history(ctx.guild.id, id)
                if problem in s:
                    await ctx.send("One or more users have already done this problem.")
                    return
            # then get all their ratings (and predicted changes) and create an embed
            embed = discord.Embed(title="Confirm", description="React with :white_check_mark: within 30 seconds to confirm", color=discord.Color.blue())
            embed.add_field(name="Time", value=util.format_time(length*60), inline=False)
            p = f"[{util.problem_dict[problem]["index"]}. {util.problem_dict[problem]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[problem]["contestId"]}/{util.problem_dict[problem]["index"]})"
            embed.add_field(name="Problem", value=p, inline=False)
            u = ""
            for i in range(len(user_list)):
                r = await util.get_rating(ctx.guild.id, user_list[i]) 
                l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
                u += f"- <@{user_list[i]}>, {r} (don't solve: {l[0]}, solve: {l[1]})\n"
            embed.add_field(name="Users", value=u, inline=False)
            message = await ctx.send(embed=embed)
            await message.add_reaction("✅")

            ready_users = set()

            def check(reaction, user):
                return user.id in user_list and str(reaction.emoji) == "✅" and reaction.message.id == message.id

            start_time = asyncio.get_event_loop().time()

            @self.bot.event
            async def on_raw_reaction_remove(payload):
                if payload.user_id in user_list and str(payload.emoji) == "✅" and payload.message_id == message.id:
                    if payload.user_id in ready_users:
                        ready_users.remove(payload.user_id)

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0 - (asyncio.get_event_loop().time() - start_time), check=check)
                    ready_users.add(user.id)
                    
                    if len(ready_users) == len(user_list):
                        break

                except asyncio.TimeoutError:
                    embed.description = "Confirmation failed :x:"
                    await message.edit(embed=embed)
                    return

            for id in user_list:
                if (id, ctx.guild.id) in active_chal:
                    await ctx.send("One or more users are already in a challenge.")
                    embed.description = "Confirmation failed :x:"
                    await message.edit(embed=embed)
                    return

            embed.description = "Challenge confirmed :white_check_mark:"
            for id in user_list:
                active_chal.add((id, ctx.guild.id))
            await message.edit(embed=embed)
            
            now = time.time()
            tasks = []
            solved = [0 for i in range(len(user_list))]
            psum = 0

            async def get_u():
                u = ""
                for j in range(len(user_list)):
                    r = await util.get_rating(ctx.guild.id, user_list[j]) 
                    l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
                    if solved[j] == 0:
                        u += f"- <@{user_list[j]}>, {r} (don't solve: {l[0]}, solve: {l[1]}) :hourglass:\n"
                    else:
                        u += f"- <@{user_list[j]}>, {r} :white_check_mark:\n"
                return u

            chal_embed = discord.Embed(title="Challenge", description="", color=discord.Color.blue())
            chal_embed.add_field(name="Time", value=f"Ends <t:{(int(now) + length * 60)}:R>", inline=False)
            chal_embed.add_field(name="Problem", value=p, inline=False)
            chal_embed.add_field(name="Users", value=await get_u(), inline=False)
            message = await ctx.channel.fetch_message(message.id)
            await message.edit(embed=chal_embed)

            for i in range(0, length * 60, 10):
                j = (i // 10) % len(user_list)
                if solved[j] == 0:
                    tasks.append(asyncio.create_task(check_ac(self.egg, ctx.guild.id, user_list[j], problem, length, now, solved, j)))
                if sum(solved) == psum and i % 60 != 0:
                    await asyncio.sleep(now + (i + 10) - time.time()) 
                    continue
                chal_embed.set_field_at(2, name="Users", value=await get_u(), inline=False)
                await asyncio.sleep(now + (i + 10) - time.time()) 
                message = await ctx.channel.fetch_message(message.id)
                await message.edit(embed=chal_embed)
                if sum(solved) == len(user_list):
                    break
                psum = sum(solved)
            
            chal_embed.title = "Updating"
            chal_embed.set_field_at(0, name="Time", value="Challenge ended", inline=False)
            chal_embed.set_field_at(2, name="Users", value=await get_u(), inline=False)
            message = await ctx.channel.fetch_message(message.id)
            await message.edit(embed=chal_embed)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    raise result

            if sum(solved) < len(user_list):
                await wait_for_queue(self.egg, ctx.guild.id, user_list, now, length, problem)

            for j in range(len(user_list)):
                if solved[j] == 0:
                    await check_ac(self.egg, ctx.guild.id, user_list[j], problem, length, now, solved, j)
                    if solved[j] == 0:
                        r = await util.get_rating(ctx.guild.id, user_list[j])
                        active_chal.remove((user_list[j], ctx.guild.id))
                        l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
                        await update_rating(ctx.guild.id, user_list[j], r + l[0], problem)
            
            chal_embed = discord.Embed(title="Challenge results", description="", color=discord.Color.blue())
            p = f"[{util.problem_dict[problem]["index"]}. {util.problem_dict[problem]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[problem]["contestId"]}/{util.problem_dict[problem]["index"]})"
            chal_embed.add_field(name="Problem", value=p, inline=False)
            u = ""
            for j in range(len(user_list)):
                r = await util.get_rating(ctx.guild.id, user_list[j]) 
                if solved[j] == 0:
                    u += f"- <@{user_list[j]}>, {r} :x:\n"
                else:
                    u += f"- <@{user_list[j]}>, {r} :white_check_mark:\n"
            
            chal_embed.add_field(name="Users", value=u, inline=False)
            message = await ctx.channel.fetch_message(message.id)
            await message.edit(embed=chal_embed)
        except Exception as e:
            logger.error(f"Some error: {e}")
            if user_list is not None:
                for id in user_list:
                    if (id, ctx.guild.id) in active_chal:
                        active_chal.remove((id, ctx.guild.id))
            await ctx.send("Something went wrong.")
        

async def setup(bot):
    await bot.add_cog(Challenge(bot))

async def wait_for_queue(egg, server_id: int, user_list: list, start_time: int, length: int, problem: str):
    # for 5 minutes we will wait for queued submissions
    wait_start = time.time()
    while time.time() - wait_start < 300:
        ok = [False]
        tasks = [asyncio.create_task(sub_in_queue(egg, server_id, us, start_time, length, problem, ok)) for us in user_list]
        await asyncio.gather(*tasks)
        if not ok[0]:
            return
        logger.info("Waiting for submission to be judged...")
        await asyncio.sleep(20)

async def sub_in_queue(egg, server_id: int, user_id: int, start_time: int, length: int, problem: str, ok: list):
    try:
        handle = await util.get_handle(server_id, user_id)
        response_data = await egg.codeforces("contest.status", {"contestId" : util.problem_dict[problem]["contestId"], "asManager" : "false", "from" : 1, "count" : 100, "handle" : handle})

        if response_data["status"] != "OK":
            ok[0] |= True
            return

        for o in response_data["result"]:
            if problem == str(str(o["problem"]["contestId"]) + o["problem"]["index"]) and o["verdict"] == "TESTING":
                if o["creationTimeSeconds"] <= start_time + length * 60 and o["creationTimeSeconds"] >= start_time:
                    ok[0] |= True
                    return

        ok[0] |= False

    except Exception as e:
        logger.error(f"Error during challenge: {e}")
        ok[0] |= True
        return

async def check_ac(egg, server_id: int, user_id: int, problem: str, length: int, start_time: int, solved: list, index: int):
    global active_chal
    handle = await util.get_handle(server_id, user_id)
    if await got_ac(egg, handle, problem, length, start_time):
        r = await util.get_rating(server_id, user_id)
        l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
        await update_rating(server_id, user_id, r + l[1], problem)
        active_chal.remove((user_id, server_id))
        solved[index] = 1

async def got_ac(egg, handle: str, problem: str, length: int, start_time: int):
    try:
        response_data = await egg.codeforces("contest.status", {"contestId" : util.problem_dict[problem]["contestId"], "asManager" : "false", "from" : 1, "count" : 100, "handle" : handle})

        if response_data["status"] != "OK":
            return False

        for o in response_data["result"]:
            if problem == str(str(o["problem"]["contestId"]) + o["problem"]["index"]) and o["verdict"] == "OK":
                if o["creationTimeSeconds"] <= start_time + length * 60 and o["creationTimeSeconds"] >= start_time:
                    return True
        
        return False

    except Exception as e:
        logger.error(f"Error during challenge: {e}")
        return False

async def update_rating(server_id: int, user_id: int, rating: int, problem: str):
    try:
        async with aiosqlite.connect(util.path + "bot_data.db") as db:
            await db.execute("BEGIN TRANSACTION")
            hist = []
            async with db.execute("SELECT rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    hist = json.loads(row[0])
                    hist.append(rating)
                else:
                    raise RuntimeError("Peter probably unlinked his account upd")
            await db.execute("UPDATE users SET rating = ?, rating_history = ? WHERE server_id = ? AND user_id = ?", (rating, json.dumps(hist), server_id, user_id))
            async with db.execute("SELECT history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    history = json.loads(row[0])
                    history.append(problem)
                else:
                    raise RuntimeError("Peter probably unlinked his account upd2")
            await db.execute("UPDATE users SET history = ? WHERE server_id = ? AND user_id = ?", (json.dumps(history), server_id, user_id))
            await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error (rating update): {e}")
        raise DatabaseError(e)