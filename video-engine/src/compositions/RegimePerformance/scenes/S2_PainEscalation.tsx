// ─────────────────────────────────────────────────────────────
// Scene 2: Pain Escalation (109-504 frames = 13.2 seconds)
// "We backtested 4,469 trades across 6 instruments from 2021 to 2025. XAUUSD, GBPUSD, EURUSD, AUDUSD, USDJPY, and US100."
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S2_PainEscalation: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const dataOpacity = interpolate(frame, [60, 120], [0, 1], { extrapolateRight: "clamp" });
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
        <p
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#ffffff",
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          We backtested
        </p>
        <h1
          style={{
            fontSize: 100,
            fontWeight: 900,
            color: "#00ff64",
            margin: "10px 0",
            textShadow: "0 0 30px rgba(0, 255, 100, 0.5)",
          }}
        >
          4,469
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
          trades across 6 instruments
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
          2021-2025
        </p>
        <p
          style={{
            fontSize: 22,
            fontWeight: 600,
            color: "#00ff64",
            margin: "10px 0 0 0",
            lineHeight: 1.4,
          }}
        >
          XAUUSD • GBPUSD • EURUSD • AUDUSD • USDJPY • US100
        </p>
      </div>
    </AbsoluteFill>
  );
};
