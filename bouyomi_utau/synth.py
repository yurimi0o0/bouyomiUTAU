from __future__ import annotations

from array import array
from dataclasses import dataclass
from pathlib import Path
import io
import wave

SMALL_KANA = set("ゃゅょぁぃぅぇぉャュョァィゥェォ")
PUNCTUATION = set("、。,.!?！？…・ \t\r\n")
VOWELS = {vowel: set(chars) for vowel, chars in {"あ": "あかがさざただなはばぱまゃやらわぁ", "い": "いきぎしじちにひびぴみりゐぃ", "う": "うくぐすずつぬふぶぷむゅゆるぅ", "え": "えけげせぜてでねへべぺめれゑぇ", "お": "おこごそぞとどのほぼぽもょよろをぉ"}.items()}


@dataclass(frozen=True)
class OtoEntry:
    wav: Path
    alias: str
    offset_ms: float = 0
    consonant_ms: float = 0
    cutoff_ms: float = 0
    preutter_ms: float = 0
    overlap_ms: float = 0


def normalize_alias(value: str) -> str:
    """Normalize an alias so hiragana input can find katakana voicebank entries."""
    value = value.strip().lstrip("- ").rstrip(" R")
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in value)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for char in text:
        if char in "っッ":
            tokens.append("~")
        elif char == "ー" and tokens:
            last = tokens[-1][-1]
            tokens.extend(vowel for vowel, chars in VOWELS.items() if last in chars)
        elif char in PUNCTUATION:
            pause = "__" if char in "。.!?！？" else "~" if char.isspace() else "_"
            if not tokens or tokens[-1] != pause:
                tokens.append(pause)
        elif char in SMALL_KANA and tokens:
            tokens[-1] += normalize_alias(char)
        else:
            tokens.append(normalize_alias(char))
    return tokens


def load_oto(voicebank: Path) -> dict[str, OtoEntry]:
    entries: dict[str, OtoEntry] = {}
    oto_files = list(voicebank.rglob("oto.ini"))
    for oto_file in oto_files:
        raw = oto_file.read_bytes()
        for encoding in ("utf-8-sig", "cp932"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            continue
        for line in text.splitlines():
            if "=" not in line:
                continue
            wav_name, values = line.split("=", 1)
            parts = values.split(",")
            alias = parts[0].strip() or Path(wav_name).stem
            nums = []
            for value in parts[1:6]:
                try:
                    nums.append(float(value or 0))
                except ValueError:
                    nums.append(0.0)
            nums += [0.0] * (5 - len(nums))
            entry = OtoEntry(oto_file.parent / wav_name, alias, *nums)
            entries[normalize_alias(alias)] = entry
            entries.setdefault(normalize_alias(Path(wav_name).stem), entry)
    return entries


def _read_samples(entry: OtoEntry, rate: int) -> array:
    with wave.open(str(entry.wav), "rb") as source:
        channels, width, source_rate, frames = (
            source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes()
        )
        data = source.readframes(frames)
    if width != 2:
        raise ValueError(f"16-bit WAV のみ対応しています: {entry.wav.name}")
    samples = array("h")
    samples.frombytes(data)
    if channels > 1:
        samples = array("h", (sum(samples[i:i + channels]) // channels for i in range(0, len(samples), channels)))
    start = max(0, round(entry.offset_ms * source_rate / 1000))
    if entry.cutoff_ms > 0:
        end = max(start, len(samples) - round(entry.cutoff_ms * source_rate / 1000))
    elif entry.cutoff_ms < 0:
        end = min(len(samples), start + round(abs(entry.cutoff_ms) * source_rate / 1000))
    else:
        end = len(samples)
    samples = samples[start:end]
    if source_rate != rate and samples:
        new_len = max(1, round(len(samples) * rate / source_rate))
        samples = array("h", (samples[min(len(samples) - 1, round(i * source_rate / rate))] for i in range(new_len)))
    return samples


def _mora_factor(token: str, previous: str | None, following: str | None, strength: float) -> float:
    """Vary mora timing like mechanical Japanese speech instead of using a metronomic grid."""
    factor = 1.0
    if token and token[-1] in "んン":
        factor *= 1.12
    if previous is None or previous in {"~", "_", "__"}:
        factor *= 1.08
    if following in {"_", "__", None}:
        factor *= 1.16
    elif following == "~":
        factor *= 0.92
    if token and token[0] in "かきくけこたちつてとぱぴぷぺぽ":
        factor *= 0.94
    return 1.0 + (factor - 1.0) * max(0.0, min(1.0, strength))


def _render_mora(clip: array, entry: OtoEntry, rate: int, target: int) -> array:
    if not clip:
        return clip
    fixed = min(len(clip), target, round(rate * min(entry.consonant_ms or 65, target * 1000 / rate * 0.7) / 1000))
    onset = clip[:fixed]
    vowel_source = clip[fixed:] or clip[-1:]
    vowel_target = max(0, target - len(onset))
    rendered = onset + array("h", (vowel_source[min(len(vowel_source) - 1, i * len(vowel_source) // max(1, vowel_target))] for i in range(vowel_target)))
    fade_in = min(len(rendered), round(rate * 0.003))
    for i in range(fade_in):
        rendered[i] = round(rendered[i] * i / max(1, fade_in))
    return rendered


def synthesize(voicebank: Path, text: str, speed: float = 1.0, crossfade_ms: int = 25, rate: int = 44100, mora_ms: int = 170, naturalness: float = 0.8) -> tuple[bytes, list[str]]:
    entries = load_oto(voicebank)
    if not entries:
        raise ValueError("oto.ini が見つかりません。UTAU音源フォルダーを指定してください。")
    output = array("h")
    missing: list[str] = []
    fade = round(crossfade_ms * rate / 1000)
    tokens = tokenize(text)
    previous: str | None = None
    for index, token in enumerate(tokens):
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if token in {"~", "_", "__"}:
            pause_ms = {"~": 70, "_": 150, "__": 280}[token]
            output.extend(array("h", [0]) * round(rate * pause_ms / 1000 / max(speed, 0.25)))
            previous = token
            continue
        entry = entries.get(normalize_alias(token))
        if not entry or not entry.wav.exists():
            missing.append(token)
            continue
        clip = _read_samples(entry, rate)
        if clip:
            factor = _mora_factor(token, previous, following, naturalness)
            target = max(1, round(rate * mora_ms * factor / 1000 / max(speed, 0.25)))
            clip = _render_mora(clip, entry, rate, target)
        configured_fade = round(rate * (entry.overlap_ms or min(crossfade_ms, max(8, entry.preutter_ms * 0.35))) / 1000)
        overlap = min(configured_fade or fade, len(output), len(clip))
        if overlap:
            start = len(output) - overlap
            for i in range(overlap):
                ratio = i / overlap
                output[start + i] = max(-32768, min(32767, round(output[start + i] * (1 - ratio) + clip[i] * ratio)))
            output.extend(clip[overlap:])
        else:
            output.extend(clip)
        previous = token
    if not output:
        output = array("h", [0]) * round(rate * 0.1)
    peak = max(abs(sample) for sample in output) or 1
    gain = min(1.0, 30000 / peak)
    if gain < 1:
        output = array("h", (round(sample * gain) for sample in output))
    target = io.BytesIO()
    with wave.open(target, "wb") as result:
        result.setnchannels(1)
        result.setsampwidth(2)
        result.setframerate(rate)
        result.writeframes(output.tobytes())
    return target.getvalue(), missing
