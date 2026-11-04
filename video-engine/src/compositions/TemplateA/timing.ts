// Template A: One chart, one question
// Total: 30 seconds (900 frames @ 30fps)

export const TEMPLATE_A_SCENES = {
  hook: { from: 0, frames: 90 },      // 0-3s: Chart/question in frame one
  highlight: { from: 90, frames: 180 }, // 3-9s: Highlight level
  explanation: { from: 270, frames: 180 }, // 9-15s: Competing interpretation
  trigger: { from: 450, frames: 180 }, // 15-21s: Trigger/invalidation
  cta: { from: 630, frames: 270 },   // 21-30s: CTA - saveable checklist
};

export const TEMPLATE_A_TOTAL_FRAMES = 900;
