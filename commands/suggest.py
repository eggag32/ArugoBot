import util
import discord
import asyncio
import aiosqlite
import json
import random
from urllib.request import urlopen
from discord.ext import commands
from main import global_cooldown

class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @global_cooldown()
    async def suggest(self, ctx, rating: int, *handles):
        if (len(handles) > 5):
            await ctx.send("Too many people (limit is 5).")
            return

        if (rating < 800 or rating > 3500) or (rating % 100 != 0):
            await ctx.send("Rating should be a multiple of 100 between 800 and 3500.")
            return

        if (util.problems is None):
            await ctx.send("Try again in a bit.")
            return

        pos_problems = [p for p in util.problems if p["rating"] == rating]

        s = []
        bad_handles = []

        for h in handles:
            if await util.handle_exists_on_cf(h):
                s.append(await get_solved(h))
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
            pr = f"{problem['contestId']}{problem['index']}"
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
            s += f"- [{sug_list[i]["index"]}. {sug_list[i]["name"]}](https://codeforces.com/problemset/problem/{sug_list[i]["contestId"]}/{sug_list[i]["index"]})"
            if i != min(10, len(sug_list)) - 1:
                s += "\n"
        embed = discord.Embed(title=f"Problem suggestions", description=s, color=util.getColor(rating))
        await ctx.send(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Suggest(bot))

async def get_solved(handle: str):
    ret = []
    new_last = -1
    async with aiosqlite.connect("bot_data.db") as db:
        async with db.execute("SELECT * FROM ac WHERE handle = ?", (handle, )) as cursor:
            row = await cursor.fetchone()
            if row:
                print("Small query.")
                prev_last = row[2] 
                cur_list = json.loads(row[1])
                try:

                    URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=20"
                    response = urlopen(URL)
                    await asyncio.sleep(2)
                    response_data = json.loads(response.read())
                    
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
                            print("Small query worked.")
                            ret = cur_list
                            break
                    
                    if not found:
                        URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
                        response = urlopen(URL)
                        await asyncio.sleep(2)
                        response_data = json.loads(response.read())

                        if (len(response_data["result"]) > 0):
                            new_last = response_data["result"][0]["id"]

                        ret = [f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}" for sub in response_data["result"] if sub["verdict"] == "OK" and "contestId" in sub]

                except Exception as e:
                    print(f"Error when getting submissions: {e}")
                    return None
            else:
                print("Large query.")
                try:

                    URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
                    response = urlopen(URL)
                    await asyncio.sleep(2)
                    response_data = json.loads(response.read())

                    if response_data["status"] != "OK":
                        return None

                    if (len(response_data["result"]) > 0):
                        new_last = response_data["result"][0]["id"]

                    ret = [f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}" for sub in response_data["result"] if sub["verdict"] == "OK" and "contestId" in sub]

                except Exception as e:
                    print(f"Error when getting submissions: {e}")
                    return None
    # write to db
    if new_last != -1:
        try:
            async with aiosqlite.connect("bot_data.db") as db:
                await db.execute("""
                    INSERT OR REPLACE INTO ac (handle, solved, last_sub) 
                    VALUES (?, ?, ?)
                """, (handle, json.dumps(ret), new_last))
                await db.commit()
        except aiosqlite.Error as e:
            print(f"Database error: {e}") 
    return ret