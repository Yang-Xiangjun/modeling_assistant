// Interactive NX journal launcher for the compiled Branch C smoke journal.
// Use this file with Tools > Journal > Play after building NxBridge.csproj.
using System;
using System.Reflection;

public class BranchCSmokeLauncher
{
    // NX Open's compiled-user-function runner looks for the conventional
    // ufusr entry point. Keep the journal launcher available as well so the
    // same assembly can be loaded from either NX entry point.
    public static void ufusr(string[] args)
    {
        Main(args);
    }

    public static void Main(string[] args)
    {
        string assemblyPath = @"D:\codes\modeling_assistant\nx_bridge\bin\Debug\net8.0-windows\Drawgen.NxBridgeBranchC.dll";
        // The Branch C assembly has a stable, distinct identity so it can be
        // loaded while an older smoke assembly remains in the NX AppDomain.
        Assembly assembly = Assembly.LoadFrom(assemblyPath);
        Type journal = assembly.GetType("BranchCSmokeRuntime", throwOnError: true);
        MethodInfo entryPoint = journal.GetMethod("Main", BindingFlags.Public | BindingFlags.Static);
        if (entryPoint == null)
        {
            throw new InvalidOperationException("BranchCSmokeRuntime.Main was not found.");
        }
        entryPoint.Invoke(null, new object[] { args ?? Array.Empty<string>() });
    }

    public static int GetUnloadOption(string dummy)
    {
        return 0;
    }
}
