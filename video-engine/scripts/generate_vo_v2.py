"""Neural voiceover for PrimeEdge Marketing Film V2.
Updated script: product-first, evidential, anti-hype.
Run:  python scripts/generate_vo_v2.py
"""
from __future__ import annotations
import asyncio, json, struct, subprocess, sys, math
from pathlib import Path

import edge_tts

ROOT  = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "public" / "audio"
FPS   = 30
VOICE = "en-US-AndrewNeural"
RATE  = "+10%"   # Slightly slower than V1 — more deliberate, confident

# ── V2 VO Lines ─────────────────────────────────────────────────
LINES = [
    {
        "id": "hook_v2",
        "text": "If every chart gives you a different answer, you don't need another signal.",
        "min_frames": 60,
    },
    {
        "id": "pain_v2",
        "text": "You need to know when to wait, when to act, and where the trade is invalidated.",
        "min_frames": 120,
    },
    {
        "id": "introduce_v2",
        "text": "PrimeEdge turns market noise into one decision, with a reason.",
        "min_frames": 90,
    },
    {
        "id": "demo_take_v2",
        "text": "It compares the current setup with similar historical trades, shows the normal adverse move, then gives you an entry zone and a risk-defined stop.",
        "min_frames": 240,
    },
    {
        "id": "demo_wait_v2",
        "text": "And when the evidence is weak, it tells you to wait.",
        "min_frames": 150,
    },
    {
        "id": "journal_v2",
        "text": "Every decision is recorded, so you review the reason, not rewrite the story.",
        "min_frames": 120,
    },
    {
        "id": "cta_v2",
        "text": "Stop guessing. Run your first replay with PrimeEdge.",
        "min_frames": 120,
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
    try:
        import mutagen  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "mutagen"])

    print("Generating V2 voiceover lines...")
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
    print(f"\nTotal V2 audio: {total} frames ({total / FPS:.1f}s)")
    print("All V2 VO files written to public/audio/")
    print("\nNext: node render.mjs --composition MarketingV2 --output out/MarketingV2.mp4")


if __name__ == "__main__":
    asyncio.run(main())
