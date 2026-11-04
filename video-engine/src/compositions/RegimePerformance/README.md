# Regime Performance Video - Audio Generation Guide

## Current Status

✅ **Video rendered without audio**: `out/RegimePerformance_TikTok.mp4` (3.27 MB)
⏳ **Audio files**: Need to be generated
⏳ **Video with audio**: Will be rendered after audio files are added

## Audio Files Needed

Place these files in `video-engine/public/audio/`:

1. `regime_pain_hook.mp3` (0-4s)
   - Script: "Why you keep losing money..."
   - Tone: Tense, urgent, heartbeat rhythm

2. `regime_pain_escalation.mp3` (4-8s)
   - Script: "Your strategy is fine. Your analysis is solid. Your entries are perfect. But you're still down."
   - Tone: Frustrated, building tension

3. `regime_loss_realization.mp3` (8-14s)
   - Script: "You're trading in the wrong regime."
   - Tone: Dramatic realization, impact

4. `regime_reveal.mp3` (14-20s)
   - Script: "Same strategy. Same market. Different results. BEARISH-DXY: 69% win rate. BULLISH-DXY: 30% win rate."
   - Tone: Dramatic reveal, contrasting

5. `regime_solution.mp3` (20-30s)
   - Script: "The Dollar Index DICTATES your success. More than your strategy ever could. Stop guessing. Know your regime at PrimeEdge.app."
   - Tone: Confident, authoritative, hopeful

## Generation Workflow

### Option 1: Use Existing TTS Script
If you have a `generate_vo_v2.py` or similar workflow:

```bash
# Create audio generation script for this composition
# Follow the same pattern as MarketingV2 voiceover generation
```

### Option 2: Manual TTS Generation
Using ElevenLabs, OpenAI, or similar:

```bash
# Example ElevenLabs API call (adjust as needed)
elevenlabs generate \
  --text "Why you keep losing money..." \
  --voice "your-voice-id" \
  --output video-engine/public/audio/regime_pain_hook.mp3

# Repeat for all 5 audio files
```

### Option 3: Professional Voiceover
Send the script to a voice talent with timing requirements.

## Rendering With Audio

Once audio files are in place:

```bash
cd video-engine
node render.mjs --composition RegimePerformance --output out/RegimePerformance_TikTok_WithAudio.mp4
```

## Rendering Without Audio (Current)

```bash
cd video-engine
REMOTION_NO_AUDIO=1 node render.mjs --composition RegimePerformance --output out/RegimePerformance_TikTok.mp4
```

## File Locations

- **Composition**: `video-engine/src/compositions/RegimePerformance/`
- **Voiceover Script**: `video-engine/src/compositions/RegimePerformance/VOICEOVER_SCRIPT.md`
- **Audio Directory**: `video-engine/public/audio/`
- **Output Directory**: `video-engine/out/`

## Next Steps

1. Generate 5 audio files using your preferred TTS method
2. Place them in `video-engine/public/audio/`
3. Render with audio: `node render.mjs --composition RegimePerformance --output out/RegimePerformance_TikTok_WithAudio.mp4`
4. Review the audio-synced version
5. Post to TikTok/Reels/Shorts
