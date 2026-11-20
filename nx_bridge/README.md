# C# NXOpen bridge (branch-C MVP)

This project is the only repository component allowed to reference NXOpen. It
uses loopback TCP with one newline-delimited JSON request per connection. The
Python client reads the endpoint file and never retries a timed-out request.

The installed NX root for this machine is:

```text
D:\softwares\NX2506
```

The bridge owns the loopback transport, token validation, and the first
interactive NXOpen dispatcher. It supports session context, current UI
selection, face and solid surface-area and volume measurement, highlight/show/hide/isolate, fit,
update, and save. `BranchCSmokeJournal.cs` is a thin journal loader for the
compiled smoke runtime. The runtime creates a 100 x 60 x 20 mm block,
subtracts a 10 mm through-cylinder, saves `work\branch_c_smoke.prt`, and
starts the same JSON protocol from inside the interactive NX session.

From a Visual Studio Developer PowerShell on the NX seat:

```powershell
$env:NX_ROOT = 'D:\softwares\NX2506'
dotnet build nx_bridge\NxBridge.csproj
```

The project emits `bin\Debug\net8.0-windows\Drawgen.NxBridgeBranchC.dll`.
The journal launcher uses this stable, distinct assembly identity so a new
Branch C build can be loaded while an older smoke assembly remains resident in
a long-lived NX process.

The smoke journal can be loaded from the interactive NX UI with **Tools >
Journal > Play**, selecting `nx_bridge\BranchCSmokeJournal.cs`. The loader only
uses core reflection because NX's journal compiler does not automatically
reference the socket and NXOpenUI assemblies. After it starts, the bridge
endpoint is written to `%LOCALAPPDATA%\drawgen\bridge.json`.

The journal reuses the active `branch_c_smoke.prt` when it is already open and
supports `create_box_with_hole` through the bridge. That command creates a new
active unsaved part with a through-hole. Omitted hole-center offsets default to
the box center. Use the explicit `save`
command when persistence is wanted.

The compiled dispatcher in `src\NxBridgeEntry.cs` is the add-in form of the
same implementation. It expects to be loaded into an interactive NX 2506
session with the per-session token environment variable set.

Remaining seat validation is limited to confirming the exact add-in load
mechanism and the NX main-thread behavior on the installed seat:

- current selection and face/body/feature surface area and volume;
- work/displayed part and active sheet/view;
- main-thread dispatch from the listener;
- undo marks, highlight, display operations, attributes, expressions, and save.

Never load the bridge without the per-session `DRAWGEN_BRIDGE_TOKEN` and a
loopback-only endpoint. By default the add-in writes endpoint metadata to
`%LOCALAPPDATA%\drawgen\bridge.json`; set `DRAWGEN_BRIDGE_ENDPOINT` to override
that path. Keep the generated endpoint metadata outside version control.
