namespace TranslatorNet
{
    using System;
    using System.Collections.Generic;
    using System.Text;
    using System.Text.RegularExpressions;
    using System.Threading.Tasks;
    using MQTTnet;
    using MQTTnet.Client;
    using MQTTnet.Client.Connecting;
    using MQTTnet.Client.Options;
    using Newtonsoft.Json.Linq;

    enum Topics
    {
        DEVICE_TWIN,
        MODULE_TWIN,
        MODULE_PROPERTIES,
        MODULE_METHODS,
        DEVICE_PROPERTIES,
        DEVICE_METHODS
    }
    public class MqttClient
    {

        private static readonly Dictionary<Topics, Regex> topics = new Dictionary<Topics, Regex>{
            {Topics.DEVICE_TWIN,new Regex(@"\$iothub\/([\S]+)\/twin\/res",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
            {Topics.DEVICE_PROPERTIES,new Regex(@"\$iothub\/([\S]+)\/twin\/desired",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
            {Topics.DEVICE_METHODS,new Regex(@"\$iothub\/([\S]+)\/methods\/res",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
            {Topics.MODULE_TWIN,new Regex(@"\$iothub\/twin\/res",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
            {Topics.MODULE_METHODS,new Regex(@"\$iothub\/methods\/res",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
            {Topics.MODULE_PROPERTIES,new Regex(@"\$iothub\/twin\/desired",RegexOptions.Compiled|RegexOptions.IgnoreCase)},
        };
        private IMqttClientOptions connectOptions;
        private IMqttClient client;

        public Action<string> OnModuleTwin;

        private void onMessage(MqttApplicationMessageReceivedEventArgs e)
        {
            Console.WriteLine(e.ApplicationMessage.Topic);
            Dictionary<Topics, MatchCollection> matches = new Dictionary<Topics, MatchCollection>{
                {Topics.DEVICE_TWIN,topics[Topics.DEVICE_TWIN].Matches(e.ApplicationMessage.Topic)},
                {Topics.DEVICE_PROPERTIES,topics[Topics.DEVICE_PROPERTIES].Matches(e.ApplicationMessage.Topic)},
                {Topics.DEVICE_METHODS,topics[Topics.DEVICE_METHODS].Matches(e.ApplicationMessage.Topic)},
                {Topics.MODULE_TWIN,topics[Topics.MODULE_TWIN].Matches(e.ApplicationMessage.Topic)},
                {Topics.MODULE_PROPERTIES,topics[Topics.MODULE_PROPERTIES].Matches(e.ApplicationMessage.Topic)},
            };

            if (matches[Topics.DEVICE_TWIN].Count > 0)
            {
                // Twin
                Console.WriteLine($"Received twin for {matches[Topics.DEVICE_TWIN][0].Groups[1]}.");
                Console.WriteLine(Encoding.UTF8.GetString(e.ApplicationMessage.Payload));
            }
            else if (matches[Topics.DEVICE_PROPERTIES].Count > 0)
            {
                // Properties
                Console.WriteLine($"Received properties PATCH for {matches[Topics.DEVICE_PROPERTIES][0].Groups[1]}.");
                Console.WriteLine(Encoding.UTF8.GetString(e.ApplicationMessage.Payload));
            }
            else if (matches[Topics.DEVICE_METHODS].Count > 0)
            {
                // Commands
                Console.WriteLine($"Received commands for {matches[Topics.DEVICE_METHODS][0].Groups[1]}.");
                Console.WriteLine(Encoding.UTF8.GetString(e.ApplicationMessage.Payload));
            }
            else if (matches[Topics.MODULE_TWIN].Count > 0)
            {
                // Module Twin
                Console.WriteLine($"Received module twin.");
                string data = Encoding.UTF8.GetString(e.ApplicationMessage.Payload);
                Console.WriteLine(data);
                OnModuleTwin?.Invoke(data);
            }
            else if (matches[Topics.DEVICE_PROPERTIES].Count > 0)
            {
                // Properties
                Console.WriteLine($"Received module properties PATCH.");
                Console.WriteLine(Encoding.UTF8.GetString(e.ApplicationMessage.Payload));
            }
            else if (matches[Topics.MODULE_METHODS].Count > 0)
            {
                // Commands
                Console.WriteLine($"Received module command.");
                Console.WriteLine(Encoding.UTF8.GetString(e.ApplicationMessage.Payload));
            }
            else
            {
                Console.WriteLine($"Received message on topic '{e.ApplicationMessage.Topic}': {Encoding.UTF8.GetString(e.ApplicationMessage.Payload)}");
            }

        }

        public MqttClient(string server, string clientId)
        {
            this.client = new MqttFactory().CreateMqttClient();
            this.client.UseApplicationMessageReceivedHandler(onMessage);
            this.connectOptions = new MqttClientOptionsBuilder()
            .WithTcpServer(server, 1883)
            .WithProtocolVersion(MQTTnet.Formatter.MqttProtocolVersion.V311)
        .WithClientId(clientId)
        .Build();
        }
        public MqttClient(string server, string clientId, string username, string password)
        {
            this.client = new MqttFactory().CreateMqttClient();
            this.client.UseApplicationMessageReceivedHandler(onMessage);
            var tlsOptions = new MqttClientOptionsBuilderTlsParameters()
            {
                UseTls = true,
                SslProtocol = System.Security.Authentication.SslProtocols.Tls12,
                AllowUntrustedCertificates = true,
                CertificateValidationHandler = (opts) => true // TODO: remove in production!!
            };
            this.connectOptions = new MqttClientOptionsBuilder()
            .WithTcpServer(server, 8883)
        .WithTls(tlsOptions)
        .WithProtocolVersion(MQTTnet.Formatter.MqttProtocolVersion.V311)
        .WithCredentials(username, password)
        .WithClientId(clientId)
        .Build();
        }

        public async Task<MQTTnet.Client.Connecting.MqttClientConnectResult> Connect(Func<MqttClientConnectedEventArgs, Task> connectHandler)
        {
            this.client.UseConnectedHandler(connectHandler);
            return await this.Connect();
        }
        public async Task<MQTTnet.Client.Connecting.MqttClientConnectResult> Connect()
        {
            return await this.client.ConnectAsync(this.connectOptions);
        }

        public async Task Disconnect()
        {
            await this.client.DisconnectAsync();
        }
        public async Task AddDevice(string deviceId)
        {
            // subscribe to device specific topics
            await this.client.SubscribeAsync(new MqttTopicFilterBuilder().WithTopic($"$iothub/{deviceId}/twin/res/#").Build());
            await this.client.SubscribeAsync(new MqttTopicFilterBuilder().WithTopic($"$iothub/{deviceId}/methods/res/#").Build());
            await this.client.SubscribeAsync(new MqttTopicFilterBuilder().WithTopic($"$iothub/{deviceId}/twin/desired/#").Build());
        }
        public async Task SendTelemetry(string deviceId, JObject payload)
        {
            var message = new MqttApplicationMessageBuilder()
                .WithTopic($"$iothub/{deviceId}/messages/events/")
                .WithPayload(payload.ToString(Newtonsoft.Json.Formatting.None))
                .WithAtLeastOnceQoS()
                .WithRetainFlag()
                .Build();

            await this.client.PublishAsync(message);
        }

        public async Task SendProperty(string deviceId, JObject payload)
        {
            var message = new MqttApplicationMessageBuilder()
                .WithTopic($"$iothub/{deviceId}/twin/reported/")
                .WithPayload(payload.ToString(Newtonsoft.Json.Formatting.None))
                .WithAtLeastOnceQoS()
                .WithRetainFlag()
                .Build();

            await this.client.PublishAsync(message);
        }

        public async Task FetchTwinAsync(string deviceId = null)
        {
            var requestId = Guid.NewGuid().ToString();
            MqttApplicationMessage message;
            if (deviceId == null)
            {
                message = new MqttApplicationMessageBuilder()
                        .WithTopic($"$iothub/twin/GET/?$rid={requestId}")
                        .WithAtLeastOnceQoS()
                        .Build();

                await this.client.SubscribeAsync(new MqttTopicFilterBuilder()
                .WithTopic($"$iothub/twin/res/#")
                .Build());
                await this.client.SubscribeAsync(new MqttTopicFilterBuilder()
                .WithTopic($"$iothub/twin/res/200/?$rid={requestId}")
                .Build());
            }
            else
            {
                message = new MqttApplicationMessageBuilder()
                    .WithTopic($"$iothub/{deviceId}/twin/get/?$rid={requestId}")
                    .WithAtLeastOnceQoS()
                    .Build();

                await this.client.SubscribeAsync(new MqttTopicFilterBuilder()
                .WithTopic($"$iothub/{deviceId}/twin/res/#")
                .Build());
                await this.client.SubscribeAsync(new MqttTopicFilterBuilder()
                .WithTopic($"$iothub/twin/{deviceId}/res/200/?$rid={requestId}")
                .Build());
            }
            Console.WriteLine($"Asking twin{(deviceId != null ? " for " + deviceId : "")} with topic {message.Topic}");
            await this.client.PublishAsync(message);
        }
    }
}