#!/usr/bin/env python3

import asyncio

from websockets import connect

from ekiden.nips import Event, Kind, dump_json, ETag

# keys for `bot`
private_key = "7a3cbb920196bfd57a57d8588852b8c314dfa8bca28deea3a75adc70273628a6"
public_key = "2183b8476998f3e2f10b757dc98d5421199e0121bf9c130ccb4628df92f1f3ad"


async def publish(uri):
    async with connect(uri) as websocket:
        event = Event(
            pubkey=public_key,
            kind=Kind.text_note,
            tags=(
                ETag(id="76e3360421f601e6f3b2205d05bb2d605c217f3814608a159139cbc1ac1d3dff", recommended_relay_url=""),
            ),
            content="hello",
        )
        command = dump_json(
            ["EVENT", event.signed(private_key=private_key)],
        )
        print(command)
        # for _ in range(1000):
        await websocket.send(command)
        print(await websocket.recv())


if __name__ == "__main__":
    # asyncio.run(publish("wss://relay.damus.io"))
    # asyncio.run(publish("wss://brb.io"))
    asyncio.run(publish("ws://0.0.0.0:8000"))
    # asyncio.run(publish("wss://ekiden-jjrbjpt6uq-ue.a.run.app"))
