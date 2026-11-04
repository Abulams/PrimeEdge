// ─────────────────────────────────────────────────────────────
// Hidden State Video Composition
// Timeline/Flow Diagram Style
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, Audio, staticFile } from "remotion";
import { HIDDEN_SCENES } from "./timing";
import { S1_Hook } from "./scenes/S1_Hook";
import { S2_ResearchContext } from "./scenes/S2_ResearchContext";
import { S3_Discovery } from "./scenes/S3_Discovery";
import { S4_FlowDiagram } from "./scenes/S4_FlowDiagram";
import { S5_CTA } from "./scenes/S5_CTA";

export interface HiddenStateData {
  hasAudio?: boolean;
}

export const defaultHiddenStateProps: HiddenStateData = {
  hasAudio: true,
};

export const HiddenState: React.FC<HiddenStateData> = ({ hasAudio = true }) => {
  const { fps } = useVideoConfig();
  const sc = HIDDEN_SCENES;

  return (
    <AbsoluteFill style={{ background: "#0f172a" }}>
      {/* Scene 1: Hook */}
      <Sequence from={sc.hook.from} durationInFrames={sc.hook.frames}>
        {hasAudio && <Audio src={staticFile("audio/hidden_hook.mp3")} />}
        <S1_Hook />
      </Sequence>

      {/* Scene 2: Research Context */}
      <Sequence from={sc.researchContext.from} durationInFrames={sc.researchContext.frames}>
        {hasAudio && <Audio src={staticFile("audio/hidden_research_context.mp3")} />}
        <S2_ResearchContext />
      </Sequence>

      {/* Scene 3: The Discovery */}
      <Sequence from={sc.discovery.from} durationInFrames={sc.discovery.frames}>
        {hasAudio && <Audio src={staticFile("audio/hidden_discovery.mp3")} />}
        <S3_Discovery />
      </Sequence>

      {/* Scene 4: Flow Diagram */}
      <Sequence from={sc.flowDiagram.from} durationInFrames={sc.flowDiagram.frames}>
        {hasAudio && <Audio src={staticFile("audio/hidden_flow_diagram.mp3")} />}
        <S4_FlowDiagram />
      </Sequence>

      {/* Scene 5: CTA */}
      <Sequence from={sc.cta.from} durationInFrames={sc.cta.frames}>
        {hasAudio && <Audio src={staticFile("audio/hidden_cta.mp3")} />}
        <S5_CTA />
      </Sequence>
    </AbsoluteFill>
  );
};
