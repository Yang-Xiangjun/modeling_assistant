using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace Drawgen.NxBridge;

// The server owns transport and authentication only. NXOpen work is supplied
// by an INxDispatcher implementation on the NX seat after its main-thread
// callback has been recorded for the installed NX release.
public interface INxDispatcher
{
    object? Dispatch(string command, Dictionary<string, object?> inputs);
}

public sealed class BridgeServer : IDisposable
{
    private readonly TcpListener _listener;
    private readonly string _token;
    private readonly INxDispatcher _dispatcher;
    private CancellationTokenSource? _stop;

    public BridgeServer(int port, string token, INxDispatcher dispatcher)
    {
        _listener = new TcpListener(IPAddress.Loopback, port);
        _token = token;
        _dispatcher = dispatcher;
    }

    public int Port => ((IPEndPoint)_listener.LocalEndpoint).Port;

    public void Start()
    {
        _stop = new CancellationTokenSource();
        _listener.Start();
        _ = AcceptLoopAsync(_stop.Token);
    }

    private async Task AcceptLoopAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            TcpClient client;
            try { client = await _listener.AcceptTcpClientAsync(cancellationToken); }
            catch (OperationCanceledException) { return; }
            _ = HandleClientAsync(client, cancellationToken);
        }
    }

    private async Task HandleClientAsync(TcpClient client, CancellationToken cancellationToken)
    {
        using var owned = client;
        using var stream = client.GetStream();
        using var reader = new StreamReader(stream, Encoding.UTF8, leaveOpen: true);
        await using var writer = new StreamWriter(stream, new UTF8Encoding(false), leaveOpen: true) { AutoFlush = true };
        var line = await reader.ReadLineAsync(cancellationToken);
        if (string.IsNullOrWhiteSpace(line)) return;
        BridgeRequest? request;
        try { request = JsonSerializer.Deserialize<BridgeRequest>(line, BridgeJson.Options); }
        catch (JsonException) { return; }
        if (request is null) return;
        var stopwatch = Stopwatch.StartNew();
        try
        {
            if (request.Token != _token) throw new UnauthorizedAccessException("invalid bridge token");
            object? result = request.Command == "ping"
                ? new { bridge_version = "c0-csharp", nx_version = Environment.GetEnvironmentVariable("UGII_VERSION") }
                : _dispatcher.Dispatch(request.Command, request.Inputs ?? new Dictionary<string, object?>());
            var status = new BridgeStatus(true, request.Command, null, stopwatch.Elapsed.TotalSeconds,
                Environment.GetEnvironmentVariable("UGII_VERSION"), null, new List<string>());
            await writer.WriteLineAsync(JsonSerializer.Serialize(new BridgeResponse(request.Id, status, result), BridgeJson.Options));
        }
        catch (Exception ex)
        {
            var status = new BridgeStatus(false, request.Command,
                new BridgeError(ex.GetType().Name, ex.Message), stopwatch.Elapsed.TotalSeconds,
                Environment.GetEnvironmentVariable("UGII_VERSION"), null, new List<string>());
            await writer.WriteLineAsync(JsonSerializer.Serialize(new BridgeResponse(request.Id, status, null), BridgeJson.Options));
        }
    }

    public void Dispose()
    {
        _stop?.Cancel();
        _listener.Stop();
    }
}
