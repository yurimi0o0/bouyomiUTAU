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


def available_player() -> list[str] | None:
    """Return the command prefix for a system WAV player, if available."""
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
        self.root.geometry("760x580")
        self.root.minsize(640, 500)
        self.wav_data: bytes | None = None
        self.temp_wav = Path(tempfile.gettempdir()) / "bouyomi_utau_preview.wav"
        settings = load_settings()
        self.voicebank = tk.StringVar(value=settings.get("voicebank", ""))
        self.speed = tk.DoubleVar(value=float(settings.get("speed", "1.0")))
        self.status = tk.StringVar(value="UTAU音源フォルダーを選んでください。")
        self._build()

    def _build(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Yu Gothic UI", 20, "bold"))
        style.configure("Heading.TLabel", font=("Yu Gothic UI", 11, "bold"))
        style.configure("Accent.TButton", font=("Yu Gothic UI", 11, "bold"), padding=(18, 10))
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="BouyomiUTAU", style="Title.TLabel").pack(anchor="w")
        ttk.Label(container, text="UTAUの単独音をつないで、ひらがな・カタカナを読み上げます。", foreground="#666").pack(anchor="w", pady=(0, 22))

        ttk.Label(container, text="1. UTAU音源フォルダー", style="Heading.TLabel").pack(anchor="w")
        folder = ttk.Frame(container)
        folder.pack(fill="x", pady=(7, 5))
        ttk.Entry(folder, textvariable=self.voicebank).pack(side="left", fill="x", expand=True)
        ttk.Button(folder, text="参照…", command=self.choose_voicebank).pack(side="left", padx=(8, 0))
        ttk.Button(folder, text="音源を確認", command=self.inspect_voicebank).pack(side="left", padx=(8, 0))

        ttk.Separator(container).pack(fill="x", pady=20)
        ttk.Label(container, text="2. しゃべらせる言葉", style="Heading.TLabel").pack(anchor="w")
        self.text = tk.Text(container, height=9, wrap="word", font=("Yu Gothic UI", 13), padx=10, pady=10)
        self.text.pack(fill="both", expand=True, pady=(7, 12))
        self.text.insert("1.0", "こんにちは、きょうもいいてんきですね。")

        options = ttk.Frame(container)
        options.pack(fill="x")
        ttk.Label(options, text="話速").pack(side="left")
        ttk.Scale(options, from_=0.6, to=1.6, variable=self.speed, command=self._update_speed, length=180).pack(side="left", padx=8)
        self.speed_label = ttk.Label(options, text=f"{self.speed.get():.1f}×", width=5)
        self.speed_label.pack(side="left")
        ttk.Label(options, text="漢字はひらがなに直してください。", foreground="#777").pack(side="right")

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(18, 10))
        self.talk_button = ttk.Button(actions, text="▶ しゃべる", style="Accent.TButton", command=self.generate_and_play)
        self.talk_button.pack(side="left")
        self.save_button = ttk.Button(actions, text="WAVを保存…", command=self.save_wav, state="disabled")
        self.save_button.pack(side="left", padx=8)
        ttk.Label(container, textvariable=self.status, foreground="#555").pack(anchor="w")

    def _update_speed(self, _value: str = "") -> None:
        self.speed_label.configure(text=f"{self.speed.get():.1f}×")

    def choose_voicebank(self) -> None:
        path = filedialog.askdirectory(title="oto.iniが入っているUTAU音源フォルダーを選択")
        if path:
            self.voicebank.set(path)
            self.inspect_voicebank()

    def inspect_voicebank(self) -> None:
        path = Path(self.voicebank.get()).expanduser()
        entries = load_oto(path) if path.is_dir() else {}
        if entries:
            self.status.set(f"✓ {path.name}: {len(entries)}個のエイリアスを読み込みました。")
            self._remember()
        else:
            self.status.set("音源を読み込めません。oto.iniが入ったフォルダーを選んでください。")

    def _remember(self) -> None:
        try:
            save_settings({"voicebank": self.voicebank.get(), "speed": str(self.speed.get())})
        except OSError:
            pass

    def generate_and_play(self) -> None:
        voicebank = Path(self.voicebank.get()).expanduser()
        text = self.text.get("1.0", "end").strip()
        if not voicebank.is_dir() or not text:
            messagebox.showwarning(APP_NAME, "UTAU音源フォルダーと、しゃべらせる言葉を入力してください。")
            return
        self.talk_button.configure(state="disabled")
        self.status.set("音声を作っています…")
        threading.Thread(target=self._synthesize, args=(voicebank, text, self.speed.get()), daemon=True).start()

    def _synthesize(self, voicebank: Path, text: str, speed: float) -> None:
        try:
            wav_data, missing = synthesize(voicebank, text, speed=speed)
            self.temp_wav.write_bytes(wav_data)
            self.wav_data = wav_data
            self.root.after(0, self._synthesis_done, missing)
        except Exception as exc:
            self.root.after(0, self._synthesis_failed, str(exc))

    def _synthesis_done(self, missing: list[str]) -> None:
        self.talk_button.configure(state="normal")
        self.save_button.configure(state="normal")
        self._remember()
        note = f"（音源にない文字: {', '.join(missing)}）" if missing else ""
        try:
            play_wav(self.temp_wav)
            self.status.set(f"再生しました。{note}")
        except RuntimeError as exc:
            self.status.set(f"音声を作成しました。{note}")
            messagebox.showinfo(APP_NAME, str(exc))

    def _synthesis_failed(self, error: str) -> None:
        self.talk_button.configure(state="normal")
        self.status.set("音声を作成できませんでした。")
        messagebox.showerror(APP_NAME, error)

    def save_wav(self) -> None:
        if not self.wav_data:
            return
        path = filedialog.asksaveasfilename(title="音声を保存", defaultextension=".wav", filetypes=[("WAV音声", "*.wav")])
        if path:
            Path(path).write_bytes(self.wav_data)
            self.status.set(f"保存しました: {path}")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()
