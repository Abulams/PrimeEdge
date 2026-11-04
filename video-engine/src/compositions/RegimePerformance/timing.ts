// ─────────────────────────────────────────────────────────────
// Regime Performance Video Timing
// 35.6 seconds · 30fps · 1067 frames · 1080×1920 (9:16)
// ─────────────────────────────────────────────────────────────

export const REGIME_TOTAL_FRAMES = 1067;

export const REGIME_SCENES = {
  // Scene 1: Pain Hook (0-109 frames = 3.6 seconds, audio: 3.31s)
  painHook: {
    from: 0,
    frames: 109,
  },
  // Scene 2: Pain Escalation (109-334 frames = 7.5 seconds, audio: 7.18s)
  painEscalation: {
    from: 109,
    frames: 225,
  },
  // Scene 3: Loss Realization (334-554 frames = 7.3 seconds, audio: 7.01s)
  lossRealization: {
    from: 334,
    frames: 220,
  },
  // Scene 4: Reveal (554-767 frames = 7.1 seconds, audio: 6.79s)
  reveal: {
    from: 554,
    frames: 213,
  },
  // Scene 5: Solution & CTA (767-1067 frames = 10 seconds, audio: 7.70s)
  solution: {
    from: 767,
    frames: 300,
  },
};
