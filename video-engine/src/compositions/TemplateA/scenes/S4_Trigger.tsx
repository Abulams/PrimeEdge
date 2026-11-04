// Scene 4: Trigger and invalidation
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S4_Trigger: React.FC = () => {
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
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 40,
            fontWeight: "bold",
            color: COLORS.green,
            marginBottom: 24,
          }}
        >
          Trigger: DXY in BEARISH regime
        </div>
        <div
          style={{
            fontSize: 40,
            fontWeight: "bold",
            color: COLORS.red,
            marginBottom: 48,
          }}
        >
          Invalidation: DXY crosses BULLISH
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 300,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 36,
            fontWeight: "bold",
            color: COLORS.yellow,
          }}
        >
          Check DXY before entry
        </div>
      </div>
    </AbsoluteFill>
  );
};
