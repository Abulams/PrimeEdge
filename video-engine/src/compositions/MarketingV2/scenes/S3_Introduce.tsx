// S3_Introduce — 0:06–0:09 (90 frames)
// PrimeEdge interface arrives large and clean
// Three decision badges appear in sequence: WAIT → TAKE IT → STAND DOWN
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { DecisionCard } from "../components/DecisionCard";

const Badge: React.FC<{
  label: string;
  color: string;
  startFrame: number;
}> = ({ label, color, startFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sc = spring({ frame: frame - startFrame, fps, config: { damping: 16, stiffness: 160 } });
  const op = interpolate(frame, [startFrame, startFrame + 10], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{
      transform: `scale(${sc})`,
      opacity: op,
      border: `2px solid ${color}`,
      borderRadius: 14,
      padding: "16px 40px",
      background: `${color}18`,
      boxShadow: `0 0 30px ${color}33`,
    }}>
      <span style={{
        fontSize: 36,
        fontWeight: 900,
        color,
        fontFamily: "Inter, SF Pro Display, sans-serif",
        letterSpacing: 3,
      }}>
        {label}
      </span>
    </div>
  );
};

export const S3_Introduce: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const logoScale = spring({ frame: frame - 5, fps, config: { damping: 20, stiffness: 100 } });
  const headlineOp = interpolate(frame, [18, 35], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: COLORS.bg,
      opacity: bgOp,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 40,
    }}>
      {/* Glow backdrop */}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${COLORS.green}0F 0%, transparent 60%)` }} />

      {/* Logo */}
      <div style={{ transform: `scale(${logoScale})`, textAlign: "center", zIndex: 2 }}>
        <div style={{
          fontSize: 48,
          fontWeight: 900,
          color: COLORS.textPrimary,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          letterSpacing: 2,
        }}>
          PrimeEdge
        </div>
        <div style={{
          fontSize: 16,
          color: COLORS.textSecondary,
          fontFamily: "Inter, sans-serif",
          letterSpacing: 4,
          marginTop: 6,
        }}>
          QUANTITATIVE FX INTELLIGENCE
        </div>
      </div>

      {/* Headline */}
      <div style={{
        opacity: headlineOp,
        fontSize: 28,
        color: COLORS.textSecondary,
        fontFamily: "Inter, sans-serif",
        textAlign: "center",
        fontWeight: 500,
        zIndex: 2,
        maxWidth: 700,
      }}>
        Market noise → <span style={{ color: COLORS.textPrimary, fontWeight: 700 }}>one decision</span> — with a reason
      </div>

      {/* Three decision badges */}
      <div style={{ display: "flex", gap: 24, zIndex: 2 }}>
        <Badge label="WAIT"       color={COLORS.amber} startFrame={40} />
        <Badge label="TAKE IT"    color={COLORS.green}  startFrame={54} />
        <Badge label="STAND DOWN" color={COLORS.red}    startFrame={68} />
      </div>
    </AbsoluteFill>
  );
};
