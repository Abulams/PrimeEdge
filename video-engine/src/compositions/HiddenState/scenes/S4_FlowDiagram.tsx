// ─────────────────────────────────────────────────────────────
// Scene 4: Flow Diagram (20-30 seconds)
// Animated timeline showing BULLISH → CONSOLIDATING → BEARISH with DXY charts
// Timeline/Flow Diagram Style - Core visual
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const Chart: React.FC<{ color: string, label: string }> = ({ color, label }) => {
  return (
    <div
      style={{
        width: 140,
        height: 80,
        background: "#1e293b",
        borderRadius: 8,
        padding: 8,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Simple line chart representation */}
      <svg width="120" height="40" viewBox="0 0 120 40">
        <line
          x1="0"
          y1={label === "BULLISH" ? 30 : label === "BEARISH" ? 10 : 20}
          x2="120"
          y2={label === "BULLISH" ? 10 : label === "BEARISH" ? 30 : 20}
          stroke={color}
          strokeWidth="3"
          fill="none"
        />
        {label === "CONSOLIDATING" && (
          <>
            <line x1="40" y1="15" x2="40" y2="25" stroke={color} strokeWidth="2" />
            <line x1="80" y1="15" x2="80" y2="25" stroke={color} strokeWidth="2" />
          </>
        )}
      </svg>
      <span style={{ fontSize: 12, fontWeight: 600, color: "#ffffff", marginTop: 4 }}>DXY</span>
    </div>
  );
};

export const S4_FlowDiagram: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  const node1Opacity = interpolate(frame, [30, 60], [0, 1], { extrapolateRight: "clamp" });
  const arrow1Width = interpolate(frame, [60, 120], [0, 150], { extrapolateRight: "clamp" });
  const node2Opacity = interpolate(frame, [90, 120], [0, 1], { extrapolateRight: "clamp" });
  const arrow2Width = interpolate(frame, [120, 180], [0, 150], { extrapolateRight: "clamp" });
  const node3Opacity = interpolate(frame, [150, 180], [0, 1], { extrapolateRight: "clamp" });
  const textOpacity = interpolate(frame, [180, 240], [0, 1], { extrapolateRight: "clamp" });

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
          fontSize: 28,
          fontWeight: 600,
          color: "#ffffff",
          margin: "0 0 60px 0",
          opacity,
          textAlign: "center",
        }}
      >
        This is how markets actually change
      </p>

      {/* Flow Diagram */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 20,
          opacity,
        }}
      >
        {/* Node 1: BULLISH */}
        <div
          style={{
            opacity: node1Opacity,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              background: "#3b82f6",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 30px rgba(59, 130, 246, 0.5)",
            }}
          >
            <span style={{ fontSize: 20, fontWeight: 700, color: "#ffffff" }}>BULLISH</span>
          </div>
          <Chart color="#3b82f6" label="BULLISH" />
        </div>

        {/* Arrow 1 */}
        <div
          style={{
            width: arrow1Width,
            height: 4,
            background: "#ffffff",
            opacity: 0.5,
          }}
        />

        {/* Node 2: CONSOLIDATING */}
        <div
          style={{
            opacity: node2Opacity,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              background: "#eab308",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 30px rgba(234, 179, 8, 0.5)",
            }}
          >
            <span style={{ fontSize: 16, fontWeight: 700, color: "#ffffff" }}>CONSOLIDATING</span>
          </div>
          <Chart color="#eab308" label="CONSOLIDATING" />
        </div>

        {/* Arrow 2 */}
        <div
          style={{
            width: arrow2Width,
            height: 4,
            background: "#ffffff",
            opacity: 0.5,
          }}
        />

        {/* Node 3: BEARISH */}
        <div
          style={{
            opacity: node3Opacity,
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              background: "#8b5cf6",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 30px rgba(139, 92, 246, 0.5)",
            }}
          >
            <span style={{ fontSize: 20, fontWeight: 700, color: "#ffffff" }}>BEARISH</span>
          </div>
          <Chart color="#8b5cf6" label="BEARISH" />
        </div>
      </div>

      {/* Bottom Text */}
      <div
        style={{
          opacity: textOpacity,
          textAlign: "center",
          marginTop: 60,
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
          Markets don't flip instantly.
        </p>
        <p
          style={{
            fontSize: 24,
            fontWeight: 600,
            color: "#eab308",
            margin: "10px 0 0 0",
            lineHeight: 1.4,
          }}
        >
          They pause in the middle.
        </p>
      </div>
    </AbsoluteFill>
  );
};
