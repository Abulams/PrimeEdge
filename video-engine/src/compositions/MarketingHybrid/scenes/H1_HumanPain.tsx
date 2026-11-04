// ─────────────────────────────────────────────────────────────
// H1_HumanPain — 0:00–0:03 (90 frames)
// Human close-up of hesitation & stop-out
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

export const H1_HumanPain: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle slow push-in (Ken Burns)
  const scale = interpolate(frame, [0, 90], [1.0, 1.07], { extrapolateRight: "clamp" });
  
  // Cut from hesitation to red loss phone at frame 45
  const showLoss = frame >= 45;
  const cutOpacity = interpolate(frame, [45, 48], [0, 1], { extrapolateRight: "clamp" });

  // Red ambient pulse simulating monitor/phone light
  const redPulse = 0.25 + 0.15 * Math.sin(frame * 0.18);

  // Typography entrance
  const textScale = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 140 } });
  const textOp = interpolate(frame, [10, 22], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#05070c", overflow: "hidden" }}>
      {/* Base shot 1: Hand hovering over mouse */}
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "center 60%" }}>
        <Img
          src={staticFile("footage/trader_hesitation.jpg")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>

      {/* Base shot 2: Red phone loss cut */}
      {showLoss && (
        <AbsoluteFill style={{ opacity: cutOpacity, transform: `scale(${scale})`, transformOrigin: "center" }}>
          <Img
            src={staticFile("footage/trader_loss_phone.jpg")}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      )}

      {/* Atmospheric lighting overlay */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 60%, rgba(255, 59, 92, ${redPulse}) 0%, transparent 65%)`,
          mixBlendMode: "screen",
          pointerEvents: "none",
        }}
      />

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background: "radial-gradient(ellipse at center, transparent 40%, rgba(5, 7, 12, 0.75) 100%)",
          pointerEvents: "none",
        }}
      />

      {/* Dramatic on-screen headline */}
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
            background: "rgba(10, 14, 26, 0.85)",
            backdropFilter: "blur(12px)",
            border: `1.5px solid rgba(255, 59, 92, 0.4)`,
            borderRadius: 18,
            padding: "20px 48px",
            textAlign: "center",
            boxShadow: "0 10px 40px rgba(0, 0, 0, 0.8)",
          }}
        >
          <div
            style={{
              fontSize: 38,
              fontWeight: 900,
              color: "#FFFFFF",
              fontFamily: "Inter, SF Pro Display, sans-serif",
              letterSpacing: 2,
              lineHeight: 1.2,
            }}
          >
            RIGHT DIRECTION.{" "}
            <span style={{ color: COLORS.red, textShadow: `0 0 20px ${COLORS.red}88` }}>
              WRONG ENTRY.
            </span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
