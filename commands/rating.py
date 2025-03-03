import matplotlib.pyplot as plt
import discord
import util
import io
import logging
from discord.ext import commands
from main import global_cooldown
from discord.utils import escape_mentions

logger = logging.getLogger("bot_logger")

class Rating(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows your rating")
    @global_cooldown()
    async def rating(self, ctx, member: discord.Member = None):
        if not member is None:
            if not isinstance(member, discord.Member):
                await ctx.send("Invalid member.")
                return

        id = member.id if member else ctx.author.id
        name = member.name if member else ctx.author.name
        mention = member.mention if member else ctx.author.mention
        if not await util.handle_linked(ctx.guild.id, id):
            await ctx.send("Handle not linked.")
            return
        r = await util.get_rating(ctx.guild.id, id)
        if r == -1:
            await ctx.send("Something went wrong, somehow the user doesn't have a rating...")
        else:
            try:
                pY = await util.get_rating_history(ctx.guild.id, id)
                pX = [i + 1 for i in range(len(pY))]
                fig, ax = plt.subplots()
                ax.axhspan(-1000, 1200, facecolor="gray", alpha=0.5)
                ax.axhspan(1200, 1400, facecolor="lime", alpha=0.5)
                ax.axhspan(1400, 1600, facecolor="cyan", alpha=0.5)
                ax.axhspan(1600, 1900, facecolor="blue", alpha=0.5)
                ax.axhspan(1900, 2100, facecolor="purple", alpha=0.5)
                ax.axhspan(2100, 2300, facecolor="yellow", alpha=0.5)
                ax.axhspan(2300, 2400, facecolor="orange", alpha=0.7)
                ax.axhspan(2400, 2600, facecolor="red", alpha=0.7)
                ax.axhspan(2600, 3000, facecolor="pink", alpha=0.9)
                ax.axhspan(3000, 5000, facecolor="magenta", alpha=0.7)
                ax.plot(pX, pY, marker="o", linestyle="-", color="blue", markerfacecolor="blue", markeredgecolor="blue", markersize=6)
                ax.set_ylim(min(pY) - 100, max(pY) + 100)
                l = [0, 1200, 1400, 1600, 1900, 2100, 2300, 2400, 2600, 3000]
                t = [i for i in l if i >= min(pY) - 100 and i <= max(pY) + 100]
                ax.set_yticks(t)
                ax.set_xticks(range(1, len(pY) + 1, 1))
                ax.set_title(f"Rating history of {name}")
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format="png", bbox_inches="tight")
                plt.close()
                img_buffer.seek(0)
                discord_file = discord.File(img_buffer, filename="image.png")
                embed = discord.Embed(title="Rating graph", description=f"{mention}'s rating is {r}", color=discord.Color.blue())
                embed.set_image(url="attachment://image.png")
                await ctx.send(file=discord_file, embed=embed)
            except Exception as e:
                logger.error(f"Something went wrong: {e}")


async def setup(bot):
    await bot.add_cog(Rating(bot))