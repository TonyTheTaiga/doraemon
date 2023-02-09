import json
from hashlib import sha256
from uuid import uuid4

from tortoise.exceptions import DoesNotExist
from tortoise.transactions import atomic

from ekiden import database
from ekiden.nips import Event, Kind, dump_json
from ekiden.subscriptions import SubscriptionPool


class AsyncRelay:
    def __init__(self, sub_pool: SubscriptionPool) -> None:
        self.conn_pool = sub_pool

    async def get_identity(self, pubkey: str) -> database.Identity:
        """Retreive an identity record by pubkey from the database if it exists, else create a new one.

        Args:
            pubkey (str): the pubkey of the identity.

        Returns:
            database.Identity: the identity record.
        """
        if await database.Identity.exists(pubkey=pubkey):
            return await database.Identity.get(pubkey=pubkey)

        return await database.Identity.create(pubkey=pubkey)

    @atomic()
    async def event(self, event_data: dict):
        """Handles the event action.

        Args:
            event_data (dict): A dict object containing the event data.
            db (Database): The database connection.
        """
        try:
            event = Event.verify(event_data)
        except:
            return dump_json(
                [
                    "OK",
                    dump_json(event_data).encode("utf-8") + uuid4().hex.encode("utf-8"),
                    "false",
                    "failed to verify key",
                ]
            )
        if event.kind == Kind.set_metadata:
            try:
                if db_event := await database.Event.get(pubkey=event.pubkey, kind=event.kind):
                    await db_event.delete()
            except DoesNotExist:
                pass

            identity = await self.get_identity(pubkey=event.pubkey)
            await self.save_metadata(identity, event)

        await self.conn_pool.broadcast(event)

        await database.Event.create(
            id=event.id,
            kind=event.kind,
            content=event.content,
            created_at=event.created_at,
            tags=[tag.dict() for tag in event.tags],
            pubkey=event.pubkey,
            sig=event.sig,
        )

        return dump_json(
            [
                "OK",
                sha256(event.json().encode("utf-8") + uuid4().hex.encode("utf-8")).hexdigest(),
                "true",
                "",
            ]
        )

    async def save_metadata(self, identity: database.Identity, event: Event):
        content = json.loads(event.content)
        if "name" in content:
            identity.name = content["name"]
        if "about" in content:
            identity.about = content["about"]
        if "picture" in content:
            identity.picture = content["picture"]

        await identity.save()
