// ─────────────────────────────────────────────────────────────
// ReasonPanel — sliding reasoning text panel
// ─────────────────────────────────────────────────────────────
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

interface ReasonLine {
  label: string;
  value: string;
  color?: string;
}

interface Props {
  lines: ReasonLine[];
  startFrame?: number;
  accentColor?: string;
}

export const ReasonPanel: React.FC<Props> = ({
  lines,
  startFrame = 0,
  accentColor = COLORS.green,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const slideX = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 20, stiffness: 100 },
  });
  const translateX = interpolate(slideX, [0, 1], [80, 0]);
  const opacity = interpolate(frame - startFrame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      transform: `translateX(${translateX}px)`,
      opacity,
      background: COLORS.bgCard,
      border: `1px solid ${COLORS.border}`,
      borderLeft: `4px solid ${accentColor}`,
      borderRadius: 14,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 12,
      minWidth: 380,
    }}>
      <div style={{
        fontSize: 12,
        color: COLORS.textMuted,
        letterSpacing: 3,
        textTransform: "uppercase",
        fontFamily: "Inter, sans-serif",
        marginBottom: 4,
      }}>
        Reasoning
      </div>

      {lines.map((line, i) => {
        const lineOpacity = interpolate(
          frame - startFrame,
          [i * 8, i * 8 + 12],
          [0, 1],
          { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
        );
        return (
          <div key={i} style={{ opacity: lineOpacity, display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div style={{
              fontSize: 12,
              color: line.color ?? COLORS.textSecondary,
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              minWidth: 120,
              paddingTop: 1,
            }}>
              {line.label}
            </div>
            <div style={{
              fontSize: 15,
              color: COLORS.textPrimary,
              fontFamily: "Inter, sans-serif",
              lineHeight: 1.4,
            }}>
              {line.value}
            </div>
          </div>
        );
      })}
    </div>
  );
};
