import discord
import asyncio
import logging
from discord.ext import commands
from main import global_cooldown

logger = logging.getLogger("bot_logger")


class Race(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Start an open race. Syntax: =race <problem_or_rating> <length>")
    @global_cooldown()
    async def race(self, ctx, problem_or_rating: str, length: int):
        """Start a race: others can react with ✅ to join for 30 seconds.

        After the join window ends the command will invoke the existing
        `challenge` command with the collected participants.
        """
        # validate length similar to challenge
        if not isinstance(length, int):
            await ctx.send("Invalid length, it should be an integer.")
            return
        if length not in (40, 60, 80, 100, 120):
            await ctx.send("Invalid length. Valid lengths are 40, 60, 80, 100, and 120 minutes.")
            return

        embed = discord.Embed(
            title="Race",
            description=("React with ✅ within 30 seconds to join the race.\n"),
            color=discord.Color.blue(),
        )
        embed.add_field(name="Problem/Rating", value=str(problem_or_rating), inline=False)
        embed.add_field(name="Time", value=f"{length} minutes", inline=False)

        message = await ctx.send(embed=embed)
        try:
            await message.add_reaction("✅")
        except Exception:
            # ignore reaction failures
            pass

        start_time = asyncio.get_event_loop().time()

        join_order = []  # preserve order of joins

        def check(reaction, user):
            if reaction.message.id != message.id:
                return False
            if str(reaction.emoji) != "✅":
                return False
            if user.bot:
                return False
            return True

        # Collect reactions for up to 30 seconds or until max participants reached
        timeout = 30.0
        max_participants = 10  # including author
        while True:
            remaining = timeout - (asyncio.get_event_loop().time() - start_time)
            if remaining <= 0:
                break
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=remaining, check=check)
                if user.id == ctx.author.id:
                    # author is already participating by default
                    continue
                if user.id in join_order:
                    continue
                join_order.append(user.id)
                # stop early if we reached max
                if 1 + len(join_order) >= max_participants:
                    break
            except asyncio.TimeoutError:
                break

        # Build final participant list (author + joiners up to 10 total)
        participants = [ctx.author.id] + join_order[: max(0, max_participants - 1)]

        # Convert participant ids (excluding author) to Member objects for challenge
        member_args = []
        for uid in participants:
            if uid == ctx.author.id:
                continue
            member = ctx.guild.get_member(uid)
            if member is None:
                try:
                    member = await ctx.guild.fetch_member(uid)
                except Exception:
                    # skip if we cannot resolve the member
                    continue
            member_args.append(member)

        # Invoke the challenge command with the collected members
        cmd = self.bot.get_command("challenge")
        if cmd is None:
            await ctx.send("Challenge command not available.")
            return

        try:
            # The `challenge` command expects the `users` parameter to be a list
            # (it uses commands.Greedy at parse-time). When invoking directly we must
            # pass a single list object, not expand it as positional args.
            await ctx.invoke(cmd, problem_or_rating, length, member_args)
        except Exception as e:
            logger.error(f"Error invoking challenge from race: {e}")
            await ctx.send("Unable to start challenge from race.")


async def setup(bot):
    await bot.add_cog(Race(bot))
