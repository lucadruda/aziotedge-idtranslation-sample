namespace TranslatorNet
{
    using System;
    using System.IO;
    using System.Runtime.InteropServices;
    using System.Runtime.Loader;
    using System.Security.Cryptography.X509Certificates;
    using System.Text;
    using System.Threading;
    using System.Threading.Tasks;
    using IoTEdgeSasTokenHelper;
    using Microsoft.Azure.Devices.Client;
    using Microsoft.Azure.Devices.Client.Transport.Mqtt;
    using Newtonsoft.Json.Linq;

    class Program
    {

        static MqttClient mqttClient;

        static void Main(string[] args)
        {
            Init().Wait();

            // Wait until the app unloads or is cancelled
            var cts = new CancellationTokenSource();
            AssemblyLoadContext.Default.Unloading += (ctx) => cts.Cancel();
            Console.CancelKeyPress += (sender, cpe) => cts.Cancel();
            WhenCancelled(cts.Token).Wait();
        }

        /// <summary>
        /// Handles cleanup operations when app is cancelled or unloads
        /// </summary>
        public static Task WhenCancelled(CancellationToken cancellationToken)
        {
            var tcs = new TaskCompletionSource<bool>();
            cancellationToken.Register(s => ((TaskCompletionSource<bool>)s).SetResult(true), tcs);
            return tcs.Task;
        }

        private static async Task onConnect(object arg)
        {
            Console.WriteLine("MQTT Client connected!");
            await mqttClient.FetchTwinAsync();
            UDPServer udpServer = new UDPServer();
            udpServer.OnConnect += async (id, data) =>
            {
                Console.WriteLine($"New connection from {id} with {data.ToString()} received");
                JToken customData;
                string modelId = null;
                if (((JObject)data).TryGetValue("modelId", out customData))
                {
                    modelId = customData.ToString();
                    Console.WriteLine(modelId);
                }
                return await Provision.ProvisionDevice(id, modelId);
            };
            udpServer.OnTelemetry += async (id, data) => { await mqttClient.SendTelemetry(id, data); };
            udpServer.OnProperty += async (id, data) => { await mqttClient.SendProperty(id, data); };
            udpServer.OnTwin += async (id, data) => { await mqttClient.FetchTwinAsync(id); };
            udpServer.Server("0.0.0.0", 64132);
            await Task.Run(() => { while (true) ; });
        }

        /// <summary>
        /// Initializes the ModuleClient and sets up the callback to receive
        /// messages containing temperature information
        /// </summary>
        static async Task Init()
        {
            MqttTransportSettings mqttSetting = new MqttTransportSettings(TransportType.Mqtt_Tcp_Only);
            ITransportSettings[] settings = { mqttSetting };
            var securityDaemonClient = new SecurityDaemonClient();
            string hostname = Environment.GetEnvironmentVariable("IOTEDGE_GATEWAYHOSTNAME");
            string clientId = $"{securityDaemonClient.DeviceId}/{securityDaemonClient.ModuleId}";
            string username = $"{securityDaemonClient.IotHubHostName}/{securityDaemonClient.DeviceId}/{securityDaemonClient.ModuleId}/?api-version=2018-06-30";
            //call the workload api to get the TOKEN 
            string password = await securityDaemonClient.GetModuleToken(3600);

            // Open a connection to the Edge Hub
            mqttClient = new MqttClient(hostname, clientId, username, password);
            mqttClient.OnModuleTwin += (twin) =>
            {
                JObject obj = JObject.Parse(twin);
                JToken desired;
                JToken groupKey;
                if (obj.TryGetValue("desired", out desired))
                {
                    if (((JObject)desired).TryGetValue("EnrollmentGroupKey", out groupKey))
                    {
                        Provision.Init("0ne0011423C", groupKey.ToString(), securityDaemonClient.DeviceId);
                    }
                }

            };
            await mqttClient.Connect(onConnect);
        }


    }
}
