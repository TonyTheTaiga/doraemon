import json
import time
from hashlib import sha256, shake_256

from pydantic import BaseModel
from secp256k1 import PrivateKey, PublicKey


class ETag(BaseModel):
    # <32-bytes hex of the id of another event>
    id: str
    #
    recommended_relay_url: str


class PTag(BaseModel):
    # <32-bytes hex of the pubkey>
    id: str
    #
    recommended_relay_url: str


class Tags(BaseModel):
    e: ETag
    p: PTag


class Event(BaseModel):
    # <32-bytes hex-encoded public key of the event creator>
    pubkey: str
    # <integer>
    kind: int
    # <unix timestamp in seconds>
    created_at = int(time.time())
    #
    tags: Tags
    # <arbitrary string> (payload)
    content: str

    @property
    def id(self) -> str:
        # <32-bytes sha256 of the the serialized event data>
        json_str = json.dumps(
            [
                0,
                self.pubkey,
                self.created_at,
                self.kind,
                [
                    ["e", self.tags.e.id, self.tags.e.recommended_relay_url],
                    ["p", self.tags.p.id, self.tags.p.recommended_relay_url],
                ],
                self.content,
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        return sha256(json_str).hexdigest()

    def signed_payload(self, private_key):
        return json.dumps(
            {
                "id": self.id,
                "pubkey": self.pubkey,
                "created_at": self.created_at,
                "kind": self.kind,
                "tags": [
                    ["e", self.tags.e.id, self.tags.e.recommended_relay_url],
                    ["p", self.tags.p.id, self.tags.p.recommended_relay_url],
                ],
                "content": self.content,
                "sig": shake_256(self.id.encode("utf-8")).hexdigest(64),
            }
        )


if __name__ == "__main__":
    pubkey = "npub1j2a2t7rscp2qrhpnt4nexs4aty2dc3stv2rr7ce4p02lvax42t9qfjvq4t"

    event = Event(
        pubkey=pubkey,
        kind=0,
        tags=Tags(
            e={"id": "another-events-id", "recommended_relay_url": "http://"},
            p={"id": pubkey, "recommended_relay_url": "http://"},
        ),
        content="hello, world",
    )
    print(event.json())
