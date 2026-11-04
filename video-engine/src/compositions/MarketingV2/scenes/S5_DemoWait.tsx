// S5_DemoWait — 0:17–0:22 (150 frames)
// EURUSD setup — sparse data, low MSS → resolves to WAIT
// Most trust-building moment: a system that visibly rejects trades
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { HistoricalSampleCounter } from "../components/HistoricalSampleCounter";
import { ReasonPanel } from "../components/ReasonPanel";
import { DecisionCard } from "../components/DecisionCard";

export const S5_DemoWait: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const setupScale = spring({ frame: frame - 0, fps, config: { damping: 18, stiffness: 120 } });
  const histOp = interpolate(frame, [20, 34], [0, 1], { extrapolateRight: "clamp" });
  const reasonOp = interpolate(frame, [60, 75], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOp }}>
      {/* Subtle amber wash — different energy from the green TAKE IT scene */}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${COLORS.amber}0C 0%, transparent 65%)` }} />

      <AbsoluteFill style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 100px",
        gap: 32,
      }}>

        <div style={{ fontSize: 12, color: COLORS.textMuted, letterSpacing: 4, textTransform: "uppercase", fontFamily: "Inter, sans-serif" }}>
          Next Setup · EURUSD
        </div>

        <div style={{ display: "flex", gap: 56, alignItems: "center", width: "100%" }}>

          {/* Setup card */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{
              transform: `scale(${setupScale})`,
              background: COLORS.bgCard,
              border: `1.5px solid ${COLORS.amber}55`,
              borderRadius: 16,
              padding: "20px 24px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 32, fontWeight: 900, color: COLORS.textPrimary, fontFamily: "Inter, sans-serif" }}>EURUSD</div>
                  <div style={{ fontSize: 16, color: COLORS.green, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>▲ LONG · London Session</div>
                </div>
                {/* Low MSS score — highlighted as weak */}
                <div style={{
                  background: `${COLORS.red}22`,
                  border: `1px solid ${COLORS.red}`,
                  borderRadius: 8,
                  padding: "6px 14px",
                  fontSize: 13,
                  color: COLORS.red,
                  fontFamily: "Inter, sans-serif",
                  fontWeight: 700,
                }}>
                  MSS · 0.41
                </div>
              </div>
            </div>

            {/* Low historical sample — sparse */}
            <div style={{ opacity: histOp }}>
              <HistoricalSampleCounter
                targetN={34}
                startFrame={20}
                label="matched historical setups"
              />
            </div>

            {/* Insufficient sample warning */}
            {frame > 40 && (
              <div style={{
                opacity: interpolate(frame, [40, 52], [0, 1], { extrapolateRight: "clamp" }),
                background: `${COLORS.amber}15`,
                border: `1px solid ${COLORS.amber}55`,
                borderRadius: 10,
                padding: "12px 18px",
                fontSize: 14,
                color: COLORS.amber,
                fontFamily: "Inter, sans-serif",
              }}>
                ⚠ Sample size below confidence threshold (min: 80)
              </div>
            )}
          </div>

          {/* Right — Reason + Wait decision */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24, alignItems: "center" }}>

            <div style={{ opacity: reasonOp, width: "100%" }}>
              <ReasonPanel
                startFrame={60}
                accentColor={COLORS.amber}
                lines={[
                  { label: "Structure",    value: "Partial — 1H structure not fully confirmed", color: COLORS.amber },
                  { label: "History",      value: "34 matches — insufficient sample",            color: COLORS.red },
                  { label: "MSS Score",    value: "0.41 — below minimum threshold (0.60)",       color: COLORS.red },
                  { label: "Verdict",      value: "Evidence too weak to justify entry risk" },
                ]}
              />
            </div>

            {frame >= 100 && (
              <DecisionCard
                state="WAIT"
                resolveAtFrame={115}
                instrument="EURUSD"
                direction="LONG"
                size="lg"
              />
            )}
          </div>
        </div>

        {/* On-screen statement */}
        {frame >= 90 && (
          <div style={{
            opacity: interpolate(frame, [90, 105], [0, 1], { extrapolateRight: "clamp" }),
            fontSize: 22,
            color: COLORS.textSecondary,
            fontFamily: "Inter, sans-serif",
            textAlign: "center",
            maxWidth: 700,
          }}>
            When the evidence is weak,{" "}
            <span style={{ color: COLORS.amber, fontWeight: 700 }}>it tells you to wait.</span>
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
