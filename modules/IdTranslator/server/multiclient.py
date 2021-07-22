from azure.iot.device import Message, MethodRequest, MethodResponse
from azure.iot.device.aio import IoTHubDeviceClient
from os import environ
from uuid import uuid4
import json
from functools import partial
from asyncio import iscoroutinefunction


def log(msg):
    print('[TRANSLATOR] - {}'.format(msg))


def async_partial(f, *args):
    async def f2(*args2):
        result = f(*args, *args2)
        if iscoroutinefunction(f):
            result = await result
        return result

    return f2


class Device():
    def __init__(self, id: str, client: IoTHubDeviceClient, msg_cb):
        self._id = id
        self._client = client
        self._msg_cb = msg_cb

    async def connect(self):
        await self._client.connect()

    @property
    def client(self):
        return self._client

    @property
    def callback(self):
        return self._msg_cb


class MultiClient():

    def __init__(self):
        self._clients = {}
        self._terminate = False

    @property
    def terminate(self):
        return self._terminate

    def connect(self):
        # no-op for multiclient
        pass

    async def register_client(self, client_id, options, msg_cb):
        log(environ['IOTEDGE_IOTHUBHOSTNAME'])
        client_key = None
        if 'primary_key' in options:
            client_key = options['primary_key']
        c_str = 'HostName={};DeviceId={};SharedAccessKey={}'.format(environ['IOTEDGE_IOTHUBHOSTNAME'], client_id, client_key)
        log('{} connection string: {}'.format(client_id, c_str))
        device_client = IoTHubDeviceClient.create_from_connection_string(c_str)
        bound_desired = async_partial(self._twin_patch_handler, client_id)
        bound_cmd = async_partial(self._cmd_handler, client_id)
        device_client.on_twin_desired_properties_patch_received = bound_desired
        device_client.on_method_request_received = bound_cmd

        # if client_id in self._clients:
        #     # disconnect first and remove device
        #     await self._clients[client_id].client.disconnect()
        #     del self._clients[client_id]
        self._clients[client_id] = Device(client_id, device_client, msg_cb)
        await self._clients[client_id].connect()
        log('Client "{}" connected!'.format(client_id))

    async def send_telemetry(self, client_id: str, payload, properties=None):
        msg = Message(json.dumps(payload))
        msg.message_id = uuid4()
        msg.correlation_id = 'correlation-{}'.format(client_id)
        if properties is not None:
            msg.custom_properties = properties
        msg.content_encoding = 'utf-8'
        msg.content_type = 'application/json'
        await self._clients[client_id].client.send_message(msg)
        # log('Sent telemetry for {}'.format(client_id))

    async def get_twin(self, client_id: str):
        twin = await self._clients[client_id].client.get_twin()
        log('Fetched twin for {}'.format(client_id))
        res = await self._clients[client_id].callback('twin', twin)

    async def send_property(self, client_id: str, payload):
        await self._clients[client_id].client.patch_twin_reported_properties(payload)
        log('Sent properties for {}'.format(client_id))

    async def _twin_patch_handler(self, client_id, patch):
        res = await self._clients[client_id].callback('property_change', patch)
        # report property

    async def _cmd_handler(self, client_id, command: MethodRequest):
        log('Received command {} for client {}'.format(command.name, client_id))
        res = await self._clients[client_id].callback('command', {'name': command.name, 'payload': command.payload})
        method_response = MethodResponse.create_from_method_request(command, 200, {"result": True, "data": "n/a"})
        await self._clients[client_id].client.send_method_response(method_response)
