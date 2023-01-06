#!/usr/bin/env python3

import asyncio

from websockets import connect

from ekiden.messages import Event, Kind, dump_json

# keys for `bot`
private_key = "0f1e6614bbbe65f130d967c1fc874d4eb263c7c2209bf40dbef0800b6989454c"
public_key = "25f46974c1fe23c683a9ad4c6ffe5e62d2d8e887dc8e9789f59d2c1bf4082479"


async def publish(uri):
    async with connect(uri) as websocket:
        event = Event(
            pubkey=public_key,
            kind=Kind.text_note,
            content="I'm a bot written by taiga",
        )
        command = dump_json(
            ["EVENT", event.signed(private_key=private_key)],
        )
        await websocket.send(command)
        print(await websocket.recv())


if __name__ == "__main__":
    # asyncio.run(publish("ws://localhost:8765"))
    asyncio.run(publish("wss://relay.damus.io"))
