using System.Runtime.InteropServices;

namespace BouyomiUTAU.YMM4;

/// <summary>Uses the Japanese Microsoft IME dictionary to obtain readings without a server.</summary>
internal static class JapaneseReadingConverter
{
    [ComImport]
    [Guid("019F7152-E6DB-11d0-83C3-00C04FDDB82E")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IFELanguage
    {
        int Open();
        int Close();
        int GetJMorphResult(uint request, uint mode, int inputLength, [MarshalAs(UnmanagedType.LPWStr)] string input, IntPtr info, out object result);
        int GetConversionModeCaps(ref uint caps);
        int GetPhonetic([MarshalAs(UnmanagedType.BStr)] string value, int start, int length, [MarshalAs(UnmanagedType.BStr)] out string result);
        int GetConversion([MarshalAs(UnmanagedType.BStr)] string value, int start, int length, [MarshalAs(UnmanagedType.BStr)] out string result);
    }

    public static string ToHiragana(string text, string dictionaryPath = "")
    {
        text = ApplyDictionary(text, dictionaryPath);
        if (!text.Any(IsKanji)) return text;
        IFELanguage? language = null;
        try
        {
            var type = Type.GetTypeFromProgID("MSIME.Japan")
                ?? Type.GetTypeFromCLSID(new Guid("46b73c9c-0e62-41ee-86c0-2f8997777f48"))
                ?? throw new InvalidOperationException("Microsoft日本語IMEが見つかりません。Windowsの日本語言語機能を追加してください。");
            language = Activator.CreateInstance(type) as IFELanguage
                ?? throw new InvalidOperationException("Microsoft日本語IMEを起動できませんでした。");
            Marshal.ThrowExceptionForHR(language.Open());
            Marshal.ThrowExceptionForHR(language.GetPhonetic(text, 1, -1, out var reading));
            return ToHiraganaCharacters(reading);
        }
        finally
        {
            language?.Close();
        }
    }

    static string ApplyDictionary(string text, string path)
    {
        if (string.IsNullOrWhiteSpace(path) || !File.Exists(path)) return text;
        foreach (var line in File.ReadLines(path))
        {
            var trimmed = line.Trim();
            if (trimmed.Length == 0 || trimmed.StartsWith('#')) continue;
            var parts = trimmed.Split(['=', '\t'], 2);
            if (parts.Length == 2 && parts[0].Length > 0) text = text.Replace(parts[0], parts[1]);
        }
        return text;
    }

    static bool IsKanji(char c) => c is >= '\u3400' and <= '\u9fff' or >= '\uf900' and <= '\ufaff';
    static string ToHiraganaCharacters(string value) => string.Concat(value.Select(c => c is >= 'ァ' and <= 'ヶ' ? (char)(c - 0x60) : c));
}
