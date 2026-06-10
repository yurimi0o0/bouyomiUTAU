param([Parameter(Mandatory=$true)][string]$Text)
$ErrorActionPreference = "Stop"
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("019F7152-E6DB-11d0-83C3-00C04FDDB82E"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IFELanguage {
    int Open(); int Close();
    int GetJMorphResult(uint request, uint mode, int inputLength, [MarshalAs(UnmanagedType.LPWStr)] string input, IntPtr info, out object result);
    int GetConversionModeCaps(ref uint caps);
    int GetPhonetic([MarshalAs(UnmanagedType.BStr)] string value, int start, int length, [MarshalAs(UnmanagedType.BStr)] out string result);
    int GetConversion([MarshalAs(UnmanagedType.BStr)] string value, int start, int length, [MarshalAs(UnmanagedType.BStr)] out string result);
}
public static class BouyomiUtauIme {
    public static string Read(string text) {
        Type type = Type.GetTypeFromProgID("MSIME.Japan") ?? Type.GetTypeFromCLSID(new Guid("46b73c9c-0e62-41ee-86c0-2f8997777f48"));
        if (type == null) throw new InvalidOperationException("Microsoft Japanese IME IFELanguage is unavailable.");
        IFELanguage ime = (IFELanguage)Activator.CreateInstance(type);
        Marshal.ThrowExceptionForHR(ime.Open());
        try { string result; Marshal.ThrowExceptionForHR(ime.GetPhonetic(text, 1, -1, out result)); return result; }
        finally { ime.Close(); Marshal.FinalReleaseComObject(ime); }
    }
}
'@
[BouyomiUtauIme]::Read($Text)
