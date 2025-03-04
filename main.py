import os
import discord
import asyncio
import aiosqlite
import util
import time
import logging
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="=", intents=intents)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(util.path + "bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bot_log")

async def init_database():
    async with aiosqlite.connect(util.path + "bot_data.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            server_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            handle TEXT NOT NULL,
            rating INTEGER NOT NULL,
            history TEXT DEFAULT '[]',
            rating_history TEXT DEFAULT '[]',
            PRIMARY KEY (server_id, user_id)
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS ac (
            handle TEXT NOT NULL,
            solved TEXT DEFAULT '[]',
            last_sub INTEGER NOT NULL,
            PRIMARY KEY (handle)  
        );
        """)
        await db.commit()

user_cooldowns = {}
last_request = 0

def global_cooldown():
    async def predicate(ctx):
        global last_request
        global user_cooldowns
        if ctx.invoked_with == "help":
            return True
        user_id = ctx.author.id
        now = time.time()
        
        if user_id in user_cooldowns and now - user_cooldowns[user_id] < 3:
            remaining = 3 - (now - user_cooldowns[user_id])
            await ctx.send("Too many requests.", delete_after=2)
            return False
        
        if now < last_request:

            if last_request - now > 5:
                await ctx.send("Too many requests, try again in a bit.", delete_after=2)
                return False

            last_request += 1
            await asyncio.sleep(2 * (last_request - now - 1)) # this is all stupid just don't try to break
        else:
            last_request = now + 1

        user_cooldowns[user_id] = now
        return True

    return commands.check(predicate)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')
    bot.loop.create_task(util.parse_data())
    await init_database()

@bot.command(help="Pings the bot")
@global_cooldown()
async def ping(ctx):
    await ctx.send('Pong!')

async def load_cogs():
    for filename in os.listdir(util.path + "/commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Failed to load {filename}: {e}")

async def main():
    async with bot:
        await load_cogs()
        with open(util.path + "token.txt", "r") as file:
            token = file.read().strip()
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())