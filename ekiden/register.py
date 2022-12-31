#!/usr/bin/env python3

import asyncio

from websockets import connect

from ekiden.messages import Event, Kind, dump_json

# keys for `boffeeblub`
# private_key = "f8c2eb92c2715f6e61c80ad2433b16faf4312c33f55595af7f109dc8d7db86f8"
# public_key = "ce8eba6311ffb9897aecd4bc52831fb2e0f2da8dbf6704643be5e9002327a3eb"

# keys for `bot`
private_key = "0f1e6614bbbe65f130d967c1fc874d4eb263c7c2209bf40dbef0800b6989454c"
public_key = "25f46974c1fe23c683a9ad4c6ffe5e62d2d8e887dc8e9789f59d2c1bf4082479"


async def register(uri):
    async with connect(uri) as websocket:
        event = Event(
            pubkey=public_key,
            kind=Kind.set_metadata,
            content=dump_json(dict(name="bot", about="beep", picture="")),
        )
        command = dump_json(
            ["EVENT", event.signed(private_key=private_key)],
        )
        await websocket.send(command)
        print(await websocket.recv())


if __name__ == "__main__":
    asyncio.run(register("ws://localhost:8765"))
    # asyncio.run(register("wss://relay.damus.io"))
