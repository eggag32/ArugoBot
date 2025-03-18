from collections import deque
from dataclasses import dataclass
import os
import logging
from typing import Any, AsyncIterator, Awaitable, Callable, Optional, Dict, TypedDict, Unpack
import asyncio
import json
from random import shuffle as random_shuffle
from urllib.parse import urlencode, urljoin

import aiohttp

logger = logging.getLogger("bot_logger")

class CFError(Exception):
    def __init__(self, comment: Optional[str] = None):
        super().__init__(f"Codeforces API error: {comment or 'unknown error'}")
        self.comment = comment

@dataclass
class EggProxy:
    url: str
    auth: aiohttp.BasicAuth

class EggFetchOptions(TypedDict, total=False):
    noproxy: Optional[bool]
    method: Optional[str]
    
class EggFetch:
    main_id = 0
    dispatchers: dict[int, Optional[EggProxy]] = { main_id: None }
    dispatcher_error_waits: dict[int, float] = dict()
    dispatcher_queue: deque[int] = deque()
    client: aiohttp.ClientSession

    def __init__(self):
        connector = aiohttp.TCPConnector(limit=None)
        self.client = aiohttp.ClientSession(connector=connector)
        self.dispatcher_queue.append(self.main_id)
    
    async def add_proxies(self):
        if not os.path.isfile("./proxies.json"):
            return

        with open("./proxies.json", encoding="utf-8") as proxies_file:
            prox = json.load(proxies_file)

        if isinstance(prox, dict) and "proxyFetchUrl" in prox:
            logger.info("fetching proxies...")
            async with aiohttp.ClientSession() as session:
                async with session.get(prox['proxyFetchUrl']) as response:
                    proxies=(await response.text()).strip().split("\n")
        else:
            logger.info("loading proxies...")
            proxies=list(prox)

        logger.info(f"adding {len(proxies)} proxies")

        for pi, p in enumerate(proxies):
            parts = p.split(":")
            if len(parts) != 4:
                raise ValueError(f"Expected 4 parts (host, port, user, pass) for proxy {p}")

            proxy_auth = aiohttp.BasicAuth(parts[2], parts[3])
            self.dispatchers[pi+1] = EggProxy(
                url=f"http://{parts[0]}:{parts[1]}",
                auth=proxy_auth
            )
    
            self.dispatcher_queue.append(pi+1)

        random_shuffle(self.dispatcher_queue)

    async def close(self):
        await self.client.close()
        for task in self.tasks:
            task.cancel()

    cond = asyncio.Condition()

    dispatcher_wait = 10.0
    dispatcher_error_wait = 60.0
    dispatcher_error_mul = 1.5
    timeout = 90.0
    max_retry = 5

    tasks: set[asyncio.Task] = set()
    
    async def __add_later(self, dispatcher_id: int, dispatcher: Optional[EggProxy], is_err: bool):
        async with self.cond:
            wait = self.dispatcher_wait
            if is_err:
                wait = self.dispatcher_error_waits.get(dispatcher_id)
                wait = wait*self.dispatcher_error_mul if wait is not None else self.dispatcher_error_wait
                self.dispatcher_error_waits[dispatcher_id] = wait
            elif dispatcher_id in self.dispatcher_error_waits:
                self.dispatcher_error_waits.pop(dispatcher_id)

            self.cond.release()
            await asyncio.sleep(wait)
            await self.cond.acquire()

            self.dispatcher_queue.append(dispatcher_id)
            if dispatcher_id in self.dispatchers:
                raise RuntimeError("dispatcher already in self.dispatchers. inconceivable!")

            self.dispatchers[dispatcher_id] = dispatcher
            # maybe some ppl are waiting for main, so everyone needs to check 🤡
            self.cond.notify_all()

    async def fetch[T](self, transform: Callable[[aiohttp.ClientResponse], Awaitable[T]], *args, **kwargs: Unpack[EggFetchOptions]) -> T:
        for _retry_i in range(self.max_retry):
            async with self.cond:
                if kwargs.get("noproxy", False):
                    await self.cond.wait_for(lambda: self.main_id in self.dispatchers)
                    dispatcher = self.dispatchers.pop(self.main_id)
                    dispatcher_id = self.main_id
                else:
                    dispatcher_id = None
                    while dispatcher_id is None:
                        if len(self.dispatcher_queue)>0:
                            dispatcher_id = self.dispatcher_queue.popleft()
                            if dispatcher_id in self.dispatchers:
                                continue
                        else:
                            await self.cond.wait()

                    dispatcher = self.dispatchers.pop(dispatcher_id)

            if _retry_i>0:
                logger.info(f"retrying {",".join(list(args))} {_retry_i}")

            err = None
            try:
                proxy_args = {} if dispatcher is None else {
                    "proxy": dispatcher.url,
                    "proxy_auth": dispatcher.auth
                }

                proxy_args.update(kwargs)

                async with self.client.request(
                    kwargs.get("method", "GET"),
                    *args,
                    timeout=self.timeout,
                    **proxy_args
                ) as resp:
                    if resp.status == 429 and 'Retry-After' in resp.headers:
                        await asyncio.sleep(float(resp.headers['Retry-After']))
                        continue

                    return await transform(resp)

            except Exception as e:
                err = e
                # break if an actual api error, since retrying doesn't change anything
                if isinstance(err, CFError):
                    break

            finally:
                self.tasks.add(asyncio.create_task(
                    self.__add_later(dispatcher_id, dispatcher, err is not None)
                ))

        logger.info(f"ran out of retries for request {args[0]}", err)
        raise err

    cf_base_url = "https://codeforces.com/api/"

    async def codeforces[T](self, endpoint: str, params: Optional[Dict[str, str]] = None) -> T:
        url = urljoin(self.cf_base_url, endpoint)
        if params:
            url += f"?{urlencode(params)}"

        async def transform(resp: aiohttp.ClientResponse) -> T:
            if resp.status != 200:
                txt = await resp.text()
                try:
                    r = json.loads(txt)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"CF error, body: {txt}") from e
            else:
                r = await resp.json()

            if not isinstance(r, dict) or "status" not in r:
                raise RuntimeError("Malformed CF response")
            
            if r["status"].lower() == "failed":
                raise CFError(r.get("comment"))

            return r

        return await self.fetch(transform, url)

async def eggfetch():
    ret = EggFetch()
    await ret.add_proxies()
    return ret