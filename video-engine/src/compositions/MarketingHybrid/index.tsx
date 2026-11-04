// ─────────────────────────────────────────────────────────────
// PrimeEdge Marketing Film (Hybrid: Human + Product + Remotion)
// 1920×1080 · 30fps · 918 frames (~30.6s)
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  delayRender,
  continueRender,
} from "remotion";
import { COLORS } from "../../utils/colors";
import { loadGoogleFonts } from "../../utils/fonts";
import { HYBRID_SCENES, HYBRID_TOTAL_FRAMES } from "./timing";
import { H1_HumanPain }       from "./scenes/H1_HumanPain";
import { H2_ProductAction }   from "./scenes/H2_ProductAction";
import { H3_RemotionExplain } from "./scenes/H3_RemotionExplain";
import { H4_HumanRestraint }  from "./scenes/H4_HumanRestraint";
import { H5_ProductJournal }  from "./scenes/H5_ProductJournal";
import { H6_BrandCTA }        from "./scenes/H6_BrandCTA";

export type MarketingHybridData = Record<string, never>;
export const defaultMarketingHybridProps: MarketingHybridData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

export const MarketingHybrid: React.FC<MarketingHybridData> = () => {
  useFonts();
  const sc = HYBRID_SCENES;

  return (
    <AbsoluteFill style={{ background: COLORS.bg, fontFamily: "Inter, SF Pro Display, sans-serif" }}>
      {/* Procedural ambient soundtrack bed */}
      <Audio
        src={staticFile("audio/bed.wav")}
        volume={(f) => {
          if (f < 30) return (f / 30) * 0.16;
          if (f > HYBRID_TOTAL_FRAMES - 30) return ((HYBRID_TOTAL_FRAMES - f) / 30) * 0.16;
          return 0.16;
        }}
      />

      {/* ── Scene 1: Human Pain / Hesitation (0:00–0:03) ── */}
      <Sequence from={sc.humanPain.from} durationInFrames={sc.humanPain.frames}>
        <Audio src={staticFile("audio/hybrid_hook.mp3")} />
        <H1_HumanPain />
      </Sequence>

      {/* ── Scene 2: Real Product Action / Filter (0:03–0:07) ── */}
      <Sequence from={sc.productAction.from} durationInFrames={sc.productAction.frames}>
        <Audio src={staticFile("audio/hybrid_check.mp3")} />
        <H2_ProductAction />
      </Sequence>

      {/* ── Scene 3: Remotion Causal Explanation (0:07–0:18) ── */}
      <Sequence from={sc.remotionExplain.from} durationInFrames={sc.remotionExplain.frames}>
        <Audio src={staticFile("audio/hybrid_explain.mp3")} />
        <H3_RemotionExplain />
      </Sequence>

      {/* ── Scene 4: Human Restraint / No Chase (0:18–0:23) ── */}
      <Sequence from={sc.humanRestraint.from} durationInFrames={sc.humanRestraint.frames}>
        <Audio src={staticFile("audio/hybrid_restraint.mp3")} />
        <H4_HumanRestraint />
      </Sequence>

      {/* ── Scene 5: Product Workflow & Auto-Journal (0:23–0:27) ── */}
      <Sequence from={sc.productJournal.from} durationInFrames={sc.productJournal.frames}>
        <Audio src={staticFile("audio/hybrid_journal.mp3")} />
        <H5_ProductJournal />
      </Sequence>

      {/* ── Scene 6: Branded CTA & Action (0:27–0:30.6) ── */}
      <Sequence from={sc.brandCta.from} durationInFrames={sc.brandCta.frames}>
        <Audio src={staticFile("audio/hybrid_cta.mp3")} />
        <H6_BrandCTA />
      </Sequence>
    </AbsoluteFill>
  );
};
