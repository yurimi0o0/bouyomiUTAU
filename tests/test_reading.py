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

    def test_non_windows_warns_when_kanji_remains(self):
        with patch("bouyomi_utau.reading.os.name", "posix"):
            reading, warning = convert_japanese_reading("今日は")
        self.assertTrue(contains_kanji(reading))
        self.assertIsNotNone(warning)


if __name__ == "__main__":
    unittest.main()
