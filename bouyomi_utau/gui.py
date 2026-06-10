"""Native desktop interface for BouyomiUTAU."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .reading import convert_japanese_reading
from .synth import load_oto, synthesize

APP_NAME = "BouyomiUTAU"
CONFIG_FILE = Path.home() / ".bouyomi_utau.json"


def load_settings(path: Path = CONFIG_FILE) -> dict[str, str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict[str, str], path: Path = CONFIG_FILE) -> None:
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def numeric_setting(settings: dict[str, str], name: str, default: float) -> float:
    try:
        return float(settings.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def available_player() -> list[str] | None:
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay"]
    for command in ("aplay", "paplay"):
        if shutil.which(command):
            return [command]
    return None


def play_wav(path: Path) -> None:
    if os.name == "nt":
        import winsound
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    player = available_player()
    if not player:
        raise RuntimeError("再生ソフトが見つかりません。［WAVを保存］から再生してください。")
    subprocess.Popen([*player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BouyomiUTAU - UTAU単独音読み上げ")
        self.root.geometry("820x720")
        self.root.minsize(700, 620)
        self.wav_data: bytes | None = None
        self.temp_wav = Path(tempfile.gettempdir()) / "bouyomi_utau_preview.wav"
        settings = load_settings()
        self.voicebank = tk.StringVar(value=settings.get("voicebank", ""))
        self.dictionary = tk.StringVar(value=settings.get("dictionary", ""))
        self.speed = tk.DoubleVar(value=numeric_setting(settings, "speed", 1.0))
        self.mora = tk.IntVar(value=round(numeric_setting(settings, "mora", 170)))
        self.crossfade = tk.IntVar(value=round(numeric_setting(settings, "crossfade", 25)))
        self.naturalness = tk.IntVar(value=round(numeric_setting(settings, "naturalness", 80)))
        self.status = tk.StringVar(value="UTAU音源フォルダーを選んでください。")
        self.reading = tk.StringVar(value="")
        self._build()

    def _build(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Yu Gothic UI", 20, "bold"))
        style.configure("Heading.TLabel", font=("Yu Gothic UI", 11, "bold"))
        style.configure("Accent.TButton", font=("Yu Gothic UI", 11, "bold"), padding=(18, 10))
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="BouyomiUTAU", style="Title.TLabel").pack(anchor="w")
        ttk.Label(container, text="YMM4と同じモーラ長・音のつなぎ・読み辞書で単独音を試聴します。", foreground="#666").pack(anchor="w", pady=(0, 16))

        self._path_row(container, "1. UTAU音源フォルダー", self.voicebank, self.choose_voicebank, "音源を確認", self.inspect_voicebank)
        self._path_row(container, "読み辞書（任意・表記=よみ）", self.dictionary, self.choose_dictionary, "IME動作確認", self.check_ime)

        ttk.Separator(container).pack(fill="x", pady=15)
        ttk.Label(container, text="2. しゃべらせる言葉（漢字対応）", style="Heading.TLabel").pack(anchor="w")
        self.text = tk.Text(container, height=7, wrap="word", font=("Yu Gothic UI", 13), padx=10, pady=10)
        self.text.pack(fill="both", expand=True, pady=(7, 7))
        self.text.insert("1.0", "こんにちは、今日はいい天気ですね。")
        ttk.Label(container, textvariable=self.reading, foreground="#667085", wraplength=750).pack(anchor="w", pady=(0, 10))

        settings = ttk.LabelFrame(container, text="3. 自然さの調整", padding=12)
        settings.pack(fill="x")
        self._slider(settings, 0, "話速", self.speed, 0.6, 1.6, lambda: f"{self.speed.get():.1f}×")
        self._slider(settings, 1, "一音の長さ", self.mora, 80, 350, lambda: f"{self.mora.get()} ms")
        self._slider(settings, 2, "音のつなぎ", self.crossfade, 0, 100, lambda: f"{self.crossfade.get()} ms")
        self._slider(settings, 3, "リズム自然さ", self.naturalness, 0, 100, lambda: f"{self.naturalness.get()} %")
        ttk.Label(settings, text="目安: 通常会話は一音140～180ms・リズム自然さ80%。", foreground="#777").grid(row=4, column=0, columnspan=3, sticky="w", pady=(7, 0))

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(18, 10))
        self.talk_button = ttk.Button(actions, text="▶ 読みを確認してしゃべる", style="Accent.TButton", command=self.generate_and_play)
        self.talk_button.pack(side="left")
        self.save_button = ttk.Button(actions, text="WAVを保存…", command=self.save_wav, state="disabled")
        self.save_button.pack(side="left", padx=8)
        ttk.Label(container, textvariable=self.status, foreground="#555", wraplength=750).pack(anchor="w")

    def _path_row(self, parent, title, variable, browse, extra_text=None, extra_command=None):
        ttk.Label(parent, text=title, style="Heading.TLabel").pack(anchor="w", pady=(5, 0))
        row = ttk.Frame(parent); row.pack(fill="x", pady=(5, 7))
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="参照…", command=browse).pack(side="left", padx=(8, 0))
        if extra_text:
            ttk.Button(row, text=extra_text, command=extra_command).pack(side="left", padx=(8, 0))

    def _slider(self, parent, row, title, variable, minimum, maximum, formatter):
        ttk.Label(parent, text=title, width=12).grid(row=row, column=0, sticky="w", pady=3)
        value = ttk.Label(parent, width=9)
        scale = ttk.Scale(parent, from_=minimum, to=maximum, variable=variable, length=300,
                          command=lambda _x: value.configure(text=formatter()))
        scale.grid(row=row, column=1, sticky="ew", padx=8); value.grid(row=row, column=2, sticky="w")
        value.configure(text=formatter()); parent.columnconfigure(1, weight=1)

    def choose_voicebank(self) -> None:
        path = filedialog.askdirectory(title="oto.iniが入っているUTAU音源フォルダーを選択")
        if path: self.voicebank.set(path); self.inspect_voicebank()

    def choose_dictionary(self) -> None:
        path = filedialog.askopenfilename(title="読み辞書を選択", filetypes=[("テキスト", "*.txt"), ("すべて", "*.*")])
        if path: self.dictionary.set(path); self._remember()

    def check_ime(self) -> None:
        reading, warning = convert_japanese_reading("今日は良い天気です", self.dictionary.get())
        self.reading.set(f"IME動作確認: {reading}" + (f"  ⚠ {warning}" if warning else "  ✓ 漢字変換できます"))
        self.status.set("IME動作確認が完了しました。")

    def inspect_voicebank(self) -> None:
        path = Path(self.voicebank.get()).expanduser()
        entries = load_oto(path) if path.is_dir() else {}
        self.status.set(f"✓ {path.name}: {len(entries)}個のエイリアスを読み込みました。" if entries else "音源を読み込めません。oto.iniが入ったフォルダーを選んでください。")
        if entries: self._remember()

    def _remember(self) -> None:
        try:
            save_settings({"voicebank": self.voicebank.get(), "dictionary": self.dictionary.get(), "speed": str(self.speed.get()), "mora": str(self.mora.get()), "crossfade": str(self.crossfade.get()), "naturalness": str(self.naturalness.get())})
        except OSError:
            pass

    def generate_and_play(self) -> None:
        voicebank = Path(self.voicebank.get()).expanduser(); text = self.text.get("1.0", "end").strip()
        if not voicebank.is_dir() or not text:
            messagebox.showwarning(APP_NAME, "UTAU音源フォルダーと、しゃべらせる言葉を入力してください。")
            return
        reading, warning = convert_japanese_reading(text, self.dictionary.get())
        self.reading.set(f"読み: {reading}" + (f"  ⚠ {warning}" if warning else ""))
        self.talk_button.configure(state="disabled"); self.status.set("読みを変換して、音声を作っています…")
        options = (self.speed.get(), self.crossfade.get(), self.mora.get(), self.naturalness.get() / 100)
        threading.Thread(target=self._synthesize, args=(voicebank, reading, *options), daemon=True).start()

    def _synthesize(self, voicebank: Path, reading: str, speed: float, crossfade: int, mora: int, naturalness: float) -> None:
        try:
            wav_data, missing = synthesize(voicebank, reading, speed=speed, crossfade_ms=crossfade, mora_ms=mora, naturalness=naturalness)
            self.temp_wav.write_bytes(wav_data); self.wav_data = wav_data
            self.root.after(0, self._synthesis_done, missing)
        except Exception as exc:
            self.root.after(0, self._synthesis_failed, str(exc))

    def _synthesis_done(self, missing: list[str]) -> None:
        self.talk_button.configure(state="normal"); self.save_button.configure(state="normal"); self._remember()
        note = f"（音源にない文字: {', '.join(dict.fromkeys(missing))}）" if missing else ""
        try: play_wav(self.temp_wav); self.status.set(f"再生しました。{note}")
        except RuntimeError as exc: self.status.set(f"音声を作成しました。{note}"); messagebox.showinfo(APP_NAME, str(exc))

    def _synthesis_failed(self, error: str) -> None:
        self.talk_button.configure(state="normal"); self.status.set("音声を作成できませんでした。"); messagebox.showerror(APP_NAME, error)

    def save_wav(self) -> None:
        if not self.wav_data: return
        path = filedialog.asksaveasfilename(title="音声を保存", defaultextension=".wav", filetypes=[("WAV音声", "*.wav")])
        if path: Path(path).write_bytes(self.wav_data); self.status.set(f"保存しました: {path}")


def main() -> None:
    root = tk.Tk(); App(root); root.mainloop()
