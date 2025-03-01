from discord.ext import commands
import discord
from main import global_cooldown
import util

class Challenge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Get a challenge")
    @global_cooldown()
    async def challenge(self, ctx, problem: str, length: int, users: commands.Greedy[discord.Member]):
        if not (len == 40 or len == 60 or len == 80):
            await ctx.send("Invalid length. Valid lengths are 40, 60, and 80 minutes.")
            return
        if not problem in util.problem_dict:
            await ctx.send("Invalid problem. Make sure it is in the correct format (concatenation of contest ID and problem index, for example 1000A).")
            return
        mentions = ", ".join(member.mention for member in users)
        user_list = [member.id for member in users]
        user_list.append(ctx.author.id)
        for id in user_list:
            if not await util.handle_linked(ctx.guild.id, id):
                await ctx.send("One or more users have not linked a handle.")
                return
        await ctx.send("Ok!")
        # i guess for each user check that it is not in their history

        # then get all their ratings and create an embed

        # then i guess keep updating the embed

        # once everyone is done we can end the challenge
        

async def setup(bot):
    await bot.add_cog(Challenge(bot))