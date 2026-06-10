"""Japanese reading conversion shared by the desktop preview UI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

IME_SCRIPT = Path(__file__).with_name("windows_ime.ps1")


def contains_kanji(text: str) -> bool:
    return any("\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff" for char in text)


def apply_reading_dictionary(text: str, path: str | Path = "") -> str:
    dictionary = Path(path).expanduser() if path else None
    if not dictionary or not dictionary.is_file():
        return text
    for line in dictionary.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        separator = "=" if "=" in line else "\t" if "\t" in line else None
        if separator:
            word, reading = line.split(separator, 1)
            if word:
                text = text.replace(word, reading)
    return text


def to_hiragana(text: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)


def convert_japanese_reading(text: str, dictionary_path: str | Path = "") -> tuple[str, str | None]:
    """Apply the custom dictionary and, on Windows, ask Microsoft IME for kanji readings."""
    text = apply_reading_dictionary(text, dictionary_path)
    if not contains_kanji(text):
        return to_hiragana(text), None
    if os.name != "nt":
        return text, "漢字が残っています。Windows版GUIまたはYMM4ではMicrosoft日本語IMEで自動変換されます。"

    script = IME_SCRIPT
    environment = os.environ.copy()
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Text", text],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        reading = result.stdout.strip().splitlines()[-1]
        if reading:
            return to_hiragana(reading), None
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return text, "Microsoft日本語IMEで漢字を読みへ変換できませんでした。読み辞書で読みを指定してください。"
