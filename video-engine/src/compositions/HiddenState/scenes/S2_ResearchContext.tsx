// ─────────────────────────────────────────────────────────────
// Scene 2: Research Context (4-12 seconds)
// "We analyzed 1,512 trading days (2020-2026). Found 163 regime transitions."
// Timeline/Flow Diagram Style - Data card aesthetic
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S2_ResearchContext: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const dataOpacity = interpolate(frame, [60, 120], [0, 1], { extrapolateRight: "clamp" });
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
        <p
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          We analyzed
        </p>
        <h1
          style={{
            fontSize: 100,
            fontWeight: 800,
            color: "#3b82f6",
            margin: "10px 0",
          }}
        >
          1,512
        </h1>
        <p
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          trading days (2020-2026)
        </p>
      </div>

      <div
        style={{
          marginTop: 60,
          opacity: dataOpacity,
          textAlign: "center",
        }}
      >
        <p
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          Found
        </p>
        <h2
          style={{
            fontSize: 60,
            fontWeight: 700,
            color: "#3b82f6",
            margin: "10px 0",
          }}
        >
          163
        </h2>
        <p
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          regime transitions
        </p>
      </div>
    </AbsoluteFill>
  );
};
