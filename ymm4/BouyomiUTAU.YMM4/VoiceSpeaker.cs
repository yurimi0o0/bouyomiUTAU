using YukkuriMovieMaker.Plugin.Voice;

namespace BouyomiUTAU.YMM4;

internal sealed class VoiceSpeaker : IVoiceSpeaker
{
    static readonly SemaphoreSlim Semaphore = new(1);

    public string EngineName => "BouyomiUTAU";
    public string SpeakerName => "UTAU単独音";
    public string API => "BouyomiUTAU.Native";
    public string ID => "UTAU-Monophone";
    public bool IsVoiceDataCachingRequired => true;
    public SupportedTextFormat Format => SupportedTextFormat.Text;
    public IVoiceLicense? License => null;
    public IVoiceResource? Resource => null;

    public bool IsMatch(string api, string id) => api == API && id == ID;
    public IVoiceParameter CreateVoiceParameter() => new VoiceParameter();
    public IVoiceParameter MigrateParameter(IVoiceParameter currentParameter) =>
        currentParameter is VoiceParameter ? currentParameter : CreateVoiceParameter();
    public Task<string> ConvertKanjiToYomiAsync(string text, IVoiceParameter voiceParameter)
    {
        var value = voiceParameter as VoiceParameter ?? (VoiceParameter)CreateVoiceParameter();
        return Task.FromResult(JapaneseReadingConverter.ToHiragana(text, value.DictionaryPath));
    }

    public async Task<IVoicePronounce?> CreateVoiceAsync(
        string text, IVoicePronounce? pronounce, IVoiceParameter? parameter, string filePath)
    {
        var value = parameter as VoiceParameter ?? (VoiceParameter)CreateVoiceParameter();
        if (string.IsNullOrWhiteSpace(value.VoicebankPath))
            throw new InvalidOperationException("声質パラメーターの「UTAU音源フォルダー」を設定してください。");

        var reading = JapaneseReadingConverter.ToHiragana(text, value.DictionaryPath);
        await Semaphore.WaitAsync();
        try
        {
            await Task.Run(() => MonophoneSynthesizer.Synthesize(
                value.VoicebankPath, reading, filePath, value.Speed / 100.0, value.Crossfade, value.MoraDuration));
        }
        finally
        {
            Semaphore.Release();
        }
        return null;
    }
}
