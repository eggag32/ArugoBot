import json
import discord
import aiosqlite
import asyncio
import logging
from urllib.request import urlopen

logger = logging.getLogger("bot_logger")
path = "/Users/eggag32/Documents/Bot/ArugoBot/"

problems = None
problem_dict = None
initialized = False

async def get_problems():
    global problems
    global problem_dict
    URL = "https://codeforces.com/api/problemset.problems"
    response = urlopen(URL)
    await asyncio.sleep(2)
    response_data = json.loads(response.read())
    if response_data["status"] != "OK":
        return
    problems = response_data["result"]["problems"]
    problems = [obj for obj in problems if "rating" in obj and not "*special" in obj["tags"]]
    problem_dict = {}
    for problem in problems:
        problem_dict[str(problem["contestId"]) + problem["index"]] = problem

async def fix_handles():
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users") as cursor:
                rows = await cursor.fetchall()
                await fix([row[0] for row in rows])
    except Exception as e:
        logger.error(f"Database error: {e}")

async def get_new_handle(handle):
    try:
        URL = f"https://codeforces.com/api/user.info?handles={handle}"
        response = urlopen(URL)
        await asyncio.sleep(2)
        response_data = json.loads(response.read())
        if response_data["status"] != "OK":
            return handle
        return response_data["result"][0]["handle"]
    except Exception as e:
        logger.info(handle)
        logger.info(f"https://codeforces.com/api/user.info?handles={handle}")
        logger.error(f"Access error: {e}")
        return handle

async def fix(handles):
    logger.info(handles)
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            for handle in handles:
                new_handle = await get_new_handle(handle)
                if new_handle != handle:
                    logger.info(f"Change from {handle} to {new_handle}.")
                    await db.execute("UPDATE users SET handle = ? WHERE handle = ?", (new_handle, handle))
                    await db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")

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
            logger.info("Parsing data...")
            await get_problems()
            logger.info("Fixing handles...")
            await fix_handles() # hi thomas
            # add submission parsing?
            logger.info("Data parsing complete.")
        except Exception as e:
            logger.error(f"Error during parsing: {e}")

        await asyncio.sleep(3600)

async def handle_exists_on_cf(handle: str):
    for c in handle:
        if not (c.isalpha() or c.isdigit() or c == '_' or c == '-'):
            return False
    try:
        URL = f"https://codeforces.com/api/user.info?handles={handle}"
        response = urlopen(URL)
        await asyncio.sleep(2)
        response_data = json.loads(response.read())
        return response_data["status"] == "OK" and response_data["result"][0]["handle"].lower() == handle.lower()
    except Exception as e:
        logger.error(f"Request error: {e}")

async def handle_exists(server_id: int, user_id: int, handle: str):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT user_id FROM users WHERE server_id = ? AND handle = ?", (server_id, handle)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        logger.error(f"Database error: {e}")

async def handle_linked(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        logger.error(f"Database error: {e}")

async def get_handle(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return None
    except Exception as e:
        logger.error(f"Database error: {e}")

def get_rating_changes(old_rating: int, problem_rating: int, length: int):
    # adjust for length
    problem_rating += 50 * ((80 - length) / 20)
    # somewhat arbitrary, but will keep the same for consistency
    magnitude = 16
    return [int(-min(magnitude * 10, (0.5 * magnitude) // (1 - (1 / (1 + 10 ** ((problem_rating - old_rating) / 500)))))), 
            int(min(magnitude * 10, (0.5 * magnitude) // (1.15 / (1 + 10 ** ((problem_rating - old_rating) / 500)))))]

async def get_rating(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT rating FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                return -1
    except Exception as e:
        logger.error(f"Database error: {e}")

async def get_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return []
    except Exception as e:
        logger.error(f"Database error: {e}")

async def get_rating_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return []
    except Exception as e:
        logger.error(f"Database error: {e}")

async def add_to_history(server_id: int, user_id: int, problem: str):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    history = json.loads(row[0])
                    history.append(problem)
                    await db.execute("UPDATE users SET history = ? WHERE server_id = ? AND user_id = ?", (json.dumps(history), server_id, user_id))
                    await db.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")

def format_time(seconds: float):
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes}:{seconds:02d}"

async def get_leaderboard(server_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT user_id, rating FROM users WHERE server_id = ? ORDER BY rating DESC", (server_id,)) as cursor:
                rows = await cursor.fetchall()
                return rows
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None

async def get_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT history, rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return [json.loads(row[0]), json.loads(row[1])]
                return None
    except Exception as e:
        logger.error(f"Database error: {e}")
        return None