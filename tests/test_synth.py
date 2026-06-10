from array import array
from pathlib import Path
import tempfile
import unittest
import wave

from bouyomi_utau.synth import load_oto, normalize_alias, synthesize, tokenize


class SynthTests(unittest.TestCase):
    def test_tokenize_normalizes_and_joins_small_kana(self):
        self.assertEqual(tokenize("キャ、きょ。"), ["きゃ", "_", "きょ", "_"])

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


if __name__ == "__main__":
    unittest.main()
