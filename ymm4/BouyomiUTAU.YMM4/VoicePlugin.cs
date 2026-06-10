using YukkuriMovieMaker.Plugin;
using YukkuriMovieMaker.Plugin.Voice;

namespace BouyomiUTAU.YMM4;

public sealed class VoicePlugin : IVoicePlugin
{
    public string Name => "BouyomiUTAU（UTAU単独音）";
    public IEnumerable<IVoiceSpeaker> Voices => [new VoiceSpeaker()];
    public bool CanUpdateVoices => false;
    public bool IsVoicesCached => true;
    public Task UpdateVoicesAsync() => Task.CompletedTask;
    public PluginDetailsAttribute Details => new() { AuthorName = "BouyomiUTAU" };
}
