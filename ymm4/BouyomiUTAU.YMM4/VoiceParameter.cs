using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using YukkuriMovieMaker.Controls;
using YukkuriMovieMaker.Plugin.Voice;

namespace BouyomiUTAU.YMM4;

internal sealed class VoiceParameter : VoiceParameterBase
{
    string voicebankPath = "";
    int speed = 100;
    int crossfade = 25;

    [Display(Name = "UTAU音源フォルダー", Description = "oto.iniが入っている単独音音源フォルダーの絶対パス")]
    [DefaultValue("")]
    public string VoicebankPath { get => voicebankPath; set => Set(ref voicebankPath, value); }

    [Display(Name = "読み上げ速度", Description = "100が標準速度です")]
    [TextBoxSlider("F0", "%", 50, 200, Delay = -1)]
    [Range(50, 200)]
    [DefaultValue(100)]
    public int Speed { get => speed; set => Set(ref speed, value); }

    [Display(Name = "音のつなぎ", Description = "隣り合う単独音を重ねる長さです")]
    [TextBoxSlider("F0", " ms", 0, 100, Delay = -1)]
    [Range(0, 100)]
    [DefaultValue(25)]
    public int Crossfade { get => crossfade; set => Set(ref crossfade, value); }
}
