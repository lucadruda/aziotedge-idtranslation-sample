# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
from uuid import uuid4
from typing import List, Tuple
from datetime import datetime
import six.moves.urllib as urllib
from . import topic_parser, constants, Message, version_compat


def build_edge_topic_prefix(device_id: str, module_id: str) -> str:
    """
    Helper function to build the prefix that is common to all topics.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if build a prefix for a device.

    :return: The topic prefix, including the trailing slash (`/`)
    """
    if module_id:
        return "$iothub/{}/{}/".format(device_id, module_id)
    else:
        return "$iothub/{}/".format(device_id)


def build_iothub_topic_prefix(device_id: str, module_id: str = None) -> str:
    """
    return the string that is at the beginning of all topics for this
    device/module

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if build a prefix for a device.

    :return: The topic prefix, including the trailing slash (`/`)
    """

    # NOTE: Neither Device ID nor Module ID should be URL encoded in a topic string.
    # See the repo wiki article for details:
    # https://github.com/Azure/azure-iot-sdk-python/wiki/URL-Encoding-(MQTT)
    topic = "devices/" + str(device_id) + "/"
    if module_id:
        topic = topic + "modules/" + str(module_id) + "/"
    return topic


def build_twin_response_subscribe_topic(
    device_id: str, module_id: str = None, include_wildcard_suffix: bool = True
) -> str:
    """
    Build a topic string that can be used to subscribe to twin resopnses.  These
    are messages that are sent back from the service when the cilent sends a twin
    "get" operation or a twin "patch reported properties" operation.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if subscribing for a device.
    :param bool include_wildcard_suffix: True to include "#" at the end (for subscribing),
        False to exclude it (for topic matching)

    :return: The topic used when subscribing for twin resoponse messages.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        topic = build_edge_topic_prefix(device_id, module_id) + "twin/res/"
    else:
        topic = "$iothub/twin/res/"
    if include_wildcard_suffix:
        return topic + "#"
    else:
        return topic


def build_twin_patch_desired_subscribe_topic(
    device_id: str, module_id: str, include_wildcard_suffix: bool = True
) -> str:
    """
    Build a topic string that can be used to subscribe to twin desired property
    patches for sepcified device or module.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if subscribing for a device.
    :param bool include_wildcard_suffix: True to include "#" at the end (for subscribing),
        False to exclude it (for topic matching)

    :return: The topic string used to subscribe to twin desired property patches.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        topic = build_edge_topic_prefix(device_id, module_id) + "twin/desired/"
    else:
        topic = "$iothub/twin/PATCH/properties/desired/"
    if include_wildcard_suffix:
        return topic + "#"
    else:
        return topic


def build_twin_patch_reported_publish_topic(
    device_id: str, module_id: str
) -> str:
    """
    Build a topic string that can be used to publish a twin reported property patch.  This is a
    "one time" topic which can only be used once since it contains a unique identifier that is used
    to match request and response messages.

    The payload of the message should be a JSON object containing the twin's reported properties.
    This object should _not_ include the top level `"properties": { "reported": { ` wrapper
    objects that you see when viewing the entire device twin.

    The response to this `patch` operation is returned in a twin response message with a matching
    `request_id` value.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if publishing for a device.


    :return: The topic string used when publishing a reported properties patch to the service.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return (
            build_edge_topic_prefix(device_id, module_id)
            + "twin/reported/?$rid="
            + str(uuid4())
        )
    else:
        return "$iothub/twin/PATCH/properties/reported/?$rid=" + str(uuid4())


def build_twin_get_publish_topic(device_id: str, module_id: str) -> str:
    """
    Build a topic string that can be used to get a device twin from the service.  This is a
    "one time" topic which can only be used once since it contains a unique identifier that is used.

    The payload of this message should be left empty.

    The response to this `get` operation is returned in a twin response message with a matching
    `request_id` value.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if publishing for a device.

    :return: The topic string used publish a twin get operation to the service.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return (
            build_edge_topic_prefix(device_id, module_id)
            + "twin/get/?$rid="
            + str(uuid4())
        )
    else:
        return "$iothub/twin/GET/?$rid=" + str(uuid4())


def build_telemetry_publish_topic(
    device_id: str, module_id: str, message: Message
) -> str:
    """
    Build a topic string that can be used to publish device/module telemetry to the service.  If
    a properties array is provided, those properties are encoded into the topic string.  This topic
    _can_ be reused if publishing for the same device/module with the same properties.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if publishing for a device.

    :return: The topic string used publish device/module telemetry to the service.
    """

    if constants.EDGEHUB_TOPIC_RULES:
        topic = (
            build_edge_topic_prefix(device_id, module_id) + "messages/events/"
        )
    else:
        topic = (
            build_iothub_topic_prefix(device_id, module_id) + "messages/events/"
        )

    if message:
        topic += encode_message_properties_for_topic(message)

    return topic


def build_c2d_subscribe_topic(
    device_id: str, module_id: str, include_wildcard_suffix: bool = True
) -> str:
    """
    Build a topic string that can be used to subscribe to C2D messages for the device or module.

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module.  Set to `None` if subscribing for a device.
    :param bool include_wildcard_suffix: True to include "#" at the end (for subscribing),
        False to exclude it (for topic matching)

    :return: The topic string used subscribe to C2D messages.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        topic = (
            build_edge_topic_prefix(device_id, module_id) + "messages/c2d/post/"
        )
    else:
        topic = (
            build_iothub_topic_prefix(device_id, module_id)
            + "messages/devicebound/"
        )
    if include_wildcard_suffix:
        return topic + "#"
    else:
        return topic


def build_method_request_subscribe_topic(
    device_id: str, module_id: str, include_wildcard_suffix: bool = True
) -> str:
    """
    Build a topic string that can be used to subscribe to method requests

    :param str device_id: The device_id for the device or module.
    :param str module_id: (optional) The module_id for the module. Set to `None` if subscribing for a device.
    :param bool include_wildcard_suffix: True to include "#" at the end (for subscribing),
        False to exclude it (for topic matching)

    :return: The topic string used to subscribe to method requests.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        topic = build_edge_topic_prefix(device_id, module_id) + "methods/post/"
    else:
        topic = "$iothub/methods/POST/"

    if include_wildcard_suffix:
        return topic + "#"
    else:
        return topic


def build_method_response_publish_topic(
    request_topic: str, status_code: str
) -> str:
    """
    Build a topic string that can be used to publish a resopnse to a specific method request.  This
    topic is built based on a specific method request, so it can only be used once, in response to
    that specific request.

    :param str request_topic: The topic from the method request message that is being responded to.
    :param str status code: The result code for the method response.

    :return: The topic string used to return method results to the service.
    """
    request_id = topic_parser.extract_request_id(request_topic)

    if constants.EDGEHUB_TOPIC_RULES:
        device_id = topic_parser.extract_device_id(request_topic)
        module_id = topic_parser.extract_module_id(request_topic)

        return build_edge_topic_prefix(
            device_id, module_id
        ) + "methods/res/{}/?$rid={}".format(
            urllib.parse.quote(str(status_code), safe=""),
            urllib.parse.quote(str(request_id), safe=""),
        )
    else:
        return "$iothub/methods/res/{status}/?$rid={request_id}".format(
            status=urllib.parse.quote(str(status_code), safe=""),
            request_id=urllib.parse.quote(str(request_id), safe=""),
        )


def encode_message_properties_for_topic(message_to_send: Message) -> str:
    """
    uri-encode the system properties of a message as key-value pairs on the topic with defined keys.
    Additionally if the message has user defined properties, the property keys and values shall be
    uri-encoded and appended at the end of the above topic with the following convention:
    '<key>=<value>&<key2>=<value2>&<key3>=<value3>(...)'
    :param message_to_send: The message to send
    :param topic: The topic which has not been encoded yet. For a device it looks like
    "devices/<deviceId>/messages/events/" and for a module it looks like
    "devices/<deviceId>/modules/<moduleId>/messages/events/
    :return: The topic which has been uri-encoded
    """
    topic = ""

    system_properties: List[Tuple[str, str]] = []

    if message_to_send.output_name:
        system_properties.append(("$.on", str(message_to_send.output_name)))
    if message_to_send.message_id:
        system_properties.append(("$.mid", str(message_to_send.message_id)))

    if message_to_send.correlation_id:
        system_properties.append(("$.cid", str(message_to_send.correlation_id)))

    if message_to_send.user_id:
        system_properties.append(("$.uid", str(message_to_send.user_id)))

    if message_to_send.content_type:
        system_properties.append(("$.ct", str(message_to_send.content_type)))

    if message_to_send.content_encoding:
        system_properties.append(
            ("$.ce", str(message_to_send.content_encoding))
        )

    if message_to_send.iothub_interface_id:
        system_properties.append(
            ("$.ifid", str(message_to_send.iothub_interface_id))
        )

    expiry = None
    if isinstance(message_to_send.expiry_time_utc, str):
        expiry = message_to_send.expiry_time_utc
    elif isinstance(message_to_send.expiry_time_utc, datetime):
        expiry = message_to_send.expiry_time_utc.isoformat()

    if expiry:
        system_properties.append(("$.exp", expiry))

    system_properties_encoded = version_compat.urlencode(
        system_properties, quote_via=urllib.parse.quote
    )
    topic += system_properties_encoded

    if (
        message_to_send.custom_properties
        and len(message_to_send.custom_properties) > 0
    ):
        if system_properties and len(system_properties) > 0:
            topic += "&"

        # Convert the custom properties to a sorted list in order to ensure the
        # resulting ordering in the topic string is consistent across versions of Python.
        # Convert to the properties to strings for safety.
        custom_prop_seq = [
            (str(i[0]), str(i[1]))
            for i in list(message_to_send.custom_properties.items())
        ]
        custom_prop_seq.sort()

        # Validate that string conversion has not created duplicate keys
        keys = [i[0] for i in custom_prop_seq]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys in custom properties!")

        user_properties_encoded = version_compat.urlencode(
            custom_prop_seq, quote_via=urllib.parse.quote
        )
        topic += user_properties_encoded

    return topic
