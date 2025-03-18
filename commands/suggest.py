import util
import discord
import aiosqlite
import asyncio
import json
import random
import logging
from exceptions import DatabaseError, RequestError
from discord.ext import commands
from main import global_cooldown

logger = logging.getLogger("bot_logger")

class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.egg = bot.egg

    @commands.command(help="Suggests a problem")
    @global_cooldown()
    async def suggest(self, ctx, rating: int = commands.param(description=": Rating of problems to suggest"),
                      users: commands.Greedy[discord.Member] = commands.param(description=": Users to suggest for other than you (e.g. @eggag33) (optional)")):
        try:
            if not isinstance(rating, int):
                await ctx.send("Rating should be an integer.")
                return
            if not isinstance(users, list):
                await ctx.send("Users must be a list.")
                return
            if not all(isinstance(user, discord.Member) for user in users):
                await ctx.send("Some inputs were not valid members.")
                return

            if (rating < 800 or rating > 3500) or (rating % 100 != 0):
                await ctx.send("Rating should be a multiple of 100 between 800 and 3500.")
                return

            if (util.problems is None):
                await ctx.send("Try again in a bit.")
                return

            pos_problems = [p for p in util.problems if p["rating"] == rating]

            user_list = [member.id for member in users]
            user_list.append(ctx.author.id)
            user_list = list(set(user_list))

            handles = []

            for u in user_list:
                try:
                    h = await util.get_handle(ctx.guild.id, u)
                    handles.append(h)
                except Exception as e:
                    await ctx.send("One or more users have not linked a handle.")
                    return

            s = []
            bad_handles = []

            for h in handles:
                if await util.handle_exists_on_cf(self.egg, h):
                    s.append(await get_solved(self.egg, h))
                    if s[-1] is None:
                        await ctx.send("Something went wrong. Try again in a bit.")
                        return
                else:
                    bad_handles.append(h)

            if len(bad_handles) > 0:
                await ctx.send(f"Invalid handle(s) (will be ignored): {', '.join(bad_handles)}.")

            # try to just pick random until have at least 10
            num = 0
            sug_list = []
            while num < 100 and len(sug_list) < 10:
                problem = random.choice(pos_problems)
                pr = f"{problem["contestId"]}{problem["index"]}"
                pos_problems.remove(problem)
                for i in range(len(s)):
                    if pr in s[i]:
                        break
                else:
                    sug_list.append(problem)
                num += 1

            if len(sug_list) < 10:
                problem_dict = {f"{entry["contestId"]}{entry["index"]}": entry for entry in pos_problems}
                for i in range(len(s)):
                    for prob in s[i]:
                        if prob in problem_dict:
                            del problem_dict[prob]
                
                sug_list = list(problem_dict.values())
                random.shuffle(sug_list)
            s = ""
            for i in range(min(10, len(sug_list))):
                s += f"- [{sug_list[i]["contestId"]}{sug_list[i]["index"]}. {sug_list[i]["name"]}](https://codeforces.com/problemset/problem/{sug_list[i]["contestId"]}/{sug_list[i]["index"]})"
                if i != min(10, len(sug_list)) - 1:
                    s += "\n"
            embed = discord.Embed(title=f"Problem suggestions for users ({', '.join(handles)})", description=s, color=util.getColor(rating))
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Some error: {e}")
            await ctx.send("Some error occurred.")
        
async def setup(bot):
    await bot.add_cog(Suggest(bot))

async def get_solved(egg, handle: str):
    ret = []
    new_last = -1
    async with aiosqlite.connect(util.path + "bot_data.db") as db:
        async with db.execute("SELECT * FROM ac WHERE handle = ?", (handle, )) as cursor:
            row = await cursor.fetchone()
            if row:
                logger.info("Small query.")
                prev_last = row[2] 
                cur_list = json.loads(row[1])
                try:
                    response_data = await egg.codeforces("user.status", {"handle": handle, "from": 1, "count": 100})
                    
                    if response_data["status"] != "OK":
                        return cur_list

                    found = False
                    first = False
                    for sub in response_data["result"]:
                        if first:
                            new_last = sub["id"]
                            first = True
                        if sub["id"] != prev_last:
                            if sub["verdict"] == "OK" and "contestId" in sub:
                                cur_list.append(f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}")
                        else:
                            found = True
                            logger.info("Small query worked.")
                            ret = cur_list
                            break
                    
                    if not found:
                        nl = [0]
                        await large_query(egg, handle, ret, nl)
                        new_last = nl[0]

                except Exception as e:
                    logger.error(f"Error when getting submissions: {e}")
                    raise RequestError(e)
                    
            else:
                logger.info("Large query.")
                try:
                    nl = [0]
                    await large_query(egg, handle, ret, nl)
                    new_last = nl[0]

                except Exception as e:
                    logger.error(f"Error when getting submissions: {e}")
                    raise RequestError(e)
    # write to db
    if new_last != -1:
        ret = list(set(ret))
        try:
            async with aiosqlite.connect(util.path + "bot_data.db") as db:
                await db.execute("""
                    INSERT OR REPLACE INTO ac (handle, solved, last_sub) 
                    VALUES (?, ?, ?)
                """, (handle, json.dumps(ret), new_last))
                await db.commit()
        except aiosqlite.Error as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(e)
    return ret

async def get_ac(egg, handle: str, start: int, ret: list):
    try:
        response_data = await egg.codeforces("user.status", {"handle": handle, "from": start, "count": 5000})
        for sub in response_data["result"]:
            if sub["verdict"] == "OK" and "contestId" in sub:
                ret.append(sub)
    except Exception as e:
        logger.error(f"Error when getting submissions: {e}")
        raise RequestError(e)

async def large_query(egg, handle: str, ret: list, new_last: list):
    subs = []
    tasks = [asyncio.create_task(get_ac(egg, handle, 1 + 5000 * k, subs)) for k in range(4)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            raise result
        
    subs.sort(key=lambda x: x["creationTimeSeconds"], reverse=True)
    new_last[0] = subs[0]["id"]
    for sub in subs:
        ret.append(f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}")