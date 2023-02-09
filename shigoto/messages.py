from __future__ import annotations

import importlib
import json
import os
from abc import abstractmethod, abstractstaticmethod
from typing import Callable, Dict, List, Optional

import dill
from pydantic import BaseModel

PICKLER_PROTOCOL_LEVEL = os.environ.get("PICKLER_PROTOCOL_LEVEL", 5)


class Message(BaseModel):
    """
    Messages are passed between nodes via channels.
    """

    pass


class Executable:
    @abstractmethod
    def execute(self):
        pass


class JSONMessage(Message):
    data: dict


class Task(Executable, Message):
    fn: Callable
    args: Optional[List] = []
    kwargs: Optional[Dict] = {}

    def execute(self):
        return self.fn(*self.args, **self.kwargs)

    def __eq__(self, other: Task):
        return all(
            [
                self.fn.__module__ == other.fn.__module__,
                self.fn.__name__ == other.fn.__name__,
                self.args == other.args,
                self.kwargs == other.kwargs,
            ]
        )


class PeriodicTask(Task):
    interval: int
    continue_callback: Callable

    def __eq__(self, other: PeriodicTask):
        return all(
            [
                self.fn.__module__ == other.fn.__module__,
                self.fn.__name__ == other.fn.__name__,
                self.args == other.args,
                self.kwargs == other.kwargs,
                self.interval == other.interval,
                self.continue_callback.__name__ == other.continue_callback.__name__,
            ]
        )


class Codec:
    """
    A codec defines how a message is serialized/deserialized.
    """

    @abstractstaticmethod
    def serialize(object) -> bytes:
        pass

    @abstractstaticmethod
    def deserialize(bytes) -> object:
        pass


class DillCodec(Codec):
    @staticmethod
    def serialize(object) -> bytes:
        return dill.dumps(object, protocol=PICKLER_PROTOCOL_LEVEL)

    @staticmethod
    def deserialize(data: bytes) -> object:
        return dill.loads(data)


class TaskCodec(Codec):
    @staticmethod
    def serialize(task: Task) -> bytes:
        """
        {
            fn: {
                "module": "",
                "name": ""
            },
            args: [...],
            kwargs: {...}
        }
        """
        return json.dumps(
            {
                "fn": {"module": task.fn.__module__, "name": task.fn.__name__},
                "args": task.args,
                "kwargs": task.kwargs,
            }
        ).encode("utf-8")

    @staticmethod
    def deserialize(data: bytes) -> Task:
        task_dict = json.loads(data)
        return Task(
            fn=getattr(
                importlib.import_module(task_dict["fn"]["module"]),
                task_dict["fn"]["name"],
            ),
            args=task_dict["args"],
            kwargs=task_dict["kwargs"],
        )


class JSONCodec(Codec):
    @staticmethod
    def serialize(message: JSONMessage) -> bytes:
        return message.json().encode("utf-8")

    @staticmethod
    def deserialize(data: bytes) -> JSONMessage:
        return JSONMessage(**json.loads(data))


__all__ = [
    "Message",
    "JSONMessage",
    "Task",
    "PeriodicTask",
    "DillCodec",
    "TaskCodec",
    "Codec",
    "Executable",
]
