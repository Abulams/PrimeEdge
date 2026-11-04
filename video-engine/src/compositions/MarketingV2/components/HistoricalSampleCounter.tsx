// ─────────────────────────────────────────────────────────────
// HistoricalSampleCounter — "0 → 187 similar trades" count-up
// ─────────────────────────────────────────────────────────────
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

interface Props {
  targetN: number;
  startFrame?: number;
  label?: string;
}

export const HistoricalSampleCounter: React.FC<Props> = ({
  targetN,
  startFrame = 0,
  label = "similar historical trades",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 28, stiffness: 60, mass: 1.4 },
  });

  const count = Math.round(interpolate(progress, [0, 1], [0, targetN]));
  const opacity = interpolate(frame - startFrame, [0, 12], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      opacity,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 4,
    }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <span style={{
          fontSize: 86,
          fontWeight: 900,
          color: COLORS.blue,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          lineHeight: 1,
          fontVariantNumeric: "tabular-nums",
        }}>
          {count}
        </span>
        <span style={{
          fontSize: 22,
          fontWeight: 700,
          color: COLORS.textSecondary,
          fontFamily: "Inter, sans-serif",
          paddingBottom: 8,
        }}>
          {label}
        </span>
      </div>
      {/* Tick marks */}
      <div style={{
        display: "flex",
        gap: 3,
        marginTop: 8,
        flexWrap: "wrap",
        maxWidth: 480,
        justifyContent: "center",
      }}>
        {Array.from({ length: Math.min(count, 50) }).map((_, i) => (
          <div key={i} style={{
            width: 7,
            height: 7,
            borderRadius: 1,
            background: i < count * 0.71 ? COLORS.green : COLORS.red,
            opacity: 0.8,
          }} />
        ))}
      </div>
      <div style={{
        fontSize: 14,
        color: COLORS.textMuted,
        fontFamily: "Inter, sans-serif",
        marginTop: 4,
      }}>
        {count > 0 && `${Math.round(71)}% win rate across matched setups`}
      </div>
    </div>
  );
};
