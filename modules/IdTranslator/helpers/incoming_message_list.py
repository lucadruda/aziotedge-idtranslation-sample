# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import logging
from typing import List, Callable
import threading
from .mqtt_message import MQTTMessage
from . import topic_matcher

logger = logging.getLogger(__name__)

message_match_predicate = Callable[[str], bool]


class IncomingMessageList(object):
    """
    thread-safe object used to keep track of incoming MQTT messages.  This object
    supports the concept of "waiting" for specific types of messages to be added to the list.
    In this way, "do-work" loops can be written which wait for specific types of messages to
    arrive and functions can be written to wait for messages like twin responses with specific
    request_id values.

    These "wait" operations are done in a thread-safe manner using the `Condition` class
    provided by the `threading` module.

    Callers using `asyncio` instead of `threading` should consider writing an awaitable version
    of this class using the `asyncio.Condition` class for synchronization.  Submitting a pull
    request with this functionality is encouraged.
    """

    def __init__(self) -> None:
        self.messages: List[MQTTMessage] = []
        self.cv = threading.Condition()

    def add_item(self, message: MQTTMessage) -> None:
        """
        Add a message to the message list and notify any listeners which might be
        waiting for this message.

        :param object message: The incoming message.
        """
        with self.cv:
            self.messages.append(message)
            self.cv.notify_all()

    def _pop_next(self, predicate: message_match_predicate) -> MQTTMessage:
        """
        Internal function to remove and return the next message in the list
        which satisfies the passed predicate.

        :param callable predicate: Function which accepts a message object and
            Returns True if that message satisfies some condition.  When this function
            returns True for some message, that message will be removed from the list and
            returned to the caller.

        :returns: The first message in our internal list which satisfies the internal predicate.
            `None` if our internal list is empty or if no messages match the predicate.
        """

        with self.cv:
            for message in self.messages:
                if predicate(message.topic):
                    self.messages.remove(message)
                    return message
        return None

    def _wait_and_pop_next(
        self, predicate: message_match_predicate, timeout: float
    ) -> MQTTMessage:
        """
        Internal function which waits until a message which matches the given predicate
        gets added to our list.

        :param callable predicate: function which accepts a message object and returns
            True if that message can be returned from this function.
        :param float timeout: Amount of time to wait before returning.

        :returns: The objet which satisfies the predicate, or `None` if no matching object
            becomes available before the timeout elapses.
        """

        with self.cv:
            return self.cv.wait_for(
                lambda: self._pop_next(predicate), timeout=timeout
            )

    def wait_for_message(self, timeout: float) -> bool:
        """
        Wait for the list to be not-empty.  If the list already has a
        message, return `True` immediately.  If not, then wait up to `timeout`
        seconds for an item to be added, and then return `True`.  If no item
        is addeded within `timeout` seconds, return False.

        This function is intended for use in a "do-work" loop to signal when
        _anyting_ gets added to the message list.  Once this message returns
        `True`, the loop can retrieve the messages from the list using the
        various `pop_next_x` functions with `timeout` = `0`.

        :param float timeout: Amount of time to wait before returning.

        :return: `True` if the list has an item, `False` otherwise.
        """
        with self.cv:
            return self.cv.wait_for(
                lambda: len(self.messages) > 0, timeout=timeout
            )

    def pop_next_message(self, timeout: float) -> MQTTMessage:
        """
        Returns the next message in the list.  If no message is in the list,
        waits for up to `timeout` seconds for one to be added.

        :param float timeout: Amount of time to wait before returning.  `0` to
            check the list and return immediately without waiting.

        :returns: The next message in the list, or `None` if no message gets
            added before the timeout elapses.
        """
        return self._wait_and_pop_next(lambda message: True, timeout=timeout)

    def pop_next_twin_patch_desired(self, timeout: float) -> MQTTMessage:
        """
        Returns the next twin desired property patch message in the list.
        If no message is in the list waits for up to `timeout` seconds for one
        to be added.

        :param float timeout: Amount of time to wait before returning.  `0` to
            check the list and return immediately without waiting.

        :returns: The next matching message in the list, or `None` if no message gets
            added before the timeout elapses.
        """
        return self._wait_and_pop_next(
            lambda message: topic_matcher.is_twin_patch_desired(message),
            timeout=timeout,
        )

    def pop_next_twin_response(
        self, request_topic: str, timeout: float
    ) -> MQTTMessage:
        """
        Returns the twin response message that matches the given request.  If no such message
        is in the list, waits for up to `timeout` seconds for one to be added.

        :param float timeout: Amount of time to wait before returning.  `0` to
            check the list and return immediately without waiting.

        :returns: The next matching message in the list, or `None` if no message gets
            added before the timeout elapses.
        """
        return self._wait_and_pop_next(
            lambda message: topic_matcher.is_twin_response(
                message, request_topic
            ),
            timeout=timeout,
        )

    def pop_next_c2d(self, timeout: float) -> MQTTMessage:
        """
        Returns the next c2d message in the list.  If no such message is in the list,
        waits for up to `timeout` seconds for one to be added.

        :param float timeout: Amount of time to wait before returning.  `0` to
            check the list and return immediately without waiting.

        :returns: The next matching message in the list, or `None` if no message gets
            added before the timeout elapses.
        """
        return self._wait_and_pop_next(
            lambda message: topic_matcher.is_c2d(message), timeout=timeout
        )

    def pop_next_method_request(
        self, timeout: float, method_name: str = None
    ) -> MQTTMessage:
        """
        Returns the next method request message in the list.  If `method_name` is `None, _any_
        method request will be matched.  If `method_name` is not `None`, only the method request
        for the given name will be returned.  If no such message is in the list, waits for up to
        `timeout` seconds for one to be added.

        :param float timeout: Amount of time to wait before returning.  `0` to
            check the list and return immediately without waiting.

        :returns: The next matching message in the list, or `None` if no message gets
            added before the timeout elapses.
        """
        return self._wait_and_pop_next(
            lambda message: topic_matcher.is_method_request(
                message, method_name
            ),
            timeout=timeout,
        )
