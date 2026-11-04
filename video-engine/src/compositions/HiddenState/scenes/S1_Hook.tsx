// ─────────────────────────────────────────────────────────────
// Scene 1: Hook (0-4 seconds)
// "You're trading the wrong market state"
// Timeline/Flow Diagram Style - Clean, minimal
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S1_Hook: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
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
          opacity,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontSize: 64,
            fontWeight: 700,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.2,
          }}
        >
          You're trading the
        </h1>
        <h1
          style={{
            fontSize: 64,
            fontWeight: 700,
            color: "#3b82f6",
            margin: "20px 0",
            lineHeight: 1.2,
          }}
        >
          wrong market state
        </h1>
      </div>
    </AbsoluteFill>
  );
};
