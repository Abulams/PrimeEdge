// ─────────────────────────────────────────────────────────────
// Scene 4: Reveal (751-964 frames = 7.1 seconds)
// "That is a 2.3 times win-rate ratio. Your entries are perfect, but market conditions control your results."
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S4_Reveal: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const ratioOpacity = interpolate(frame, [60, 120], [0, 1], { extrapolateRight: "clamp" });
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
          opacity,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: 80,
            fontWeight: 900,
            color: "#00ff64",
            margin: 0,
            textShadow: "0 0 30px rgba(0, 255, 100, 0.5)",
          }}
        >
          2.3×
        </h1>
        <p
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#ffffff",
            margin: "10px 0",
            lineHeight: 1.4,
          }}
        >
          win-rate ratio
        </p>
      </div>

      <div
        style={{
          marginTop: 60,
          opacity: ratioOpacity,
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#ff4444",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          Your entries are perfect
        </p>
        <p
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#ffffff",
            margin: "10px 0 0 0",
            lineHeight: 1.4,
          }}
        >
          but market conditions control your results
        </p>
      </div>
    </AbsoluteFill>
  );
};
