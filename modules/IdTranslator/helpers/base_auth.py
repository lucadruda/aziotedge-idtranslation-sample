# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import ssl
import abc
import threading
import time
import logging
from typing import Callable
from . import sas_token, constants

logger = logging.getLogger(__name__)

sas_token_renewed_handler = Callable[[], None]

# TODO: what about websockets?  Does port belong here?  Transport?  if not here, where?


def format_sas_uri(hostname: str, device_id: str, module_id: str) -> str:
    """
    Return the sas uri used to make a sas token for the given device or module.

    :param str hostname: name of the host that is being authorized with.  In the case of
        a transparent gateway, this is the name of the destination host, and NOT the name
        of the gateway.
    :param str device_id: device_id for the device or module which is being authorized.
    :param str module_id: module_id for the module being authorized.  `None` if a device is being
        authorized.

    :return: The URI which gets signed to create the SAS token.
    """

    if module_id:
        return "{}/devices/{}/modules/{}".format(hostname, device_id, module_id)
    else:
        return "{}/devices/{}".format(hostname, device_id)


class AuthorizationBase(abc.ABC):
    """
    Base object for all authorization and authentication mechanisms, including symmetric-key
    and certificate-based auth.
    """

    def __init__(self) -> None:
        self.hostname: str = None
        self.device_id: str = None
        self.module_id: str = None
        self.port: int = 8883
        self.api_version: str = constants.IOTHUB_API_VERSION
        self.gateway_host_name: str = None

    @property
    @abc.abstractmethod
    def password(self) -> str:
        pass

    @property
    def username(self) -> str:
        """
        Value to be sent in the MQTT `username` field.
        """
        # TODO: add product_info stuff
        if self.module_id:
            return "{}/{}/{}/?api-version={}".format(
                self.hostname, self.device_id, self.module_id, self.api_version
            )
        else:
            return "{}/{}/?api-version={}".format(
                self.hostname, self.device_id, self.api_version
            )

    @property
    def client_id(self) -> str:
        """
        Value to be sent in the MQTT `client_id` field.
        """
        if self.module_id:
            return "{}/{}".format(self.device_id, self.module_id)
        else:
            return self.device_id


class RenewableTokenAuthorizationBase(AuthorizationBase):
    """
    Base class for authentication/authorization which uses a SAS token
    which needs to be refreshed on some periodic interval.  This base class does not
    specify _how_ the token gets refreshed, but it does control the interval that
    the token is valid and how frequently it needs to be refreshed.
    """

    def __init__(self) -> None:
        super(RenewableTokenAuthorizationBase, self).__init__()

        self.server_verification_cert: str = None
        self.sas_token: sas_token.RenewableSasToken = None
        self.sas_token_renewal_timer: threading.Timer = None
        self.on_sas_token_renewed: sas_token_renewed_handler = None

    @property
    def password(self) -> str:
        """
        Value to be sent in the MQTT `password` field.
        """
        return str(self.sas_token)

    @property
    def sas_uri(self) -> str:
        """
        The URI which is being signed to create the SAS token
        """
        return format_sas_uri(self.hostname, self.device_id, self.module_id)

    @property
    def sas_token_expiry_time(self) -> int:
        """
        The Unix epoch time when the SAS token expires.
        """
        return self.sas_token.expiry_time

    @property
    def sas_token_renewal_time(self) -> int:
        """
        The Unix epoch time when the SAS token should be renewed.  This is typically
        some amount of time before the token expires.  That amount of time is known
        as the "token renewal margin"
        """
        return (
            self.sas_token.expiry_time - constants.DEFAULT_TOKEN_RENEWAL_MARGIN
        )

    @property
    def sas_token_ready_to_renew(self) -> bool:
        """
        True if the current token is "ready to renew", meaning the current time is
        after the token's renewal time.
        """
        return time.time() > self.sas_token_renewal_time

    @property
    def seconds_until_sas_token_renewal(self) -> int:
        """
        Number of seconds before the current SAS token needs to be removed.
        """
        return max(0, self.sas_token_renewal_time - int(time.time()))

    def cancel_sas_token_renewal_timer(self) -> None:
        """
        Cancel the running timer which is set to fire when the current SAS token
        needs to be renewed.
        """
        if self.sas_token_renewal_timer:
            self.sas_token_renewal_timer.cancel()
            self.sas_token_renewal_timer = None

    def set_sas_token_renewal_timer(
        self, on_sas_token_renewed: sas_token_renewed_handler = None
    ) -> None:
        """
        Set a timer which renews the current SAS token before it expires and calls
        the supplied handler after the renewal is complete.  The supplied handler
        is responsible for re-authorizing using the new SAS token and setting up a new
        timer by calling `set_sas_token_renewal_timer` again.

        :param function on_sas_token_renewed: Handler function which gets called after
            the token is renewed.  This function is responsible for calling
            `set_sas_token_renewal_timer` in order to schedule subsequent renewals.
        """

        # If there is an old renewal timer, cancel it
        self.cancel_sas_token_renewal_timer()
        self.on_sas_token_renewed = on_sas_token_renewed

        # Set a new timer.
        seconds_until_renewal = self.seconds_until_sas_token_renewal
        self.sas_token_renewal_timer = threading.Timer(
            seconds_until_renewal, self.renew_sas_token
        )
        self.sas_token_renewal_timer.daemon = True
        self.sas_token_renewal_timer.start()

        logger.info(
            "SAS token renewal timer set for {} seconds in the future, at approximately {}".format(
                seconds_until_renewal, self.sas_token_expiry_time
            )
        )

    def renew_sas_token(self) -> None:
        """
        Renew authorization. This  causes a new password string to be generated and the
            `on_sas_token_renewed` function to be called.
        """
        logger.info("Renewing sas token and reconnecting")

        # Cancel any timers that might be running.
        self.cancel_sas_token_renewal_timer()

        # Calculate the new token value
        self.sas_token.refresh()

        # notify
        if self.on_sas_token_renewed:
            self.on_sas_token_renewed()

    def create_tls_context(self) -> ssl.SSLContext:
        """
        Create an SSLContext object based on this object.

        :returns: SSLContext object which can be used to secure the TLS connection.
        """
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
        if self.server_verification_cert:
            ssl_context.load_verify_locations(
                cadata=self.server_verification_cert
            )
        else:
            ssl_context.load_default_certs()

        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        return ssl_context
