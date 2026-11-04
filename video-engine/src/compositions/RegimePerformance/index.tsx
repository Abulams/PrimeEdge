// ─────────────────────────────────────────────────────────────
// PrimeEdge Regime Performance Video
// 30 seconds · 30fps · 900 frames · 1080×1920 (9:16)
// TikTok/Reels/Shorts - Problem-First Approach
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Sequence,
  staticFile,
  delayRender,
  continueRender,
  useVideoConfig,
  Audio,
} from "remotion";
import { COLORS } from "../../utils/colors";
import { loadGoogleFonts } from "../../utils/fonts";
import { REGIME_SCENES, REGIME_TOTAL_FRAMES } from "./timing";
import { S1_PainHook } from "./scenes/S1_PainHook";
import { S2_PainEscalation } from "./scenes/S2_PainEscalation";
import { S3_LossRealization } from "./scenes/S3_LossRealization";
import { S4_Reveal } from "./scenes/S4_Reveal";
import { S5_Solution } from "./scenes/S5_Solution";

export type RegimePerformanceData = Record<string, never>;
export const defaultRegimePerformanceProps: RegimePerformanceData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

const hasAudio = (id: string): boolean => {
  // Enable audio when files are generated via generate_vo_v2.py
  // Set REMOTION_NO_AUDIO=1 to render without audio
  return process.env.REMOTION_NO_AUDIO !== "1";
};

export const RegimePerformance: React.FC<RegimePerformanceData> = () => {
  useFonts();
  const { fps } = useVideoConfig();
  const sc = REGIME_SCENES;

  return (
    <AbsoluteFill style={{ background: "#0a0a0a", fontFamily: "Inter, SF Pro Display, sans-serif" }}>

      {/* ── Scene 1: Pain Hook (0-120 frames = 4 seconds) ── */}
      <Sequence from={sc.painHook.from} durationInFrames={sc.painHook.frames}>
        {hasAudio("pain_hook") && <Audio src={staticFile("audio/regime_pain_hook.mp3")} />}
        <S1_PainHook />
      </Sequence>

      {/* ── Scene 2: Pain Escalation (120-240 frames = 4 seconds) ── */}
      <Sequence from={sc.painEscalation.from} durationInFrames={sc.painEscalation.frames}>
        {hasAudio("pain_escalation") && <Audio src={staticFile("audio/regime_pain_escalation.mp3")} />}
        <S2_PainEscalation />
      </Sequence>

      {/* ── Scene 3: Loss Realization (240-420 frames = 6 seconds) ── */}
      <Sequence from={sc.lossRealization.from} durationInFrames={sc.lossRealization.frames}>
        {hasAudio("loss_realization") && <Audio src={staticFile("audio/regime_loss_realization.mp3")} />}
        <S3_LossRealization />
      </Sequence>

      {/* ── Scene 4: Reveal (420-600 frames = 6 seconds) ── */}
      <Sequence from={sc.reveal.from} durationInFrames={sc.reveal.frames}>
        {hasAudio("reveal") && <Audio src={staticFile("audio/regime_reveal.mp3")} />}
        <S4_Reveal />
      </Sequence>

      {/* ── Scene 5: Solution & CTA (600-900 frames = 10 seconds) ── */}
      <Sequence from={sc.solution.from} durationInFrames={sc.solution.frames}>
        {hasAudio("solution") && <Audio src={staticFile("audio/regime_solution.mp3")} />}
        <S5_Solution />
      </Sequence>

    </AbsoluteFill>
  );
};
