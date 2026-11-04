// ─────────────────────────────────────────────────────────────
// DecisionCard — WAIT / TAKE IT / STAND DOWN badge
// States: evaluating → resolved
// ─────────────────────────────────────────────────────────────
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

export type DecisionState = "EVALUATING" | "TAKE IT" | "WAIT" | "STAND DOWN";

const STATE_COLOR: Record<DecisionState, string> = {
  "EVALUATING": COLORS.textMuted,
  "TAKE IT":    COLORS.green,
  "WAIT":       COLORS.amber,
  "STAND DOWN": COLORS.red,
};

const STATE_GLOW: Record<DecisionState, string> = {
  "EVALUATING": "transparent",
  "TAKE IT":    `${COLORS.green}44`,
  "WAIT":       `${COLORS.amber}33`,
  "STAND DOWN": `${COLORS.red}44`,
};

interface Props {
  state: DecisionState;
  resolveAtFrame?: number; // frame at which EVALUATING flips to final state
  instrument?: string;
  direction?: "LONG" | "SHORT";
  size?: "sm" | "lg";
}

export const DecisionCard: React.FC<Props> = ({
  state,
  resolveAtFrame = 0,
  instrument = "XAUUSD",
  direction = "LONG",
  size = "lg",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Resolve animation
  const resolved = frame >= resolveAtFrame;
  const displayState: DecisionState = resolved ? state : "EVALUATING";
  const color = STATE_COLOR[displayState];
  const glow  = STATE_GLOW[displayState];

  const revealScale = spring({
    frame: frame - resolveAtFrame,
    fps,
    config: { damping: 14, stiffness: 160, mass: 0.7 },
  });
  const pulseScale = resolved
    ? 1 + 0.012 * Math.sin(frame * 0.18)
    : 1;

  const isLg = size === "lg";
  const dirColor = direction === "LONG" ? COLORS.green : COLORS.red;

  return (
    <div style={{
      display: "inline-flex",
      flexDirection: "column",
      alignItems: "center",
      gap: isLg ? 12 : 6,
      transform: `scale(${resolved ? pulseScale : 1})`,
    }}>
      {/* Instrument row */}
      {isLg && (
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{
            fontSize: 22,
            fontWeight: 900,
            color: COLORS.textPrimary,
            fontFamily: "Inter, sans-serif",
            letterSpacing: 2,
          }}>{instrument}</span>
          <span style={{
            fontSize: 15,
            fontWeight: 700,
            color: dirColor,
            fontFamily: "Inter, sans-serif",
          }}>
            {direction === "LONG" ? "▲ LONG" : "▼ SHORT"}
          </span>
        </div>
      )}

      {/* Decision badge */}
      <div style={{
        background: resolved ? glow : "transparent",
        border: `2px solid ${color}`,
        borderRadius: isLg ? 16 : 10,
        padding: isLg ? "18px 48px" : "8px 20px",
        transform: resolved ? `scale(${revealScale})` : "scale(1)",
        boxShadow: resolved ? `0 0 40px ${color}55` : "none",
        transition: "box-shadow 0.4s",
      }}>
        <span style={{
          fontSize: isLg ? 42 : 20,
          fontWeight: 900,
          color,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          letterSpacing: isLg ? 3 : 1.5,
        }}>
          {displayState === "EVALUATING"
            ? `EVALUATING${".".repeat((Math.floor(frame / 8) % 4))}`
            : displayState}
        </span>
      </div>
    </div>
  );
};
