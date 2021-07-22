# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
from typing import Any
from . import (
    base_auth,
    hmac_signing_mechanism,
    sas_token,
    connection_string as cs,
    constants,
)


class SymmetricKeyAuth(base_auth.RenewableTokenAuthorizationBase):
    def __init__(self) -> None:
        super(SymmetricKeyAuth, self).__init__()

    @classmethod
    def create_from_connection_string(cls, connection_string: str) -> Any:
        """
        create a new auth object from a connection string

        :param str connection_string: Connection string to create auth object for
        :param int token_renewal_interval: Number of seconds that SAS tokens created by
            this obhject will be valid.
        :param int token_renewal_margen: Number of seconds to subtract from
            `token_renewal_inteavral` when calculating the `token_expiry` time.

        :returns: MqttEdgeAuth object created by this function.
        """
        obj = SymmetricKeyAuth()
        obj._initialize(connection_string)
        return obj

    def _initialize(self, connection_string: str) -> None:
        """
        Helper function to initialize a newly created auth object.
        """
        conn_str = cs.ConnectionString(connection_string)

        self.hostname = conn_str[cs.HOST_NAME]
        self.device_id = conn_str[cs.DEVICE_ID]
        self.module_id = conn_str.get(cs.MODULE_ID, None)
        self.gateway_host_name = conn_str.get(cs.GATEWAY_HOST_NAME, None)

        shared_access_key = conn_str[cs.SHARED_ACCESS_KEY]

        signing_mechanism = hmac_signing_mechanism.HmacSigningMechanism(
            shared_access_key
        )
        self.sas_token = sas_token.RenewableSasToken(
            uri=self.sas_uri,
            signing_function=signing_mechanism.sign,
            ttl=constants.DEFAULT_TOKEN_RENEWAL_INTERVAL,
        )

        self.sas_token.refresh()
