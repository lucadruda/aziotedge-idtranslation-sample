# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for working with Shared Access Signature (SAS) Tokens"""

import time
import six.moves.urllib as urllib
from typing import Dict, Callable
from . import constants

SigningFunction = Callable[[str], str]


class RenewableSasToken(object):
    """Renewable Shared Access Signature Token used to authenticate a request.

    This token is 'renewable', which means that it can be updated when necessary to
    prevent expiry, by using the .refresh() method.

    Data Attributes:
    expiry_time (int): Time that token will expire (in UTC, since epoch)
    ttl (int): Time to live for the token, in seconds
    """

    _auth_rule_token_format = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}&skn={keyname}"
    _simple_token_format = (
        "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}"
    )

    def __init__(
        self,
        uri: str,
        signing_function: SigningFunction,
        key_name: str = None,
        ttl: int = constants.DEFAULT_TOKEN_RENEWAL_INTERVAL,
    ):
        """
        :param str uri: URI of the resouce to be accessed
        :param function signing_function: The signing function to use in the SasToken
        :param str key_name: Symmetric Key Name (optional)
        :param int ttl: Time to live for the token, in seconds (default 3600)

        :raises: SasTokenError if an error occurs building a SasToken
        """
        self._uri = uri
        self._signing_function = signing_function
        self._key_name = key_name
        self._expiry_time: int = (
            None
        )  # This will be overwritten by the .refresh() call below
        self._token: str = (
            None
        )  # This will be overwritten by the .refresh() call below

        self.ttl = ttl
        self.refresh()

    def __str__(self) -> str:
        return self._token

    def refresh(self) -> None:
        """
        Refresh the SasToken lifespan, giving it a new expiry time, and generating a new token.
        """
        self._expiry_time = int(time.time() + self.ttl)
        self._token = self._build_token()

    def _build_token(self) -> str:
        """Buid SasToken representation

        :returns: String representation of the token
        """
        url_encoded_uri = urllib.parse.quote(self._uri, safe="")
        message = url_encoded_uri + "\n" + str(self.expiry_time)
        try:
            signature = self._signing_function(message)
        except Exception as e:
            # Because of variant signing mechanisms, we don't know what error might be raised.
            # So we catch all of them.
            raise ValueError("Unable to build SasToken from given values", e)
        url_encoded_signature = urllib.parse.quote(signature, safe="")
        if self._key_name:
            token = self._auth_rule_token_format.format(
                resource=url_encoded_uri,
                signature=url_encoded_signature,
                expiry=str(self.expiry_time),
                keyname=self._key_name,
            )
        else:
            token = self._simple_token_format.format(
                resource=url_encoded_uri,
                signature=url_encoded_signature,
                expiry=str(self.expiry_time),
            )
        return token

    @property
    def expiry_time(self) -> int:
        """Expiry Time is READ ONLY"""
        return self._expiry_time


REQUIRED_SASTOKEN_FIELDS = ["sr", "sig", "se"]
VALID_SASTOKEN_FIELDS = REQUIRED_SASTOKEN_FIELDS + ["skn"]


def get_sastoken_info_from_string(sastoken_string: str) -> Dict[str, str]:
    pieces = sastoken_string.split("SharedAccessSignature ")
    if len(pieces) != 2:
        raise ValueError("Invalid SasToken string: Not a SasToken ")

    # Get sastoken info as dictionary
    try:
        sastoken_info: Dict[str, str] = dict(
            map(str.strip, sub.split("=", 1))  # type: ignore
            for sub in pieces[1].split("&")
        )
    except Exception as e:
        raise ValueError("Invalid SasToken string: Incorrectly formatted", e)

    # Validate that all required fields are present
    if not all(key in sastoken_info for key in REQUIRED_SASTOKEN_FIELDS):
        raise ValueError(
            "Invalid SasToken string: Not all required fields present"
        )

    # Validate that no unexpected fields are present
    if not all(key in VALID_SASTOKEN_FIELDS for key in sastoken_info):
        raise ValueError("Invalid SasToken string: Unexpected fields present")

    return sastoken_info
