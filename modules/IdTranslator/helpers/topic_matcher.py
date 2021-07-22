# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
from . import topic_parser, topic_builder, constants


def is_twin_response(topic: str, request_topic: str) -> bool:
    """
    Determine if a received topic string is a response to a previously sent twin request topic

    :param str topic: The topic which was received.
    :param str request_topic: (optional) The twin request which was previously sent.  If `None`, this function will return True if `topic` is a twin response for _any_ request.

    :returns: `True` if `topic` is a twin response.  If `request_topic` is provided, only return `True` if the response matches the request.
    """
    if request_topic:
        request_id = topic_parser.extract_request_id(request_topic)
        if constants.EDGEHUB_TOPIC_RULES:
            device_id = topic_parser.extract_device_id(request_topic)
            module_id = topic_parser.extract_module_id(request_topic)
        else:
            device_id = None
            module_id = None

        return topic.startswith(
            topic_builder.build_twin_response_subscribe_topic(
                device_id, module_id, False
            )
        ) and (topic_parser.extract_request_id(topic) == request_id)
    else:
        if constants.EDGEHUB_TOPIC_RULES:
            return topic.startswith("$iothub/") and "/twin/res/" in topic
        else:
            return topic.startswith("$iothub/twin/res/")


def is_twin_patch_desired(topic: str) -> bool:
    """
    Determine if a topic string is for a twin patch desired properties patch

    :param str topic: The topic to test

    :returns: True if the topic is a twin desired property patch
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return topic.startswith("$iothub/") and "/twin/desired/" in topic
    else:
        return topic.startswith("$iothub/twin/PATCH/properties/desired/")


def is_c2d(topic: str) -> bool:
    """
    Determine if a topic string is for a c2d message.

    :param str topic: The topic to test

    :returns: True if the topic is a c2d message.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return topic.startswith("$iothub/") and "/messages/c2d/post/" in topic
    else:
        return (
            topic.startswith("devices/") and "/messages/devicebound/" in topic
        )


def is_method_request(topic: str, method_name: str = None) -> bool:
    """
    Determine if a topic string is for a method request.

    :param str topic: The topic to test

    :returns: True if the topic is for a method request.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        is_method = topic.startswith("$iothub/") and "/methods/post/" in topic
    else:
        is_method = topic.startswith("$iothub/methods/POST")

    if not method_name:
        return is_method
    else:
        return topic_parser.extract_method_name(topic) == method_name


def sent_to_device(topic: str, device_id: str) -> bool:
    """
    Determine if a topic string was sent to a specific device.

    :param str topic: The topic to test
    :param str device_id: the device_id to test against

    :returns: True if the topic was sent to this specific device.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return topic.startswith(
            topic_builder.build_edge_topic_prefix(device_id, None)
        )
    else:
        if topic.startswith("$iothub"):
            raise ValueError(
                "Cannot determine if topic is sent to device without device_id in topic"
            )
        else:
            return topic.startswith(
                topic_builder.build_iothub_topic_prefix(device_id, None)
            )


def sent_to_module(topic: str, device_id: str, module_id: str) -> bool:
    """
    Determine if a topic string was sent to a specific device.

    :param str topic: The topic to test
    :param str device_id: the device_id to test against
    :param str module_id: the module_id to test against

    :returns: True if the topic was sent to this specific module.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        return topic.startswith(
            topic_builder.build_edge_topic_prefix(device_id, module_id)
        )
    else:
        if topic.startswith("$iothub"):
            raise ValueError(
                "Cannot determine if topic is sent to device without module_id in topic"
            )
        else:
            return topic.startswith(
                topic_builder.build_iothub_topic_prefix(device_id, module_id)
            )
