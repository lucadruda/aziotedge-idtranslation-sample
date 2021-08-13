import asyncio
import json
from sys import argv
from random import randint


HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 64132        # The port used by the server

class Client():

    def __init__(self, id, key):
        self._id = id
        self._key = key
        self.terminate = False
        self._on_cmd = None
        self._on_prop = None
        self._connected = False

    @property
    def connected(self):
        return self._connected

    async def _handle_message(self):
        print('Setup message handler')
        msg = None
        while msg != 'quit':
            msg = (await self._reader.readline()).decode('utf8')
            print('Message: {}'.format(msg))
            if not msg:
                break
            payload = json.loads(msg)
            if payload['type'] == 'connected':
                self._connected = True
            elif payload['type'] == 'twin_res':
                self._twin = payload['data']
                print('Device twin: {}'.format(self._twin))
            elif payload['type'] == 'prop_changed':
                print('Property changed: {}'.format(payload['data']))
                if self._on_prop is not None:
                    if asyncio.iscoroutinefunction(self._on_prop):
                        await self._on_prop(payload['data'])
                    else:
                        self._on_prop(payload['data'])
            elif payload['type'] == 'command':
                print('Command received: {}'.format(payload['data']))
                if self._on_cmd is not None:
                    if asyncio.iscoroutinefunction(self._on_cmd):
                        await self._on_cmd(payload['data'])
                    else:
                        self._on_cmd(payload['data'])
            else:
                print('Unknown message type "{}":{}'.format(payload.type, payload['data']))

    async def start(self):
        self._reader, self._writer = await asyncio.open_connection(HOST, PORT)
        self._msg_handler = asyncio.create_task(self._handle_message())
        print('Starting client {}'.format(self._id))
        await self.connect()

    async def stop(self):
        if hasattr(self, '_reader') and hasattr(self, '_writer'):
            self._writer.close()
            self._reader.close()
            await self._reader.wait_closed()
            await self._writer.wait_closed()

    async def connect(self):
        self._writer.write(json.dumps({'type': 'connect', 'id': self._id, 'data': {'custom': True}}).encode() + b'\n')
        await self._writer.drain()

    async def send_telemetry(self, message):
        payload = json.dumps({'type': 'telemetry', 'id': self._id, 'data': message})
        print('Sending telemetry {}'.format(payload))
        self._writer.write(payload.encode() + b'\n')
        await self._writer.drain()

    async def send_property(self, message):
        self._writer.write(json.dumps({'type': 'property', 'id': self._id, 'data': message}).encode() + b'\n')
        await self._writer.drain()

    async def get_twin(self):
        self._writer.write(json.dumps({'type': 'twin_req', 'id': self._id}).encode() + b'\n')
        await self._writer.drain()
        print("Waiting for twin")

    @property
    def on_command(self, fn):
        self._on_cmd = fn

    @property
    def on_properties(self, fn):
        self._on_prop = fn


async def main():
    client = Client(argv[1], argv[2])
    await client.start()
    await client.get_twin()
    # await client.send_property({'fanSpeed': 10})
    while not client.terminate:
        await client.send_telemetry({'temperature': randint(10, 40)})
        await asyncio.sleep(7.0)

asyncio.run(main())
