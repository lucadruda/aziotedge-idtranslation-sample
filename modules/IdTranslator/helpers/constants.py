# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

# TODO: document all of these constants

# what rules should we use for building topic strings?
# True = New EdgeHub topic rules.
# False = Old IotHub topic rules.
EDGEHUB_TOPIC_RULES = False

# Defult expiration period, in seconds, of any SAS tokens created by this code
DEFAULT_TOKEN_RENEWAL_INTERVAL = 3600

# Number of seconds before a SAS token expires that this code will create a new SAS token.
DEFAULT_TOKEN_RENEWAL_MARGIN = 300

# API version string for IOTHub APIs
if EDGEHUB_TOPIC_RULES:
    IOTHUB_API_VERSION = "2018-06-30"
else:
    IOTHUB_API_VERSION = "2019-10-01"

# Interface ID for Azure Security Center messages
SECURITY_MESSAGE_INTERFACE_ID = "urn:azureiot:Security:SecurityAgent:1"

# string encoding to use when converting between strings and byte arrays
DEFAULT_STRING_ENCODING = "utf-8"
