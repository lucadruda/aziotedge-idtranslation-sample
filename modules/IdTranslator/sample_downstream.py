from downstream.client import Client
from sys import argv
import asyncio
from random import randint



async def main():
    client = Client(argv[1])
    await client.start()
    await client.get_twin()
    await client.send_property({'fanSpeed': 10})
    while not client.terminate:
        await client.send_telemetry({'temperature': randint(10, 40)})
        await asyncio.sleep(3.0)

asyncio.run(main())
