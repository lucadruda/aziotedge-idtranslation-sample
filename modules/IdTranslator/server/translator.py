from helpers import EdgeAuth
from .provision import ProvisioningManager
from paho.mqtt import client as mqtt
import asyncio
from re import compile
from os import environ
import json
from uuid import uuid4
from random import randint
import toml

twin_res_topic = "$iothub/+/twin/res/#"
twin_module_res_topic = "$iothub/twin/res/#"
desired_prop_topic = "$iothub/{}/twin/desired/#"
command_res_topic = "$iothub/{}/methods/res/#"
twin_topic_compiler = compile("\$iothub\/([\S]+)\/twin\/res")
desired_topic_compiler = compile("\$iothub\/([\S]+)\/twin\/desired")
command_topic_compiler = compile("\$iothub\/([\S]+)\/methods\/res")


def log(msg):
    print("[BROKER_TRANSLATOR] - {}".format(msg))


class Translator:
    def __init__(self):
        # Create an auth object which can help us get the credentials we need in order to connect
        self.auth = EdgeAuth.create_from_environment()
        self.terminate = False
        self._initialized = False
        self.connected = False
        self._running_loop = asyncio.get_running_loop()
        self.auth.set_sas_token_renewal_timer(self.handle_sas_token_renewed)
        log("Client Id: {}".format(self.auth.client_id))
        self.edge_id = self.auth.device_id
        log("Edge Id: {}".format(self.edge_id))

        # Create an MQTT client object, passing in the credentials we get from the auth object
        self.mqtt_client = mqtt.Client(self.auth.client_id)
        self.mqtt_client.enable_logger()
        log(
            'Username: "{}", Password: "{}"'.format(
                self.auth.username, self.auth.password
            )
        )
        self.mqtt_client.username_pw_set(self.auth.username, self.auth.password)
        # In this sample, we use the TLS context that the auth object builds for
        # us.  We could also build our own from the contents of the auth object
        # QUESTION: IS THIS THE SAME AS 1883 vs 8883?
        self.mqtt_client.tls_set_context(self.auth.create_tls_context())
        self._clients = {}
        self._config = toml.load("config.toml")

    def handle_on_connect(
        self, mqtt_client: mqtt.Client, userdata, flags, rc: int
    ) -> None:
        # Set an event when we're connected so our main thread can continue
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self.connected = True
            log("Module connected to hub!")
            self._initialized = False
            # subscribe to twin
            # self.mqtt_client.subscribe(twin_res_topic, qos=1)
            # self.mqtt_client.message_callback_add(twin_res_topic, self._on_twin_response)

            # fallback for other topics
            self.mqtt_client.on_message = self._handle_message

            # request module twin. subscribe to own twin
            log("Fetching module twin")
            req_id = str(uuid4())
            twin_topic = "$iothub/twin/GET/?$rid={}".format(req_id)
            self.mqtt_client.subscribe(
                "$iothub/twin/res/200/?$rid={}".format(req_id), qos=1
            )
            self.mqtt_client.subscribe("$iothub/twin/desired/#", qos=1)
            self.mqtt_client.subscribe("$iothub/#", qos=1)
            self.mqtt_client.subscribe("$edgehub/#", qos=1)
            self.mqtt_client.subscribe("$edgehub/twin/desired/#", qos=1)
            self.mqtt_client.message_callback_add(
                twin_module_res_topic, self._on_module_twin_response
            )
            self.mqtt_client.publish(twin_topic, qos=1)

        elif rc == mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:
            # actually, server is available, but username is probably wrong
            pass
        elif rc == mqtt.MQTT_ERR_NO_CONN:
            # client_id or password is wrong.  Check the sas token expired.  That's all we can do
            if self.auth.sas_token_ready_to_renew:
                self.auth.renew_sas_token()

    def handle_sas_token_renewed(self) -> None:
        log("handle_sas_token_renewed")

        # Set the new MQTT auth parameters
        self.mqtt_client.username_pw_set(self.auth.username, self.auth.password)

        # Reconnect the client.  (This actually just disconnects it and lets Paho's automatic
        # reconnect connect again.)
        self.mqtt_client.reconnect()

        self.auth.set_sas_token_renewal_timer(self.handle_sas_token_renewed)

    def connect(self):
        self.mqtt_client.on_connect = self.handle_on_connect
        self.mqtt_client.loop_start()
        gateway_hostname = environ["IOTEDGE_GATEWAYHOSTNAME"]
        log("Gateway hostname: {}".format(gateway_hostname))
        self.mqtt_client.connect(gateway_hostname, 8883)

    async def send_telemetry(self, device_id, data):
        telemetry_topic = "$iothub/" + device_id + "/messages/events/"
        log("Sending telemetry for {}".format(device_id))
        self.mqtt_client.publish(telemetry_topic, json.dumps(data).encode(), qos=1)

    async def send_property(self, device_id, data):
        property_topic = "$iothub/" + device_id + "/twin/reported/"
        log("Sending property for {}".format(device_id))
        self.mqtt_client.publish(property_topic, json.dumps(data).encode(), qos=1)

    async def register_client(self, client_id, options, msg_cb):
        if not self._initialized:
            log("Not initialized")
            return  # no-op. we're not ready yet
        log('Registering device "{}"'.format(client_id))
        if client_id not in self._clients:
            self._clients[client_id] = msg_cb
            log("Provisioning device {}".format(client_id))
            hub = await self._provisioning_manager.provision_device(client_id)
            log("Device provisioned to {}".format(hub))
            log("Device {} registered to the broker!".format(client_id))

            log("Subscribing to twin...")
            # subscribe to device twin
            self.mqtt_client.subscribe("$iothub/{}/twin/res/#".format(client_id), qos=1)
            self.mqtt_client.subscribe(
                "$edgehub/{}/twin/res/#".format(client_id), qos=1
            )
            # subscribe to desired property change
            log("Subscribing to property changes...")
            self.mqtt_client.subscribe(
                "$iothub/{}/twin/desired/#".format(client_id), qos=1
            )
            self.mqtt_client.subscribe(
                "$edgehub/{}/twin/desired/#".format(client_id), qos=1
            )
            self.mqtt_client.subscribe(
                "$iothub/{}/twin/PATCH/properties/desired/#".format(client_id), qos=1
            )
            self.mqtt_client.subscribe(
                "$eventhub/{}/twin/PATCH/properties/desired/#".format(client_id), qos=1
            )
            self.mqtt_client.message_callback_add(
                "$iothub/{}/twin/desired/#".format(client_id), self._on_prop_change
            )
            self.mqtt_client.message_callback_add(
                "$edgehub/{}/twin/desired/#".format(client_id), self._on_prop_change
            )

            log("Subscribing to commands...")
            # subscribe to command
            self.mqtt_client.subscribe(command_res_topic.format(client_id), qos=1)
            self.mqtt_client.message_callback_add(
                command_res_topic.format(client_id), self._on_command
            )

    def _handle_message(self, client, userdata, msg: mqtt.MQTTMessage):
        log('Received topic "{}": "{}"'.format(msg.topic, msg.payload))

    async def get_twin(self, device_id: str):
        req_id = str(uuid4())
        twin_topic = "$iothub/{}/twin/get/?$rid={}".format(device_id, req_id)
        self.mqtt_client.message_callback_add(
            "$iothub/{}/twin/res/#".format(device_id), self._on_twin_response
        )
        log("Asking twin for device {}. {}".format(device_id, twin_topic))
        self.mqtt_client.publish(twin_topic, qos=1)

    def _on_module_twin_response(self, client, userdata, msg: mqtt.MQTTMessage):
        log("Received module twin. Initializing broker...")
        twin = json.loads(msg.payload)
        self._API_KEY = twin["desired"]["ApiKey"]
        self._ENROLLMENT_KEY = twin["desired"]["EnrollmentGroupKey"]
        self._DOWNSTREAM_MODEL_ID = twin["desired"]["DownstreamModelId"]
        self._provisioning_manager = ProvisioningManager(
            self._config["provisioning"]["id_scope"],
            self._ENROLLMENT_KEY,
            gateway_id=self.edge_id,
            downstream_model_id=self._DOWNSTREAM_MODEL_ID,
        )
        self._initialized = True
        log("Broker initialized.")

    def _on_twin_response(self, client, userdata, msg: mqtt.MQTTMessage):
        match = twin_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            log(
                'Received twin for "{}":{}'.format(
                    device_id, msg.payload.decode("utf-8")
                )
            )
            self._running_loop.create_task(
                self.return_twin(device_id, msg.payload.decode("utf-8"))
            )

    async def return_twin(self, device_id, payload):
        await self._clients[device_id]("twin", payload)

    def _on_prop_change(self, client, userdata, msg: mqtt.MQTTMessage):
        log("Received prop change")
        match = desired_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            self._clients[device_id]("property_change", msg.payload)

    def _on_command(self, client, userdata, msg: mqtt.MQTTMessage):
        match = command_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            self._clients[device_id]("command", msg.payload)
