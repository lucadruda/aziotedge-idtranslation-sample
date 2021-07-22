# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import sys
from typing import Union

# using the typical ImportError pattern leads to "incompatible import" error
if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class MQTTMessage(Protocol):
    """
    PEP 544-compatible Protocol object for defining what our helper methods expect
    when they accept an MQTT Message object.  Only used for static code validation.
    """

    topic: str
    payload: Union[str, bytes]
