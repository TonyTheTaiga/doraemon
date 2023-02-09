from __future__ import annotations

import logging
import multiprocessing
import threading
from abc import abstractmethod
from typing import List, Union

from . import channels, messages


def build_node_class(mode: Union[threading.Thread, multiprocessing.Process]):
    """
    Builds the base class for nodes. This allows us to use the same classes but switch between Threads and Processes easily.
    """

    class Node(mode):
        @abstractmethod
        def run(self):
            pass

        @abstractmethod
        def clone(self):
            pass

    return Node


Node = build_node_class(threading.Thread)


class Worker(Node):
    def __init__(
        self,
        input_channel: channels.Channel,
        output_channels: List[channels.Channel] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._input_channel = input_channel
        self._output_channels = output_channels
        self.busy: bool = False

    def run(self):
        """
        Waits for a executable message and executes it.
        """
        while True:
            message = self._input_channel.get()
            self.busy = True
            if isinstance(message, messages.Executable):
                self._do_task(message)
            self.busy = False

    def _do_task(self, task: messages.Executable):
        """
        Handles task execution.
        """
        try:
            logging.debug(f"{self.name}: executing {task}")
            res = task.execute()
            if res:
                self.notify(res)
        except Exception as e:
            logging.error(e)

    def notify(self, result: messages.Message):
        """
        Notify all nodes in the output channels with the result.
        """
        if self._output_channels:
            for output_channel in self._output_channels:
                output_channel.put(result)

    def clone(self) -> Worker:
        """Create a clone of this worker."""
        clone = type(self)(
            input_channel=self._input_channel,
            output_channels=self._output_channels,
        )
        return clone


class Tasker(Node):
    def __init__(
        self,
        input_channel: channels.Channel,
        output_channel: channels.Channel,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._input_channel = input_channel
        self._output_channel = output_channel

    def add_task(self, task: messages.Task):
        """
        Adds a task to the queue of tasks to be submitted to the workers.
        """
        self._input_channel.put(task)

    def run(self):
        """
        Waits for a task to submit and submits them.
        """

        while True:
            data = self._input_channel.get()
            logging.debug(f"Tasker: got task {data}")
            if isinstance(data, messages.Executable):
                self._submit_task(data)

    def _submit_task(self, task: messages.Executable):
        """
        Submits a task to the output channel.

        For `PeriodicTask`, the continue_callback is checked to see if the task should be executed again and if so,
        a Timer is started that will submit a task after the specified interval.
        """
        if isinstance(task, messages.PeriodicTask):
            if task.continue_callback():
                threading.Timer(
                    interval=task.interval,
                    function=self._submit_task,
                    args=(task,),
                ).start()
                self._output_channel.put(task)
        else:
            self._output_channel.put(task)

    def clone(self):
        clone = type(self)(
            input_channel=self._input_channel,
            output_channel=self._output_channel,
        )
        return clone
