using System.Text;

namespace BouyomiUTAU.YMM4;

internal static class MonophoneSynthesizer
{
    const int OutputRate = 44100;
    static readonly HashSet<char> SmallKana = [.. "ゃゅょぁぃぅぇぉャュョァィゥェォ"];
    static readonly HashSet<char> Punctuation = [.. "、。,.!?！？…・ \t\r\n"];

    sealed record OtoEntry(string WavPath, double Offset, double Cutoff);

    public static void Synthesize(string voicebankPath, string text, string outputPath, double speed, int crossfadeMs)
    {
        var entries = LoadOto(voicebankPath);
        if (entries.Count == 0) throw new InvalidOperationException("oto.iniが見つかりません。単独音音源フォルダーを確認してください。");
        var output = new List<short>();
        var fade = crossfadeMs * OutputRate / 1000;
        var silence = new short[(int)(OutputRate * 0.16 / Math.Max(speed, 0.25))];

        foreach (var token in Tokenize(text))
        {
            if (token == "_") { output.AddRange(silence); continue; }
            if (!entries.TryGetValue(Normalize(token), out var entry) || !File.Exists(entry.WavPath)) continue;
            var clip = ReadWav(entry);
            clip = Resample(clip.Samples, clip.Rate, OutputRate, speed);
            var overlap = Math.Min(fade, Math.Min(output.Count, clip.Length));
            for (var i = 0; i < overlap; i++)
            {
                var ratio = (double)i / overlap;
                output[output.Count - overlap + i] = Clamp(output[output.Count - overlap + i] * (1 - ratio) + clip[i] * ratio);
            }
            output.AddRange(clip.Skip(overlap));
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
                var entry = new OtoEntry(Path.Combine(Path.GetDirectoryName(otoPath)!, wavName), Number(values, 1), Number(values, 3));
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
            if (Punctuation.Contains(character))
            {
                if (result.Count == 0 || result[^1] != "_") result.Add("_");
            }
            else if (SmallKana.Contains(character) && result.Count > 0) result[^1] += Normalize(character.ToString());
            else result.Add(Normalize(character.ToString()));
        }
        return result;
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

    static short[] Resample(short[] source, int sourceRate, int targetRate, double speed)
    {
        if (source.Length == 0) return source;
        var length = Math.Max(1, (int)Math.Round(source.Length * targetRate / sourceRate / Math.Max(speed, 0.25)));
        return Enumerable.Range(0, length).Select(i => source[Math.Min(source.Length - 1, (int)Math.Round(i * sourceRate * speed / targetRate))]).ToArray();
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
