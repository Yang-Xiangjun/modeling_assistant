using NXOpen;
using NXOpen.Assemblies;
using NXOpen.Features;
using NXOpen.GeometricUtilities;
using NXOpen.Utilities;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Drawgen.NxBridge;

public static class NxBridgeEntry
{
    private static BridgeServer? _server;

    // NXOpen.Session.GetSession is the published entry point. The dispatcher
    // is deliberately not guessed here: selection and main-thread scheduling
    // must be recorded against NX 2506 before this is loaded in production.
    public static int Main(string[] args)
    {
        var session = Session.GetSession();
        _ = session;
        var token = Environment.GetEnvironmentVariable("DRAWGEN_BRIDGE_TOKEN")
            ?? throw new InvalidOperationException("DRAWGEN_BRIDGE_TOKEN is required");
        var port = int.TryParse(Environment.GetEnvironmentVariable("DRAWGEN_BRIDGE_PORT"), out var configured)
            ? configured : 0;
        _server = new BridgeServer(port, token, new InteractiveNxDispatcher(session));
        _server.Start();
        var endpoint = Environment.GetEnvironmentVariable("DRAWGEN_BRIDGE_ENDPOINT")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "drawgen", "bridge.json");
        Directory.CreateDirectory(Path.GetDirectoryName(endpoint)!);
        File.WriteAllText(endpoint, JsonSerializer.Serialize(new { host = "127.0.0.1", port = _server.Port, token }));
        return 0;
    }

    public static int GetUnloadOption(string dummy) => (int)Session.LibraryUnloadOption.Explicitly;

    private sealed class InteractiveNxDispatcher : INxDispatcher
    {
        private readonly Session _session;
        private readonly UI _ui;

        public InteractiveNxDispatcher(Session session)
        {
            _session = session;
            _ui = UI.GetUI();
        }

        public object? Dispatch(string command, Dictionary<string, object?> inputs)
        {
            _ui.LockAccess();
            try
            {
                return command switch
                {
                    "get_context" => GetContext(),
                    "get_selection" => GetSelection(GetBool(inputs, "include_properties", true)),
                    "measure" => Measure(inputs),
                    "create_box_with_hole" => CreateBoxWithHole(inputs),
                    "highlight" => Display(inputs, DisplayAction.Highlight),
                    "show_entity" => Display(inputs, DisplayAction.Show),
                    "hide_entity" => Display(inputs, DisplayAction.Hide),
                    "isolate_entity" => Display(inputs, DisplayAction.Isolate),
                    "fit_view" => FitView(),
                    "update" => Update(),
                    "save" => Save(),
                    _ => throw new NotSupportedException($"unsupported NX command '{command}'")
                };
            }
            finally
            {
                _ui.UnlockAccess();
            }
        }

        private object GetContext()
        {
            var work = _session.Parts.Work;
            var display = _session.Parts.Display;
            return new
            {
                schema = "session_context/0",
                work_part = PartRef(work),
                displayed_part = PartRef(display),
                application = "NX",
                active_sheet = (string?)null,
                active_view = work?.ModelingViews.WorkView?.Name
            };
        }

        private static object? PartRef(BasePart? part)
        {
            if (part is null) return null;
            return new { name = part.Leaf, path = part.FullPath, modified = false };
        }

        private object GetSelection(bool includeProperties)
        {
            var items = new List<object>();
            var selection = _ui.SelectionManager;
            for (var i = 0; i < selection.GetNumSelectedObjects(); i++)
            {
                var obj = selection.GetSelectedTaggedObject(i) as NXObject;
                if (obj is null) continue;
                var kind = EntityKind(obj);
                var properties = new Dictionary<string, object?>
                {
                    ["tag"] = (uint)obj.Tag,
                    ["name"] = obj.Name ?? string.Empty,
                };
                if (includeProperties && obj is Face face)
                {
                    try
                    {
                        var area = FaceArea(face);
                        properties["area_mm2"] = area;
                    }
                    catch
                    {
                        // Keep the selection readable even when a display-only face
                        // cannot be queried for an area.
                    }
                }
                else if (includeProperties && (obj is Body || obj is BodyFeature))
                {
                    try
                    {
                        properties["surface_area_mm2"] = SurfaceArea(obj);
                    }
                    catch
                    {
                        // Keep the selection readable when a feature has no solid body.
                    }
                    try
                    {
                        properties["volume_mm3"] = Volume(obj);
                    }
                    catch
                    {
                        // Keep the selection readable when a feature has no solid body.
                    }
                }
                items.Add(new
                {
                    handle = Handle(obj),
                    entity_kind = kind,
                    object_type = obj.GetType().Name,
                    component_path = (string?)null,
                    fingerprint = (object?)null,
                    properties,
                });
            }
            return new { schema = "selection/0", items };
        }

        private object Measure(Dictionary<string, object?> inputs)
        {
            var results = new List<object>();
            if (!inputs.TryGetValue("requests", out var raw) || raw is not JsonElement requests || requests.ValueKind != JsonValueKind.Array)
                return new { results };
            foreach (var request in requests.EnumerateArray())
            {
                var id = request.TryGetProperty("id", out var idValue) ? idValue.GetString() ?? "" : "";
                var kind = request.TryGetProperty("kind", out var kindValue) ? kindValue.GetString() ?? "" : "";
                var handle = request.TryGetProperty("a", out var aValue) ? aValue.GetString() ?? "" : "";
                try
                {
                    var obj = Resolve(handle);
                    if (kind == "area")
                    {
                        var area = SurfaceArea(obj);
                        results.Add(new { id, value = area, unit = "mm2", error = (string?)null });
                    }
                    else if (kind == "volume")
                    {
                        var volume = Volume(obj);
                        results.Add(new { id, value = volume, unit = "mm3", error = (string?)null });
                    }
                    else
                    {
                        results.Add(new { id, value = (double?)null, unit = (string?)null, error = $"unsupported measurement '{kind}'" });
                    }
                }
                catch (Exception ex)
                {
                    results.Add(new { id, value = (double?)null, unit = (string?)null, error = ex.Message });
                }
            }
            return new { results };
        }

        private double SurfaceArea(NXObject obj)
        {
            if (obj is Face face)
            {
                return FaceArea(face);
            }
            if (obj is Body body)
            {
                return BodySurfaceArea(body);
            }
            if (obj is BodyFeature feature)
            {
                var total = 0.0;
                foreach (var featureBody in feature.GetBodies())
                {
                    total += BodySurfaceArea(featureBody);
                }
                return total;
            }
            throw new InvalidOperationException("area measurement requires a face, body, or body feature");
        }

        private double BodySurfaceArea(Body body)
        {
            var total = 0.0;
            foreach (var bodyFace in body.GetFaces())
            {
                total += FaceArea(bodyFace);
            }
            return total;
        }

        private double Volume(NXObject obj)
        {
            if (obj is Body body)
            {
                return BodyVolume(body);
            }
            if (obj is BodyFeature feature)
            {
                var total = 0.0;
                foreach (var featureBody in feature.GetBodies())
                {
                    total += BodyVolume(featureBody);
                }
                return total;
            }
            throw new InvalidOperationException("volume measurement requires a body or body feature");
        }

        private double BodyVolume(Body body)
        {
            var part = _session.Parts.Work
                ?? throw new InvalidOperationException("no work part for volume measurement");
            var massUnits = new[]
            {
                part.UnitCollection.GetBase("Area"),
                part.UnitCollection.GetBase("Volume"),
                part.UnitCollection.GetBase("Mass"),
                part.UnitCollection.GetBase("Length"),
                part.UnitCollection.GetBase("Force"),
            };
            var newMassProperties = Array.Find(
                part.MeasureManager.GetType().GetMethods(),
                candidate =>
                {
                    var parameters = candidate.GetParameters();
                    var bodyArrayElementType = parameters.Length == 3
                        ? parameters[2].ParameterType.GetElementType()
                        : null;
                    return candidate.Name == "NewMassProperties"
                        && parameters.Length == 3
                        && parameters[1].ParameterType == typeof(double)
                        && bodyArrayElementType?.FullName == "NXOpen.IBody";
                })
                ?? throw new InvalidOperationException("NX body-volume measurement API is unavailable");
            var bodyArrayType = newMassProperties.GetParameters()[2].ParameterType.GetElementType()
                ?? throw new InvalidOperationException("NX body-volume measurement API has no body-array element type");
            var bodies = Array.CreateInstance(bodyArrayType, 1);
            bodies.SetValue(body, 0);
            object? measurement = null;
            try
            {
                measurement = newMassProperties.Invoke(part.MeasureManager, new object[] { massUnits, 0.999, bodies });
                var volumeProperty = measurement.GetType().GetProperty("Volume")
                    ?? throw new InvalidOperationException("NX body-volume measurement returned no volume");
                var volume = volumeProperty.GetValue(measurement)
                    ?? throw new InvalidOperationException("NX body-volume measurement returned no value");
                return Convert.ToDouble(volume, CultureInfo.InvariantCulture);
            }
            finally
            {
                var dispose = measurement?.GetType().GetMethod("Dispose", System.Type.EmptyTypes);
                dispose?.Invoke(measurement, null);
            }
        }

        private double FaceArea(Face face)
        {
            var part = _session.Parts.Work
                ?? throw new InvalidOperationException("no work part for face-area measurement");
            var areaUnit = part.UnitCollection.GetBase("Area");
            var lengthUnit = part.UnitCollection.GetBase("Length");
            var newFaceProperties = Array.Find(
                part.MeasureManager.GetType().GetMethods(),
                candidate => candidate.Name == "NewFaceProperties" && candidate.GetParameters().Length == 4)
                ?? throw new InvalidOperationException("NX face-area measurement API is unavailable");
            var faceArrayType = newFaceProperties.GetParameters()[3].ParameterType.GetElementType()
                ?? throw new InvalidOperationException("NX face-area measurement API has no face-array element type");
            var faces = Array.CreateInstance(faceArrayType, 1);
            faces.SetValue(face, 0);
            object? measurement = null;
            try
            {
                measurement = newFaceProperties.Invoke(
                    part.MeasureManager,
                    new object[] { areaUnit, lengthUnit, 0.001, faces });
                var areaProperty = measurement.GetType().GetProperty("Area")
                    ?? throw new InvalidOperationException("NX face-area measurement returned no area");
                var area = areaProperty.GetValue(measurement)
                    ?? throw new InvalidOperationException("NX face-area measurement returned no value");
                return Convert.ToDouble(area, CultureInfo.InvariantCulture);
            }
            finally
            {
                var dispose = measurement?.GetType().GetMethod("Dispose", System.Type.EmptyTypes);
                dispose?.Invoke(measurement, null);
            }
        }

        private object Display(Dictionary<string, object?> inputs, DisplayAction action)
        {
            var handle = GetString(inputs, "handle");
            var obj = Resolve(handle);
            if (obj is not DisplayableObject displayable)
                throw new InvalidOperationException($"handle '{handle}' is not displayable");
            switch (action)
            {
                case DisplayAction.Highlight: displayable.Highlight(); break;
                case DisplayAction.Show: displayable.Unblank(); break;
                case DisplayAction.Hide: displayable.Blank(); break;
                case DisplayAction.Isolate:
                    var work = _session.Parts.Work ?? throw new InvalidOperationException("no work part");
                    foreach (var body in work.Bodies)
                    {
                        if (body is DisplayableObject bodyDisplayable && !ReferenceEquals(bodyDisplayable, displayable))
                            bodyDisplayable.Blank();
                    }
                    displayable.Unblank();
                    break;
            }
            return new { command = action.ToString().ToLowerInvariant(), undo_mark = "branch_c", changed = true, saved = false, details = new { handle } };
        }

        private object FitView()
        {
            _session.Parts.Work?.ModelingViews.WorkView.Fit();
            return new { command = "fit_view", undo_mark = (string?)null, changed = true, saved = false, details = new { } };
        }

        private object CreateBoxWithHole(Dictionary<string, object?> inputs)
        {
            var width = GetDouble(inputs, "width", 100.0);
            var depth = GetDouble(inputs, "depth", 60.0);
            var height = GetDouble(inputs, "height", 20.0);
            var diameter = GetDouble(inputs, "hole_diameter", 10.0);
            if (diameter >= width || diameter >= depth)
                throw new ArgumentException("hole_diameter must be smaller than both box width and depth");
            var radius = diameter / 2.0;
            var centerLeft = GetDouble(inputs, "hole_center_left", width / 2.0);
            var centerBottom = GetDouble(inputs, "hole_center_bottom", depth / 2.0);
            if (centerLeft < radius || centerLeft > width - radius)
                throw new ArgumentException("hole_center_left must keep the hole inside the box width");
            if (centerBottom < radius || centerBottom > depth - radius)
                throw new ArgumentException("hole_center_bottom must keep the hole inside the box depth");

            var root = @"D:\codes\modeling_assistant\work";
            Directory.CreateDirectory(root);
            var stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss_fff", CultureInfo.InvariantCulture);
            var path = Path.Combine(root, $"branch_c_chat_{stamp}.prt");
            var part = _session.Parts.NewDisplay(path, Part.Units.Millimeters);
            _session.Parts.SetWork(part);

            var block = part.Features.CreateBlockFeatureBuilder(null);
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

            Body? body = null;
            foreach (var candidate in part.Bodies)
            {
                body = (Body)candidate;
                break;
            }
            if (body is null) throw new InvalidOperationException("box creation did not produce a body");

            var cylinder = part.Features.CreateCylinderBuilder(null);
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
            return new
            {
                command = "create_box_with_hole",
                undo_mark = (string?)null,
                changed = true,
                saved = false,
                details = new
                {
                    part_name = part.Leaf,
                    part_path = part.FullPath,
                    width_mm = width,
                    depth_mm = depth,
                    height_mm = height,
                    hole_diameter_mm = diameter,
                    hole_center_left_mm = centerLeft,
                    hole_center_bottom_mm = centerBottom,
                }
            };
        }

        private object Update()
        {
            var mark = _session.SetUndoMark(Session.MarkVisibility.Invisible, "branch_c_update");
            var errors = _session.UpdateManager.DoUpdate(mark);
            return new { command = "update", undo_mark = "branch_c_update", changed = errors == 0, saved = false, details = new { errors } };
        }

        private object Save()
        {
            var work = _session.Parts.Work ?? throw new InvalidOperationException("no work part");
            var status = work.Save(BasePart.SaveComponents.True, BasePart.CloseAfterSave.False);
            status.Dispose();
            return new { command = "save", undo_mark = (string?)null, changed = false, saved = true, details = new { path = work.FullPath } };
        }

        private static string EntityKind(NXObject obj) => obj switch
        {
            Face => "face",
            Edge => "edge",
            Body => "body",
            Feature => "feature",
            Component => "component",
            _ => "other",
        };

        private static string Handle(NXObject obj) => $"tag:{(uint)obj.Tag}";

        private static NXObject Resolve(string handle)
        {
            if (!handle.StartsWith("tag:", StringComparison.OrdinalIgnoreCase) ||
                !uint.TryParse(handle[4..], NumberStyles.None, CultureInfo.InvariantCulture, out var raw))
                throw new InvalidOperationException($"invalid NX handle '{handle}'");
            var obj = NXObjectManager.GetObjectFromUInt(raw) as NXObject;
            return obj ?? throw new InvalidOperationException($"NX object not found for '{handle}'");
        }

        private static string GetString(Dictionary<string, object?> inputs, string key)
            => inputs.TryGetValue(key, out var raw) && raw is JsonElement value && value.ValueKind == JsonValueKind.String
                ? value.GetString() ?? ""
                : raw?.ToString() ?? "";

        private static bool GetBool(Dictionary<string, object?> inputs, string key, bool fallback)
            => inputs.TryGetValue(key, out var raw) && raw is JsonElement value && value.ValueKind == JsonValueKind.True
                ? true
                : inputs.TryGetValue(key, out raw) && raw is JsonElement falseValue && falseValue.ValueKind == JsonValueKind.False
                    ? false
                    : fallback;

        private static double GetDouble(Dictionary<string, object?> inputs, string key, double fallback)
        {
            if (!inputs.TryGetValue(key, out var raw)) return fallback;
            if (raw is JsonElement value)
            {
                if (value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out var number)) return number;
                if (value.ValueKind == JsonValueKind.String && double.TryParse(value.GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out number)) return number;
            }
            if (raw is double direct) return direct;
            return fallback;
        }

        private enum DisplayAction { Highlight, Show, Hide, Isolate }
    }
}
