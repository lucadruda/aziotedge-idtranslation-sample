from azure.iot.device.aio import ProvisioningDeviceClient
from base64 import b64decode, b64encode
from hmac import HMAC
from hashlib import sha256

DPS_ENDPOINT = 'global.azure-devices-provisioning.net'

class ProvisioningManager():

    def __init__(self, scope_id, group_key):
        self._group_key = group_key
        self._scope_id = scope_id

    async def provision_device(self, device_id, model_id=None, gateway_id=None):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=DPS_ENDPOINT,
            registration_id=device_id,
            id_scope=self._scope_id,
            symmetric_key=compute_derived_symmetric_key(
                self._group_key, device_id),
        )

        provisioning_device_client.provisioning_payload = {}
        if model_id is not None:
            provisioning_device_client.provisioning_payload["iotcModelId"] = model_id
        if gateway_id is not None:
            provisioning_device_client.provisioning_payload["iotcGateway"] = {
                "iotcGatewayId": gateway_id}
        registration_result = await provisioning_device_client.register()

        if registration_result.status == "assigned":
            return registration_result.registration_state.assigned_hub
        else:
            return None


def compute_derived_symmetric_key(secret, reg_id):
    secret = b64decode(secret)
    return b64encode(
        HMAC(
            secret, msg=reg_id.encode("utf8"), digestmod=sha256
        ).digest()
    ).decode("utf-8")
