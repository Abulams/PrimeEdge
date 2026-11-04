// ─────────────────────────────────────────────────────────────
// AdverseExcursionChart — P25/P75/P90 MAE bar chart
// Draws itself frame by frame (causal animation)
// ─────────────────────────────────────────────────────────────
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

interface Props {
  p25: number;  // pips
  p75: number;
  p90: number;
  startFrame?: number;
  maxPips?: number;
}

export const AdverseExcursionChart: React.FC<Props> = ({
  p25,
  p75,
  p90,
  startFrame = 0,
  maxPips = 40,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 22, stiffness: 70 },
  });

  const opacity = interpolate(frame - startFrame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  const bars = [
    { label: "P25", pips: p25, color: COLORS.green,       desc: "50% of trades stay within" },
    { label: "P75", pips: p75, color: COLORS.amber,       desc: "75% of trades stay within" },
    { label: "P90", pips: p90, color: COLORS.red,         desc: "Invalidation threshold" },
  ];

  const W = 440;

  return (
    <div style={{ opacity, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{
        fontSize: 13,
        color: COLORS.textMuted,
        letterSpacing: 3,
        textTransform: "uppercase",
        fontFamily: "Inter, sans-serif",
        marginBottom: 4,
      }}>
        Typical Adverse Move (MAE)
      </div>

      {bars.map((b) => {
        const barW = (b.pips / maxPips) * W * progress;
        return (
          <div key={b.label} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span style={{
                fontSize: 13,
                fontWeight: 700,
                color: b.color,
                fontFamily: "Inter, sans-serif",
                letterSpacing: 1,
              }}>{b.label}</span>
              <span style={{
                fontSize: 22,
                fontWeight: 900,
                color: b.color,
                fontFamily: "Inter, sans-serif",
              }}>{b.pips} pips</span>
            </div>
            {/* Bar track */}
            <div style={{
              width: W,
              height: 10,
              background: COLORS.bgAccent,
              borderRadius: 5,
              overflow: "hidden",
            }}>
              <div style={{
                width: barW,
                height: "100%",
                background: b.color,
                borderRadius: 5,
                boxShadow: `0 0 10px ${b.color}88`,
              }} />
            </div>
            <div style={{
              fontSize: 12,
              color: COLORS.textMuted,
              fontFamily: "Inter, sans-serif",
            }}>{b.desc}</div>
          </div>
        );
      })}
    </div>
  );
};
