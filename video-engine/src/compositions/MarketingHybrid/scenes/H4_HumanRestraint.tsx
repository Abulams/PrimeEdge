// ─────────────────────────────────────────────────────────────
// H4_HumanRestraint — 0:18–0:23 (150 frames)
// Human restraint & composure: hand disengaging from mouse
// ─────────────────────────────────────────────────────────────
import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  spring,
  useVideoConfig,
} from "remotion";
import { COLORS } from "../../../utils/colors";

export const H4_HumanRestraint: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Slow smooth Ken Burns drift (pulling back slightly, calm energy)
  const scale = interpolate(frame, [0, 150], [1.06, 1.0], { extrapolateRight: "clamp" });

  // Cool cyan/emerald ambient monitor glow breathing across the desk
  const glow = 0.2 + 0.08 * Math.sin(frame * 0.12);

  // Text entrance
  const textScale = spring({ frame: frame - 15, fps, config: { damping: 16, stiffness: 120 } });
  const textOp = interpolate(frame, [15, 30], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#05070c", overflow: "hidden" }}>
      {/* Hand resting flat on desk away from mouse */}
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "center 50%" }}>
        <Img
          src={staticFile("footage/trader_restraint.jpg")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>

      {/* Cool institutional ambient lighting overlay */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 40%, rgba(0, 200, 150, ${glow}) 0%, transparent 65%)`,
          mixBlendMode: "screen",
          pointerEvents: "none",
        }}
      />

      {/* Cinematic vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse at center, transparent 45%, rgba(5, 7, 12, 0.75) 100%)",
          pointerEvents: "none",
        }}
      />

      {/* On-screen statement */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-end",
          paddingBottom: 90,
          opacity: textOp,
          zIndex: 4,
        }}
      >
        <div
          style={{
            transform: `scale(${textScale})`,
            background: "rgba(10, 14, 26, 0.88)",
            backdropFilter: "blur(14px)",
            border: `1.5px solid ${COLORS.green}55`,
            borderRadius: 18,
            padding: "20px 48px",
            textAlign: "center",
            boxShadow: `0 10px 40px rgba(0, 0, 0, 0.8), 0 0 30px ${COLORS.green}22`,
          }}
        >
          <div
            style={{
              fontSize: 36,
              fontWeight: 900,
              color: "#FFFFFF",
              fontFamily: "Inter, SF Pro Display, sans-serif",
              letterSpacing: 2,
              lineHeight: 1.2,
            }}
          >
            NO CHASE.{" "}
            <span style={{ color: COLORS.green, textShadow: `0 0 20px ${COLORS.green}88` }}>
              NO GUESSING.
            </span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
