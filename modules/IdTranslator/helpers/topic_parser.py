# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
from typing import Dict, List, Union
import six.moves.urllib as urllib
from . import constants


def _verify_topic(
    topic: str, subtopics: Union[str, List[str]] = None, feature: str = None
) -> None:
    """
    Helper function to verify that a topic is for iothub and is targeted for a specific feature.

    :param str topic: Topic string to test.
    :param Union[str, List[str]] subtopics: (optional) Subtopic or list of subtopics which must be in the topic string.
    :param str feature: (optional) Name of feature that these subtopics belong in.  Used for formatting `ValueError` message.

    :raises: `ValueError` if the topic is not targeted to iothub or to the specific feature of iothub.

    :returns: None
    """
    if constants.EDGEHUB_TOPIC_RULES:
        if not topic.startswith("$iothub"):
            raise ValueError("Topic is not iothub topic")
    else:
        if not topic.startswith("$iothub") and not topic.startswith("devices/"):
            raise ValueError("Topic is not iothub topic")

    if subtopics:
        if isinstance(subtopics, str):
            subtopics = [subtopics]
        for subtopic in subtopics:
            if subtopic in topic:
                return
        if feature:
            raise ValueError("Topic is not for {}".format(feature))
        else:
            raise ValueError("topic is not formatted correctly")


def extract_request_id(topic: str) -> str:
    """
    Extract the request_id from a twin or method topic.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the topic is not targeted to iothub or to a feature of iothub that uses a request_id property.

    :returns: The extracted request_id value.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        _verify_topic(
            topic,
            [
                "/twin/reported/",
                "/twin/get/",
                "/twin/res/",
                "/methods/post/",
                "/methods/res/",
            ],
            "twin or methods",
        )
    else:
        _verify_topic(
            topic,
            [
                "/twin/PATCH/properties/reported/",
                "/twin/res/",
                "/twin/GET/",
                "/methods/POST/",
                "/methods/res",
            ],
            "twin or methods",
        )
    return extract_properties(topic)["rid"]


def extract_device_id(topic: str) -> str:
    """
    Extract the device_id for a topic that is used for an iothub feature.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the topic is not targeted to iothub.

    :returns: The extracted device_id value.
    """
    _verify_topic(topic)
    prefix = topic.split("?")[0]
    segments = prefix.split("/")
    if constants.EDGEHUB_TOPIC_RULES:
        return segments[1]
    else:
        if topic.startswith("devices"):
            return segments[1]
        else:
            raise ValueError(
                "Can't parse device_id out of topic that doesn't contain it."
            )


def extract_module_id(topic: str) -> str:
    """
    Extract the module_id for a topic that is used for an iothub feature.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the topic is not targeted to iothub.

    :returns: The extracted module_id value.  `None` if the topic is for a device and not a module.
    """
    _verify_topic(topic)
    prefix = topic.split("?")[0]
    segments = prefix.split("/")
    if constants.EDGEHUB_TOPIC_RULES:
        module_id = segments[1]
        if module_id in ["messages", "twin", "methods"]:
            return None
        else:
            return module_id
    else:
        if segments[2] == "modules":
            return segments[3]
        else:
            return None


def extract_method_name(topic: str) -> str:
    """
    Extract the method name for a topic that is used for iothub methods.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the topic is not targeted to iothub, is not targeted to a method, or does not contain a method name

    :returns: The extracted method_name value.
    """
    if constants.EDGEHUB_TOPIC_RULES:
        _verify_topic(topic, "/methods/post/", "methods")
        post_segment = "post"
    else:
        _verify_topic(topic, "/methods/POST/", "methods")
        post_segment = "POST"
    segments = topic.split("/")
    for i in range(len(segments)):
        if segments[i] == "methods" and segments[i + 1] == post_segment:
            return segments[i + 2]
    raise ValueError(
        "Topic string is not a method call or does not contain a method name"
    )


def extract_status_code(topic: str) -> str:
    """
    Extract the status code for a topic that is used to return a twin or methods response.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the topic is not targeted to iothub, is not targeted to a feature with a status code, or does not contain a status code.

    :returns: The extracted status_code value
    """
    _verify_topic(
        topic, ["/methods/res/", "/twin/res"], "methods or twin response"
    )
    segments = topic.split("/")
    for i in range(len(segments)):
        if segments[i] == "res":
            return segments[i + 1]
    raise ValueError("Topic string does not contain a result value")


def extract_twin_version(topic: str) -> str:
    if constants.EDGEHUB_TOPIC_RULES:
        _verify_topic(
            topic, ["/twin/reported/"], "twin reported property patch"
        )
    else:
        _verify_topic(
            topic,
            ["/twin/PATCH/properties/reported/"],
            "twin reported property patch",
        )
    return extract_properties(topic)["version"]


def extract_properties(topic: str) -> Dict[str, str]:
    """
    Return a dictionary of properties from a topic string

    :param str topic: Full topic string to extract properties from

    :returns: dictionary with topic names and values
    """
    properties = topic.split("?")[1]
    d = {}
    kv_pairs = properties.split("&")

    for entry in kv_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote(pair[0]).lstrip("$")
        value = urllib.parse.unquote(pair[1])
        d[key] = value

    return d


def extract_input_name(topic: str) -> str:
    """
    Extract the input name out of a topic string.

    :param str topic: The topic to extract the value from

    :raises: `ValueError` if the value could not be extracted from the string.

    :returns: The extracted value
    """

    _verify_topic(topic, "/inputs/", "Edge module input")

    segments = topic.split("/")
    for i in range(len(segments)):
        if segments[i] == "inputs":
            return segments[i + 1]

    raise ValueError(
        "Topic string is not an input message or does not contain an input name"
    )
