using System.Text;

namespace BouyomiUTAU.YMM4;

internal static class MonophoneSynthesizer
{
    const int OutputRate = 44100;
    static readonly HashSet<char> SmallKana = [.. "ゃゅょぁぃぅぇぉャュョァィゥェォ"];
    static readonly HashSet<char> Punctuation = [.. "、。,.!?！？…・ \t\r\n"];

    sealed record OtoEntry(string WavPath, double Offset, double Consonant, double Cutoff, double Preutter, double Overlap);

    public static void Synthesize(string voicebankPath, string text, string outputPath, double speed, int crossfadeMs, int moraDurationMs, double naturalness)
    {
        var entries = LoadOto(voicebankPath);
        if (entries.Count == 0) throw new InvalidOperationException("oto.iniが見つかりません。単独音音源フォルダーを確認してください。");
        var output = new List<short>();
        var tokens = Tokenize(text).ToList();
        string? previous = null;
        for (var tokenIndex = 0; tokenIndex < tokens.Count; tokenIndex++)
        {
            var token = tokens[tokenIndex];
            var following = tokenIndex + 1 < tokens.Count ? tokens[tokenIndex + 1] : null;
            if (token is "~" or "_" or "__")
            {
                var pauseMs = token == "~" ? 70 : token == "_" ? 150 : 280;
                output.AddRange(new short[(int)(OutputRate * pauseMs / 1000 / Math.Max(speed, 0.25))]);
                previous = token;
                continue;
            }
            if (!entries.TryGetValue(Normalize(token), out var entry) || !File.Exists(entry.WavPath)) continue;
            var source = ReadWav(entry);
            var targetMs = moraDurationMs * MoraFactor(token, previous, following, naturalness) / Math.Max(speed, 0.25);
            var clip = RenderMora(source.Samples, source.Rate, entry, targetMs);
            var overlapMs = entry.Overlap > 0 ? entry.Overlap : Math.Min(crossfadeMs, Math.Max(8, entry.Preutter * 0.35));
            var configuredOverlap = (int)Math.Round(overlapMs * OutputRate / 1000);
            var overlap = Math.Min(configuredOverlap, Math.Min(output.Count, clip.Length));
            for (var i = 0; i < overlap; i++)
            {
                var ratio = (double)i / overlap;
                output[output.Count - overlap + i] = Clamp(output[output.Count - overlap + i] * (1 - ratio) + clip[i] * ratio);
            }
            output.AddRange(clip.Skip(overlap));
            previous = token;
        }
        if (output.Count == 0) output.AddRange(new short[OutputRate / 10]);
        NormalizeVolume(output);
        WriteWav(outputPath, output.ToArray(), OutputRate);
    }

    static Dictionary<string, OtoEntry> LoadOto(string voicebankPath)
    {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var result = new Dictionary<string, OtoEntry>();
        foreach (var otoPath in Directory.EnumerateFiles(voicebankPath, "oto.ini", SearchOption.AllDirectories))
        {
            var bytes = File.ReadAllBytes(otoPath);
            string content;
            try { content = new UTF8Encoding(false, true).GetString(bytes); }
            catch (DecoderFallbackException) { content = Encoding.GetEncoding(932).GetString(bytes); }
            foreach (var line in content.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries))
            {
                var equals = line.IndexOf('=');
                if (equals < 1) continue;
                var wavName = line[..equals];
                var values = line[(equals + 1)..].Split(',');
                var alias = values.ElementAtOrDefault(0)?.Trim();
                if (string.IsNullOrEmpty(alias)) alias = Path.GetFileNameWithoutExtension(wavName);
                var entry = new OtoEntry(
                    Path.Combine(Path.GetDirectoryName(otoPath)!, wavName),
                    Number(values, 1), Number(values, 2), Number(values, 3), Number(values, 4), Number(values, 5));
                result[Normalize(alias)] = entry;
                result.TryAdd(Normalize(Path.GetFileNameWithoutExtension(wavName)), entry);
            }
        }
        return result;
    }

    static double Number(string[] values, int index) =>
        index < values.Length && double.TryParse(values[index], out var value) ? value : 0;

    static IEnumerable<string> Tokenize(string text)
    {
        var result = new List<string>();
        foreach (var character in text)
        {
            if (character is 'っ' or 'ッ') result.Add("~");
            else if (character == 'ー' && result.Count > 0)
            {
                var vowel = LastVowel(result[^1]);
                if (vowel.Length > 0) result.Add(vowel);
            }
            else if (Punctuation.Contains(character))
            {
                var pause = "。.!?！？".Contains(character) ? "__" : char.IsWhiteSpace(character) ? "~" : "_";
                if (result.Count == 0 || result[^1] != pause) result.Add(pause);
            }
            else if (SmallKana.Contains(character) && result.Count > 0) result[^1] += Normalize(character.ToString());
            else result.Add(Normalize(character.ToString()));
        }
        return result;
    }

    static string LastVowel(string token)
    {
        const string a = "あかがさざただなはばぱまゃやらわぁ";
        const string i = "いきぎしじちにひびぴみりゐぃ";
        const string u = "うくぐすずつぬふぶぷむゅゆるぅ";
        const string e = "えけげせぜてでねへべぺめれゑぇ";
        const string o = "おこごそぞとどのほぼぽもょよろをぉ";
        var last = token.LastOrDefault();
        if (a.Contains(last)) return "あ"; if (i.Contains(last)) return "い"; if (u.Contains(last)) return "う";
        if (e.Contains(last)) return "え"; if (o.Contains(last)) return "お"; return "";
    }

    static string Normalize(string value)
    {
        value = value.Trim().TrimStart('-', ' ').TrimEnd('R', ' ');
        return string.Concat(value.Select(c => c is >= 'ァ' and <= 'ヶ' ? (char)(c - 0x60) : c));
    }

    static (short[] Samples, int Rate) ReadWav(OtoEntry entry)
    {
        using var reader = new BinaryReader(File.OpenRead(entry.WavPath));
        if (new string(reader.ReadChars(4)) != "RIFF") throw new InvalidDataException($"WAVではありません: {entry.WavPath}");
        reader.ReadInt32();
        if (new string(reader.ReadChars(4)) != "WAVE") throw new InvalidDataException($"WAVではありません: {entry.WavPath}");
        ushort channels = 0, bits = 0; int rate = 0; byte[]? data = null;
        while (reader.BaseStream.Position + 8 <= reader.BaseStream.Length)
        {
            var id = new string(reader.ReadChars(4)); var size = reader.ReadInt32(); var start = reader.BaseStream.Position;
            if (id == "fmt ") { if (reader.ReadUInt16() != 1) throw new InvalidDataException("PCM WAVのみ対応しています。"); channels = reader.ReadUInt16(); rate = reader.ReadInt32(); reader.ReadInt32(); reader.ReadUInt16(); bits = reader.ReadUInt16(); }
            else if (id == "data") data = reader.ReadBytes(size);
            reader.BaseStream.Position = Math.Min(reader.BaseStream.Length, start + size + (size & 1));
        }
        if (data is null || bits != 16 || channels == 0) throw new InvalidDataException("16-bit PCM WAVのみ対応しています。");
        var raw = new short[data.Length / 2]; Buffer.BlockCopy(data, 0, raw, 0, data.Length);
        var mono = channels == 1 ? raw : Enumerable.Range(0, raw.Length / channels).Select(i => Clamp(Enumerable.Range(0, channels).Average(c => raw[i * channels + c]))).ToArray();
        var startSample = Math.Max(0, (int)Math.Round(entry.Offset * rate / 1000));
        var end = entry.Cutoff > 0 ? Math.Max(startSample, mono.Length - (int)Math.Round(entry.Cutoff * rate / 1000)) : entry.Cutoff < 0 ? Math.Min(mono.Length, startSample + (int)Math.Round(-entry.Cutoff * rate / 1000)) : mono.Length;
        return (mono[startSample..end], rate);
    }

    static double MoraFactor(string token, string? previous, string? following, double strength)
    {
        var factor = 1.0;
        if (token.EndsWith('ん')) factor *= 1.12;
        if (previous is null or "~" or "_" or "__") factor *= 1.08;
        if (following is null or "_" or "__") factor *= 1.16;
        else if (following == "~") factor *= 0.92;
        if ("かきくけこたちつてとぱぴぷぺぽ".Contains(token[0])) factor *= 0.94;
        return 1 + (factor - 1) * Math.Clamp(strength, 0, 1);
    }

    static short[] RenderMora(short[] source, int sourceRate, OtoEntry entry, double targetMs)
    {
        if (source.Length == 0) return source;
        var targetLength = Math.Max(1, (int)Math.Round(targetMs * OutputRate / 1000));
        // Preserve the consonant/attack and compress the long sustained vowel separately.
        var fixedMs = entry.Consonant > 0 ? Math.Min(entry.Consonant, targetMs * 0.7) : Math.Min(65, targetMs * 0.4);
        var sourceFixed = Math.Min(source.Length, Math.Max(1, (int)Math.Round(fixedMs * sourceRate / 1000)));
        var targetFixed = Math.Min(targetLength, Math.Max(1, (int)Math.Round(fixedMs * OutputRate / 1000)));
        var result = new short[targetLength];
        for (var i = 0; i < targetFixed; i++)
            result[i] = source[Math.Min(sourceFixed - 1, (int)((long)i * sourceRate / OutputRate))];
        var vowelStart = Math.Min(source.Length - 1, sourceFixed);
        var vowelSourceLength = Math.Max(1, source.Length - vowelStart);
        var vowelTargetLength = targetLength - targetFixed;
        for (var i = 0; i < vowelTargetLength; i++)
            result[targetFixed + i] = source[vowelStart + Math.Min(vowelSourceLength - 1, (int)((long)i * vowelSourceLength / Math.Max(1, vowelTargetLength)))];
        ApplyEnvelope(result, 3);
        return result;
    }

    static void ApplyEnvelope(short[] samples, double fadeInMs)
    {
        var fadeIn = Math.Min(samples.Length, (int)Math.Round(fadeInMs * OutputRate / 1000));
        for (var i = 0; i < fadeIn; i++) samples[i] = Clamp(samples[i] * i / Math.Max(1.0, fadeIn));
    }

    static void NormalizeVolume(List<short> samples)
    {
        var peak = samples.Max(x => Math.Abs((int)x));
        if (peak <= 30000) return;
        var gain = 30000.0 / peak;
        for (var i = 0; i < samples.Count; i++) samples[i] = Clamp(samples[i] * gain);
    }

    static short Clamp(double value) => (short)Math.Clamp((int)Math.Round(value), short.MinValue, short.MaxValue);

    static void WriteWav(string path, short[] samples, int rate)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        using var writer = new BinaryWriter(File.Create(path));
        writer.Write(Encoding.ASCII.GetBytes("RIFF")); writer.Write(36 + samples.Length * 2); writer.Write(Encoding.ASCII.GetBytes("WAVEfmt "));
        writer.Write(16); writer.Write((ushort)1); writer.Write((ushort)1); writer.Write(rate); writer.Write(rate * 2); writer.Write((ushort)2); writer.Write((ushort)16);
        writer.Write(Encoding.ASCII.GetBytes("data")); writer.Write(samples.Length * 2); foreach (var sample in samples) writer.Write(sample);
    }
}
