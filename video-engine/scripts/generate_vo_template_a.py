#!/usr/bin/env python3
"""
Generate voiceover for Template A: One chart, one question
Using edge-tts
"""

import edge_tts
import asyncio
from pathlib import Path

AUDIO_DIR = Path("video-engine/public/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "en-US-AndrewNeural"
RATE = "+5%"

async def generate_audio(text: str, filename: str) -> float:
    """Generate audio and return duration in seconds"""
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    output_path = AUDIO_DIR / filename

    await communicate.save(str(output_path))

    # Calculate duration from file
    from mutagen.mp3 import MP3
    audio = MP3(str(output_path))
    duration = audio.info.length
    return duration

async def main():
    print("Generating voiceover for Template A...")

    # Scene 1: Hook (3s)
    hook_text = "Same ticker, two timeframes, opposite signals. Why?"
    hook_duration = await generate_audio(hook_text, "template_a_hook.mp3")
    print(f"  Hook: {hook_duration:.2f}s")

    # Scene 2: Highlight (6s)
    highlight_text = "This level marks regime entry. Watch how price reacts here."
    highlight_duration = await generate_audio(highlight_text, "template_a_highlight.mp3")
    print(f"  Highlight: {highlight_duration:.2f}s")

    # Scene 3: Explanation (6s)
    explanation_text = "Bearish DXY: 69% win rate. Bullish DXY: 30% win rate. Same setup, opposite outcomes."
    explanation_duration = await generate_audio(explanation_text, "template_a_explanation.mp3")
    print(f"  Explanation: {explanation_duration:.2f}s")

    # Scene 4: Trigger (6s)
    trigger_text = "Trigger: DXY in BEARISH regime. Invalidation: DXY crosses BULLISH. Check DXY before entry."
    trigger_duration = await generate_audio(trigger_text, "template_a_trigger.mp3")
    print(f"  Trigger: {trigger_duration:.2f}s")

    # Scene 5: CTA (9s)
    cta_text = "Save the regime checklist at PRIMEEDGE.APP. Evidence before execution."
    cta_duration = await generate_audio(cta_text, "template_a_cta.mp3")
    print(f"  CTA: {cta_duration:.2f}s")

    total = hook_duration + highlight_duration + explanation_duration + trigger_duration + cta_duration
    print(f"\nTotal duration: {total:.2f}s ({int(total * 30)} frames @ 30fps)")

if __name__ == "__main__":
    asyncio.run(main())
