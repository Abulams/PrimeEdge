"""Neural voiceover for PrimeEdge Regime Performance TikTok Video.
Problem-first approach: 69% vs 30% regime performance.
Run:  python scripts/generate_vo_regime.py
"""
from __future__ import annotations
import asyncio, json, struct, subprocess, sys, math
from pathlib import Path

import edge_tts

ROOT  = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "public" / "audio"
FPS   = 30
VOICE = "en-US-AndrewNeural"
RATE  = "+5%"   # Slightly slower for dramatic effect

# ── Regime Performance VO Lines ─────────────────────────────────────
LINES = [
    {
        "id": "regime_pain_hook",
        "text": "The same trading setup does not always perform the same way.",
        "min_frames": 90,
    },
    {
        "id": "regime_pain_escalation",
        "text": "We backtested 4,469 trades across 6 instruments from 2021 to 2025.",
        "min_frames": 150,
    },
    {
        "id": "regime_loss_realization",
        "text": "When the Dollar is weak, the regime produces a 69 percent win rate. When it's strong, only 30 percent.",
        "min_frames": 180,
    },
    {
        "id": "regime_reveal",
        "text": "That is a 2.3 times win-rate ratio. Your entries are perfect, but market conditions control your results.",
        "min_frames": 180,
    },
    {
        "id": "regime_solution",
        "text": "Check the Dollar Index before you enter. PrimeEdge tracks it and tells you when conditions are favorable. See the evidence at PrimeEdge.APP.",
        "min_frames": 300,
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
    return {"id": line['id'], "seconds": round(dur, 2), "frames": frames}


async def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    AUDIO.mkdir(parents=True, exist_ok=True)
    try:
        import mutagen  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "mutagen"])

    print("Generating Regime Performance voiceover lines...")
    timings = []
    for line in LINES:
        out = AUDIO / f"{line['id']}.mp3"
        if out.exists() and out.stat().st_size > 1000:
            dur = mp3_duration(out)
            frames = max(line["min_frames"], math_ceil((dur + 0.3) * FPS))
            print(f"  {line['id']}: {dur:.2f}s -> {frames} frames (cached)")
            timings.append({"id": line["id"], "seconds": round(dur, 2), "frames": frames})
            continue
        timings.append(await synth(line))

    total = sum(t["frames"] for t in timings)
    print(f"\nTotal Regime Performance audio: {total} frames ({total / FPS:.1f}s)")
    print("All Regime Performance VO files written to public/audio/")
    print("\nNext: node render.mjs --composition RegimePerformance --output out/RegimePerformance_TikTok_WithAudio.mp4")


if __name__ == "__main__":
    asyncio.run(main())
