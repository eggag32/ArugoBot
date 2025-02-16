import os
import discord
from discord.ext import commands
import asyncio
import aiosqlite
import util

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="=", intents=intents)

async def init_database():
    async with aiosqlite.connect("bot_data.db") as db:
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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.loop.create_task(util.parse_data())
    await init_database()

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

async def load_cogs():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                print(f"Loaded {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

async def main():
    async with bot:
        await load_cogs()
        with open("token.txt", "r") as file:
            token = file.read().strip()
        await bot.start(token)

asyncio.run(main())