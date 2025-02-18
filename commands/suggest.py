from discord.ext import commands
import util
import discord
import random

class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
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
                s.append(await util.get_solved(h))
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