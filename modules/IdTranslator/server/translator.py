from helpers import EdgeAuth
from paho.mqtt import client as mqtt
import asyncio
from re import compile
from os import environ
import json
from uuid import uuid4
from random import randint

twin_res_topic = '$iothub/+/twin/res/#'
desired_prop_topic = '$iothub/+/twin/desired/#'
command_res_topic = '$iothub/+/methods/res/#'
twin_topic_compiler = compile('\$iothub\/([\S]+)\/twin\/res')
desired_topic_compiler = compile('\$iothub\/([\S]+)\/twin\/desired')
command_topic_compiler = compile('\$iothub\/([\S]+)\/methods\/res')


def log(msg):
    print('[BROKER_TRANSLATOR] - {}'.format(msg))


class Translator():
    def __init__(self):
       # Create an auth object which can help us get the credentials we need in order to connect
        self.auth = EdgeAuth.create_from_environment()
        self.terminate = False
        self.connected = False
        self.auth.set_sas_token_renewal_timer(self.handle_sas_token_renewed)
        log('Client Id: {}'.format(self.auth.client_id))
        # Create an MQTT client object, passing in the credentials we get from the auth object
        self.mqtt_client = mqtt.Client(self.auth.client_id)
        self.mqtt_client.enable_logger()
        log('Username: "{}", Password: "{}"'.format(self.auth.username, self.auth.password))
        self.mqtt_client.username_pw_set(self.auth.username, self.auth.password)
        # In this sample, we use the TLS context that the auth object builds for
        # us.  We could also build our own from the contents of the auth object
        self.mqtt_client.tls_set_context(self.auth.create_tls_context())  # QUESTION: IS THIS THE SAME AS 1883 vs 8883?
        self._clients = {}

    def handle_on_connect(
        self, mqtt_client: mqtt.Client, userdata, flags, rc: int
    ) -> None:
        # Set an event when we're connected so our main thread can continue
        log(rc)
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self.connected = True
            log('Module connected to hub!')
            # subscribe to twin
            # self.mqtt_client.subscribe(twin_res_topic, qos=1)
            # self.mqtt_client.message_callback_add(twin_res_topic, self._on_twin_response)

            # subscribe to desired property change
            self.mqtt_client.subscribe(desired_prop_topic, qos=1)
            self.mqtt_client.message_callback_add(desired_prop_topic, self._on_prop_change)

            # subscribe to command
            self.mqtt_client.subscribe(command_res_topic, qos=1)
            self.mqtt_client.message_callback_add(command_res_topic, self._on_command)

            # fallback for other topics
            self.mqtt_client.subscribe("$iothub/twin/res/#")
            self.mqtt_client.on_message = self._handle_message
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
        log('Gateway hostname: {}'.format(gateway_hostname))
        self.mqtt_client.connect(gateway_hostname, 8883)

    async def send_telemetry(self, device_id, data):
        telemetry_topic = "$iothub/" + device_id + "/messages/events/"
        log('Sending telemetry for {}'.format(device_id))
        self.mqtt_client.publish(
            telemetry_topic, json.dumps(data).encode(), qos=1)

    async def send_property(self, device_id, data):
        property_topic = "$iothub/" + device_id + "/twin/reported/"
        log('Sending property for {}'.format(device_id))
        self.mqtt_client.publish(
            property_topic, json.dumps(data).encode(), qos=1)

    async def register_client(self, client_id, options, msg_cb):
        log('Registering device "{}"'.format(client_id))
        if client_id not in self._clients:
            self._clients[client_id] = msg_cb
            log('Device {} registered to the broker!'.format(client_id))
            log('Subscribing to $iothub/{}/twin/res/#'.format(client_id))
            # self.mqtt_client.subscribe('$iothub/{}/twin/res/#'.format(client_id), qos=1)
            # self.mqtt_client.message_callback_add('$iothub/{}/twin/res/#'.format(client_id), self._on_twin_response)

    def _handle_message(self, client, userdata, msg: mqtt.MQTTMessage):
        log('Received topic "{}": "{}"'.format(msg.topic, msg.payload))

    async def get_twin(self, device_id: str):
        
        req_id = str(uuid4())
        twin_topic = "$iothub/{}/twin/GET/?$rid={}".format(device_id, req_id)
        self.mqtt_client.subscribe("$iothub/{}/twin/res/200/?$rid={}".format(device_id, req_id), qos=1)
        self.mqtt_client.message_callback_add(twin_res_topic, self._on_twin_response)
        log('Asking twin for device {}. {}'.format(device_id, twin_topic))
        self.mqtt_client.publish(twin_topic,qos=1)
        # self.mqtt_client.subscribe('$iothub/twin/res/200/?rid={}'.format(req_id))
        # self.mqtt_client.publish("$iothub/twin/GET/?$rid={}".format(req_id), qos=1)

    def _on_twin_response(self, client, userdata, msg: mqtt.MQTTMessage):
        log('Received twin')
        match = twin_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            self._clients[device_id]('twin', msg.payload)

    def _on_prop_change(self, client, userdata, msg: mqtt.MQTTMessage):
        match = desired_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            self._clients[device_id]('property_change', msg.payload)

    def _on_command(self, client, userdata, msg: mqtt.MQTTMessage):
        match = command_topic_compiler.match(msg.topic)
        if match.group(1) is not None:
            device_id = match.group(1)
            self._clients[device_id]('command', msg.payload)
