// Thin NX journal loader for the compiled Branch C smoke runtime.
//
// NX's interactive C# journal compiler has a smaller reference set than the
// NX2506 .NET 8 bridge project. Keep this file limited to core reflection so
// Tools > Journal > Play does not need to compile sockets or NXOpenUI types.
using System;
using System.IO;
using System.Reflection;

public class BranchCSmokeJournal
{
    public static void Main(string[] args)
    {
        string assemblyPath = Path.Combine(
            @"D:\codes\modeling_assistant",
            "nx_bridge",
            "bin",
            "Debug",
            "net8.0-windows",
            "Drawgen.NxBridgeBranchC.dll");
        if (!File.Exists(assemblyPath))
            throw new FileNotFoundException("Build the Branch C bridge before loading the journal.", assemblyPath);

        Assembly assembly = Assembly.LoadFrom(assemblyPath);
        Type runtime = assembly.GetType("BranchCSmokeRuntime", throwOnError: true);
        MethodInfo entryPoint = runtime.GetMethod("Main", BindingFlags.Public | BindingFlags.Static);
        if (entryPoint == null)
            throw new InvalidOperationException("BranchCSmokeRuntime.Main was not found.");
        entryPoint.Invoke(null, new object[] { args ?? new string[0] });
    }

    public static int GetUnloadOption(string dummy)
    {
        return 0;
    }
}
