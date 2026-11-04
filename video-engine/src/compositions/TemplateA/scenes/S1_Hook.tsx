// Scene 1: Hook - Chart/question in frame one
// "Same ticker, two timeframes, opposite signals—why?"
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: () => 1 });

  return (
    <AbsoluteFill style={{ background: "#0f172a" }}>
      {/* Source/date/state label */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 40,
          fontSize: 18,
          color: "#94a3b8",
          fontWeight: 400,
          opacity,
        }}
      >
        XAUUSD • H4 • 2020-2026 • REPLAY
      </div>

      {/* Chart - Bearish DXY Regime */}
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 100,
          right: 100,
          height: 400,
          background: "#1e293b",
          borderRadius: 16,
          opacity,
          display: "flex",
          flexDirection: "column",
          padding: 24,
        }}
      >
        <div
          style={{
            fontSize: 28,
            fontWeight: "bold",
            color: COLORS.green,
            marginBottom: 20,
          }}
        >
          Bearish DXY Regime
        </div>
        {/* Simulated chart line */}
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 800 300"
          style={{ overflow: "visible" }}
        >
          <path
            d="M 0 250 Q 100 200 200 220 T 400 180 T 600 140 T 800 100"
            stroke={COLORS.green}
            strokeWidth="4"
            fill="none"
          />
        </svg>
      </div>

      {/* Hook text */}
      <div
        style={{
          position: "absolute",
          bottom: 200,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity,
        }}
      >
        <div
          style={{
            fontSize: 42,
            fontWeight: "bold",
            color: "#ffffff",
            marginBottom: 16,
          }}
        >
          Same ticker, two timeframes,
        </div>
        <div
          style={{
            fontSize: 42,
            fontWeight: "bold",
            color: COLORS.yellow,
          }}
        >
          opposite signals—why?
        </div>
      </div>
    </AbsoluteFill>
  );
};
