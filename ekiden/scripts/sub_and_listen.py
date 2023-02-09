#!/usr/bin/env python3

import asyncio
import json
from uuid import uuid4

from websockets import connect

from ekiden.nips import Filters, Subscribe, dump_json

public_key = "25f46974c1fe23c683a9ad4c6ffe5e62d2d8e887dc8e9789f59d2c1bf4082479"


async def subscribe(uri):
    async with connect(uri) as websocket:
        subscription_id = uuid4().hex
        print("sub_id: ", subscription_id)
        filters = Filters(
            # kinds=[3],
            # authors=[
            #     public_key,
            #     "2183b8476998f3e2f10b757dc98d5421199e0121bf9c130ccb4628df92f1f3ad",
            # ],
            # limit=1
        )
        msg = Subscribe(subscription_id=subscription_id, filters=filters)
        await websocket.send(dump_json(msg.json_array()))
        async for message in websocket:
            print(message)
            print("\n\n")


if __name__ == "__main__":
    asyncio.run(subscribe("ws://0.0.0.0:8000"))
    # asyncio.run(subscribe("wss://ekiden-jjrbjpt6uq-ue.a.run.app"))
    # asyncio.run(subscribe("wss://relay.damus.io"))
