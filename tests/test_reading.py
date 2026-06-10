from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bouyomi_utau.reading import apply_reading_dictionary, contains_kanji, convert_japanese_reading


class ReadingTests(unittest.TestCase):
    def test_custom_dictionary_replaces_words_before_synthesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            dictionary = Path(tmp) / "reading.txt"
            dictionary.write_text("# comment\n今日=きょう\nYMM4\tわいえむえむふぉー\n", encoding="utf-8")
            self.assertEqual(apply_reading_dictionary("今日のYMM4", dictionary), "きょうのわいえむえむふぉー")

    def test_katakana_is_normalized_without_ime(self):
        reading, warning = convert_japanese_reading("コンニチハ")
        self.assertEqual(reading, "こんにちは")
        self.assertIsNone(warning)

    def test_windows_ime_bridge_invokes_explicit_powershell_script(self):
        completed = __import__("subprocess").CompletedProcess([], 0, stdout="キョウハ\n", stderr="")
        with patch("bouyomi_utau.reading.os.name", "nt"), patch("bouyomi_utau.reading.subprocess.run", return_value=completed) as run:
            reading, warning = convert_japanese_reading("今日は")
        self.assertEqual(reading, "きょうは")
        self.assertIsNone(warning)
        command = run.call_args.args[0]
        self.assertIn("windows_ime.ps1", " ".join(command))
        self.assertIn("-File", command)

    def test_ime_bridge_declares_ifelanguage(self):
        script = (Path(__file__).resolve().parents[1] / "bouyomi_utau" / "windows_ime.ps1").read_text(encoding="utf-8")
        self.assertIn("interface IFELanguage", script)
        self.assertIn("GetPhonetic", script)
        self.assertIn("46b73c9c-0e62-41ee-86c0-2f8997777f48", script)

    def test_non_windows_warns_when_kanji_remains(self):
        with patch("bouyomi_utau.reading.os.name", "posix"):
            reading, warning = convert_japanese_reading("今日は")
        self.assertTrue(contains_kanji(reading))
        self.assertIsNotNone(warning)


if __name__ == "__main__":
    unittest.main()
