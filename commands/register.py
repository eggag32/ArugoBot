from discord.ext import commands
import ArugoBot.util as util

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def register(self, ctx, handle: str):
        b = util.handle_exists(handle)
        if not b:
            await ctx.send("Invalid handle.")
            return
        # check that it is not in the database already (for this server)
        if util.handle_exists(ctx.guild.id, ctx.author.id, handle):
            await ctx.send("Handle taken in this server.")
            return
        # check that user does not already have a handle
        if util.handle_linked(ctx.guild.id, ctx.author.id, handle):
            await ctx.send("You already linked a handle (use unlink if you wish to remove it).")
            return
        # now give them the verification challenge
        ret = util.validate_handle(ctx, ctx.guild.id, ctx.author.id, handle)
        if ret == 1:
            await ctx.send(f"Handle set to {handle}")
        elif ret == 2:
            await ctx.send("Verification failed.")
        elif ret == 3:
            await ctx.send("Handle has been taken (;-; are you trying to break me).")
        elif ret == 4:
            await ctx.send("You already linked a handle (during verification, is this a test?).")
        else:
            await ctx.send("Some error (maybe CF is down).")
        

async def setup(bot):
    await bot.add_cog(Register(bot))