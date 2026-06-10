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
    int moraDuration = 170;
    string dictionaryPath = "";
    int naturalness = 80;

    [Display(Name = "UTAU音源フォルダー", Description = "oto.iniが入っている単独音音源フォルダーの絶対パス")]
    [DefaultValue("")]
    public string VoicebankPath { get => voicebankPath; set => Set(ref voicebankPath, value); }

    [Display(Name = "読み上げ速度", Description = "100が標準速度です")]
    [TextBoxSlider("F0", "%", 50, 200, Delay = -1)]
    [Range(50, 200)]
    [DefaultValue(100)]
    public int Speed { get => speed; set => Set(ref speed, value); }

    [Display(Name = "一音の長さ", Description = "単独音をこの長さへ整えます。短いほど自然な早口になります")]
    [TextBoxSlider("F0", " ms", 80, 350, Delay = -1)]
    [Range(80, 350)]
    [DefaultValue(170)]
    public int MoraDuration { get => moraDuration; set => Set(ref moraDuration, value); }

    [Display(Name = "リズムの自然さ", Description = "文頭・文末・音の種類に応じて一音の長さを変化させます")]
    [TextBoxSlider("F0", "%", 0, 100, Delay = -1)]
    [Range(0, 100)]
    [DefaultValue(80)]
    public int Naturalness { get => naturalness; set => Set(ref naturalness, value); }

    [Display(Name = "音のつなぎ", Description = "隣り合う単独音を重ねる長さです")]
    [TextBoxSlider("F0", " ms", 0, 100, Delay = -1)]
    [Range(0, 100)]
    [DefaultValue(25)]
    public int Crossfade { get => crossfade; set => Set(ref crossfade, value); }

    [Display(Name = "読み辞書", Description = "任意。『単語=よみ』形式のUTF-8テキストファイルです")]
    [DefaultValue("")]
    public string DictionaryPath { get => dictionaryPath; set => Set(ref dictionaryPath, value); }
}
