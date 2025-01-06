from urllib.request import urlopen
import requests
import json
import aiosqlite
import asyncio
import random

problems = None

def get_problems():
    URL = "https://codeforces.com/api/problemset.problems"
    response = urlopen(URL)
    response_data = json.loads(response.read())
    problems = response_data["result"]["problems"]

    with open('problems.json', 'w') as file:
        json.dump(problems, file)

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

def handle_exists(handle):
    try:
        URL = "https://codeforces.com/api/user.info?handles=" + handle
        response = urlopen(URL)
        response_data = json.loads(response.read())
        return response_data["status"] == "OK"
    except:
        return False

def handle_linked(server_id: int, user_id: int, handle: str):
    pass

def handle_exists(server_id: int, user_id: int, handle: str):
    pass

async def validate_handle(ctx, server_id: int, user_id: int, handle: str):
    # 1 - ok
    # 2 - didn't receive
    # 3 - handle exists
    # 4 - you have a handle
    # 5 - some other error

    # give a problem, tell them to submit
    if problems is None:
        try:
            get_problems()    
        except Exception as e:
            print(f"Error during parsing: {e}")
            return 5

    problem = problems[random.randint(0, len(problems) - 1)]
    await ctx.send(f"Submit a compilation error to the following problem in the next 60 seconds:\nhttps://codeforces.com/problemset/problem/{problem['contestId']}/{problem['index']}")
    # for 60 seconds we monitor
    
    # if bad, then bad, if good, then we add it to the database (check when inserting to make sure)
    pass