// ─────────────────────────────────────────────────────────────
// PrimeEdge Template A: One chart, one question
// 30 seconds · 30fps · 900 frames · 1080×1920 (9:16)
// TikTok Constitution Template A
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
import { TEMPLATE_A_SCENES, TEMPLATE_A_TOTAL_FRAMES } from "./timing";
import { S1_Hook } from "./scenes/S1_Hook";
import { S2_Highlight } from "./scenes/S2_Highlight";
import { S3_Explanation } from "./scenes/S3_Explanation";
import { S4_Trigger } from "./scenes/S4_Trigger";
import { S5_CTA } from "./scenes/S5_CTA";

export type TemplateAData = Record<string, never>;
export const defaultTemplateAProps: TemplateAData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

const hasAudio = (id: string): boolean => {
  return process.env.REMOTION_NO_AUDIO !== "1";
};

export const TemplateA: React.FC<TemplateAData> = () => {
  useFonts();
  const { fps } = useVideoConfig();
  const sc = TEMPLATE_A_SCENES;

  return (
    <AbsoluteFill style={{ background: "#0f172a", fontFamily: "Inter, SF Pro Display, sans-serif" }}>

      {/* ── Scene 1: Hook (0-90 frames = 3 seconds) ── */}
      <Sequence from={sc.hook.from} durationInFrames={sc.hook.frames}>
        {hasAudio("hook") && <Audio src={staticFile("audio/template_a_hook.mp3")} />}
        <S1_Hook />
      </Sequence>

      {/* ── Scene 2: Highlight (90-270 frames = 6 seconds) ── */}
      <Sequence from={sc.highlight.from} durationInFrames={sc.highlight.frames}>
        {hasAudio("highlight") && <Audio src={staticFile("audio/template_a_highlight.mp3")} />}
        <S2_Highlight />
      </Sequence>

      {/* ── Scene 3: Explanation (270-450 frames = 6 seconds) ── */}
      <Sequence from={sc.explanation.from} durationInFrames={sc.explanation.frames}>
        {hasAudio("explanation") && <Audio src={staticFile("audio/template_a_explanation.mp3")} />}
        <S3_Explanation />
      </Sequence>

      {/* ── Scene 4: Trigger (450-630 frames = 6 seconds) ── */}
      <Sequence from={sc.trigger.from} durationInFrames={sc.trigger.frames}>
        {hasAudio("trigger") && <Audio src={staticFile("audio/template_a_trigger.mp3")} />}
        <S4_Trigger />
      </Sequence>

      {/* ── Scene 5: CTA (630-900 frames = 9 seconds) ── */}
      <Sequence from={sc.cta.from} durationInFrames={sc.cta.frames}>
        {hasAudio("cta") && <Audio src={staticFile("audio/template_a_cta.mp3")} />}
        <S5_CTA />
      </Sequence>

    </AbsoluteFill>
  );
};
