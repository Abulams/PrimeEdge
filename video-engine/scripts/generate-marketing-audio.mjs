import { spawnSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const audioDir = path.join(root, "public", "audio");
const speakPs1 = path.join(__dirname, "speak.ps1");
const fps = 30;

const LINES = [
  {
    id: "hook",
    text: "London open. Forty-seven signals. And you still don't know if you should buy.",
  },
  {
    id: "problem",
    text: "You don't lack charts. You lack a decision.",
  },
  {
    id: "stop",
    text: "Round-number stop. Tagged. Then forty-seven pips without you.",
  },
  {
    id: "fomo",
    text: "Gold is running. You chase. Instant red. You rented FOMO.",
  },
  {
    id: "journal",
    text: "Tonight you'll rewrite the journal. Memory is a liar.",
  },
  {
    id: "aha",
    text: "Here's the aha. PrimeEdge doesn't shout buy. It says wait. Or ready. With evidence.",
  },
  {
    id: "solve",
    text: "Historical P-ninety stop. A real corridor. Why this now. Execute. The journal writes itself.",
  },
  {
    id: "cta",
    text: "Stop guessing. Execute on evidence. PrimeEdge. Get started.",
  },
];

function wavDurationSeconds(file) {
  const buf = fs.readFileSync(file);
  const byteRate = buf.readUInt32LE(28);
  const bits = buf.readUInt16LE(34);
  const channels = buf.readUInt16LE(22);
  const dataSize = buf.length - 44;
  const bytesPerSample = bits / 8;
  const samples = dataSize / (bytesPerSample * channels);
  const sampleRate = buf.readUInt32LE(24);
  return samples / sampleRate;
}

function writeWav(file, samples, sampleRate = 44100) {
  const data = Buffer.alloc(samples.length * 2);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    data.writeInt16LE(Math.round(s * 32767), i * 2);
  }
  const header = Buffer.alloc(44);
  const dataSize = data.length;
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + dataSize, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28);
  header.writeUInt16LE(2, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36);
  header.writeUInt32LE(dataSize, 40);
  fs.writeFileSync(file, Buffer.concat([header, data]));
}

function makeBed(seconds) {
  const sr = 44100;
  const n = Math.floor(seconds * sr);
  const samples = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    const env =
      Math.min(1, t / 1.4) *
      Math.min(1, (seconds - t) / 2.2);
    const pad =
      0.22 * Math.sin(2 * Math.PI * 65.41 * t) +
      0.16 * Math.sin(2 * Math.PI * 98.0 * t) +
      0.1 * Math.sin(2 * Math.PI * 130.81 * t) +
      0.06 * Math.sin(2 * Math.PI * 196.0 * t + 0.4);
    const lfo = 0.72 + 0.28 * Math.sin(2 * Math.PI * 0.08 * t);
    const pulse = Math.exp(-((t % 2.0) * 7)) * 0.08 * Math.sin(2 * Math.PI * 49 * t);
    samples[i] = (pad * lfo + pulse) * env * 0.22;
  }
  return samples;
}

fs.mkdirSync(audioDir, { recursive: true });

const timings = [];
for (const line of LINES) {
  const out = path.join(audioDir, `${line.id}.wav`);
  const result = spawnSync(
    "powershell.exe",
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      speakPs1,
      "-Text",
      line.text,
      "-Out",
      out,
      "-Rate",
      "0",
    ],
    { encoding: "utf8" }
  );
  if (result.status !== 0) {
    console.error(result.stdout);
    console.error(result.stderr);
    throw new Error(`TTS failed for ${line.id}`);
  }
  const dur = wavDurationSeconds(out);
  const frames = Math.ceil((dur + 0.85) * fps);
  timings.push({ id: line.id, seconds: Number(dur.toFixed(2)), frames });
  console.log(`${line.id}: ${dur.toFixed(2)}s → ${frames} frames`);
}

const totalFrames = timings.reduce((sum, s) => sum + s.frames, 0);
const totalSeconds = totalFrames / fps + 0.4;
writeWav(path.join(audioDir, "bed.wav"), makeBed(totalSeconds));

const scenesTs = `export const FPS = ${fps};

export const MARKETING_SCENES = ${JSON.stringify(timings, null, 2)} as const;

export const MARKETING_TOTAL_FRAMES = ${totalFrames};
`;

fs.writeFileSync(
  path.join(root, "src", "compositions", "MarketingHero", "timing.ts"),
  scenesTs
);
console.log(`total: ${totalFrames} frames (${(totalFrames / fps).toFixed(1)}s)`);
