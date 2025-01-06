from discord.ext import commands

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def history(self, ctx):
        await ctx.send("This is history!")

async def setup(bot):
    await bot.add_cog(History(bot))