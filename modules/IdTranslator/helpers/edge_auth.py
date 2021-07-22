# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import os
from . import base_auth, edge_workload_api, sas_token
from typing import Any


class EdgeAuth(base_auth.RenewableTokenAuthorizationBase):
    def __init__(self) -> None:
        super(EdgeAuth, self).__init__()

        self.hostname: str = os.environ["IOTEDGE_IOTHUBHOSTNAME"]
        self.device_id: str = os.environ["IOTEDGE_DEVICEID"]
        self.module_id: str = os.environ["IOTEDGE_MODULEID"]
        self.module_generation_id: str = os.environ[
            "IOTEDGE_MODULEGENERATIONID"
        ]
        self.workload_uri: str = os.environ["IOTEDGE_WORKLOADURI"]
        self.api_version: str = os.environ["IOTEDGE_APIVERSION"]

        self.workload_api = edge_workload_api.EdgeWorkloadApi(
            module_id=self.module_id,
            generation_id=self.module_generation_id,
            workload_uri=self.workload_uri,
            api_version=self.api_version,
        )

    @classmethod
    def create_from_environment(cls) -> Any:
        """
        create a new auth object from the Edge module's environment.

        :returns: MqttEdgeAuth object created by this function.
        """
        obj = EdgeAuth()
        obj._initialize()
        return obj

    def _initialize(self) -> None:
        """
        Helper function to initialize a newly created auth object.
        """
        self.server_verification_cert = self.workload_api.get_certificate()

        self.sas_token = sas_token.RenewableSasToken(
            uri=self.sas_uri, signing_function=self.workload_api.sign
        )

        self.sas_token.refresh()
