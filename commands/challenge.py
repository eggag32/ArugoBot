import discord
import asyncio
import time
import util
import aiosqlite
import json
import logging
from main import global_cooldown
from discord.ext import commands
from urllib.request import urlopen

logger = logging.getLogger("bot_logger")

class Challenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Get a challenge")
    @global_cooldown()
    async def challenge(self, ctx, problem: str, length: int, users: commands.Greedy[discord.Member]):
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
        await asyncio.sleep(30)
        has_react = False
        bad = False
        message = await ctx.channel.fetch_message(message.id)
        for reaction in message.reactions:
            if str(reaction.emoji) == "✅":
                reactors = [user.id async for user in reaction.users()]
                has_react = True
                for us in user_list:
                    if us not in reactors:
                        bad = True
                        break
                break

        if (not has_react) or bad:
            embed.description = "Confirmation failed :x:."
            await message.edit(embed=embed)
            return
        else:
            embed.description = "Challenge confirmed :white_check_mark:."
            await message.edit(embed=embed)
        
        for id in user_list:
            await util.add_to_history(ctx.guild.id, id, problem)

        chal_embed = discord.Embed(title="Challenge", description="", color=discord.Color.blue())
        chal_embed.add_field(name="Time", value=util.format_time(length * 60), inline=False)
        p = f"[{util.problem_dict[problem]["index"]}. {util.problem_dict[problem]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[problem]["contestId"]}/{util.problem_dict[problem]["index"]})"
        chal_embed.add_field(name="Problem", value=p, inline=False)
        u = ""
        for i in range(len(user_list)):
            r = await util.get_rating(ctx.guild.id, user_list[i]) 
            l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
            u += f"- <@{user_list[i]}>, {r} (don't solve: {l[0]}, solve: {l[1]}) :hourglass:\n"
        chal_embed.add_field(name="Users", value=u, inline=False)
        message = await ctx.send(embed=chal_embed)

        solved = [0 for i in range(len(user_list))]

        now = time.time()

        for i in range(0, length * 60, 5):
            chal_embed = discord.Embed(title="Challenge", description="", color=discord.Color.blue())
            chal_embed.add_field(name="Time", value=util.format_time(length * 60 - (i + 5)), inline=False)
            p = f"[{util.problem_dict[problem]["index"]}. {util.problem_dict[problem]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[problem]["contestId"]}/{util.problem_dict[problem]["index"]})"
            chal_embed.add_field(name="Problem", value=p, inline=False)
            u = ""
            if i % 10 == 0:
                j = (i // 10) % len(user_list)
                if j < len(user_list) and solved[j] == 0:
                    solved[j] |= await check_ac(ctx.guild.id, user_list[j], problem, length, now)
            for j in range(len(user_list)):
                r = await util.get_rating(ctx.guild.id, user_list[j]) 
                l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
                if solved[j] == 0:
                    u += f"- <@{user_list[j]}>, {r} (don't solve: {l[0]}, solve: {l[1]}) :hourglass:\n"
                else:
                    u += f"- <@{user_list[j]}>, {r} :white_check_mark:\n"
        
            await asyncio.sleep(now + (i + 5) - time.time()) 
            chal_embed.add_field(name="Users", value=u, inline=False)
            message = await ctx.channel.fetch_message(message.id)
            await message.edit(embed=chal_embed)
            if sum(solved) == len(user_list):
                break

        for j in range(len(user_list)):
            if solved[j] == 0:
                solved[j] |= await check_ac(ctx.guild.id, user_list[j], problem, length, now)
                if solved[j] == 0:
                    r = await util.get_rating(ctx.guild.id, user_list[j])
                    l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
                    await update_rating(ctx.guild.id, user_list[j], r + l[0])
                await asyncio.sleep(2)
        
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
        

async def setup(bot):
    await bot.add_cog(Challenge(bot))

async def check_ac(server_id: str, user_id: int, problem: str, length: int, start_time: int):
    handle = await util.get_handle(server_id, user_id)
    if await got_ac(handle, problem, length, start_time):
        r = await util.get_rating(server_id, user_id)
        l = util.get_rating_changes(r, util.problem_dict[problem]["rating"], length)
        await update_rating(server_id, user_id, r + l[1])
        return 1
    return 0

async def got_ac(handle: str, problem: str, length: int, start_time: int):
    try:

        URL = f"https://codeforces.com/api/contest.status?contestId={util.problem_dict[problem]['contestId']}&asManager=false&from=1&count=100&handle={handle}"
        response = urlopen(URL)
        response_data = json.loads(response.read())

        if response_data["status"] != "OK":
            return False

        for o in response_data["result"]:
            if problem == str(str(o["problem"]["contestId"]) + o["problem"]["index"]) and o["verdict"] == "OK":
                return o["creationTimeSeconds"] <= start_time + length * 60 and o["creationTimeSeconds"] >= start_time

    except Exception as e:
        logger.error(f"Error during challenge: {e}")
        return False

async def update_rating(server_id: str, user_id: int, rating: int):
    try:
        async with aiosqlite.connect(util.path + "bot_data.db") as db:
            hist = []
            async with db.execute("SELECT rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    hist = json.loads(row[0])
                    hist.append(rating)
                else:
                    hist = [rating]
            await db.execute("UPDATE users SET rating = ?, rating_history = ? WHERE server_id = ? AND user_id = ?", (rating, json.dumps(hist), server_id, user_id))
            await db.commit()
    except Exception as e:
        logger.error(f"Database error (rating update): {e}")