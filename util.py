import json
import discord
import aiosqlite
import asyncio
from urllib.request import urlopen

problems = None
initialized = False

async def get_problems():
    global problems
    URL = "https://codeforces.com/api/problemset.problems"
    response = urlopen(URL)
    await asyncio.sleep(2)
    response_data = json.loads(response.read())
    problems = response_data["result"]["problems"]
    problems = [obj for obj in problems if "rating" in obj and not "*special" in obj["tags"]]

async def fix_handles():
    try:
        async with aiosqlite.connect("bot_data.db") as db:
            async with db.execute("SELECT handle FROM users") as cursor:
                rows = await cursor.fetchall()
                await fix([row[0] for row in rows])
    except Exception as e:
        print(f"Database error: {e}")

async def get_new_handle(handle):
    try:
        URL = "https://codeforces.com/api/user.info?handles=" + handle
        response = urlopen(URL)
        await asyncio.sleep(2) 
        response_data = json.loads(response.read())
        return response_data["result"][0]["handle"]
    except Exception as e:
        print(f"Access error: {e}")
        return handle

async def fix(handles):
    print(handles)
    try:
        async with aiosqlite.connect("bot_data.db") as db:
            for handle in handles:
                new_handle = await get_new_handle(handle)
                if new_handle != handle:
                    print(f"Change from {handle} to {new_handle}.")
                    await db.execute("UPDATE users SET handle = ? WHERE handle = ?", (new_handle, handle))
                    await db.commit()
    except Exception as e:
        print(f"Database error: {e}")

def getColor(rating):
    if rating < 1200:
        return discord.Color.light_grey()
    if rating < 1400:
        return discord.Color.green()
    if rating < 1600:
        return discord.Color.from_rgb(0, 255, 255)
    if rating < 1900:
        return discord.Color.blue()
    if rating < 2100:
        return discord.Color.purple()
    if rating < 2300:
        return discord.Color.yellow()
    if rating < 2400:
        return discord.Color.orange()
    if rating < 2600:
        return discord.Color.red()
    if rating < 3000:
        return discord.Color.from_rgb(255, 105, 180)
    return discord.Color.from_rgb(173, 216, 230)

async def parse_data():
    global initialized
    if initialized:
        return
    initialized = True
    # every hour it will update the problems
    while True:
        try:
            print("Parsing data...")
            await get_problems()
            print("Fixing handles...")
            await fix_handles() # hi thomas
            # add submission parsing?
            print("Data parsing complete.")
        except Exception as e:
            print(f"Error during parsing: {e}")

        await asyncio.sleep(3600)

async def handle_exists_on_cf(handle):
    try:
        URL = "https://codeforces.com/api/user.info?handles=" + handle
        response = urlopen(URL)
        await asyncio.sleep(2)
        response_data = json.loads(response.read())
        return response_data["status"] == "OK" and response_data["result"][0]["handle"].lower() == handle.lower()
    except:
        return False

async def handle_exists(server_id: int, user_id: int, handle: str):
    print("handle_exists")
    try:
        async with aiosqlite.connect("bot_data.db") as db:
            async with db.execute("SELECT user_id FROM users WHERE server_id = ? AND handle = ?", (server_id, handle)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        print(f"Database error: {e}")

async def handle_linked(server_id: int, user_id: int):
    print("handle_linked")
    try:
        async with aiosqlite.connect("bot_data.db") as db:
            async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        print(f"Database error: {e}")