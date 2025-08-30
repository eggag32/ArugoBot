import util
import discord
import random
import logging
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

            await ctx.send("Fetching data, please wait.", delete_after=2)

            for h in handles:
                if await util.handle_exists_on_cf(self.egg, h):
                    s.append(await util.get_solved(self.egg, h))
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