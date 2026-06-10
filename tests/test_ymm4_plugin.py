from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "ymm4" / "BouyomiUTAU.YMM4"


class Ymm4PluginSourceTests(unittest.TestCase):
    def test_plugin_implements_voice_interfaces(self):
        plugin = (PLUGIN / "VoicePlugin.cs").read_text(encoding="utf-8")
        speaker = (PLUGIN / "VoiceSpeaker.cs").read_text(encoding="utf-8")
        self.assertIn("IVoicePlugin", plugin)
        self.assertIn("IVoiceSpeaker", speaker)
        self.assertIn("CreateVoiceAsync", speaker)

    def test_plugin_synthesizes_without_bouyomi_or_http(self):
        source = "\n".join(path.read_text(encoding="utf-8") for path in PLUGIN.glob("*.cs"))
        self.assertNotIn("HttpClient", source)
        self.assertNotIn("BouyomiChan", source)
        self.assertIn("MonophoneSynthesizer.Synthesize", source)

    def test_plugin_targets_current_ymm_framework(self):
        project = (PLUGIN / "BouyomiUTAU.YMM4.csproj").read_text(encoding="utf-8")
        self.assertIn("net10.0-windows10.0.19041.0", project)
        self.assertIn("YukkuriMovieMaker.Plugin", project)


if __name__ == "__main__":
    unittest.main()
