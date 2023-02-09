from __future__ import annotations

import logging
import multiprocessing
from abc import abstractmethod
from queue import Queue
from uuid import uuid4

import redis
import redis.asyncio
from google.cloud import pubsub_v1

from .messages import *


class Channel:
    """
    Channels define how messages are passed between nodes.
    """

    def __init__(self):
        self.ulid = uuid4().hex

    @abstractmethod
    def put(self, data):
        pass

    @abstractmethod
    def get(self):
        pass


class InputChannel:
    def __init__(self):
        self.ulid = uuid4().hex

    @abstractmethod
    def get(self):
        pass


class OutputChannel:
    def __init__(self):
        self.ulid = uuid4().hex

    @abstractmethod
    def put(self, data):
        pass


class QueueChannel(Channel):
    def __init__(self, codec: Codec, queue: Queue = None, maxsize: int = -1):
        super().__init__()
        self.codec = codec

        self.queue = queue
        if not self.queue:
            self.queue = Queue(maxsize=maxsize)

    def put(self, message: Message):
        try:
            serialized = self.codec.serialize(message)
        except Exception as e:
            logging.error(f"message type {type(message)} is not supported for this codec {self.codec}. {e}")
            return

        self.queue.put(serialized)

    def get(self):
        data = self.queue.get()

        try:
            deserialized = self.codec.deserialize(data)
        except Exception as e:
            logging.error(f"message data could not be deserialized with this codec {self.codec}. {e}")
            return

        return deserialized


class MPQueueChannel(Channel):
    def __init__(self, codec: Codec, queue=None, maxsize=-1):
        super().__init__()

        self.codec = codec
        self.queue = queue
        if not self.queue:
            self.queue = multiprocessing.Queue(maxsize=maxsize)

    def put(self, message: Message):
        try:
            serialized = self.codec.serialize(message)
        except Exception as e:
            logging.error(f"message type {type(message)} is not supported for this codec {self.codec}. {e}")
            return

        self.queue.put(serialized)

    def get(self):
        data = self.queue.get()

        try:
            deserialized = self.codec.deserialize(data)
        except Exception as e:
            logging.error(f"message data could not be deserialized with this codec {self.codec}. {e}")
            return

        return deserialized


class RedisChannel(Channel):
    def __init__(self, codec: Codec, uri: str, key: str):
        super().__init__()
        self._codec = codec
        self._key = key

        self._client = redis.from_url(uri)

    def put(self, data):
        self._client.lpush(self._key, self._codec.serialize(data))

    def get(self, timeout: float = None):
        msg = self._client.blpop(self._key, timeout=timeout)
        if msg:
            return self._codec.deserialize(msg[1])


class AsyncRedisChannel(Channel):
    def __init__(self, codec: Codec, uri: str, key: str):
        super().__init__()
        self._codec = codec
        self._key = key

        self._client = redis.asyncio.from_url(uri)

    async def put(self, data):
        await self._client.rpush(self._key, self._codec.serialize(data))

    async def get(self, timeout: float = None):
        msg = await self._client.blpop(self._key, timeout=timeout)
        if msg:
            return self._codec.deserialize(msg[1])


class PublishChannel(OutputChannel):
    def __init__(self, topic: str, codec: Codec):
        self.topic = topic
        self.codec = codec

        self._publisher = pubsub_v1.PublisherClient(
            publisher_options=pubsub_v1.types.PublisherOptions(
                enable_message_ordering=True,
            )
        )
        self._message_count = 1

    def put(self, message: Message):
        try:
            serialized = self.codec.serialize(message)
        except Exception as e:
            logging.error(f"message type {type(message)} is not supported for this codec {self.codec}. {e}")
            return

        self._publisher.publish(self.topic, serialized, ordering_key=str(self._message_count))
        self._message_count += 1


class SubscriptionChannel(InputChannel):
    def __init__(
        self,
        subscription: str,
        codec: Codec,
    ):
        self.codec = codec
        self._message_queue = Queue()

        subscriber = pubsub_v1.SubscriberClient()
        self._future = subscriber.subscribe(subscription, callback=self._callback)

    def _callback(self, message: pubsub_v1.subscriber.message.Message):
        deserialized = self.codec.deserialize(message.data)
        self._message_queue.put(deserialized)
        message.ack()

    def get(self):
        message = self._message_queue.get()
        return message


class PubSubChannel(PublishChannel, SubscriptionChannel):
    def __init__(self, topic: str, subscription: str, codec: Codec):
        self._pub_channel = PublishChannel(topic, codec=codec)
        self._sub_channel = SubscriptionChannel(subscription, codec=codec)

    def get(self):
        return self._sub_channel.get()

    def put(self, message: Message):
        self._pub_channel.put(message)


__all__ = [
    "Channel",
    "QueueChannel",
    "PubSubChannel",
    "InputChannel",
    "OutputChannel",
    "PublishChannel",
    "SubscriptionChannel",
    "MPQueueChannel",
]
