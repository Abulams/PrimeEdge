// ─────────────────────────────────────────────────────────────
// Scene 5: CTA (30-40 seconds)
// "PrimeEdge tracks these transitions. Know when to wait and when to act."
// Timeline/Flow Diagram Style - Clean branding
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S5_CTA: React.FC = () => {
  const frame = useCurrentFrame();

  const mainTextOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const subTextOpacity = interpolate(frame, [60, 90], [0, 1], { extrapolateRight: "clamp" });
  const logoOpacity = interpolate(frame, [120, 150], [0, 1], { extrapolateRight: "clamp" });
  const ctaOpacity = interpolate(frame, [150, 180], [0, 1], { extrapolateRight: "clamp" });

  const scale = interpolate(frame, [0, 60], [0.9, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: "#0f172a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        padding: 60,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          opacity: mainTextOpacity,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.2,
          }}
        >
          Know when to wait
        </h1>
        <h1
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: "#3b82f6",
            margin: "20px 0",
            lineHeight: 1.2,
          }}
        >
          and when to act
        </h1>
      </div>

      <p
        style={{
          fontSize: 28,
          fontWeight: 600,
          color: "#ffffff",
          margin: "40px 0 20px 0",
          opacity: subTextOpacity,
          textAlign: "center",
          lineHeight: 1.4,
        }}
      >
        PrimeEdge tracks these transitions
      </p>

      {/* Logo */}
      <div
        style={{
          opacity: logoOpacity,
          marginTop: 60,
        }}
      >
        <h2
          style={{
            fontSize: 48,
            fontWeight: 800,
            color: "#ffffff",
            margin: 0,
            letterSpacing: "1px",
          }}
        >
          PRIMEEDGE.APP
        </h2>
      </div>

      {/* CTA */}
      <p
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: "#3b82f6",
          margin: "40px 0 0 0",
          opacity: ctaOpacity,
          textAlign: "center",
          textTransform: "uppercase",
          letterSpacing: "1px",
        }}
      >
        See the research at PRIMEEDGE.APP
      </p>
    </AbsoluteFill>
  );
};
