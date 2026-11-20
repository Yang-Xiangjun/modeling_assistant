using System.Text.Json;
using System.Text.Json.Serialization;

namespace Drawgen.NxBridge;

public sealed record BridgeRequest(
    string Protocol,
    string Id,
    string Token,
    string Command,
    Dictionary<string, object?>? Inputs,
    Dictionary<string, object?>? Options);

public sealed record BridgeStatus(
    bool Ok,
    string? Command,
    BridgeError? Error,
    double DurationS,
    string? NxVersion,
    string? PythonVersion,
    List<string> Log);

public sealed record BridgeError(string Type, string Message, string? Traceback = null);

public sealed record BridgeResponse(string Id, BridgeStatus Status, object? Result);

public static class BridgeJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}
