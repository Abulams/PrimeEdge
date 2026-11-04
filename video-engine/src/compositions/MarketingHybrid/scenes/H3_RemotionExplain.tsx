// ─────────────────────────────────────────────────────────────
// H3_RemotionExplain — 0:07–0:18 (330 frames)
// Causal Remotion logic: 187 matches -> 31 pip MAE -> Corridor -> WAIT
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { HistoricalSampleCounter } from "../../MarketingV2/components/HistoricalSampleCounter";
import { AdverseExcursionChart } from "../../MarketingV2/components/AdverseExcursionChart";
import { ReasonPanel } from "../../MarketingV2/components/ReasonPanel";
import { DecisionCard } from "../../MarketingV2/components/DecisionCard";

const TIMELINE = {
  sampleStart: 15,
  maeStart: 75,
  corridorStart: 145,
  reasonStart: 210,
  decisionStart: 250,
};

export const H3_RemotionExplain: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const cardScale = spring({ frame: frame - 5, fps, config: { damping: 18, stiffness: 120 } });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOp }}>
      {/* Background ambient lighting */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 30%, ${COLORS.amber}10 0%, transparent 65%)`,
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 80px",
          gap: 28,
        }}
      >
        {/* Top Header */}
        <div
          style={{
            fontSize: 13,
            color: COLORS.textMuted,
            letterSpacing: 4,
            textTransform: "uppercase",
            fontFamily: "Inter, sans-serif",
          }}
        >
          Quantitative Sample Analysis · XAUUSD
        </div>

        {/* Content Columns */}
        <div style={{ display: "flex", gap: 52, alignItems: "flex-start", width: "100%" }}>
          {/* Left Column: Setup card & Sample size counter */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Setup Header card */}
            <div
              style={{
                transform: `scale(${cardScale})`,
                background: COLORS.bgCard,
                border: `1.5px solid ${COLORS.border}`,
                borderRadius: 18,
                padding: "22px 28px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 34, fontWeight: 900, color: COLORS.textPrimary }}>XAUUSD</div>
                  <div style={{ fontSize: 16, color: COLORS.green, fontWeight: 700, marginTop: 4 }}>
                    ▲ LONG · London Session
                  </div>
                </div>
                <div
                  style={{
                    background: `${COLORS.blue}22`,
                    border: `1px solid ${COLORS.blue}`,
                    borderRadius: 10,
                    padding: "8px 16px",
                    fontSize: 14,
                    color: COLORS.blue,
                    fontWeight: 800,
                  }}
                >
                  MSS · 0.82
                </div>
              </div>
            </div>

            {/* Historical sample counter */}
            {frame >= TIMELINE.sampleStart && (
              <HistoricalSampleCounter
                targetN={187}
                startFrame={TIMELINE.sampleStart}
                label="matched historical trades"
              />
            )}
          </div>

          {/* Right Column: MAE distribution, Invalidation zone, and Decision */}
          <div style={{ flex: 1.25, display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Adverse excursion chart */}
            {frame >= TIMELINE.maeStart && (
              <AdverseExcursionChart
                p25={8}
                p75={22}
                p90={31}
                startFrame={TIMELINE.maeStart}
                maxPips={40}
              />
            )}

            {/* Reason Panel */}
            {frame >= TIMELINE.reasonStart && (
              <ReasonPanel
                startFrame={TIMELINE.reasonStart}
                accentColor={COLORS.amber}
                lines={[
                  { label: "Normal Adverse Move", value: "8–22 pips across 187 historical setups" },
                  { label: "Valid Entry Zone", value: "2318.50 – 2321.00 (within P75 threshold)" },
                  { label: "Invalidation (P90)", value: "31 pips — historical boundary beyond noise" },
                  { label: "Execution Rule", value: "Price currently extended: WAIT for pullback", color: COLORS.amber },
                ]}
              />
            )}

            {/* Decision card resolving firmly to WAIT */}
            {frame >= TIMELINE.decisionStart && (
              <div style={{ display: "flex", justifyContent: "center", marginTop: 8 }}>
                <DecisionCard
                  state="WAIT"
                  resolveAtFrame={TIMELINE.decisionStart + 25}
                  instrument="XAUUSD"
                  direction="LONG"
                  size="lg"
                />
              </div>
            )}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
