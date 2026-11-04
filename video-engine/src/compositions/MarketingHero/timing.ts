export const FPS = 30;

export const MARKETING_SCENES = [
  {
    "id": "hook",
    "seconds": 3.98,
    "frames": 175
  },
  {
    "id": "problem",
    "seconds": 2.93,
    "frames": 150
  },
  {
    "id": "pain",
    "seconds": 8.45,
    "frames": 310
  },
  {
    "id": "aha",
    "seconds": 5.59,
    "frames": 255
  },
  {
    "id": "solve",
    "seconds": 8.57,
    "frames": 300
  },
  {
    "id": "cta",
    "seconds": 3.62,
    "frames": 195
  }
] as const;

export const MARKETING_TOTAL_FRAMES = 1385;

export const MARKETING_TIMELINE = MARKETING_SCENES.reduce<
  { id: string; seconds: number; frames: number; from: number }[]
>((acc, scene) => {
  const from = acc.length ? acc[acc.length - 1].from + acc[acc.length - 1].frames : 0;
  acc.push({ ...scene, from });
  return acc;
}, []);
