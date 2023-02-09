#!/usr/bin/env python3

import asyncio

from websockets import connect

from ekiden.nips import Event, Kind, dump_json, PTag

# keys for `bot`
private_key = "7a3cbb920196bfd57a57d8588852b8c314dfa8bca28deea3a75adc70273628a6"
public_key = "2183b8476998f3e2f10b757dc98d5421199e0121bf9c130ccb4628df92f1f3ad"


async def publish(uri):
    async with connect(uri) as websocket:
        event = Event(
            pubkey=public_key,
            kind=Kind.contact_list,
            tags=(
                PTag(
                    pubkey="d367c5d6de7e4f07ce03e69d249302920ac69d84c29d6b81d77cb7b13728b1da", recommended_relay_url=""
                ),
            ),
            content="",
        )
        command = dump_json(
            ["EVENT", event.signed(private_key=private_key)],
        )
        print(command)
        await websocket.send(command)
        print(await websocket.recv())


if __name__ == "__main__":
    # asyncio.run(publish("wss://relay.damus.io"))
    # asyncio.run(publish("wss://brb.io"))
    # asyncio.run(publish("ws://0.0.0.0:8000"))
    asyncio.run(publish("wss://ekiden-jjrbjpt6uq-ue.a.run.app"))
