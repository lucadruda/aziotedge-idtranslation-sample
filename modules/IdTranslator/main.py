from paho.mqtt import client as mqtt
from server import Translator, Server, MultiClient
import asyncio
import os


async def main():
    trans_type = os.environ.get('ID_TRANSLATOR_TYPE', 'translator')
    print("Starting module.")
    translator = Translator() if trans_type == 'translator' else MultiClient()
    server = Server(translator)
    print("Starting protocol server...")
    asyncio.create_task(server.start())
    print("Starting translator...")
    translator.connect()
    while not translator.terminate:
        await asyncio.sleep(0.5)
    print('Closing...')


asyncio.run(main())
