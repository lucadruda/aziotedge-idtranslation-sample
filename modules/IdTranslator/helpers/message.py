# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""
from datetime import datetime
import json
from typing import Any, Union, Dict, List
from . import constants


class Message(object):
    """Represents a message to or from IoTHub
    """

    def __init__(
        self, payload: Union[bytes, str, Dict[str, Any], List[Any]]
    ) -> None:
        """
        Initializer for Message

        :param data: The  data that constitutes the payload
        """
        self.payload = payload
        self.custom_properties: Dict[str, str] = {}

        # system properties
        self.iothub_interface_id: str = None
        self._content_type: str = None
        self._content_encoding: str = None
        self.output_name: str = None
        self.message_id: str = None
        self.correlation_id: str = None
        self.user_id: str = None
        self.expiry_time_utc: Union[datetime, str] = None

    def set_as_security_message(self) -> None:
        """
        Set the message as a security message.

        This is a provisional API. Functionality not yet guaranteed.
        """
        self.interface_id = constants.SECURITY_MESSAGE_INTERFACE_ID

    @property
    def content_type(self) -> str:
        """
        content-type of the message.  Can be manually set.  If not manually set, intelligent
        defaults are attempted based on self.payload.
        """
        if self._content_type:
            return self._content_type
        elif self.is_data_json():
            return "application/json"
        elif isinstance(self.payload, str):
            return "application/text"
        else:
            return None

    @content_type.setter
    def content_type(self, content_type: str) -> None:
        self._content_type = content_type

    @property
    def content_encoding(self) -> str:
        """
        content-encoding of the message.  Can be manually set.  If not manually set, intelligent
        defaults are attempted based on self.payload.
        """
        if self._content_encoding:
            return self._content_encoding
        elif self.is_data_json():
            return constants.DEFAULT_STRING_ENCODING
        elif isinstance(self.payload, str):
            return constants.DEFAULT_STRING_ENCODING
        else:
            return None

    @content_encoding.setter
    def content_encoding(self, content_encoding: str) -> None:
        self._content_encoding = content_encoding

    def is_data_json(self) -> bool:
        """
        Return True if the data is json-parsable.  Used to set content_type and content_encoding defaults.
        """
        if isinstance(self.payload, dict) or isinstance(self.payload, list):
            return True
        elif isinstance(self.payload, bytes) or isinstance(self.payload, str):
            try:
                json.loads(self.payload)
            except json.JSONDecodeError:
                return False
            return True
        else:
            return True

    def get_binary_payload(self) -> bytes:
        """
        Get the payload of the message as an array of bytes

        :returns: array of bytes that can be sent over the transport.
        """
        if isinstance(self.payload, bytes):
            return self.payload
        elif isinstance(self.payload, str):
            return self.payload.encode(constants.DEFAULT_STRING_ENCODING)
        elif isinstance(self.payload, dict) or isinstance(self.payload, list):
            return json.dumps(self.payload).encode(
                constants.DEFAULT_STRING_ENCODING
            )
        else:
            assert False
