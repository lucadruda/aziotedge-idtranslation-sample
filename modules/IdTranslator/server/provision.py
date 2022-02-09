from azure.iot.device.aio import ProvisioningDeviceClient
from helpers import compute_derived_symmetric_key

DPS_ENDPOINT = "global.azure-devices-provisioning.net"


class ProvisioningManager:
    def __init__(self, scope_id, group_key, gateway_id, downstream_model_id):
        self._group_key = group_key
        self._scope_id = scope_id
        self._gateway_id = gateway_id
        self._downstream_model_id = downstream_model_id

    async def provision_device(self, device_id):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=DPS_ENDPOINT,
            registration_id=device_id,
            id_scope=self._scope_id,
            symmetric_key=compute_derived_symmetric_key(self._group_key, device_id),
        )

        provisioning_device_client.provisioning_payload = {
            "iotcModelId": self._downstream_model_id,
            "iotcGateway": {"iotcGatewayId": self._gateway_id},
        }
        registration_result = await provisioning_device_client.register()

        if registration_result.status == "assigned":
            return registration_result.registration_state.assigned_hub
        else:
            return None