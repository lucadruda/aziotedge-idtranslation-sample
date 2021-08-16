# Azure IoT Edge Identity Translation Sample for IoT Central

This repo aims to provide sample Azure IoT Edge modules to be used when implementing the [Identity Translation Pattern](https://docs.microsoft.com/en-us/azure/iot-edge/iot-edge-as-gateway?view=iotedge-2020-11#identity-translation) for IoT Edge with Azure IoT Central.

> Note: _Part of this repo uses versions of Azure product in preview thus might not be available in all regions or environments_

# Contents
The _modules_ folder contains the following modules written in Python:
- [__Provisioning Module__](./modules/ProvisioningModule): The module is responsible for provisioning downstream device through Azure DPS ([Device Provisioning Service](https://docs.microsoft.com/en-us/azure/iot-dps/)).
Downstream devices or edge modules asks to provision a device by sending a specific request to this module.
- [__Identity Translator__](./modules/IdTranslator): The module is responsible to act on behalf of downstream devices. It sends telemetry and receive properties and commands for devices connected to it. By leveraging new features in IoT Edge v1.2, it can use a multiplexed connection to IoT Hub without creating underlying device clients.
The protocol translation work is simulated by a socket server communicating with the translation core.
## Instructions

The quickest way to run the sample solution is to use [Visual Studio Code](https://code.visualstudio.com/) and the [Azure IoT Tools](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.azure-iot-tools) extension.
You may also need Docker to build and push container images.


### Prepare deployment manifest
Configuration of the edge device is done through deployment manifests.
This repo contains some manifest templates (_deployment.*.template.json) that can be edited, cloned and used to generate final deployment manifests by right-clicking on them in vscode and selecting "Generate IoT Edge deployment manifest".
Resulting templates will be saved in the "_config_" subfolder ready to be uploaded with in the device template of IoT Central.

### Build and publish container images

The Azure IoT Tools extension provides simple commands to build and publish container on the preferred container registry.
If you need more control and prefer manual steps, modules can be easily built by running the following from each module folder:

```sh
docker build -t <registry><account>/<module-name>:<arch>.<config> -f Dockerfile.<arch>.<config>
# docker build -t <acrname>.azurecr.io:amd64.debug -f Dockerfile.amd64.debug

docker push <registry><account>/<module-name>:<arch>.<config>
# docker push <acrname>.azurecr.io:amd64.debug
```

### Running sample clients

Once edge device gets configured, run the downstream client in _downstream/client.py_ folder from the same machine/VM.
Best to create a python virtualenv and run

```bash
python -m pip install -r requirements.txt
```

before launch it.

```bash
python ./client.py "<DEVICE_ID>"
```
If you like to run your clients from outside the Edge machine, change the "HOST" variable at line [7](./downstream/client.py#L7) of client.py