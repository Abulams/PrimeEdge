// ─────────────────────────────────────────────────────────────
// H6_BrandCTA — 0:27–0:30.6 (108 frames)
// Final Branded CTA & Actionable Next Step
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

export const H6_BrandCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const logoScale = spring({ frame: frame - 5, fps, config: { damping: 18, stiffness: 110 } });
  const taglineOp = interpolate(frame, [18, 32], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: frame - 35, fps, config: { damping: 15, stiffness: 140 } });
  const btnOp = interpolate(frame, [35, 48], [0, 1], { extrapolateRight: "clamp" });
  const discOp = interpolate(frame, [55, 70], [0, 1], { extrapolateRight: "clamp" });

  const pulse = 1 + 0.05 * Math.sin(frame * 0.15);

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        opacity: bgOp,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 5,
      }}
    >
      {/* Background emerald glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 45%, ${COLORS.green}15 0%, transparent 60%)`,
        }}
      />

      {/* Brand Name */}
      <div style={{ transform: `scale(${logoScale})`, textAlign: "center", marginBottom: 12 }}>
        <div
          style={{
            fontSize: 58,
            fontWeight: 900,
            color: COLORS.textPrimary,
            fontFamily: "Inter, SF Pro Display, sans-serif",
            letterSpacing: 2,
          }}
        >
          PrimeEdge
        </div>
      </div>

      {/* Tagline */}
      <div
        style={{
          opacity: taglineOp,
          fontSize: 20,
          color: COLORS.textSecondary,
          letterSpacing: 3,
          fontFamily: "Inter, sans-serif",
          marginBottom: 40,
        }}
      >
        Trade with evidence. Execute with discipline.
      </div>

      {/* CTA Button */}
      <div
        style={{
          opacity: btnOp,
          transform: `scale(${btnScale * pulse})`,
          marginBottom: 28,
        }}
      >
        <div
          style={{
            background: COLORS.green,
            borderRadius: 60,
            padding: "18px 52px",
            fontSize: 22,
            fontWeight: 800,
            color: COLORS.bg,
            fontFamily: "Inter, SF Pro Display, sans-serif",
            letterSpacing: 0.5,
            boxShadow: `0 0 35px ${COLORS.green}66`,
          }}
        >
          Run a historical replay →
        </div>
      </div>

      {/* URL */}
      <div
        style={{
          opacity: btnOp,
          fontSize: 18,
          color: COLORS.textSecondary,
          fontFamily: "Inter, monospace",
          marginBottom: 32,
        }}
      >
        primeedge.app
      </div>

      {/* Risk Disclosure */}
      <div
        style={{
          opacity: discOp,
          fontSize: 12,
          color: COLORS.textMuted,
          fontFamily: "Inter, sans-serif",
          textAlign: "center",
          maxWidth: 660,
          lineHeight: 1.5,
          padding: "0 40px",
        }}
      >
        Decision support system. Historical analysis is not a guarantee of future outcomes.
        All stops are statistical boundaries informed by historical distributions.
      </div>
    </AbsoluteFill>
  );
};
