// ─────────────────────────────────────────────────────────────
// Hidden State Video Timing
// 45 seconds · 30fps · 1350 frames · 1080×1920 (9:16)
// Timeline/Flow Diagram Style
// ─────────────────────────────────────────────────────────────

export const HIDDEN_TOTAL_FRAMES = 1350;

export const HIDDEN_SCENES = {
  // Scene 1: Hook (0-120 frames = 4 seconds, audio: 1.97s)
  hook: {
    from: 0,
    frames: 120,
  },
  // Scene 2: Research Context (120-389 frames = 9 seconds, audio: 8.95s)
  researchContext: {
    from: 120,
    frames: 269,
  },
  // Scene 3: The Discovery (389-629 frames = 8 seconds, audio: 6.58s)
  discovery: {
    from: 389,
    frames: 240,
  },
  // Scene 4: Flow Diagram (629-1050 frames = 14 seconds, audio: 5.35s)
  flowDiagram: {
    from: 629,
    frames: 421,
  },
  // Scene 5: CTA (1050-1350 frames = 10 seconds, audio: 6.43s)
  cta: {
    from: 1050,
    frames: 300,
  },
};
