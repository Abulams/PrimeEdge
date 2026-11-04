// Scene 3: Explanation - Competing interpretation
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S3_Explanation: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#0f172a" }}>
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 40,
          fontSize: 18,
          color: "#94a3b8",
          fontWeight: 400,
        }}
      >
        XAUUSD • H4 • 2020-2026 • REPLAY
      </div>

      <div
        style={{
          position: "absolute",
          top: 300,
          left: 100,
          right: 100,
          height: 400,
          background: "#1e293b",
          borderRadius: 16,
          display: "flex",
          flexDirection: "column",
          padding: 24,
        }}
      >
        <div
          style={{
            fontSize: 28,
            fontWeight: "bold",
            color: COLORS.red,
            marginBottom: 20,
          }}
        >
          Bullish DXY Regime
        </div>
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 800 300"
          style={{ overflow: "visible" }}
        >
          <path
            d="M 0 100 Q 100 150 200 130 T 400 170 T 600 210 T 800 250"
            stroke={COLORS.red}
            strokeWidth="4"
            fill="none"
          />
        </svg>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 350,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 44,
            fontWeight: "bold",
            color: COLORS.green,
            marginBottom: 16,
          }}
        >
          Bearish DXY: 69% win rate
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: "bold",
            color: COLORS.red,
          }}
        >
          Bullish DXY: 30% win rate
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 200,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 32,
            fontWeight: "bold",
            color: "#ffffff",
          }}
        >
          Same setup, opposite outcomes
        </div>
      </div>
    </AbsoluteFill>
  );
};
