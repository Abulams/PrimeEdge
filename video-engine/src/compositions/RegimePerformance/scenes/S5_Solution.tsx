// ─────────────────────────────────────────────────────────────
// Scene 5: Solution & CTA (964-1264 frames = 10 seconds)
// "Check the Dollar Index before you enter. PrimeEdge tracks it and tells you when conditions are favorable. See the evidence at PrimeEdge dot app."
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S5_Solution: React.FC = () => {
  const frame = useCurrentFrame();

  const mainTextOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const subTextOpacity = interpolate(frame, [60, 90], [0, 1], { extrapolateRight: "clamp" });
  const logoOpacity = interpolate(frame, [120, 150], [0, 1], { extrapolateRight: "clamp" });
  const ctaOpacity = interpolate(frame, [150, 180], [0, 1], { extrapolateRight: "clamp" });

  const scale = interpolate(frame, [0, 60], [0.9, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        background: "#0a0a0a",
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
            fontSize: 60,
            fontWeight: 900,
            color: "#00ff64",
            margin: 0,
            textTransform: "uppercase",
            letterSpacing: "1px",
            textShadow: "0 0 20px rgba(0, 255, 100, 0.3)",
          }}
        >
          Check the Dollar Index
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
        before you enter.
      </p>

      <p
        style={{
          fontSize: 28,
          fontWeight: 600,
          color: "#ffffff",
          margin: 0,
          opacity: subTextOpacity,
          textAlign: "center",
          lineHeight: 1.4,
        }}
      >
        PrimeEdge tracks it and tells you when conditions are favorable.
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
          color: "#00ff64",
          margin: "40px 0 0 0",
          opacity: ctaOpacity,
          textAlign: "center",
          textTransform: "uppercase",
          letterSpacing: "1px",
        }}
      >
        See the evidence at PRIMEEDGE.APP.
      </p>
    </AbsoluteFill>
  );
};
