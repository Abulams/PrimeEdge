// Scene 2: Highlight the level
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S2_Highlight: React.FC = () => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 90], [0, 1], { extrapolateRight: () => 1 });
  const lineOpacity = interpolate(frame, [45, 90], [0, 1], { extrapolateRight: () => 1 });

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
            color: COLORS.green,
            marginBottom: 20,
          }}
        >
          Bearish DXY Regime
        </div>
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
          {/* Key resistance level */}
          <line
            x1="0"
            y1="150"
            x2="800"
            y2="150"
            stroke={COLORS.yellow}
            strokeWidth="4"
            strokeDasharray="10,5"
            opacity={lineOpacity}
          />
        </svg>
      </div>

      {progress > 0.5 && (
        <div
          style={{
            position: "absolute",
            top: 750,
            left: 100,
            fontSize: 28,
            fontWeight: "bold",
            color: COLORS.yellow,
          }}
        >
          Key resistance level
        </div>
      )}

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
            fontSize: 36,
            fontWeight: "bold",
            color: "#ffffff",
          }}
        >
          This level marks regime entry
        </div>
      </div>
    </AbsoluteFill>
  );
};
