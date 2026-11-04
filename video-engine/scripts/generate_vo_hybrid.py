"""Neural voiceover for PrimeEdge Hybrid Film (Human + Product + Remotion).
Run: python scripts/generate_vo_hybrid.py
"""
from __future__ import annotations
import asyncio, math, subprocess, sys
from pathlib import Path
import edge_tts

ROOT  = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "public" / "audio"
FPS   = 30
VOICE = "en-US-AndrewNeural"
RATE  = "+8%"

LINES = [
    {
        "id": "hybrid_hook",
        "text": "The idea was right. The entry was wrong.",
        "min_frames": 90,
    },
    {
        "id": "hybrid_check",
        "text": "PrimeEdge checks whether the setup is still valid before you act.",
        "min_frames": 120,
    },
    {
        "id": "hybrid_explain",
        "text": "It compares the current setup with similar historical trades, shows how far those trades normally dip, and defines the zone where the idea is still valid.",
        "min_frames": 330,
    },
    {
        "id": "hybrid_restraint",
        "text": "Sometimes the best decision is to wait.",
        "min_frames": 150,
    },
    {
        "id": "hybrid_journal",
        "text": "Every decision is recorded with the reason behind it.",
        "min_frames": 120,
    },
    {
        "id": "hybrid_cta",
        "text": "Stop guessing. Run your first replay with PrimeEdge.",
        "min_frames": 90,
    },
]

def mp3_duration(path: Path) -> float:
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(path)).info.length)
    except Exception:
        pass
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode == 0 and r.stdout.strip():
        return float(r.stdout.strip())
    raise RuntimeError(f"Cannot read duration: {path}")

def math_ceil(x: float) -> int:
    return int(x) if int(x) == x else int(x) + 1

async def synth(line: dict) -> dict:
    out = AUDIO / f"{line['id']}.mp3"
    if out.exists():
        try:
            out.unlink()
        except Exception:
            pass
    last_err = None
    for attempt in range(5):
        try:
            comm = edge_tts.Communicate(line["text"], VOICE, rate=RATE)
            await comm.save(str(out))
            if out.exists() and out.stat().st_size > 500:
                last_err = None
                break
        except Exception as e:
            last_err = e
            await asyncio.sleep(2.0 * (attempt + 1))
    if last_err or not (out.exists() and out.stat().st_size > 500):
        if last_err:
            raise last_err
        raise RuntimeError(f"Failed to generate valid audio for {line['id']}")
    dur = mp3_duration(out)
    frames = max(line["min_frames"], math_ceil((dur + 0.3) * FPS))
    print(f"  {line['id']}: {dur:.2f}s -> {frames} frames")
    return {"id": line["id"], "seconds": round(dur, 2), "frames": frames}

async def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    AUDIO.mkdir(parents=True, exist_ok=True)
    print("Generating Hybrid voiceover lines...")
    timings = []
    for line in LINES:
        timings.append(await synth(line))
    total = sum(t["frames"] for t in timings)
    print(f"\nTotal Hybrid audio: {total} frames ({total / FPS:.1f}s)")

if __name__ == "__main__":
    asyncio.run(main())
