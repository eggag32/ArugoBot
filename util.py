from urllib.request import urlopen
import json
import aiosqlite
import asyncio
import random
import time

problems = None

def get_problems():
    global problems
    URL = "https://codeforces.com/api/problemset.problems"
    response = urlopen(URL)
    response_data = json.loads(response.read())
    problems = response_data["result"]["problems"]
    problems = [obj for obj in problems if "rating" in obj]

async def parse_data():
    # every hour it will update the problems
    while True:
        try:
            print("Parsing data...")
            get_problems()
            print("Data parsing complete.")
        except Exception as e:
            print(f"Error during parsing: {e}")

        await asyncio.sleep(3600)

def handle_exists_on_cf(handle):
    try:
        URL = "https://codeforces.com/api/user.info?handles=" + handle
        response = urlopen(URL)
        response_data = json.loads(response.read())
        return response_data["status"] == "OK"
    except:
        return False

async def handle_exists(server_id: int, user_id: int, handle: str):
    print("handle_exists")
    async with aiosqlite.connect("bot_data.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE server_id = ? AND handle = ?", (server_id, handle)) as cursor:
            row = await cursor.fetchone()
            if row:
                return True
            return False

async def handle_linked(server_id: int, user_id: int, handle: str):
    print("handle_linked")
    async with aiosqlite.connect("bot_data.db") as db:
        async with db.execute("SELECT handle FROM users WHERE server_id = ? AND user_id = ?", (server_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                return True
            return False

def got_submission(handle: str, problem, t):
    try:

        URL = f"https://codeforces.com/api/contest.status?contestId={problem['contestId']}&asManager=false&from=1&count=10&handle={handle}"
        response = urlopen(URL)
        response_data = json.loads(response.read())

        for o in response_data["result"]:
            if o["problem"]["index"] == problem["index"] and o["verdict"] == "COMPILATION_ERROR" and o["contestId"] == problem["contestId"]:
                return o["creationTimeSeconds"] > t

    except Exception as e:
        print(f"Error during parsing: {e}")
        return False

def get_solved(handle: str):
    # I can speed this up by storing solved problems for each user in a database and updating but I'm lazy so I'll try this...
    try:

        URL = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000000"
        response = urlopen(URL)
        response_data = json.loads(response.read())

        return [f"{sub["problem"]["contestId"]}{sub["problem"]["index"]}" for sub in response_data["result"] if sub["verdict"] == "OK" and "contestId" in sub]

    except Exception as e:
        print(f"Error when getting submissions: {e}")
        return None

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
    if not got_submission(handle, problem, t):
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