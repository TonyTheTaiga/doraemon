#!/usr/bin/env python3

import asyncio
import json

from websockets import connect

from ekiden.keys import PrivateKey
from ekiden.messages import Event

private_key = PrivateKey()
print(f"private key {private_key.hex()}")
print(f"public key {private_key.public_key_hex()}")


async def hello(uri):
    async with connect(uri) as websocket:
        event = Event(pubkey=private_key.public_key_hex(), kind=0, content="hello, world")
        print("sending...")
        await websocket.send(
            json.dumps(
                ["EVENT", event.signed(private_key=private_key.hex())],
                separators=(",", ":"),
                ensure_ascii=False,
            )
        )
        print(await websocket.recv())


if __name__ == "__main__":
    asyncio.run(hello("ws://localhost:8765"))
    # asyncio.run(hello("wss://relay.damus.io"))
