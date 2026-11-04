// ─────────────────────────────────────────────────────────────
// Scene 3: Loss Realization (504-751 frames = 8.2 seconds)
// "When the Dollar is weak, gold and EUR pairs win 69 percent of the time. When it's strong, you lose 70 percent of trades."
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S3_LossRealization: React.FC = () => {
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
          When the Dollar is weak
        </p>
      </div>

      <div
        style={{
          marginTop: 60,
          opacity: dataOpacity,
          display: "flex",
          flexDirection: "column",
          gap: 20,
          alignItems: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            gap: 40,
            alignItems: "center",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 20, color: "#00ff64", margin: 0, fontWeight: 700 }}>Bearish DXY</p>
            <h2 style={{ fontSize: 80, color: "#00ff64", margin: "10px 0", textShadow: "0 0 20px rgba(0, 255, 100, 0.5)" }}>69%</h2>
            <p style={{ fontSize: 20, color: "#ffffff", margin: 0 }}>win rate</p>
          </div>
          <div style={{ textAlign: "center" }}>
            <p style={{ fontSize: 20, color: "#ff4444", margin: 0, fontWeight: 700 }}>Bullish DXY</p>
            <h2 style={{ fontSize: 80, color: "#ff4444", margin: "10px 0", textShadow: "0 0 20px rgba(255, 0, 0, 0.5)" }}>30%</h2>
            <p style={{ fontSize: 20, color: "#ffffff", margin: 0 }}>win rate</p>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
