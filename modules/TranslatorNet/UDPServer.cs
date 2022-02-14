using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;

public class UDPServer
{
    private Socket _socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
    private const int bufSize = 8 * 1024;
    private State state = new State();
    private EndPoint epFrom = new IPEndPoint(IPAddress.Any, 0);
    private AsyncCallback recv = null;

    private Dictionary<string, Socket> clients;

    public delegate Task<bool> ProcessConnectMessage(string id, JObject data);
    public delegate Task ProcessTelemetryMessage(string id, JObject data);
    public delegate Task ProcessPropertyMessage(string id, JObject data);
    public delegate Task ProcessTwinMessage(string id, JObject data);
    public ProcessConnectMessage OnConnect;
    public ProcessTelemetryMessage OnTelemetry;
    public ProcessPropertyMessage OnProperty;
    public ProcessTwinMessage OnTwin;

    public UDPServer()
    {
        clients = new Dictionary<string, Socket>();
    }
    public class State
    {
        public byte[] buffer = new byte[bufSize];
    }

    public void Server(string address, int port)
    {
        _socket.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.ReuseAddress, true);
        _socket.Bind(new IPEndPoint(IPAddress.Parse(address), port));
        Console.WriteLine($"Starting UDP server at {address}:{port}");
        Receive();
    }

    public void Client(string address, int port)
    {
        _socket.Connect(IPAddress.Parse(address), port);
        Receive();
    }

    public void Send(string text)
    {
        byte[] data = Encoding.ASCII.GetBytes(text);
        _socket.BeginSend(data, 0, data.Length, SocketFlags.None, (ar) =>
        {
            State so = (State)ar.AsyncState;
            int bytes = _socket.EndSend(ar);
            Console.WriteLine("SEND: {0}, {1}", bytes, text);
        }, state);
    }

    private void Receive()
    {
        _socket.BeginReceiveFrom(state.buffer, 0, bufSize, SocketFlags.None, ref epFrom, recv = async (ar) =>
        {
            State so = (State)ar.AsyncState;
            int bytes = _socket.EndReceiveFrom(ar, ref epFrom);
            _socket.BeginReceiveFrom(so.buffer, 0, bufSize, SocketFlags.None, ref epFrom, recv, so);
            string content = Encoding.ASCII.GetString(so.buffer, 0, bytes);
            Console.WriteLine($"Received '{content}' from {epFrom.ToString()}");
            var payload = JObject.Parse(content);
            string type = payload.Value<string>("type");
            string id = payload.Value<string>("id");
            JObject data = payload.Value<JObject>("data");

            switch (type)
            {
                case "connect":
                    JToken addr;
                    if (payload.TryGetValue("addr", out addr))
                    {
                        // IPEndPoint clientEp = IPEndPoint.Parse($"{((JArray)addr)[0].ToString()}:{((JArray)addr)[1].ToString()}");

                        if (await OnConnect?.Invoke(id, data))
                        {
                            byte[] resp = Encoding.ASCII.GetBytes("{\"type\":\"connected\"}");
                            // var sock = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
                            // sock.SetSocketOption(SocketOptionLevel.IP, SocketOptionName.ReuseAddress, true);

                            // await sock.ConnectAsync(epFrom);
                            Console.WriteLine($"Sending connect confirm to {epFrom.ToString()}");
                            // await sock.SendAsync(resp, SocketFlags.None);
                            await _socket.SendToAsync(resp, SocketFlags.None, epFrom);
                            // clients.TryAdd(id, sock);
                        }
                    }
                    break;
                case "telemetry":
                    OnTelemetry?.Invoke(id, data).Wait();
                    break;
                case "property":
                    OnProperty?.Invoke(id, data).Wait();
                    break;
                case "twin_req":
                    OnTwin?.Invoke(id, data).Wait();
                    break;
            }
        }, state);
    }
}