from __future__ import annotations

import json
import time
from enum import IntEnum
from hashlib import sha256
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from ekiden.keys import PrivateKey, PublicKey, VerificationError


def dump_json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


class Kind(IntEnum):
    set_metadata = 0
    text_note = 1
    recommend_server = 2
    contact_list = 3


class Tag(BaseModel):
    def json_array(self):
        raise NotImplemented("json_array is not implemented!")


class ETag(Tag):
    # e (event) tags are a list of parent event ids (list of event ids `this` event references)
    id: str  # <32-bytes hex of the id of another event>
    recommended_relay_url: Optional[str] = ""

    def json_array(self):
        # <['e', event_id, recommended_relay_url]>
        return ["e", self.id, self.recommended_relay_url]


class UnknownTagError(Exception):
    """Throw when the stored tag could not be parsed back to its data model"""


class PTag(Tag):
    # p (pubkey) tags are list of pubkeys mentioned in `this` event
    pubkey: str  # <32-bytes hex of the pubkey>
    recommended_relay_url: Optional[str] = ""

    def json_array(self):
        # <['p', pubkey, recommended_relay_url]>
        return ["p", self.pubkey, self.recommended_relay_url]


def create_tag(tag_info) -> Tag:
    if tag_info[0] == "e":
        return ETag(id=tag_info[1], recommended_relay_url=tag_info[2])
    elif tag_info[0] == "p":
        return PTag(pubkey=tag_info[1], recommended_relay_url=tag_info[2])

    raise UnknownTagError(f"Could not parse tag {tag_info}")


class Event(BaseModel):
    # NIP-1

    pubkey: str  # <32-bytes hex-encoded public key of the event creator>
    kind: int  # <integer>
    created_at: Optional[int] = int(time.time())  # <unix timestamp in seconds>
    tags: Optional[Tuple[Tag, ...]] = []
    content: str  # <arbitrary string> (payload)

    sig: Optional[str] = None

    @property
    def id(self) -> str:
        """
        <32-bytes sha256 hex-encoded string of the the serialized event data>
        To obtain the `event.id`, we sha256 the serialized event. The serialization is done over the UTF-8 JSON-serialized string (with no white space or line breaks) of the following structure:

        `[
        0,
        <pubkey, as a (lowercase) hex string>,
        <created_at, as a number>,
        <kind, as a number>,
        <tags, as an array of arrays of non-null strings>,
        <content, as a string>
        ]`

        """
        return sha256(
            Event.serialize(
                pubkey=self.pubkey,
                created_at=self.created_at,
                kind=self.kind,
                tags=[tag.json_array() for tag in self.tags],
                content=self.content,
            ).encode("utf-8")
        ).hexdigest()

    def sign(self, private_key: str) -> str:
        """Signs the messge (Event.id) and sets the sig field

        Args:
            private_key (str): The private key to sign the message with

        Returns:
            str: _description_
        """
        self.sig = PrivateKey.load(private_key).sign(msg=bytes.fromhex(self.id))

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
    def verify(cls, event: dict) -> Event:
        """
        Verify the contents of the event with the signature and fields given.

        Returns a new instance with the provided information if successful else raises a VerificationError
        """
        ret = PublicKey(event["pubkey"]).verify(
            msg=bytes.fromhex(event["id"]),
            signature=event["sig"],
        )
        if not ret:
            raise VerificationError("contents of the message could not be verified with the signature provided")
        event["tags"] = [create_tag(tag_info) for tag_info in event["tags"]]
        return Event(**event)

    @staticmethod
    def serialize(pubkey, created_at, kind, tags, content) -> str:
        return dump_json([0, pubkey, created_at, kind, tags, content])

    def dict(self):
        return {
            "id": self.id,
            "pubkey": self.pubkey,
            "created_at": self.created_at,
            "kind": self.kind,
            "tags": [tag.json_array() for tag in self.tags],
            "content": self.content,
            "sig": self.sig,
        }


class Filters(BaseModel):
    # NIP-1
    # each field is considered a `filter`. multiple filters are or conditions (e.g only one has to pass for the event to be valid)
    # a filter that can contain more than one items are to be treated as and conditions

    #  A prefix match is when the filter string is an exact string prefix of the event value
    # prefix = aaa, aaa432 is valid, xaaa12332 is not valid
    ids: Optional[List[str]] = []  # <a list of event ids or prefixes>
    authors: Optional[List[str]] = []  # <a list of pubkeys or prefixes, the pubkey of an event must be one of these>

    kinds: Optional[List[int]] = []  # <a list of a kind numbers>
    event_ids: Optional[List[str]] = Field(
        alias="#e", default=[]
    )  # <a list of event ids that are referenced in an "e" tag>
    pubkeys: Optional[List[str]] = Field(alias="#p", default=[])  # <a list of pubkeys that are referenced in a "p" tag>
    since: Optional[int]  #  <a timestamp, events must be newer than this to pass>
    until: Optional[int]  # <a timestamp, events must be older than this to pass>
    limit: Optional[int]  # <maximum number of events to be returned in the initial query>


class Subscribe(BaseModel):
    # NIP-1
    # used to request events and subscribe to new updates.
    subscription_id: str  # a random string that should be used to represent a subscription
    filters: Filters  # A filter determines what events will be sent in that subscription

    def json_array(self) -> str:
        # ['REQ', <subscription id>, <[Filter, ...]>]
        return ["REQ", self.subscription_id, self.filters.dict(exclude_defaults=True)]


class Close(BaseModel):
    # NIP-1
    # used to stop previous subscriptions.
    subscription_id: str

    def json_array(self) -> str:
        return ["CLOSE", self.subscription_id]


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
