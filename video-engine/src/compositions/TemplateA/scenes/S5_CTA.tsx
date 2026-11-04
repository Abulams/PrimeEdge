// Scene 5: CTA - Saveable checklist
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { COLORS } from "../../../utils/colors";

export const S5_CTA: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: "#0f172a" }}>
      <div
        style={{
          position: "absolute",
          top: 350,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: "bold",
            color: COLORS.blue,
            marginBottom: 32,
          }}
        >
          PRIMEEDGE.APP
        </div>
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
            color: "#ffffff",
            marginBottom: 24,
          }}
        >
          Save the regime checklist
        </div>
        <div
          style={{
            fontSize: 32,
            fontWeight: "bold",
            color: "#94a3b8",
          }}
        >
          Evidence before execution.
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 0,
          right: 0,
          textAlign: "center",
          fontSize: 16,
          color: "#64748b",
          padding: "0 40px",
        }}
      >
        Historical analysis is not a guarantee of future results. Trading involves risk.
      </div>
    </AbsoluteFill>
  );
};
