// Interactive NX 2506 journal for the branch-C smoke test.
//
// It creates a deterministic 100 x 60 x 20 mm block, subtracts a 10 mm
// through-cylinder, saves the part, and leaves a loopback JSON bridge running
// inside the interactive NX process.  The journal intentionally uses only
// framework APIs so it can be loaded from NX's Journal > Play command.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using NXOpen;
using NXOpen.Features;
using NXOpen.GeometricUtilities;
using NXOpen.Utilities;

public class BranchCSmokeRuntime
{
    private static Session session;
    private static UI ui;
    private static TcpListener listener;
    private static object requestTimer;
    private static string token;
    private static string endpointPath;
    private static readonly object gate = new object();
    private static readonly object queueGate = new object();
    private static readonly Queue<PendingRequest> pending = new Queue<PendingRequest>();

    private sealed class PendingRequest
    {
        public TcpClient Client;
        public StreamReader Reader;
        public string Line;
    }

    public static void Main(string[] args)
    {
        session = Session.GetSession();
        ui = UI.GetUI();
        session.SetUndoMark(Session.MarkVisibility.Invisible, "branch_c_smoke");

        string root = @"D:\codes\modeling_assistant";
        string workDir = Path.Combine(root, "work");
        Directory.CreateDirectory(workDir);
        string partPath = Path.Combine(workDir, "branch_c_smoke.prt");
        if (String.Equals(Environment.GetEnvironmentVariable("DRAWGEN_CREATE_FIXTURE"), "explicit", StringComparison.OrdinalIgnoreCase))
        {
            CreateFixture(partPath);
        }

        token = Environment.GetEnvironmentVariable("DRAWGEN_BRIDGE_TOKEN");
        if (String.IsNullOrEmpty(token)) token = Guid.NewGuid().ToString("N");
        listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        endpointPath = Path.Combine(localAppData, "drawgen", "bridge.json");
        Directory.CreateDirectory(Path.GetDirectoryName(endpointPath));
        File.WriteAllText(
            endpointPath,
            "{\"host\":\"127.0.0.1\",\"port\":" + ((IPEndPoint)listener.LocalEndpoint).Port.ToString(CultureInfo.InvariantCulture)
                + ",\"token\":" + Quote(token) + "}",
            Encoding.UTF8);

        System.Threading.Thread thread = new System.Threading.Thread(ListenLoop);
        thread.IsBackground = true;
        thread.Start();
        requestTimer = CreateUiTimer();
        session.LogFile.WriteLine("branch_c_smoke: fixture=" + partPath);
        session.LogFile.WriteLine("branch_c_smoke: bridge=" + endpointPath);
        session.LogFile.WriteLine("branch_c_smoke: select a face in the viewport, then run the Python chat test");
    }

    private static object CreateUiTimer()
    {
        string desktopRoot = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            "dotnet", "shared", "Microsoft.WindowsDesktop.App");
        // NX 2506 hosts the .NET 8 runtime. Choose the matching WindowsDesktop
        // framework even when a newer .NET SDK is installed on the workstation.
        string desktopVersion = Directory.GetDirectories(desktopRoot)
            .Where(path => Version.TryParse(Path.GetFileName(path), out Version? candidate)
                && candidate.Major == 8
                && candidate.Minor == 0)
            .OrderByDescending(path => Version.Parse(Path.GetFileName(path)))
            .FirstOrDefault()
            ?? throw new FileNotFoundException("Microsoft.WindowsDesktop.App 8.0 was not found", desktopRoot);
        string formsPath = Path.Combine(desktopVersion, "System.Windows.Forms.dll");
        Assembly formsAssembly = Assembly.LoadFrom(formsPath);
        System.Type timerType = formsAssembly.GetType("System.Windows.Forms.Timer", throwOnError: true);
        object timer = Activator.CreateInstance(timerType) ?? throw new InvalidOperationException("could not create the NX UI timer");
        timerType.GetProperty("Interval")!.SetValue(timer, 50);
        EventInfo tick = timerType.GetEvent("Tick") ?? throw new InvalidOperationException("NX UI timer has no Tick event");
        Delegate handler = Delegate.CreateDelegate(
            tick.EventHandlerType!,
            typeof(BranchCSmokeRuntime),
            nameof(ProcessPendingRequests));
        tick.AddEventHandler(timer, handler);
        timerType.GetMethod("Start")!.Invoke(timer, null);
        return timer;
    }

    public static int GetUnloadOption(string dummy)
    {
        return (int)Session.LibraryUnloadOption.Explicitly;
    }

    private static void CreateFixture(string partPath)
    {
        Part part = null;
        Part active = session.Parts.Display ?? session.Parts.Work;
        if (active != null && String.Equals(active.FullPath, partPath, StringComparison.OrdinalIgnoreCase))
        {
            session.Parts.SetWork(active);
            return;
        }
        if (File.Exists(partPath))
        {
            PartLoadStatus status;
            part = (Part)session.Parts.OpenActiveDisplay(partPath, DisplayPartOption.AllowAdditional, out status);
            status.Dispose();
            session.Parts.SetWork(part);
            return;
        }

        part = session.Parts.NewDisplay(partPath, Part.Units.Millimeters);
        session.Parts.SetWork(part);

        BlockFeatureBuilder block = part.Features.CreateBlockFeatureBuilder(null);
        try
        {
            block.Type = BlockFeatureBuilder.Types.OriginAndEdgeLengths;
            block.SetOriginAndLengths(new Point3d(0.0, 0.0, 0.0), "100", "60", "20");
            block.CommitFeature();
        }
        finally
        {
            block.Destroy();
        }

        Body body = null;
        foreach (Body candidate in part.Bodies)
        {
            body = candidate;
            break;
        }
        if (body == null) throw new InvalidOperationException("block creation did not produce a body");

        CylinderBuilder cylinder = part.Features.CreateCylinderBuilder(null);
        try
        {
            cylinder.Type = CylinderBuilder.Types.AxisDiameterAndHeight;
            cylinder.Origin = new Point3d(50.0, 30.0, -1.0);
            cylinder.Direction = new Vector3d(0.0, 0.0, 1.0);
            cylinder.Height.RightHandSide = "22";
            cylinder.Diameter.RightHandSide = "10";
            cylinder.BooleanOption.Type = BooleanOperation.BooleanType.Subtract;
            cylinder.BooleanOption.SetTargetBodies(new[] { body });
            cylinder.CommitFeature();
        }
        finally
        {
            cylinder.Destroy();
        }

        PartSaveStatus save = part.Save(BasePart.SaveComponents.True, BasePart.CloseAfterSave.False);
        save.Dispose();
        part.ModelingViews.WorkView.Fit();
    }

    private static void ListenLoop()
    {
        while (true)
        {
            try
            {
                TcpClient client = listener.AcceptTcpClient();
                System.Threading.Thread worker = new System.Threading.Thread(delegate() { Queue(client); });
                worker.IsBackground = true;
                worker.Start();
            }
            catch
            {
                return;
            }
        }
    }

    private static void Queue(TcpClient client)
    {
        try
        {
            NetworkStream stream = client.GetStream();
            StreamReader reader = new StreamReader(stream, Encoding.UTF8);
            string line = reader.ReadLine();
            if (String.IsNullOrWhiteSpace(line))
            {
                reader.Dispose();
                client.Close();
                return;
            }
            lock (queueGate)
            {
                pending.Enqueue(new PendingRequest { Client = client, Reader = reader, Line = line });
            }
        }
        catch
        {
            client.Close();
        }
    }

    private static void ProcessPendingRequests(object sender, EventArgs e)
    {
        while (true)
        {
            PendingRequest request = null;
            lock (queueGate)
            {
                if (pending.Count > 0) request = pending.Dequeue();
            }
            if (request == null) return;

            using (request.Reader)
            using (request.Client)
            using (StreamWriter writer = new StreamWriter(request.Client.GetStream(), new UTF8Encoding(false)))
            {
                writer.AutoFlush = true;
                string id = Field(request.Line, "id");
                string command = Field(request.Line, "command");
                string requestToken = Field(request.Line, "token");
                DateTime start = DateTime.UtcNow;
                try
                {
                    if (!String.Equals(requestToken, token, StringComparison.Ordinal))
                    {
                        writer.WriteLine(Response(id, command, false, "invalid bridge token", "null"));
                        continue;
                    }

                    object result;
                    lock (gate)
                    {
                        ui.LockAccess();
                        try { result = Dispatch(command, request.Line); }
                        finally { ui.UnlockAccess(); }
                    }
                    double seconds = (DateTime.UtcNow - start).TotalSeconds;
                    writer.WriteLine(Response(id, command, true, null, Json(result), seconds));
                }
                catch (Exception ex)
                {
                    double seconds = (DateTime.UtcNow - start).TotalSeconds;
                    writer.WriteLine(Response(id, command, false, ex.Message, "null", seconds));
                }
            }
        }
    }

    private static object Dispatch(string command, string request)
    {
        if (command == "ping") return new Dictionary<string, object> { { "bridge_version", "nx-journal-1" }, { "nx_version", "NX2506" } };
        if (command == "get_context") return Context();
        if (command == "get_selection") return Selection();
        if (command == "measure") return Measure(request);
        if (command == "create_box_with_hole") return CreateBoxWithHole(request);
        if (command == "highlight" || command == "show_entity" || command == "hide_entity" || command == "isolate_entity")
            return Display(command, Field(request, "handle"));
        if (command == "fit_view")
        {
            session.Parts.Work.ModelingViews.WorkView.Fit();
            return Operation(command, null, true);
        }
        if (command == "update")
        {
            Session.UndoMarkId mark = session.SetUndoMark(Session.MarkVisibility.Invisible, "branch_c_update");
            int errors = session.UpdateManager.DoUpdate(mark);
            return Operation(command, "branch_c_update", errors == 0);
        }
        if (command == "save")
        {
            PartSaveStatus status = session.Parts.Work.Save(BasePart.SaveComponents.True, BasePart.CloseAfterSave.False);
            status.Dispose();
            return new Dictionary<string, object> { { "command", command }, { "undo_mark", null }, { "changed", false }, { "saved", true }, { "details", new Dictionary<string, object>() } };
        }
        throw new NotSupportedException("unsupported NX command '" + command + "'");
    }

    private static object CreateBoxWithHole(string request)
    {
        double width = Number(request, "width", 100.0);
        double depth = Number(request, "depth", 60.0);
        double height = Number(request, "height", 20.0);
        double diameter = Number(request, "hole_diameter", 10.0);
        if (diameter >= width || diameter >= depth)
            throw new ArgumentException("hole_diameter must be smaller than both box width and depth");
        double radius = diameter / 2.0;
        double centerLeft = Number(request, "hole_center_left", width / 2.0);
        double centerBottom = Number(request, "hole_center_bottom", depth / 2.0);
        if (centerLeft < radius || centerLeft > width - radius)
            throw new ArgumentException("hole_center_left must keep the hole inside the box width");
        if (centerBottom < radius || centerBottom > depth - radius)
            throw new ArgumentException("hole_center_bottom must keep the hole inside the box depth");

        string workDir = Path.Combine(@"D:\codes\modeling_assistant", "work");
        Directory.CreateDirectory(workDir);
        string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss_fff", CultureInfo.InvariantCulture);
        string partPath = Path.Combine(workDir, "branch_c_chat_" + stamp + ".prt");
        Part part = session.Parts.NewDisplay(partPath, Part.Units.Millimeters);
        session.Parts.SetWork(part);

        BlockFeatureBuilder block = part.Features.CreateBlockFeatureBuilder(null);
        try
        {
            block.Type = BlockFeatureBuilder.Types.OriginAndEdgeLengths;
            block.SetOriginAndLengths(new Point3d(0.0, 0.0, 0.0),
                width.ToString("R", CultureInfo.InvariantCulture),
                depth.ToString("R", CultureInfo.InvariantCulture),
                height.ToString("R", CultureInfo.InvariantCulture));
            block.CommitFeature();
        }
        finally
        {
            block.Destroy();
        }

        Body body = null;
        foreach (Body candidate in part.Bodies)
        {
            body = candidate;
            break;
        }
        if (body == null) throw new InvalidOperationException("box creation did not produce a body");

        CylinderBuilder cylinder = part.Features.CreateCylinderBuilder(null);
        try
        {
            cylinder.Type = CylinderBuilder.Types.AxisDiameterAndHeight;
            cylinder.Origin = new Point3d(centerLeft, centerBottom, -1.0);
            cylinder.Direction = new Vector3d(0.0, 0.0, 1.0);
            cylinder.Height.RightHandSide = (height + 2.0).ToString("R", CultureInfo.InvariantCulture);
            cylinder.Diameter.RightHandSide = diameter.ToString("R", CultureInfo.InvariantCulture);
            cylinder.BooleanOption.Type = BooleanOperation.BooleanType.Subtract;
            cylinder.BooleanOption.SetTargetBodies(new[] { body });
            cylinder.CommitFeature();
        }
        finally
        {
            cylinder.Destroy();
        }

        part.ModelingViews.WorkView.Fit();
        Dictionary<string, object> details = new Dictionary<string, object>
        {
            { "part_name", part.Leaf },
            { "part_path", part.FullPath },
            { "width_mm", width },
            { "depth_mm", depth },
            { "height_mm", height },
            { "hole_diameter_mm", diameter },
            { "hole_center_left_mm", centerLeft },
            { "hole_center_bottom_mm", centerBottom },
            { "saved", false },
        };
        return new Dictionary<string, object>
        {
            { "command", "create_box_with_hole" },
            { "undo_mark", null },
            { "changed", true },
            { "saved", false },
            { "details", details },
        };
    }

    private static object Context()
    {
        Part work = session.Parts.Work;
        Part display = session.Parts.Display;
        return new Dictionary<string, object>
        {
            { "schema", "session_context/0" },
            { "work_part", PartRef(work) },
            { "displayed_part", PartRef(display) },
            { "application", "NX" },
            { "active_sheet", null },
            { "active_view", work == null ? null : work.ModelingViews.WorkView.Name },
        };
    }

    private static object PartRef(Part part)
    {
        if (part == null) return null;
        return new Dictionary<string, object>
        {
            { "name", part.Leaf },
            { "path", part.FullPath },
            { "modified", false },
        };
    }

    private static object Selection()
    {
        List<object> items = new List<object>();
        Selection selection = ui.SelectionManager;
        for (int i = 0; i < selection.GetNumSelectedObjects(); i++)
        {
            NXObject obj = selection.GetSelectedTaggedObject(i) as NXObject;
            if (obj == null) continue;
            Dictionary<string, object> properties = new Dictionary<string, object>();
            properties.Add("tag", (uint)obj.Tag);
            properties.Add("name", obj.Name ?? "");
            if (obj is Face)
            {
                try
                {
                    double area = FaceArea((Face)obj);
                    properties.Add("area_mm2", area);
                }
                catch { }
            }
            else if (obj is Body || obj is NXOpen.Features.BodyFeature)
            {
                try
                {
                    properties.Add("surface_area_mm2", SurfaceArea(obj));
                }
                catch { }
                try
                {
                    properties.Add("volume_mm3", Volume(obj));
                }
                catch { }
            }
            items.Add(new Dictionary<string, object>
            {
                { "handle", Handle(obj) },
                { "entity_kind", Kind(obj) },
                { "object_type", obj.GetType().Name },
                { "component_path", null },
                { "fingerprint", null },
                { "properties", properties },
            });
        }
        return new Dictionary<string, object> { { "schema", "selection/0" }, { "items", items } };
    }

    private static object Measure(string request)
    {
        List<object> results = new List<object>();
        MatchCollection matches = Regex.Matches(request, "\\\"id\\\"\\s*:\\s*\\\"(?<id>[^\\\"]+)\\\"\\s*,\\s*\\\"kind\\\"\\s*:\\s*\\\"(?<kind>[^\\\"]+)\\\"\\s*,\\s*\\\"a\\\"\\s*:\\s*\\\"(?<a>[^\\\"]+)\\\"");
        foreach (Match match in matches)
        {
            string id = match.Groups["id"].Value;
            string kind = match.Groups["kind"].Value;
            string handle = match.Groups["a"].Value;
            try
            {
                NXObject obj = Resolve(handle);
                if (kind == "area")
                {
                    double area = SurfaceArea(obj);
                    results.Add(new Dictionary<string, object> { { "id", id }, { "value", area }, { "unit", "mm2" }, { "error", null } });
                }
                else if (kind == "volume")
                {
                    double volume = Volume(obj);
                    results.Add(new Dictionary<string, object> { { "id", id }, { "value", volume }, { "unit", "mm3" }, { "error", null } });
                }
                else
                {
                    throw new InvalidOperationException("unsupported measurement '" + kind + "'");
                }
            }
            catch (Exception ex)
            {
                results.Add(new Dictionary<string, object> { { "id", id }, { "value", null }, { "unit", null }, { "error", ex.Message } });
            }
        }
        return new Dictionary<string, object> { { "results", results } };
    }

    private static double SurfaceArea(NXObject obj)
    {
        Face face = obj as Face;
        if (face != null)
        {
            return FaceArea(face);
        }
        Body body = obj as Body;
        if (body != null) return BodySurfaceArea(body);
        NXOpen.Features.BodyFeature feature = obj as NXOpen.Features.BodyFeature;
        if (feature != null)
        {
            double total = 0.0;
            foreach (Body featureBody in feature.GetBodies()) total += BodySurfaceArea(featureBody);
            return total;
        }
        throw new InvalidOperationException("area measurement requires a face, body, or body feature");
    }

    private static double BodySurfaceArea(Body body)
    {
        double total = 0.0;
        foreach (Face bodyFace in body.GetFaces())
        {
            total += FaceArea(bodyFace);
        }
        return total;
    }

    private static double Volume(NXObject obj)
    {
        Body body = obj as Body;
        if (body != null) return BodyVolume(body);
        NXOpen.Features.BodyFeature feature = obj as NXOpen.Features.BodyFeature;
        if (feature != null)
        {
            double total = 0.0;
            foreach (Body featureBody in feature.GetBodies()) total += BodyVolume(featureBody);
            return total;
        }
        throw new InvalidOperationException("volume measurement requires a body or body feature");
    }

    private static double BodyVolume(Body body)
    {
        Part part = session.Parts.Work;
        if (part == null) throw new InvalidOperationException("no work part for volume measurement");
        Unit[] massUnits = new Unit[]
        {
            part.UnitCollection.GetBase("Area"),
            part.UnitCollection.GetBase("Volume"),
            part.UnitCollection.GetBase("Mass"),
            part.UnitCollection.GetBase("Length"),
            part.UnitCollection.GetBase("Force"),
        };
        System.Reflection.MethodInfo newMassProperties = null;
        foreach (System.Reflection.MethodInfo candidate in part.MeasureManager.GetType().GetMethods())
        {
            System.Reflection.ParameterInfo[] parameters = candidate.GetParameters();
            System.Type bodyArrayElementType = parameters.Length == 3
                ? parameters[2].ParameterType.GetElementType()
                : null;
            if (candidate.Name == "NewMassProperties"
                && parameters.Length == 3
                && parameters[1].ParameterType == typeof(double)
                && bodyArrayElementType != null
                && bodyArrayElementType.FullName == "NXOpen.IBody")
            {
                newMassProperties = candidate;
                break;
            }
        }
        if (newMassProperties == null) throw new InvalidOperationException("NX body-volume measurement API is unavailable");
        System.Type bodyArrayType = newMassProperties.GetParameters()[2].ParameterType.GetElementType();
        if (bodyArrayType == null) throw new InvalidOperationException("NX body-volume measurement API has no body-array element type");
        Array bodies = Array.CreateInstance(bodyArrayType, 1);
        bodies.SetValue(body, 0);
        object measurement = null;
        try
        {
            measurement = newMassProperties.Invoke(part.MeasureManager, new object[] { massUnits, 0.999, bodies });
            System.Reflection.PropertyInfo volumeProperty = measurement.GetType().GetProperty("Volume");
            if (volumeProperty == null) throw new InvalidOperationException("NX body-volume measurement returned no volume");
            object volume = volumeProperty.GetValue(measurement);
            if (volume == null) throw new InvalidOperationException("NX body-volume measurement returned no value");
            return Convert.ToDouble(volume, CultureInfo.InvariantCulture);
        }
        finally
        {
            if (measurement != null)
            {
                System.Reflection.MethodInfo dispose = measurement.GetType().GetMethod("Dispose", System.Type.EmptyTypes);
                if (dispose != null) dispose.Invoke(measurement, null);
            }
        }
    }

    private static double FaceArea(Face face)
    {
        Part part = session.Parts.Work;
        if (part == null) throw new InvalidOperationException("no work part for face-area measurement");
        Unit areaUnit = part.UnitCollection.GetBase("Area");
        Unit lengthUnit = part.UnitCollection.GetBase("Length");
        System.Reflection.MethodInfo newFaceProperties = null;
        foreach (System.Reflection.MethodInfo candidate in part.MeasureManager.GetType().GetMethods())
        {
            System.Reflection.ParameterInfo[] parameters = candidate.GetParameters();
            if (candidate.Name == "NewFaceProperties" && parameters.Length == 4)
            {
                newFaceProperties = candidate;
                break;
            }
        }
        if (newFaceProperties == null) throw new InvalidOperationException("NX face-area measurement API is unavailable");
        System.Type faceArrayType = newFaceProperties.GetParameters()[3].ParameterType.GetElementType();
        Array faces = Array.CreateInstance(faceArrayType, 1);
        faces.SetValue(face, 0);
        object measurement = null;
        try
        {
            measurement = newFaceProperties.Invoke(
                part.MeasureManager,
                new object[] { areaUnit, lengthUnit, 0.001, faces });
            System.Reflection.PropertyInfo areaProperty = measurement.GetType().GetProperty("Area");
            object area = areaProperty.GetValue(measurement);
            return Convert.ToDouble(area, CultureInfo.InvariantCulture);
        }
        finally
        {
            if (measurement != null)
            {
                System.Reflection.MethodInfo dispose = measurement.GetType().GetMethod("Dispose", System.Type.EmptyTypes);
                if (dispose != null) dispose.Invoke(measurement, null);
            }
        }
    }

    private static object Display(string command, string handle)
    {
        NXObject obj = Resolve(handle);
        DisplayableObject displayable = obj as DisplayableObject;
        if (displayable == null) throw new InvalidOperationException("handle is not displayable");
        if (command == "highlight") displayable.Highlight();
        else if (command == "show_entity") displayable.Unblank();
        else if (command == "hide_entity") displayable.Blank();
        else
        {
            foreach (Body body in session.Parts.Work.Bodies)
            {
                if (!Object.ReferenceEquals(body, displayable)) body.Blank();
            }
            displayable.Unblank();
        }
        return Operation(command, "branch_c_display", true);
    }

    private static object Operation(string command, string undo, bool changed)
    {
        return new Dictionary<string, object>
        {
            { "command", command }, { "undo_mark", undo }, { "changed", changed }, { "saved", false }, { "details", new Dictionary<string, object>() }
        };
    }

    private static string Kind(NXObject obj)
    {
        if (obj is Face) return "face";
        if (obj is Edge) return "edge";
        if (obj is Body) return "body";
        if (obj is NXOpen.Features.Feature) return "feature";
        if (obj is NXOpen.Assemblies.Component) return "component";
        return "other";
    }

    private static string Handle(NXObject obj) { return "tag:" + ((uint)obj.Tag).ToString(CultureInfo.InvariantCulture); }

    private static NXObject Resolve(string handle)
    {
        if (handle == null || !handle.StartsWith("tag:", StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("invalid NX handle");
        uint value;
        if (!UInt32.TryParse(handle.Substring(4), NumberStyles.None, CultureInfo.InvariantCulture, out value)) throw new InvalidOperationException("invalid NX handle");
        NXObject obj = NXObjectManager.GetObjectFromUInt(value) as NXObject;
        if (obj == null) throw new InvalidOperationException("NX object not found for " + handle);
        return obj;
    }

    private static string Field(string json, string name)
    {
        Match match = Regex.Match(json, "\\\"" + Regex.Escape(name) + "\\\"\\s*:\\s*\\\"(?<value>(?:\\\\.|[^\\\"\\\\])*)\\\"");
        return match.Success ? match.Groups["value"].Value.Replace("\\\"", "\"").Replace("\\\\", "\\") : "";
    }

    private static double Number(string json, string name, double fallback)
    {
        string pattern = "\\\"" + Regex.Escape(name) + "\\\"\\s*:\\s*(?:\\\"(?<quoted>[^\\\"]+)\\\"|(?<raw>[-+0-9.eE]+))";
        Match match = Regex.Match(json, pattern);
        if (!match.Success) return fallback;
        string text = match.Groups["quoted"].Success ? match.Groups["quoted"].Value : match.Groups["raw"].Value;
        double value;
        if (!Double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out value) || value <= 0.0)
            throw new ArgumentException("invalid positive number for '" + name + "'");
        return value;
    }

    private static string Response(string id, string command, bool ok, string error, string result) { return Response(id, command, ok, error, result, 0.0); }

    private static string Response(string id, string command, bool ok, string error, string result, double seconds)
    {
        string status = "{\"ok\":" + (ok ? "true" : "false") + ",\"command\":" + Quote(command)
            + ",\"error\":" + (error == null ? "null" : "{\"type\":\"NXBridgeError\",\"message\":" + Quote(error) + ",\"traceback\":null}")
            + ",\"duration_s\":" + seconds.ToString("0.######", CultureInfo.InvariantCulture) + ",\"nx_version\":\"NX2506\",\"python_version\":null,\"log\":[]}";
        return "{\"id\":" + Quote(id) + ",\"status\":" + status + ",\"result\":" + result + "}";
    }

    private static string Json(object value)
    {
        if (value == null) return "null";
        if (value is string) return Quote((string)value);
        if (value is bool) return ((bool)value) ? "true" : "false";
        if (value is double) return ((double)value).ToString("R", CultureInfo.InvariantCulture);
        if (value is float) return ((float)value).ToString("R", CultureInfo.InvariantCulture);
        if (value is int || value is uint || value is long) return Convert.ToString(value, CultureInfo.InvariantCulture);
        if (value is IDictionary<string, object> dict)
        {
            List<string> fields = new List<string>();
            foreach (KeyValuePair<string, object> item in dict) fields.Add(Quote(item.Key) + ":" + Json(item.Value));
            return "{" + String.Join(",", fields.ToArray()) + "}";
        }
        if (value is IEnumerable<object> list)
        {
            List<string> values = new List<string>();
            foreach (object item in list) values.Add(Json(item));
            return "[" + String.Join(",", values.ToArray()) + "]";
        }
        return Quote(value.ToString());
    }

    private static string Quote(string value)
    {
        if (value == null) return "null";
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n") + "\"";
    }
}

