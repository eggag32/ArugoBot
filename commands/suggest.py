from discord.ext import commands
import util
import discord
import random

class Suggest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def suggest(self, ctx, rating: int, *handles):
        if (util.problems is None):
            await ctx.send("Try again in a bit.")
            return
        pos_problems = [p for p in util.problems if p["rating"] == rating]
        problem_dict = {f"{entry["contestId"]}{entry["index"]}": entry for entry in pos_problems}
        for h in handles:
            if util.handle_exists_on_cf(h):
                s = util.get_solved(h)
                if s is None:
                    await ctx.send("Something went wrong. Try again in a bit.")
                    return
                for prob in s:
                    if prob in problem_dict:
                        del problem_dict[prob]
        
        sug_list = list(problem_dict.values())
        random.shuffle(sug_list)
        s = ""
        for i in range(min(10, len(sug_list))):
            s += f"- [{sug_list[i]["index"]}. {sug_list[i]["name"]}](https://codeforces.com/problemset/problem/{sug_list[i]["contestId"]}/{sug_list[i]["index"]})\n"
        embed = discord.Embed(title=f"Problem suggestions", description=s, color=discord.Color.green())
        await ctx.send(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Suggest(bot))