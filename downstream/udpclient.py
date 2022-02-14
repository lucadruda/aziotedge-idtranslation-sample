from random import randint
import asyncio
import asyncudp
import json
from sys import argv


HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 64132  # The port used by the server
LOCAL_PORT = randint(45000, 50000)


class Client:
    def __init__(self, id, model=None):
        self._id = id
        self._model_id = model
        self.terminate = False
        self._on_cmd = None
        self._on_prop = None
        self._connected = False

    @property
    def connected(self):
        return self._connected

    async def _handle_message(self):
        print("Setup message handler")
        msg = None
        while msg != "quit":
            data, _ = await self._sender_sock.recvfrom()
            msg = data.decode("utf8")
            print("Message: {}".format(msg))
            if not msg:
                break
            payload = json.loads(msg)
            if payload["type"] == "connected":
                print("connected!")
                self._connected = True
            elif payload["type"] == "twin_res":
                self._twin = payload["data"]
                print("Device twin: {}".format(self._twin))
            elif payload["type"] == "prop_changed":
                print("Property changed: {}".format(payload["data"]))
                if self._on_prop is not None:
                    if asyncio.iscoroutinefunction(self._on_prop):
                        await self._on_prop(payload["data"])
                    else:
                        self._on_prop(payload["data"])
            elif payload["type"] == "command":
                print("Command received: {}".format(payload["data"]))
                if self._on_cmd is not None:
                    if asyncio.iscoroutinefunction(self._on_cmd):
                        await self._on_cmd(payload["data"])
                    else:
                        self._on_cmd(payload["data"])
            else:
                print(
                    'Unknown message type "{}":{}'.format(payload.type, payload["data"])
                )

    async def start(self):
        self._sender_sock = await asyncudp.create_socket(remote_addr=(HOST, PORT))
        # self._sender_sock = await asyncudp.create_socket(
        #     local_addr=("0.0.0.0", LOCAL_PORT)
        # )
        print(
            "Starting client {} with socket at {}".format(
                self._id, self._sender_sock.getsockname()
            )
        )
        await self.connect()

    async def stop(self):
        if hasattr(self, "_sender_sock"):
            self._sender_sock.close()

    async def connect(self):
        self._sender_sock.sendto(
            json.dumps(
                {
                    "type": "connect",
                    "id": self._id,
                    "addr": self._sender_sock.getsockname(),
                    "data": {"modelId": self._model_id}
                    if self._model_id is not None
                    else {},
                }
            ).encode()
            + b"\n"
        )
        asyncio.create_task(self._handle_message())

    async def send_telemetry(self, message):
        payload = json.dumps({"type": "telemetry", "id": self._id, "data": message})
        print("Sending telemetry {}".format(payload))
        self._sender_sock.sendto(payload.encode() + b"\n")

    async def send_property(self, message):
        self._sender_sock.sendto(
            json.dumps({"type": "property", "id": self._id, "data": message}).encode()
            + b"\n"
        )

    async def get_twin(self):
        self._sender_sock.sendto(
            json.dumps({"type": "twin_req", "id": self._id}).encode() + b"\n"
        )
        print("Waiting for twin")

    @property
    def on_command(self, fn):
        self._on_cmd = fn

    @property
    def on_properties(self, fn):
        self._on_prop = fn


async def main():
    client = Client(argv[1], argv[2] if len(argv) > 2 else None)
    await client.start()
    while not client.connected:
        await asyncio.sleep(1)
    await client.get_twin()
    await asyncio.sleep(1)
    await client.send_property({"assetId": "dummy"})
    await asyncio.sleep(1)
    while not client.terminate:
        await client.send_telemetry({"lastReadDate": "custom_date"})
        await asyncio.sleep(7.0)


asyncio.run(main())
