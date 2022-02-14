using System;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Azure.Devices.Provisioning.Client;
using Microsoft.Azure.Devices.Provisioning.Client.Transport;
using Microsoft.Azure.Devices.Shared;
using Newtonsoft.Json.Linq;

namespace TranslatorNet
{

    public class Provision
    {
        static readonly string DPS_ENDPOINT = "global.azure-devices-provisioning.net";
        static string _groupKey;
        static string _scopeId;
        static string _gatewayId;
        private static string ComputeDerivedSymmetricKey(string enrollmentKey, string deviceId)
        {
            if (string.IsNullOrWhiteSpace(enrollmentKey))
            {
                return enrollmentKey;
            }

            using var hmac = new HMACSHA256(Convert.FromBase64String(enrollmentKey));
            return Convert.ToBase64String(hmac.ComputeHash(Encoding.UTF8.GetBytes(deviceId)));
        }
        public static void Init(string scopeId, string groupKey, string gatewayId)
        {
            _scopeId = scopeId;
            _groupKey = groupKey;
            _gatewayId = gatewayId;
        }

        public static async Task<bool> ProvisionDevice(string deviceId, string modelId = null)
        {
            if (_scopeId == null)
            {
                Console.WriteLine("No scope Id has been specified.");
                return false;
            }
            using var security = new SecurityProviderSymmetricKey(
                                       deviceId,
                                       ComputeDerivedSymmetricKey(_groupKey, deviceId),
                                       null);

            using var transportHandler = new ProvisioningTransportHandlerHttp();

            ProvisioningDeviceClient provClient = ProvisioningDeviceClient.Create(
               DPS_ENDPOINT,
                _scopeId,
                security,
                transportHandler);
            Console.WriteLine($"Initialized for registration Id {security.GetRegistrationID()}.");

            Console.WriteLine("Registering with the device provisioning service...");
            JObject provisioningData = new JObject()
            {
                {"iotcGateway", new JObject()
                    {
                        {"iotcGatewayId",_gatewayId}

                    }
                }
            };
            if (modelId != null)
            {
                provisioningData["iotcModelId"] = modelId;
            }
            Console.WriteLine($"Registering with payload '{provisioningData.ToString(Newtonsoft.Json.Formatting.None)}'");
            DeviceRegistrationResult result = await provClient.RegisterAsync(new ProvisioningRegistrationAdditionalData()
            {
                JsonData = provisioningData.ToString(Newtonsoft.Json.Formatting.None)
            });

            Console.WriteLine($"Registration status: {result.Status}.");
            if (result.Status != ProvisioningRegistrationStatusType.Assigned)
            {
                Console.WriteLine($"Registration status did not assign a hub, so exiting this sample.");
                return false;
            }

            Console.WriteLine($"Device {result.DeviceId} registered to {result.AssignedHub}.");
            return true;
        }
    }
}