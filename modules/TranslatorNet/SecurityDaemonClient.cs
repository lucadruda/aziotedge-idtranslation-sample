using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Runtime.CompilerServices;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Encodings.Web;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Azure.EventGridEdge.IotEdge;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using Newtonsoft.Json.Serialization;

namespace IoTEdgeSasTokenHelper
{
    public sealed class SecurityDaemonClient : IDisposable
    {
        private const string UnixScheme = "unix";
        private readonly JsonSerializerSettings jsonSettings = new JsonSerializerSettings
        {
            Formatting = Formatting.None,
            NullValueHandling = NullValueHandling.Ignore,
            FloatParseHandling = FloatParseHandling.Decimal,
            ContractResolver = new CamelCasePropertyNamesContractResolver(),
            Converters = new JsonConverter[] { new StringEnumConverter() },
        };

        private readonly string moduleGenerationId;
        private readonly string edgeGatewayHostName;
        private readonly string workloadApiVersion;

        private readonly HttpClient httpClient;
        private readonly Uri postSignRequestUri;
        private readonly string asString;

        public SecurityDaemonClient()
        {
            this.ModuleId = Environment.GetEnvironmentVariable("IOTEDGE_MODULEID");
            this.DeviceId = Environment.GetEnvironmentVariable("IOTEDGE_DEVICEID");
            this.IotHubHostName = Environment.GetEnvironmentVariable("IOTEDGE_IOTHUBHOSTNAME");
            this.IotHubName = this.IotHubHostName.Split('.').FirstOrDefault();

            this.moduleGenerationId = Environment.GetEnvironmentVariable("IOTEDGE_MODULEGENERATIONID");
            this.edgeGatewayHostName = Environment.GetEnvironmentVariable("IOTEDGE_GATEWAYHOSTNAME");
            this.workloadApiVersion = Environment.GetEnvironmentVariable("IOTEDGE_APIVERSION");
            string workloadUriString = Environment.GetEnvironmentVariable("IOTEDGE_WORKLOADURI");

            Validate.ArgumentNotNullOrEmpty(this.ModuleId, nameof(this.ModuleId));
            Validate.ArgumentNotNullOrEmpty(this.DeviceId, nameof(this.DeviceId));
            Validate.ArgumentNotNullOrEmpty(this.IotHubHostName, nameof(this.IotHubHostName));
            Validate.ArgumentNotNullOrEmpty(this.moduleGenerationId, nameof(this.moduleGenerationId));
            Validate.ArgumentNotNullOrEmpty(this.edgeGatewayHostName, nameof(this.edgeGatewayHostName));
            Validate.ArgumentNotNullOrEmpty(this.workloadApiVersion, nameof(this.workloadApiVersion));
            Validate.ArgumentNotNullOrEmpty(workloadUriString, nameof(workloadUriString));

            var workloadUri = new Uri(workloadUriString);

            string baseUrlForRequests;
            if (workloadUri.Scheme.Equals(SecurityDaemonClient.UnixScheme, StringComparison.OrdinalIgnoreCase))
            {
                baseUrlForRequests = $"http://{workloadUri.Segments.Last()}";
                this.httpClient = new HttpClient(new HttpUdsMessageHandler(workloadUri));
            }
            else if (workloadUri.Scheme.Equals(Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase) ||
                workloadUri.Scheme.Equals(Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase))
            {
                baseUrlForRequests = workloadUriString;
                this.httpClient = new HttpClient();
            }
            else
            {
                throw new InvalidOperationException($"Unknown workloadUri scheme specified. {workloadUri}");
            }

            baseUrlForRequests = baseUrlForRequests.TrimEnd();
            this.httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            string encodedApiVersion = UrlEncoder.Default.Encode(this.workloadApiVersion);
            string encodedModuleId = UrlEncoder.Default.Encode(this.ModuleId);
            string encodedModuleGenerationId = UrlEncoder.Default.Encode(this.moduleGenerationId);

            this.postSignRequestUri = new Uri($"{baseUrlForRequests}/modules/{encodedModuleId}/genid/{encodedModuleGenerationId}/sign?api-version={encodedApiVersion}");

            var settings = new
            {
                this.ModuleId,
                this.DeviceId,
                IotHubHostName = this.IotHubHostName,
                ModuleGenerationId = this.moduleGenerationId,
                GatewayHostName = this.edgeGatewayHostName,
                WorkloadUri = workloadUriString,
                WorkloadApiVersion = this.workloadApiVersion,
            };
            this.asString = $"{nameof(SecurityDaemonClient)}{JsonConvert.SerializeObject(settings, Formatting.None, this.jsonSettings)}";
        }

        public string IotHubName { get; }
        public string IotHubHostName { get; set; }

        public string DeviceId { get; }

        public string ModuleId { get; }

        public void Dispose() => this.httpClient.Dispose();

        public override string ToString() => this.asString;

        public async Task<string> GetModuleToken(int expiryInSeconds = 3600)
        {
            TimeSpan fromEpochStart = DateTime.UtcNow - new DateTime(1970, 1, 1);
            string expiry = Convert.ToString((int)fromEpochStart.TotalSeconds + expiryInSeconds);

            string resourceUri = $"{this.IotHubHostName}/devices/{this.DeviceId}/modules/{this.ModuleId}";
            string stringToSign = WebUtility.UrlEncode(resourceUri) + "\n" + expiry;
            var signResponse = await this.SignUriAsync(Encoding.UTF8.GetBytes(stringToSign));
            var signature = Convert.ToBase64String(signResponse.Digest);

            string token = String.Format(CultureInfo.InvariantCulture, "SharedAccessSignature sr={0}&sig={1}&se={2}",
                WebUtility.UrlEncode(resourceUri), WebUtility.UrlEncode(signature), expiry);

            return token;
        }

        public async Task<SignResponse> SignUriAsync(byte[] data, CancellationToken token = default)
        {
            var request = new SignRequest
            {
                Algo = SignRequestAlgo.HMACSHA256,
                Data = data,
                KeyId = "primary"
            };

            string requestString = JsonConvert.SerializeObject(request, Formatting.None, this.jsonSettings);
            using (var content = new StringContent(requestString, Encoding.UTF8, "application/json"))
            using (var httpRequest = new HttpRequestMessage(HttpMethod.Post, this.postSignRequestUri) { Content = content })
            using (HttpResponseMessage httpResponse = await this.httpClient.SendAsync(httpRequest, token))
            {
                string responsePayload = await httpResponse.Content.ReadAsStringAsync();
                if (httpResponse.StatusCode == HttpStatusCode.OK)
                {
                    SignResponse signResponse = JsonConvert.DeserializeObject<SignResponse>(responsePayload, this.jsonSettings);
                    return signResponse;
                }

                throw new InvalidOperationException($"Failed to execute sign request from IoTEdge security daemon. StatusCode={httpResponse.StatusCode} ReasonPhrase='{httpResponse.ReasonPhrase}' ResponsePayload='{responsePayload}' Request={requestString} This={this}");
            }
        }
    }
}