import socket
import selectors
import asyncio
import signal
import json
from random import randint, choice
import traceback

HOST = '0.0.0.0'
PORT = 64132


def log(msg):
    print('[SERVER] - {}'.format(msg))


class Server():

    def __init__(self, translator):
        self._clients = {}
        self._translator = translator
        self._terminate = False

    async def handle_client(self, reader, writer):
        request = None
        while request != 'quit!':
            try:
                request = (await reader.readline()).decode('utf8')
                log(request)
                if not request:
                    break
                else:
                    payload = json.loads(request)
                    if payload['type'] == 'connect':
                        await self._handle_connect(payload['id'], payload['data'], writer)
                    elif payload['type'] == 'telemetry':
                        await self._handle_telemetry(payload['id'], payload['data'])
                    elif payload['type'] == 'property':
                        await self._handle_property(payload['id'], payload['data'])
                    elif payload['type'] == 'twin_req':
                        await self._translator.get_twin(payload['id'])
                    else:
                        pass
            except Exception as e:
                log('Exception {}. Message:{}'.format(e, request))
                traceback.print_exc()
        writer.close()

    async def start(self):
        self._server = await asyncio.start_server(self.handle_client, HOST, PORT)
        log('Server started on port {}'.format(PORT))
        async with self._server:
            await self._server.serve_forever()

    async def _handle_connect(self, client, options, writer):
        # This callback gets executed every time a C2D message arrives (either direct-method, twin change or offline commands)
        async def msg_cb(cmd_type, payload):
            if cmd_type == 'twin':
                self._clients[client].write(json.dumps({'type': 'twin_res', 'data': payload}).encode() + b'\n')
                await self._clients[client].drain()
            elif cmd_type == 'property_change':
                self._clients[client].write(json.dumps({'type': 'prop_changed', 'data': payload}).encode() + b'\n')
                await self._clients[client].drain()
            elif cmd_type == 'command':
                self._clients[client].write(json.dumps({'type': 'command', 'data': payload}).encode() + b'\n')
                await self._clients[client].drain()
            else:
                self._clients[client].write(json.dumps({'type': 'unknown', 'data': payload}).encode() + b'\n')
                await self._clients[client].drain()

        self._clients[client] = writer
        await self._translator.register_client(client, options, msg_cb)

    async def _handle_telemetry(self, client, data):
        await self._translator.send_telemetry(client, data)
        # log('Received telemetry from "{}". Payload" {}'.format(client, data))

    async def _handle_property(self, client, data):
        log('Received property from "{}". Payload" {}'.format(client, data))
        await self._translator.send_property(client, data)
