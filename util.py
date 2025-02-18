from urllib.request import urlopen
import json
import discord
import aiosqlite
import asyncio
import random
import time

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
        return response_data["status"] == "OK" and response_data["result"][0]["handle"] == handle
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

async def unlink(server_id: int, user_id: int):
    try:
        async with aiosqlite.connect("bot_data.db") as db:
            await db.execute("DELETE FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id))
            await db.commit()
    except Exception as e:
        print(f"Database error: {e}")

async def got_submission(handle: str, problem, t):
    try:

        URL = f"https://codeforces.com/api/contest.status?contestId={problem['contestId']}&asManager=false&from=1&count=10&handle={handle}"
        response = urlopen(URL)
        await asyncio.sleep(2)
        response_data = json.loads(response.read())

        for o in response_data["result"]:
            if o["problem"]["index"] == problem["index"] and o["verdict"] == "COMPILATION_ERROR" and o["contestId"] == problem["contestId"]:
                return o["creationTimeSeconds"] > t

    except Exception as e:
        print(f"Error during parsing: {e}")
        return False

async def get_solved(handle: str):
    ret = []
    new_last = -1
    async with aiosqlite.connect("bot_data.db") as db:
        async with db.execute("SELECT * FROM ac WHERE handle = ?", (handle, )) as cursor:
            row = await cursor.fetchone()
            if row:
                print("Small query.")
                prev_last = row[2] 
                cur_list = json.loads(row[1])
                try:

                    URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=20"
                    response = urlopen(URL)
                    await asyncio.sleep(2)
                    response_data = json.loads(response.read())

                    found = False
                    first = False
                    for sub in response_data["result"]:
                        if first:
                            new_last = sub["id"]
                            first = True
                        if sub["id"] != prev_last:
                            if sub["verdict"] == "OK" and "contestId" in sub:
                                cur_list.append(f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}")
                        else:
                            found = True
                            print("Small query worked.")
                            ret = cur_list
                            break
                    
                    if not found:
                        URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
                        response = urlopen(URL)
                        await asyncio.sleep(2)
                        response_data = json.loads(response.read())

                        if (len(response_data["result"]) > 0):
                            new_last = response_data["result"][0]["id"]

                        ret = [f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}" for sub in response_data["result"] if sub["verdict"] == "OK" and "contestId" in sub]

                except Exception as e:
                    print(f"Error when getting submissions: {e}")
                    return None
            else:
                print("Large query.")
                try:

                    URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
                    response = urlopen(URL)
                    await asyncio.sleep(2)
                    response_data = json.loads(response.read())

                    if (len(response_data["result"]) > 0):
                        new_last = response_data["result"][0]["id"]

                    ret = [f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}" for sub in response_data["result"] if sub["verdict"] == "OK" and "contestId" in sub]

                except Exception as e:
                    print(f"Error when getting submissions: {e}")
                    return None
    # write to db
    if new_last != -1:
        try:
            async with aiosqlite.connect("bot_data.db") as db:
                await db.execute("""
                    INSERT OR REPLACE INTO ac (handle, solved, last_sub) 
                    VALUES (?, ?, ?)
                """, (handle, json.dumps(ret), new_last))
                await db.commit()
        except aiosqlite.Error as e:
            print(f"Database error: {e}") 
    return ret

async def validate_handle(ctx, server_id: int, user_id: int, handle: str):
    # 1 - ok
    # 2 - didn't receive
    # 3 - handle exists
    # 4 - you have a handle
    # 5 - some other error

    if problems is None:
        try:
            get_problems()    
        except Exception as e:
            print(f"Error during parsing: {e}")
            return 5

    problem = problems[random.randint(0, len(problems) - 1)]
    t = time.time()
    await ctx.send(f"Submit a compilation error to the following problem in the next 60 seconds:\nhttps://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}")

    await asyncio.sleep(60)
    if not await got_submission(handle, problem, t):
        return 2
    async with aiosqlite.connect('bot_data.db') as db:
        try:
            await db.execute("BEGIN TRANSACTION")

            async with db.execute('SELECT handle FROM users WHERE server_id = ? AND handle = ?', (server_id, handle)) as cursor:
                existing_handle = await cursor.fetchone()

            if existing_handle:
                await db.rollback()
                return 3

            async with db.execute('SELECT handle FROM users WHERE server_id = ? AND user_id = ?', (server_id, user_id)) as cursor:
                linked_handle = await cursor.fetchone()

            if linked_handle:
                await db.rollback()
                return 4

            history = "[]"
            rating_history = "[]"
            await db.execute(
                'INSERT INTO users (server_id, user_id, handle, rating, history, rating_history) VALUES (?, ?, ?, ?, ?, ?)',
                (server_id, user_id, handle, 1500, history, rating_history)
            )

            await db.commit()
            return 1
        except Exception as e:
            await db.rollback()
            print(f"Transaction failed: {e}")
            return 5