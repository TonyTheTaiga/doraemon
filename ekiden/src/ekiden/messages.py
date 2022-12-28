from __future__ import annotations

import json
import time
from enum import IntEnum
from hashlib import sha256
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from ekiden.keys import PrivateKey, PublicKey


def dump_json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


class Kind(IntEnum):
    set_metadata = 0
    text_note = 1
    recommend_server = 2


class Tag(BaseModel):
    def json_array(self):
        raise NotImplemented("json_array is not implemented!")


class ETag(Tag):
    # e (event) tags are a list of parent event ids (list of event ids `this` event references)
    id: str  # <32-bytes hex of the id of another event>
    recommended_relay_url: Optional[str] = ""

    def json_array(self):
        # <['e', event_id, recommended_relay_url]>
        return dump_json(["e", self.id, self.recommended_relay_url])


class PTag(Tag):
    # p (pubkey) tags are list of pubkeys mentioned in `this` event
    pubkey: str  # <32-bytes hex of the pubkey>
    recommended_relay_url: Optional[str] = ""

    def json_array(self):
        # <['p', pubkey, recommended_relay_url]>
        return dump_json(["p", self.pubkey, self.recommended_relay_url])


class Event(BaseModel):
    pubkey: str  # <32-bytes hex-encoded public key of the event creator>
    kind: int  # <integer>
    created_at: Optional[int] = int(time.time())  # <unix timestamp in seconds>
    tags: Optional[Tuple[Tag, ...]] = []
    content: str  # <arbitrary string> (payload)

    sig: Optional[str] = None

    @property
    def id(self) -> str:
        # <32-bytes sha256 hex-encoded string of the the serialized event data>
        return sha256(
            Event.serialize(
                pubkey=self.pubkey,
                created_at=self.created_at,
                kind=self.kind,
                tags=[tag.json_array() for tag in self.tags],
                content=self.content,
            ).encode("utf-8")
        ).hexdigest()

    def sign(self, private_key: str):
        self.sig = PrivateKey.load(private_key).sign(bytes.fromhex(self.id))

    def signed(self, private_key: str) -> dict:
        if not self.sig:
            self.sign(private_key=private_key)

        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": [tag.json_array() for tag in self.tags],
            "content": self.content,
            "sig": self.sig,
        }

    @classmethod
    def verify(cls, event) -> Event:
        """
        Verify the contents of the event with the signature and fields given.

        Returns a new instance with the provided information if successful else raises a ValueError
        """
        ret = PublicKey(event["pubkey"]).verify(
            msg=sha256(
                Event.serialize(
                    pubkey=event["pubkey"],
                    created_at=event["created_at"],
                    kind=event["kind"],
                    tags=event["tags"],
                    content=event["content"],
                ).encode("utf-8")
            ).digest(),
            signature=event["sig"],
        )
        if not ret:
            raise ValueError(
                "contents of the message could not be verified with the signature provided"
            )

        return Event(
            pubkey=event["pubkey"],
            created_at=event["created_at"],
            kind=event["kind"],
            tags=event["tags"],
            content=event["content"],
            sig=event["sig"],
        )

    @staticmethod
    def serialize(pubkey, created_at, kind, tags, content) -> str:
        return dump_json([0, pubkey, created_at, kind, tags, content])


class Filters(BaseModel):
    # each field is considered a `filter`. multiple filters are or conditions (e.g only one has to pass for the event to be valid)
    # a filter that can contain more than one items are to be treated as and conditions

    ids: Optional[List[str]] = []  # <a list of event ids or prefixes>
    authors: Optional[
        List[str]
    ] = []  # <a list of pubkeys or prefixes, the pubkey of an event must be one of these>
    #  A prefix match is when the filter string is an exact string prefix of the event value

    kinds: Optional[List[int]] = []  # <a list of a kind numbers>
    event_ids: Optional[List[str]] = Field(
        alias="#e", default=[]
    )  # <a list of event ids that are referenced in an "e" tag>
    pubkeys: Optional[List[str]] = Field(
        alias="#p", default=[]
    )  # <a list of pubkeys that are referenced in a "p" tag>
    since: Optional[int]  #  <a timestamp, events must be newer than this to pass>
    until: Optional[int]  # <a timestamp, events must be older than this to pass>
    limit: Optional[int]  # <maximum number of events to be returned in the initial query>


class Command(BaseModel):
    def command_array(self):
        raise NotImplemented("command_array not implemented")


class Subscribe(BaseModel):
    # used to request events and subscribe to new updates.
    subscription_id: str  # a random string that should be used to represent a subscription
    filters: Filters  # A filter determines what events will be sent in that subscription

    def json_array(self) -> str:
        # ['REQ', <subscription id>, <[Filter, ...]>]
        return dump_json(
            [
                "REQ",
                self.subscription_id,
                self.filter.json(separators=(",", ":"), ensure_ascii=False),
            ]
        )


class Close(BaseModel):
    # used to stop previous subscriptions.
    subscription_id: str

    def json_array(self) -> str:
        return dump_json(["CLOSE", self.subscription_id])


class Notice(BaseModel):
    #  used to send human-readable error messages or other things to clients.
    message: str


if __name__ == "__main__":
    pk = PrivateKey()

    event = Event(
        pubkey=pk.public_key_hex(),
        kind=Kind.text_note,
        content="hello, world",
    )
    payload = event.signed_json(pk.hex())

    data = json.loads(payload)
    print(Event.verify(data))
