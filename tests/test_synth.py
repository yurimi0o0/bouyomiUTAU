from array import array
from pathlib import Path
import tempfile
import unittest
import wave

from bouyomi_utau.synth import load_oto, normalize_alias, synthesize, tokenize


class SynthTests(unittest.TestCase):
    def test_tokenize_normalizes_and_joins_small_kana(self):
        self.assertEqual(tokenize("キャ、きょ。"), ["きゃ", "_", "きょ", "__"])

    def test_tokenize_distinguishes_pauses_sokuon_and_long_vowels(self):
        self.assertEqual(tokenize("コーヒー、かった。"), ["こ", "お", "ひ", "い", "_", "か", "~", "た", "__"])

    def test_normalize_alias_removes_common_prefix_and_suffix(self):
        self.assertEqual(normalize_alias("- カ R"), "か")

    def test_load_and_synthesize_voicebank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with wave.open(str(root / "a.wav"), "wb") as wav:
                wav.setparams((1, 2, 8000, 0, "NONE", ""))
                wav.writeframes(array("h", [1000] * 800).tobytes())
            (root / "oto.ini").write_text("a.wav=あ,0,0,0,0,0\n", encoding="utf-8")
            self.assertIn("あ", load_oto(root))
            result, missing = synthesize(root, "あい", rate=8000)
            self.assertGreater(len(result), 44)
            self.assertEqual(missing, ["い"])
            self.assertEqual(result[:4], b"RIFF")


class GuiHelperTests(unittest.TestCase):
    def test_settings_round_trip(self):
        from bouyomi_utau.gui import load_settings, save_settings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            save_settings({"voicebank": "voice", "speed": "1.2"}, path)
            self.assertEqual(load_settings(path), {"voicebank": "voice", "speed": "1.2"})

    def test_invalid_numeric_setting_uses_default(self):
        from bouyomi_utau.gui import numeric_setting

        self.assertEqual(numeric_setting({"mora": "broken"}, "mora", 170), 170)

    def test_invalid_settings_are_ignored(self):
        from bouyomi_utau.gui import load_settings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            self.assertEqual(load_settings(path), {})


class NaturalTimingTests(unittest.TestCase):
    def test_natural_timing_varies_phrase_final_duration(self):
        from bouyomi_utau.synth import _mora_factor

        self.assertGreater(_mora_factor("あ", "か", None, 1.0), _mora_factor("あ", "か", "き", 1.0))
        self.assertEqual(_mora_factor("あ", "か", None, 0.0), 1.0)

    def test_vowel_extension_preserves_recorded_pitch(self):
        import math
        from bouyomi_utau.synth import _fit_vowel

        rate = 8000
        source = array("h", (round(12000 * math.sin(2 * math.pi * 200 * i / rate)) for i in range(rate // 5)))
        fitted = _fit_vowel(source, rate // 2, rate)
        crossings = [i for i in range(1, len(fitted)) if fitted[i - 1] <= 0 < fitted[i]]
        frequency = len(crossings) / (len(fitted) / rate)
        self.assertAlmostEqual(frequency, 200, delta=8)

    def test_repeated_vowel_is_joined_as_a_long_vowel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, value in (("i", 1200), ("a", 800)):
                with wave.open(str(root / f"{name}.wav"), "wb") as wav:
                    wav.setparams((1, 2, 8000, 0, "NONE", ""))
                    wav.writeframes(array("h", [value] * 2400).tobytes())
            (root / "oto.ini").write_text("i.wav=い,0,60,0,0,20\na.wav=あ,0,60,0,0,20\n", encoding="utf-8")
            joined, _ = synthesize(root, "いい", rate=8000, naturalness=0)
            separate, _ = synthesize(root, "いあ", rate=8000, naturalness=0)
            with wave.open(__import__('io').BytesIO(joined), "rb") as wav:
                joined_frames = wav.getnframes()
            with wave.open(__import__('io').BytesIO(separate), "rb") as wav:
                separate_frames = wav.getnframes()
            self.assertLess(joined_frames, separate_frames)

    def test_long_recording_is_shortened_to_mora_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with wave.open(str(root / "a.wav"), "wb") as wav:
                wav.setparams((1, 2, 8000, 0, "NONE", ""))
                wav.writeframes(array("h", [1000] * 8000).tobytes())
            (root / "oto.ini").write_text("a.wav=あ,0,80,0,0,20\n", encoding="utf-8")
            result, _ = synthesize(root, "ああ", rate=8000, mora_ms=170, crossfade_ms=20)
            with wave.open(__import__('io').BytesIO(result), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            self.assertLess(duration, 0.4)
            self.assertGreater(duration, 0.25)


if __name__ == "__main__":
    unittest.main()
