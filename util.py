import json
import discord
import aiosqlite
import asyncio
import logging
from exceptions import DatabaseError, RequestError
from pathlib import Path

logger = logging.getLogger("bot_logger")
path = str(Path(__file__).parent) + "/"

problems = None
problem_dict = None
initialized = False

async def get_problems(egg):
    global problems
    global problem_dict
    logger.info("Getting problems...")
    response_data = await egg.codeforces("problemset.problems")
    logger.info("Got problems.")
    if response_data["status"] != "OK":
        return
    problems = response_data["result"]["problems"]
    problems = [obj for obj in problems if "rating" in obj and not "*special" in obj["tags"]]
    problem_dict = {}
    for problem in problems:
        problem_dict[str(problem["contestId"]) + problem["index"]] = problem

async def fix_handles(egg):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users") as cursor:
                rows = await cursor.fetchall()
                await fix(egg, [row[0] for row in rows])
    except Exception as e:
        logger.error(f"Database error, fix_handles(): {e}")

async def get_new_handle(egg, handle):
    try:
        response_data = await egg.codeforces("user.info", {"handles": handle})
        if response_data["status"] != "OK":
            return handle
        return response_data["result"][0]["handle"]
    except Exception as e:
        logger.info(handle)
        logger.info(f"https://codeforces.com/api/user.info?handles={handle}")
        logger.error(f"Access error, get_new_handle(): {e}")
        return handle

async def fix(egg, handles):
    logger.info(handles)
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            for handle in handles:
                new_handle = await get_new_handle(egg, handle)
                if new_handle != handle:
                    logger.info(f"Change from {handle} to {new_handle}.")
                    await db.execute("UPDATE users SET handle = ? WHERE handle = ?", (new_handle, handle))
                    await db.commit()
    except Exception as e:
        logger.error(f"Database error, fix(): {e}")

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

async def parse_data(egg):
    global initialized
    if initialized:
        return
    initialized = True
    # every hour it will update the problems
    while True:
        try:
            logger.info("Parsing data...")
            await get_problems(egg)
            logger.info("Fixing handles...")
            await fix_handles(egg) # hi thomas
            logger.info("Data parsing complete.")
        except Exception as e:
            logger.error(f"Error during parsing, parse_data(): {e}")

        await asyncio.sleep(3600)

async def handle_exists_on_cf(egg, handle: str):
    for c in handle:
        if not (c.isalpha() or (c >= '0' and c <= '9') or c == '_' or c == '-' or c == '.'):
            return False
    try:
        response_data = await egg.codeforces("user.info", {"handles": handle})
        return response_data["status"] == "OK" and response_data["result"][0]["handle"].lower() == handle.lower()
    except Exception as e:
        logger.error(f"Request error, handle_exists_on_cf(): {e}")
        raise RequestError(e)

async def handle_exists(server_id: int, user_id: int, handle: str):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT user_id FROM users WHERE server_id = ? AND handle = ?", (server_id, handle)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        logger.error(f"Database error, handle_exists(): {e}")
        raise DatabaseError(e)

async def handle_linked(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return True
                return False
    except Exception as e:
        logger.error(f"Database error, handle_linked(): {e}")
        raise DatabaseError(e)

async def get_handle(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0]
                raise RuntimeError("No handle found")
    except Exception as e:
        logger.error(f"Database error, get_handle(): {e}")
        raise DatabaseError(e)

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
                raise RuntimeError("No rating found")
    except Exception as e:
        logger.error(f"Database error, get_rating(): {e}")
        raise DatabaseError(e)

async def get_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return []
    except Exception as e:
        logger.error(f"Database error, get_history(): {e}")
        raise DatabaseError(e)

async def get_rating_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return []
    except Exception as e:
        logger.error(f"Database error, get_rating_history(): {e}")
        raise DatabaseError(e)

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
        logger.error(f"Database error, get_leaderboard(): {e}")
        return None

async def get_history_with_rating_history(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect(path + "bot_data.db") as db:
            async with db.execute("SELECT history, rating_history FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return [json.loads(row[0]), json.loads(row[1])]
                return None
    except Exception as e:
        logger.error(f"Database error, get_history_with_rating_history(): {e}")
        raise DatabaseError(e)