// ─────────────────────────────────────────────────────────────
// Scene 1: Pain Hook (0-109 frames = 3.6 seconds)
// "The same trading setup does not always perform the same way."
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S1_PainHook: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
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
            fontSize: 70,
            fontWeight: 900,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.1,
            textShadow: "0 0 20px rgba(255, 255, 255, 0.3)",
          }}
        >
          SAME SETUP.
        </h1>
        <h1
          style={{
            fontSize: 70,
            fontWeight: 900,
            color: "#ff4444",
            margin: "20px 0",
            lineHeight: 1.1,
            textShadow: "0 0 20px rgba(255, 0, 0, 0.3)",
          }}
        >
          DIFFERENT REGIME.
        </h1>
      </div>
    </AbsoluteFill>
  );
};
