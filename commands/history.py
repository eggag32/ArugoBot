import util
import discord
import logging
from discord.ext import commands
from main import global_cooldown

logger = logging.getLogger("bot_logger")

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows your history")
    @global_cooldown()
    async def history(self, ctx, page: int = 1):
        if not isinstance(page, int) or page < 1:
            await ctx.send("Invalid page.")
            return

        try:
            h = await util.get_history(ctx.guild.id, ctx.author.id)
            if h is None:
                await ctx.send("No history...")
                return
            if util.problem_dict is None:
                await ctx.send("Wait a bit.")
                return
            ind = (page - 1) * 10
            if ind >= len(h[0]):
                await ctx.send("Empty page.")
                return
            embed = discord.Embed(title="History", description=f"Page {page}", color=discord.Color.blue())
            s = ""
            for i in range(10):
                if ind + i >= len(h[0]):
                    break
                name = h[0][ind + i]
                s += f"- [{name}. {util.problem_dict[name]["name"]}](https://codeforces.com/problemset/problem/{util.problem_dict[name]["contestId"]}/{util.problem_dict[name]["index"]})"
                s += f" (rating change: {h[1][ind + i + 1] - h[1][ind + i]})\n"
            embed.add_field(name="Problems", value=s, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in history: {e}")


async def setup(bot):
    await bot.add_cog(History(bot))