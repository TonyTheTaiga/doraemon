#!/usr/bin/env python3

import asyncio

from websockets import connect

from ekiden.nips import Event, Kind, dump_json

# keys for `bot`
private_key = "7a3cbb920196bfd57a57d8588852b8c314dfa8bca28deea3a75adc70273628a6"
public_key = "2183b8476998f3e2f10b757dc98d5421199e0121bf9c130ccb4628df92f1f3ad"


async def register(uri):
    async with connect(uri) as websocket:
        event = Event(
            pubkey=public_key,
            kind=Kind.set_metadata,
            content=dump_json(dict(name="bot", about="beet", picture="")),
        )
        command = dump_json(
            ["EVENT", event.signed(private_key=private_key)],
        )
        print(command)
        await websocket.send(command)
        print(await websocket.recv())


if __name__ == "__main__":
    asyncio.run(register("ws://localhost:8000"))
    # asyncio.run(register("wss://relay.damus.io"))
