// ─────────────────────────────────────────────────────────────
// H2_ProductAction — 0:03–0:07 (120 frames)
// Real PrimeEdge UI interaction: tight 2.4x crop & animated cursor
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

export const H2_ProductAction: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Camera pan & zoom into active watchlist row
  const zoom = interpolate(frame, [0, 40], [1.4, 2.1], { extrapolateRight: "clamp" });
  const panX = interpolate(frame, [0, 60], [0, -180], { extrapolateRight: "clamp" });
  const panY = interpolate(frame, [0, 60], [0, 90], { extrapolateRight: "clamp" });

  // Cursor coordinates animating into the watchlist row & clicking
  const cursorX = interpolate(frame, [15, 60], [900, 720], { extrapolateRight: "clamp" });
  const cursorY = interpolate(frame, [15, 60], [800, 480], { extrapolateRight: "clamp" });
  const isClick = frame >= 60 && frame <= 75;
  const cursorScale = isClick ? 0.85 : 1.0;

  // Highlight box appearing around setup upon click
  const highlightOp = interpolate(frame, [60, 72], [0, 1], { extrapolateRight: "clamp" });

  // Badge entrance
  const badgeScale = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 130 } });
  const badgeOp = interpolate(frame, [10, 20], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, overflow: "hidden" }}>
      {/* Real product screenshot with high-resolution pan & zoom */}
      <AbsoluteFill
        style={{
          transform: `scale(${zoom}) translate(${panX}px, ${panY}px)`,
          transformOrigin: "center center",
        }}
      >
        <Img
          src={staticFile("footage/product_cockpit.png")}
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
        />

        {/* Dynamic click highlight overlay on the row */}
        <div
          style={{
            position: "absolute",
            left: "22%",
            top: "36%",
            width: "56%",
            height: "18%",
            border: `2px solid ${COLORS.amber}`,
            borderRadius: 8,
            boxShadow: `0 0 35px ${COLORS.amber}55`,
            background: `${COLORS.amber}15`,
            opacity: highlightOp,
            pointerEvents: "none",
          }}
        />
      </AbsoluteFill>

      {/* Animated SVG mouse cursor */}
      <div
        style={{
          position: "absolute",
          left: cursorX,
          top: cursorY,
          transform: `scale(${cursorScale})`,
          transition: "transform 0.1s",
          pointerEvents: "none",
          zIndex: 10,
        }}
      >
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path
            d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87c.45 0 .67-.54.35-.85L6.35 2.85a.5.5 0 0 0-.85.36z"
            fill="#FFFFFF"
            stroke="#000000"
            strokeWidth="1.5"
          />
        </svg>
      </div>

      {/* Top Header Badge */}
      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "flex-start",
          alignItems: "flex-start",
          padding: 60,
          opacity: badgeOp,
          zIndex: 5,
        }}
      >
        <div
          style={{
            transform: `scale(${badgeScale})`,
            background: "rgba(10, 14, 26, 0.9)",
            border: `1.5px solid ${COLORS.blue}`,
            borderRadius: 14,
            padding: "14px 28px",
            display: "flex",
            alignItems: "center",
            gap: 12,
            boxShadow: `0 0 30px ${COLORS.blue}44`,
          }}
        >
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: COLORS.blue }} />
          <span
            style={{
              fontSize: 16,
              fontWeight: 800,
              color: "#FFFFFF",
              letterSpacing: 2,
              fontFamily: "Inter, sans-serif",
            }}
          >
            DECISION FILTER ACTIVE
          </span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
