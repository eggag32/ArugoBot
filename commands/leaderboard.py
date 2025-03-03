import util
import discord
import logging
from discord.ext import commands
from main import global_cooldown

logger = logging.getLogger("bot_logger")

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows the server leaderboard")
    @global_cooldown()
    async def leaderboard(self, ctx, page: int = 1):
        if not isinstance(page, int) or page < 1:
            await ctx.send("Invalid page.")
            return

        try:
            lb = await util.get_leaderboard(ctx.guild.id)
            if lb is None:
                await ctx.send("No leaderboard...")
                return
            ind = (page - 1) * 10
            if ind >= len(lb):
                await ctx.send("Empty page.")
                return
            embed = discord.Embed(title="Leaderboard", description=f"Page {page}", color=discord.Color.blue())
            s = ""
            for i in range(10):
                if ind + i >= len(lb):
                    break
                user = await ctx.guild.fetch_member(lb[ind + i][0])
                s += f"{ind + i + 1}. {user.mention} ({lb[ind + i][1]})"
                if ind + i == 0:
                    s += " :first_place:\n"
                elif ind + i == 1:
                    s += " :second_place:\n"
                elif ind + i == 2:
                    s += " :third_place:\n"
                else:
                    s += "\n"
            embed.add_field(name="Users", value=s, inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error during leaderboard command: {e}")

async def setup(bot):
    await bot.add_cog(Leaderboard(bot))