import json
from asyncio import Lock
from typing import Dict, List, Tuple

import aiofiles
from pydantic import BaseModel
from websockets.server import WebSocketServerProtocol

from ekiden.messages import Event, Filters, Kind, Tag, dump_json

db_lock = Lock()
subscriptions = []


class Identity(BaseModel):
    name: str
    about: str
    picture: str
    pubkey: str


class DBEvent(BaseModel):
    id: str
    kind: int
    pubkey: str
    created_at: int
    tags: Tuple[Tag, ...]
    content: str
    sig: str


class DB(BaseModel):
    identities: Dict[str, Identity]
    events: Dict[str, Dict[Kind, List[DBEvent]]]

    class Config:
        extra = "allow"


async def load_db() -> DB:
    async with aiofiles.open("db.json", mode="r") as fp:
        return DB(**json.loads(await fp.read()))


async def save_db(db: DB):
    async with aiofiles.open("db.json", mode="w") as fp:
        await fp.write(db.json(indent=4))


def validate_ids(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_authors(candidates, subject):
    if len(candidates) == 0:
        return True

    return True if subject in candidates else False


def validate_filters(event: Event, filters: Filters):
    if validate_ids(filters.ids, event.id) and validate_authors(filters.authors, event.pubkey):
        return True
    return False


async def registration_handler(websocket: WebSocketServerProtocol, db: DB, event: Event):
    content = json.loads(event.content)
    if event.pubkey in db.identities:
        identity = db.identities.get(event.pubkey)
        print(f"updating identity {event.pubkey}:{content}")
        if "name" in content:
            identity.name = content["name"]
        if "about" in content:
            identity.about = content["about"]
        if "picture" in content:
            identity.picture = content["picture"]
    else:
        print(f"new identity {content}")
        db.identities.update(
            {
                event.pubkey: Identity(
                    name=content["name"],
                    about=content["about"],
                    picture=content["picture"],
                    pubkey=event.pubkey,
                )
            }
        )


async def publication_handler(websocket, db: DB, event: Event):
    # Publishe the event to all valid subscriptions
    for websocket, subscription_id, filters in subscriptions:
        if websocket.open:
            if validate_filters(event, filters):
                await websocket.send(dump_json(["EVENT", subscription_id, event.dict()]))
        else:
            # remove from list of subscriptions
            pass


async def event_handler(websocket: WebSocketServerProtocol, db: DB, event: Event):
    if not event.pubkey in db.identities and event.kind != Kind.set_metadata:
        print(f"Received a event from a unidentifiable user\n{event}")
        return

    events = db.events.setdefault(event.pubkey, {})
    if event.kind == Kind.set_metadata and event.kind in events:
        # Remove previous set_metadata event for `this` pubkey
        events[event.kind].pop(0)

    kind_events = events.setdefault(event.kind, [])
    kind_events.append(
        {
            "id": event.id,
            "kind": event.kind,
            "pubkey": event.pubkey,
            "created_at": event.created_at,
            "tags": event.tags,
            "content": event.content,
            "sig": event.sig,
        }
    )

    if event.kind == Kind.set_metadata:
        await registration_handler(websocket, db, event)
    elif event.kind in [Kind.text_note, Kind.recommend_server]:
        # TODO: if Kind.recommend_server validate that the content of the event is a valid websocket uri (ws://..., wss://...)
        await publication_handler(websocket, db, event)

    async with db_lock:
        await save_db(db)

    await websocket.send(dump_json(["NOTICE", "OK"]))


async def subscription_handler(websocket: WebSocketServerProtocol, db: DB, subscription_id: str, filters: Filters):
    subscriptions.append((websocket, subscription_id, filters))

    hits = []
    for user_pubkey, user_events in db.events.items():
        for kind, kind_events in user_events.items():
            for event in kind_events:
                if validate_filters(event, filters):
                    hits.append(event)

    for event in hits:
        await websocket.send(dump_json(["EVENT", subscription_id, event.dict()]))


async def handler(websocket: WebSocketServerProtocol):
    db = await load_db()

    async for message in websocket:  # This waits for messages indefinitely on this websocket unless the client terminates connection
        decoded = json.loads(message)
        if decoded[0] == "EVENT":
            event = Event.verify(decoded[1])
            await event_handler(websocket, db, event)

        elif decoded[0] == "REQ":
            subscription_id = decoded[1]
            filters = Filters.parse_obj(decoded[2])
            await subscription_handler(websocket, db, subscription_id, filters)

        elif decoded[0] == "CLOSE":
            pass

    print(f"closing {websocket}")
