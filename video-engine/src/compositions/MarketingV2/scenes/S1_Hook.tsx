// S1_Hook — 0:00–0:02 (60 frames)
// Wall of signal noise → hard cut → one clean decision card
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { SignalNoiseField } from "../components/SignalNoiseField";

export const S1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Noise fades at frame 70, card enters at frame 76
  const noiseOpacity = interpolate(frame, [60, 75], [1, 0], { extrapolateRight: "clamp" });
  const cardScale = spring({ frame: frame - 76, fps, config: { damping: 16, stiffness: 140 } });
  const cardOpacity = interpolate(frame, [76, 88], [0, 1], { extrapolateRight: "clamp" });

  const textOpacity = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      {/* Signal chaos layer */}
      <div style={{ opacity: noiseOpacity, position: "absolute", inset: 0 }}>
        <SignalNoiseField collapseAtFrame={70} />
      </div>

      {/* Headline — visible through noise */}
      <AbsoluteFill style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: textOpacity,
        zIndex: 2,
      }}>
        <div style={{
          fontSize: 64,
          fontWeight: 900,
          color: COLORS.textPrimary,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          textAlign: "center",
          lineHeight: 1.1,
          opacity: noiseOpacity,  // disappears when noise collapses
          textShadow: `0 0 60px ${COLORS.bg}`,
          padding: "0 80px",
        }}>
          Too many signals.<br />
          <span style={{ color: COLORS.textSecondary }}>No clear decision?</span>
        </div>
      </AbsoluteFill>

      {/* PrimeEdge card — appears after noise collapse */}
      <AbsoluteFill style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: cardOpacity,
        zIndex: 3,
      }}>
        <div style={{
          transform: `scale(${cardScale})`,
          background: COLORS.bgCard,
          border: `1.5px solid ${COLORS.border}`,
          borderRadius: 20,
          padding: "32px 56px",
          textAlign: "center",
          boxShadow: `0 0 80px ${COLORS.green}22`,
        }}>
          <div style={{ fontSize: 14, color: COLORS.textMuted, letterSpacing: 4, fontFamily: "Inter, sans-serif", marginBottom: 12 }}>
            PRIMEEDGE
          </div>
          <div style={{
            fontSize: 48,
            fontWeight: 900,
            color: COLORS.green,
            fontFamily: "Inter, SF Pro Display, sans-serif",
            letterSpacing: 3,
            textShadow: `0 0 30px ${COLORS.green}66`,
          }}>
            TAKE IT
          </div>
          <div style={{ fontSize: 15, color: COLORS.textSecondary, fontFamily: "Inter, sans-serif", marginTop: 10 }}>
            One clear call. With a reason.
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
