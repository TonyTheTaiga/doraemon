#!/usr/bin/env python3

import asyncio
import json
from uuid import uuid4

from websockets import connect

from ekiden.messages import Filters, Subscribe, dump_json

public_key = "25f46974c1fe23c683a9ad4c6ffe5e62d2d8e887dc8e9789f59d2c1bf4082479"


async def subscribe(uri):
    async with connect(uri) as websocket:
        subscription_id = uuid4().hex
        filters = Filters(
            # ids=["xxx"],
            authors=[
                public_key,
                "ce8eba6311ffb9897aecd4bc52831fb2e0f2da8dbf6704643be5e9002327a3eb",
            ],
            since=1672373502,
        )
        command = dump_json(
            [
                "REQ",
                subscription_id,
                filters.dict(exclude_defaults=True),
            ]
        )
        print(command)
        await websocket.send(command)
        # while True:
        #     print(await websocket.recv())
        async for message in websocket:
            print(message)


if __name__ == "__main__":
    # asyncio.run(subscribe("ws://localhost:8765"))
    asyncio.run(subscribe("wss://relay.damus.io"))
