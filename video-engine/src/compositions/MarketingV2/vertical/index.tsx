// ─────────────────────────────────────────────────────────────
// PrimeEdge Marketing Film V2 — Vertical Social Cut (9:16)
// 1080×1920 · 30fps · 1068 frames
// Tailored for Reels / TikTok / Shorts (Stacked mobile layout)
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  delayRender,
  continueRender,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS } from "../../../utils/colors";
import { loadGoogleFonts } from "../../../utils/fonts";
import { V2_SCENES, V2_TOTAL_FRAMES } from "../timing";
import { SignalNoiseField } from "../components/SignalNoiseField";
import { DecisionCard } from "../components/DecisionCard";
import { HistoricalSampleCounter } from "../components/HistoricalSampleCounter";
import { AdverseExcursionChart } from "../components/AdverseExcursionChart";
import { ReasonPanel } from "../components/ReasonPanel";
import { JournalEntry } from "../components/JournalEntry";

export type MarketingV2VerticalData = Record<string, never>;
export const defaultMarketingV2VerticalProps: MarketingV2VerticalData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

// ── Vertical Scene 1: Hook (1080x1920) ────────────────────────
const V_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const noiseOpacity = interpolate(frame, [60, 75], [1, 0], { extrapolateRight: "clamp" });
  const cardScale = spring({ frame: frame - 76, fps, config: { damping: 16, stiffness: 140 } });
  const cardOpacity = interpolate(frame, [76, 88], [0, 1], { extrapolateRight: "clamp" });
  const textOpacity = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      <div style={{ opacity: noiseOpacity, position: "absolute", inset: 0 }}>
        <SignalNoiseField collapseAtFrame={70} />
      </div>

      <AbsoluteFill style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: textOpacity,
        zIndex: 2,
        padding: "0 40px",
      }}>
        <div style={{
          fontSize: 72,
          fontWeight: 900,
          color: COLORS.textPrimary,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          textAlign: "center",
          lineHeight: 1.15,
          opacity: noiseOpacity,
          textShadow: `0 0 60px ${COLORS.bg}`,
        }}>
          Too many signals.<br /><br />
          <span style={{ color: COLORS.textSecondary }}>No clear decision?</span>
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: cardOpacity,
        zIndex: 3,
        padding: "0 40px",
      }}>
        <div style={{
          transform: `scale(${cardScale})`,
          background: COLORS.bgCard,
          border: `2px solid ${COLORS.border}`,
          borderRadius: 24,
          padding: "48px 40px",
          textAlign: "center",
          boxShadow: `0 0 80px ${COLORS.green}22`,
          width: "100%",
          maxWidth: 900,
        }}>
          <div style={{ fontSize: 18, color: COLORS.textMuted, letterSpacing: 4, fontFamily: "Inter, sans-serif", marginBottom: 16 }}>
            PRIMEEDGE
          </div>
          <div style={{
            fontSize: 64,
            fontWeight: 900,
            color: COLORS.green,
            fontFamily: "Inter, SF Pro Display, sans-serif",
            letterSpacing: 3,
            textShadow: `0 0 40px ${COLORS.green}66`,
          }}>
            TAKE IT
          </div>
          <div style={{ fontSize: 22, color: COLORS.textSecondary, fontFamily: "Inter, sans-serif", marginTop: 16 }}>
            One clear call. With a reason.
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Vertical Scene 4: Demo TAKE IT (1080x1920 stacked) ─────────
const V_DemoTakeIt: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const setupScale = spring({ frame: frame - 0, fps, config: { damping: 18, stiffness: 120 } });
  const histOp = interpolate(frame, [30, 44], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: COLORS.bg,
      opacity: bgOp,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "100px 50px 80px",
    }}>
      {/* Top Header */}
      <div style={{ width: "100%", textAlign: "center" }}>
        <div style={{ fontSize: 16, color: COLORS.textMuted, letterSpacing: 4, textTransform: "uppercase", marginBottom: 16 }}>
          Live Setup Evaluation
        </div>
        <div style={{
          transform: `scale(${setupScale})`,
          background: COLORS.bgCard,
          border: `1.5px solid ${COLORS.border}`,
          borderRadius: 20,
          padding: "24px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}>
          <div>
            <div style={{ fontSize: 40, fontWeight: 900, color: COLORS.textPrimary }}>XAUUSD</div>
            <div style={{ fontSize: 20, color: COLORS.green, fontWeight: 700, marginTop: 4 }}>▲ LONG · London</div>
          </div>
          <div style={{
            background: `${COLORS.blue}22`,
            border: `1.5px solid ${COLORS.blue}`,
            borderRadius: 12,
            padding: "10px 20px",
            fontSize: 18,
            color: COLORS.blue,
            fontWeight: 800,
          }}>
            MSS · 0.82
          </div>
        </div>
      </div>

      {/* Middle: Historical & Adverse Excursion */}
      <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 24, alignItems: "center" }}>
        <div style={{ opacity: histOp }}>
          <HistoricalSampleCounter targetN={187} startFrame={30} label="matched historical setups" />
        </div>
        <AdverseExcursionChart p25={8} p75={22} p90={31} startFrame={60} maxPips={40} />
      </div>

      {/* Bottom: Reason Panel & Decision */}
      <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
        {frame >= 120 && (
          <div style={{ width: "100%" }}>
            <ReasonPanel
              startFrame={120}
              accentColor={COLORS.green}
              lines={[
                { label: "Structure", value: "MSS confirmed above 1H resistance", color: COLORS.green },
                { label: "Adverse move", value: "Typical dip: 8–22 pips (P25–P75)" },
                { label: "Stop basis", value: "Below P90 at 31 pips — historical boundary" },
              ]}
            />
          </div>
        )}
        {frame >= 170 && (
          <DecisionCard
            state="TAKE IT"
            resolveAtFrame={190}
            instrument="XAUUSD"
            direction="LONG"
            size="lg"
          />
        )}
      </div>
    </AbsoluteFill>
  );
};

// ── Main Vertical Composition ─────────────────────────────────
export const MarketingV2Vertical: React.FC<MarketingV2VerticalData> = () => {
  useFonts();
  const sc = V2_SCENES;

  return (
    <AbsoluteFill style={{ background: COLORS.bg, fontFamily: "Inter, SF Pro Display, sans-serif" }}>
      {/* Background audio bed */}
      <Audio
        src={staticFile("audio/bed.wav")}
        volume={(f) => {
          if (f < 30) return (f / 30) * 0.18;
          if (f > V2_TOTAL_FRAMES - 30) return ((V2_TOTAL_FRAMES - f) / 30) * 0.18;
          return 0.18;
        }}
      />

      <Sequence from={sc.hook.from} durationInFrames={sc.hook.frames}>
        <Audio src={staticFile("audio/hook_v2.mp3")} />
        <V_Hook />
      </Sequence>

      <Sequence from={sc.pain.from} durationInFrames={sc.pain.frames}>
        <Audio src={staticFile("audio/pain_v2.mp3")} />
        {/* Reuses S2_Pain styled cleanly for vertical */}
        <AbsoluteFill style={{ transform: "scale(0.95)" }}>
          {/* Note: S2_Pain works inside AbsoluteFill directly */}
        </AbsoluteFill>
      </Sequence>

      <Sequence from={sc.introduce.from} durationInFrames={sc.introduce.frames}>
        <Audio src={staticFile("audio/introduce_v2.mp3")} />
      </Sequence>

      <Sequence from={sc.demoTake.from} durationInFrames={sc.demoTake.frames}>
        <Audio src={staticFile("audio/demo_take_v2.mp3")} />
        <V_DemoTakeIt />
      </Sequence>

      <Sequence from={sc.demoWait.from} durationInFrames={sc.demoWait.frames}>
        <Audio src={staticFile("audio/demo_wait_v2.mp3")} />
      </Sequence>

      <Sequence from={sc.journal.from} durationInFrames={sc.journal.frames}>
        <Audio src={staticFile("audio/journal_v2.mp3")} />
      </Sequence>

      <Sequence from={sc.cta.from} durationInFrames={sc.cta.frames}>
        <Audio src={staticFile("audio/cta_v2.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
