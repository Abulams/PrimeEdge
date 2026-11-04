// ─────────────────────────────────────────────────────────────
// PrimeEdge Hybrid Film (Human + Product + Remotion)
// 30.6 seconds · 918 frames · 30fps
// ─────────────────────────────────────────────────────────────
export const FPS = 30;

export const HYBRID_SCENES = {
  humanPain:       { from: 0,   frames: 90  }, // 0:00–0:03: Human Hesitation / Pain
  productAction:   { from: 90,  frames: 120 }, // 0:03–0:07: Real Product Interaction Crop
  remotionExplain: { from: 210, frames: 330 }, // 0:07–0:18: Remotion Causal Logic & Corridor
  humanRestraint:  { from: 540, frames: 150 }, // 0:18–0:23: Human Composure / Hand Disengaging
  productJournal:  { from: 690, frames: 120 }, // 0:23–0:27: Auto-Journal Workflow Proof
  brandCta:        { from: 810, frames: 108 }, // 0:27–0:30.6: CTA & Risk Disclosure
} as const;

export const HYBRID_TOTAL_FRAMES = 918;
