import util
import discord
import logging
from discord.ext import commands
from main import global_cooldown

logger = logging.getLogger("bot_logger")

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.egg = bot.egg

    @commands.command(help="Shows the history of a user")
    @global_cooldown()
    async def history(self, ctx, member: discord.Member = commands.param(default=None, description=": User to show history of (e.g. @eggag32) (optional)"),
                      page: int = commands.param(default=1, description=": Page number")):
        if not isinstance(page, int) or page < 1:
            await ctx.send("Invalid page.")
            return
        if not member is None:
            if not isinstance(member, discord.Member):
                await ctx.send("Invalid member.")
                return
        id = member.id if member else ctx.author.id
        name = member.name if member else ctx.author.name
        try:
            h = await util.get_history_with_rating_history(ctx.guild.id, id)
            if h is None:
                await ctx.send("No history...")
                return
            if util.problem_dict is None:
                await ctx.send("Wait a bit.")
                return
            h[0].reverse()
            h[1].reverse()
            ind = (page - 1) * 10
            if ind >= len(h[0]):
                await ctx.send("Empty page.")
                return
            embed = discord.Embed(title=f"History of {name}", description=f"Page {page}", color=discord.Color.blue())
            s = ""
            for i in range(10):
                if ind + i >= len(h[0]):
                    break
                name = h[0][ind + i]
                s += f"- [{name}. {util.problem_dict[name]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[name]["contestId"]}/{util.problem_dict[name]["index"]})"
                s += f" (rating change: {h[1][ind + i + 1]} -> {h[1][ind + i]}, {h[1][ind + i] - h[1][ind + i + 1]})\n"
            embed.add_field(name="Problems", value=s, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in history: {e}")
            await ctx.send("Something went wrong.")


async def setup(bot):
    await bot.add_cog(History(bot))