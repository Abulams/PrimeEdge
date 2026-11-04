"""Neural voiceover for the PrimeEdge marketing film (edge-tts)."""
from __future__ import annotations

import asyncio
import json
import struct
import subprocess
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "public" / "audio"
FPS = 30
VOICE = "en-US-AndrewNeural"
RATE = "+15%"

LINES = [
    {
        "id": "hook",
        "text": "London open. Forty-seven signals screaming buy. And you still freeze.",
        "min_frames": 175,
    },
    {
        "id": "problem",
        "text": "You're not missing charts. You're missing a clear yes or no.",
        "min_frames": 150,
    },
    {
        "id": "pain",
        "text": "You park a stop on a round number. It tags you. Then price rips without you. Gold is running. You chase. Instant red. That's not trading. That's panic.",
        "min_frames": 310,
    },
    {
        "id": "aha",
        "text": "Here's the click. PrimeEdge doesn't yell buy. It tells you wait. Or take the trade. And it shows you why.",
        "min_frames": 255,
    },
    {
        "id": "solve",
        "text": "A stop based on how far similar trades usually dip. A real entry zone. One screen for why this setup, right now. You take it. The log writes itself.",
        "min_frames": 300,
    },
    {
        "id": "cta",
        "text": "Stop guessing. Trade with a reason. PrimeEdge. Get started.",
        "min_frames": 195,
    },
]


def mp3_duration(path: Path) -> float:
    try:
        from mutagen.mp3 import MP3

        return float(MP3(str(path)).info.length)
    except Exception:
        pass
    # Fallback: parse Xing/VBRI-less CBR-ish length from file size at 48kbps estimate is bad.
    # Use ffprobe if present.
    ffprobe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if ffprobe.returncode == 0 and ffprobe.stdout.strip():
        return float(ffprobe.stdout.strip())
    raise RuntimeError(f"Could not read duration for {path}")


def write_bed(seconds: float) -> None:
    sr = 44100
    n = int(seconds * sr)
    samples = bytearray()
    import math

    for i in range(n):
        t = i / sr
        env = min(1.0, t / 0.9) * min(1.0, (seconds - t) / 1.6)
        pad = (
            0.2 * math.sin(2 * math.pi * 73.42 * t)
            + 0.14 * math.sin(2 * math.pi * 110.0 * t)
            + 0.08 * math.sin(2 * math.pi * 146.83 * t)
        )
        lfo = 0.75 + 0.25 * math.sin(2 * math.pi * 0.11 * t)
        pulse = math.exp(-((t % 1.6) * 8)) * 0.07 * math.sin(2 * math.pi * 55 * t)
        s = max(-1.0, min(1.0, (pad * lfo + pulse) * env * 0.2))
        samples += struct.pack("<h", int(s * 32767))
    data = bytes(samples)
    header = bytearray(44)
    header[0:4] = b"RIFF"
    struct.pack_into("<I", header, 4, 36 + len(data))
    header[8:12] = b"WAVE"
    header[12:16] = b"fmt "
    struct.pack_into("<IHHIIHH", header, 16, 16, 1, 1, sr, sr * 2, 2, 16)
    header[36:40] = b"data"
    struct.pack_into("<I", header, 40, len(data))
    (AUDIO / "bed.wav").write_bytes(bytes(header) + data)


async def synth(line: dict) -> dict:
    out = AUDIO / f"{line['id']}.mp3"
    last_error = None
    for attempt in range(4):
        try:
            communicate = edge_tts.Communicate(line["text"], VOICE, rate=RATE)
            await communicate.save(str(out))
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1.2 * (attempt + 1))
    if last_error:
        raise last_error
    dur = mp3_duration(out)
    frames = max(line["min_frames"], math_ceil((dur + 0.35) * FPS))
    print(f"{line['id']}: {dur:.2f}s → {frames} frames")
    return {"id": line["id"], "seconds": round(dur, 2), "frames": frames}


def math_ceil(x: float) -> int:
    return int(x) if int(x) == x else int(x) + 1


async def main() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    try:
        import mutagen  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "mutagen"])

    timings = []
    for line in LINES:
        out = AUDIO / f"{line['id']}.mp3"
        if out.exists() and out.stat().st_size > 1000 and line["id"] != "cta":
            dur = mp3_duration(out)
            frames = max(line["min_frames"], math_ceil((dur + 0.35) * FPS))
            print(f"{line['id']}: {dur:.2f}s → {frames} frames (cached)")
            timings.append({"id": line["id"], "seconds": round(dur, 2), "frames": frames})
            continue
        timings.append(await synth(line))

    total = sum(s["frames"] for s in timings)
    write_bed(total / FPS + 0.6)
    timing_path = ROOT / "src" / "compositions" / "MarketingHero" / "timing.ts"
    body = f"""export const FPS = {FPS};

export const MARKETING_SCENES = {json.dumps(timings, indent=2)} as const;

export const MARKETING_TOTAL_FRAMES = {total};

export const MARKETING_TIMELINE = MARKETING_SCENES.reduce<
  {{ id: string; seconds: number; frames: number; from: number }}[]
>((acc, scene) => {{
  const from = acc.length ? acc[acc.length - 1].from + acc[acc.length - 1].frames : 0;
  acc.push({{ ...scene, from }});
  return acc;
}}, []);
"""
    timing_path.write_text(body, encoding="utf-8")
    print(f"total: {total} frames ({total / FPS:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
