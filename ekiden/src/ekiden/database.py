from tortoise import fields
from tortoise.models import Model

from ekiden import nips


class UnknownTagError(Exception):
    """Throw when the stored tag could not be parsed back to its data model"""


def create_tag(tag_dict) -> nips.Tag:
    try:
        return nips.ETag.parse_obj(tag_dict)
    except:
        pass

    try:
        return nips.PTag.parse_obj(tag_dict)
    except:
        pass

    raise UnknownTagError(f"Could not parse tag {tag_dict}")


class Identity(Model):
    pubkey: str = fields.CharField(max_length=64, pk=True, index=True)
    name: str = fields.TextField(null=True)
    about: str = fields.TextField(null=True)
    picture: str = fields.TextField(null=True)

    class Meta:
        table = "identity"

    def __str__(self) -> str:
        return f"{self.pubkey}, {self.name}, {self.about}, {self.picture}"


class Event(Model):
    table_id = fields.IntField(pk=True)

    id: str = fields.TextField()
    kind = fields.IntField()
    content: str = fields.TextField()
    created_at = fields.IntField()
    tags = fields.JSONField()
    pubkey: str = fields.TextField()
    sig: str = fields.TextField()

    class Meta:
        table = "event"

    def __str__(self) -> str:
        return f"{self.id} {self.kind} {self.content} {self.tags} {self.pubkey} {self.sig}"

    def nipple(self) -> nips.Event:
        """Converts the database record into a NIPS defined event

        Returns:
            nips.Event: NIP Event
        """
        return nips.Event(
            pubkey=self.pubkey,
            create_at=self.created_at,
            kind=self.kind,
            sig=self.sig,
            tags=[create_tag(tag_dict) for tag_dict in self.tags],
            content=self.content,
        )
