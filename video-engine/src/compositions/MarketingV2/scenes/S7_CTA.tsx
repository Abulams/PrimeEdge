// S7_CTA — 0:26–0:30 (120 frames)
// Logo + clean interface + specific CTA + risk disclaimer
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S7_CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });

  const logoScale = spring({ frame: frame - 8, fps, config: { damping: 18, stiffness: 100 } });
  const taglineOp = interpolate(frame, [24, 40], [0, 1], { extrapolateRight: "clamp" });
  const btnScale  = spring({ frame: frame - 45, fps, config: { damping: 14, stiffness: 130 } });
  const btnOp     = interpolate(frame, [45, 60], [0, 1], { extrapolateRight: "clamp" });
  const urlOp     = interpolate(frame, [65, 80], [0, 1], { extrapolateRight: "clamp" });
  const discOp    = interpolate(frame, [75, 90], [0, 1], { extrapolateRight: "clamp" });

  // Subtle pulsing glow on CTA button
  const glowPulse = 1 + 0.06 * Math.sin(frame * 0.14);

  return (
    <AbsoluteFill style={{
      background: COLORS.bg,
      opacity: bgOp,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: 0,
    }}>
      {/* Background glow */}
      <AbsoluteFill style={{
        background: `radial-gradient(ellipse at 50% 45%, ${COLORS.green}12 0%, transparent 60%)`,
      }} />

      {/* Logo */}
      <div style={{
        transform: `scale(${logoScale})`,
        textAlign: "center",
        zIndex: 2,
        marginBottom: 16,
      }}>
        <div style={{
          fontSize: 56,
          fontWeight: 900,
          color: COLORS.textPrimary,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          letterSpacing: 2,
        }}>
          PrimeEdge
        </div>
      </div>

      {/* Tagline */}
      <div style={{
        opacity: taglineOp,
        fontSize: 18,
        color: COLORS.textSecondary,
        letterSpacing: 4,
        fontFamily: "Inter, sans-serif",
        marginBottom: 48,
        zIndex: 2,
      }}>
        QUANTITATIVE FX INTELLIGENCE
      </div>

      {/* CTA Button */}
      <div style={{
        opacity: btnOp,
        transform: `scale(${btnScale})`,
        zIndex: 2,
        marginBottom: 32,
      }}>
        <div style={{
          background: COLORS.green,
          borderRadius: 60,
          padding: "20px 56px",
          fontSize: 22,
          fontWeight: 800,
          color: COLORS.bg,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          letterSpacing: 0.5,
          boxShadow: `0 0 ${40 * glowPulse}px ${COLORS.green}66`,
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}>
          Run a historical replay →
        </div>
      </div>

      {/* URL */}
      <div style={{
        opacity: urlOp,
        fontSize: 18,
        color: COLORS.textSecondary,
        fontFamily: "Inter, monospace",
        zIndex: 2,
        marginBottom: 32,
      }}>
        primeedge.app
      </div>

      {/* Risk disclaimer — small, visible, important */}
      <div style={{
        opacity: discOp,
        fontSize: 13,
        color: COLORS.textMuted,
        fontFamily: "Inter, sans-serif",
        textAlign: "center",
        maxWidth: 640,
        lineHeight: 1.6,
        zIndex: 2,
        padding: "0 40px",
      }}>
        Decision support tool only. Historical performance is not indicative of future results.
        Stops are informed by historical data — not guaranteed. Trading involves risk.
      </div>
    </AbsoluteFill>
  );
};
