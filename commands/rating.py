from discord.ext import commands
from main import global_cooldown
from discord.utils import escape_mentions
import util

class Rating(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Shows your rating")
    @global_cooldown()
    async def rating(self, ctx):
        if not await util.handle_linked(ctx.guild.id, ctx.author.id):
            await ctx.send("Handle not linked.")
            return
        r = await util.get_rating(ctx.guild.id, ctx.author.id)
        if r == -1:
            await ctx.send("Something went wrong, somehow you don't have a rating...")
        else:
            await ctx.send(f"{ctx.author.mention}'s rating is {r}.")

async def setup(bot):
    await bot.add_cog(Rating(bot))