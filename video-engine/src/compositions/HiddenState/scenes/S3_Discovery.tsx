// ─────────────────────────────────────────────────────────────
// Scene 3: The Discovery (12-20 seconds)
// "Only 2 direct transitions. 161 went through consolidation."
// Timeline/Flow Diagram Style - Comparison visualization
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const S3_Discovery: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const bar1Width = interpolate(frame, [60, 150], [0, 540], { extrapolateRight: "clamp" });
  const bar2Width = interpolate(frame, [90, 180], [0, 10], { extrapolateRight: "clamp" });
  const textOpacity = interpolate(frame, [120, 180], [0, 1], { extrapolateRight: "clamp" });

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
      <p
        style={{
          fontSize: 32,
          fontWeight: 700,
          color: "#ffffff",
          margin: "0 0 60px 0",
          opacity,
          textAlign: "center",
        }}
      >
        How did markets actually transition?
      </p>

      {/* Bar 1: Through Consolidation */}
      <div style={{ width: "100%", opacity, marginBottom: 40 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
          <span style={{ fontSize: 24, color: "#ffffff", fontWeight: 600 }}>Through Consolidation</span>
          <span style={{ fontSize: 24, color: "#eab308", fontWeight: 700 }}>161</span>
        </div>
        <div
          style={{
            width: bar1Width,
            height: 40,
            background: "#eab308",
            borderRadius: 8,
            boxShadow: "0 0 20px rgba(234, 179, 8, 0.3)",
          }}
        />
      </div>

      {/* Bar 2: Direct */}
      <div style={{ width: "100%", opacity, marginBottom: 40 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
          <span style={{ fontSize: 24, color: "#ffffff", fontWeight: 600 }}>Direct Transition</span>
          <span style={{ fontSize: 24, color: "#3b82f6", fontWeight: 700 }}>2</span>
        </div>
        <div
          style={{
            width: bar2Width,
            height: 40,
            background: "#3b82f6",
            borderRadius: 8,
            boxShadow: "0 0 20px rgba(59, 130, 246, 0.3)",
          }}
        />
      </div>

      {/* Percentage Callout */}
      <div
        style={{
          opacity: textOpacity,
          textAlign: "center",
          marginTop: 40,
        }}
      >
        <h2
          style={{
            fontSize: 80,
            fontWeight: 800,
            color: "#eab308",
            margin: 0,
          }}
        >
          95%
        </h2>
        <p
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: "#ffffff",
            margin: "10px 0 0 0",
          }}
        >
          went through consolidation
        </p>
      </div>
    </AbsoluteFill>
  );
};
