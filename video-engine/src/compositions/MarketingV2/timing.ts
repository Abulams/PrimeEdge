// PrimeEdge Marketing Film V2 — Scene Timing Contract
// Total: 1068 frames · ~35.6 seconds · 30fps (synced to neural voiceover)

export const FPS = 30;

export const V2_SCENES = {
  hook:      { from: 0,   frames: 122 },  // 0:00–0:04
  pain:      { from: 122, frames: 138 },  // 0:04–0:08
  introduce: { from: 260, frames: 128 },  // 0:08–0:13
  demoTake:  { from: 388, frames: 250 },  // 0:13–0:21
  demoWait:  { from: 638, frames: 150 },  // 0:21–0:26
  journal:   { from: 788, frames: 150 },  // 0:26–0:31
  cta:       { from: 938, frames: 130 },  // 0:31–0:35
} as const;

export const V2_TOTAL_FRAMES = 1068;

// VO lines matched to scenes
export const V2_VO_LINES = [
  { id: "hook",      text: "If every chart gives you a different answer — you don't need another signal." },
  { id: "pain",      text: "You need to know when to wait, when to act, and where the trade is invalidated." },
  { id: "introduce", text: "PrimeEdge turns market noise into one decision — with a reason." },
  { id: "demoTake",  text: "It compares the current setup with similar historical trades, shows the normal adverse move, then gives you an entry zone and a risk-defined stop." },
  { id: "demoWait",  text: "And when the evidence is weak, it tells you to wait." },
  { id: "journal",   text: "Every decision is recorded — so you review the reason, not rewrite the story." },
  { id: "cta",       text: "Stop guessing. Run your first replay with PrimeEdge." },
] as const;
