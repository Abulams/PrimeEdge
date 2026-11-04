# ─────────────────────────────────────────────────────────────
# Hidden State Voiceover Generation
# 5 scenes · Timeline/Flow Diagram Style
# ─────────────────────────────────────────────────────────────
import asyncio
import edge_tts
import os
from pathlib import Path
from mutagen.mp3 import MP3

# ── Configuration ─────────────────────────────────────────────
AUDIO = Path("public/audio")
VOICE = "en-US-AndrewNeural"  # Professional male voice
RATE = "+5%"  # Slightly faster

# ── Hidden State VO Lines ─────────────────────────────────────
LINES = [
    {
        "id": "hidden_hook",
        "text": "You're trading the wrong market state.",
        "min_frames": 120,
    },
    {
        "id": "hidden_research_context",
        "text": "We analyzed 1,512 trading days from 2020 to 2026. We found 163 regime transitions.",
        "min_frames": 240,
    },
    {
        "id": "hidden_discovery",
        "text": "Only 2 were direct transitions. 161 went through consolidation. That's 95 percent.",
        "min_frames": 240,
    },
    {
        "id": "hidden_flow_diagram",
        "text": "Markets don't flip instantly. They pause in the middle through consolidation before changing direction.",
        "min_frames": 300,
    },
    {
        "id": "hidden_cta",
        "text": "PrimeEdge tracks these transitions. Know when to wait and when to act. See the research at PrimeEdge.APP.",
        "min_frames": 300,
    },
]

# ── Duration Detection ─────────────────────────────────────────
def mp3_duration(path: Path) -> float:
    """Get MP3 duration using mutagen"""
    try:
        audio = MP3(path)
        return audio.info.length
    except Exception as e:
        raise RuntimeError(f"Cannot read duration: {path}")


def math_ceil(x: float) -> int:
    return int(x) if int(x) == x else int(x) + 1


# ── Voiceover Generation ─────────────────────────────────────
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
    frames = math_ceil(dur * 30)
    if frames < line["min_frames"]:
        frames = line["min_frames"]
    return {"id": line["id"], "duration": dur, "frames": frames}


async def main():
    print("Generating Hidden State voiceover lines...")

    # Ensure output directory exists
    AUDIO.mkdir(parents=True, exist_ok=True)

    timings = []
    for line in LINES:
        result = await synth(line)
        print(f"  {result['id']}: {result['duration']:.2f}s -> {result['frames']} frames")
        timings.append(result["frames"])

    total_frames = sum(timings)
    total_seconds = total_frames / 30

    print(f"\nTotal Hidden State audio: {total_frames} frames ({total_seconds:.1f}s)")
    print(f"All Hidden State VO files written to {AUDIO}/")

    print("\nNext: node render.mjs --composition HiddenState --output out/HiddenState_TikTok_WithAudio.mp4")

if __name__ == "__main__":
    asyncio.run(main())
