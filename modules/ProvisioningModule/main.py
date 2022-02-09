from azure.iot.device.aio import IoTHubModuleClient
import asyncio
from provision import ProvisioningManager
from os import environ
from utils import error, info, debug
import sys

NEW_REGISTRATION_INPUT = "new_reg"
QUERY_REGISTRATION = "query_reg"


async def main():
    info('Starting module...')
    _terminate = False
    try:
        id_scope = environ['ID_SCOPE']
        info('Fetched Id Scope')
    except KeyError:
        debug('Id scope not in env')
        from toml import load as load_toml
        config = load_toml('/app/config.toml')
        id_scope = config['provisioning']['id_scope']

    try:
        debug('Trying to fetch enrollment key from env...')
        enrollment_key = environ['ENROLLMENT_KEY']
        debug('Fetched enrollment key from env')
    except KeyError:
        enrollment_key = None

    module_client = IoTHubModuleClient.create_from_edge_environment()
    await module_client.connect()

    if enrollment_key is None:
        try:
            debug('Trying to fetch enrollment key from module twin')
            twin = await module_client.get_twin()
            enrollment_key = twin['desired']['ENROLLMENT_KEY']
            debug('Fetched enrollment key from module twin')
        except:
            error(
                'No Enrollment key found in either env variables or module twin. Exiting')
            _terminate = True
            sys.exit(1)

    info('Fetched Enrollment key')
    provisioning_manager = ProvisioningManager(id_scope, enrollment_key)

    async def message_handler(message):
        if message.input_name == NEW_REGISTRATION_INPUT:

            debug('Received new registration request for device "{}"'.format(
                message.data['device_id']))
            await provisioning_manager.provision_device(message.data['device_id'], model_id=message.data.get(
                'model_id'), gateway_id=message.data.get('gateway_id'))
        else:
            print("message received on unknown input")

    # set the received data handlers on the client
    module_client.on_message_received = message_handler
    while not _terminate:
        await asyncio.sleep(0.1)


asyncio.run(main())
