// S6_Journal — 0:22–0:26 (120 frames)
// Auto-populating trade journal — reason on record before entry
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { JournalEntry } from "../components/JournalEntry";

export const S6_Journal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const titleOp = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOp }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 80%, ${COLORS.blue}0A 0%, transparent 60%)` }} />

      <AbsoluteFill style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 100px",
        gap: 32,
      }}>

        {/* Headline */}
        <div style={{ opacity: titleOp, textAlign: "center" }}>
          <div style={{
            fontSize: 42,
            fontWeight: 900,
            color: COLORS.textPrimary,
            fontFamily: "Inter, SF Pro Display, sans-serif",
            lineHeight: 1.1,
          }}>
            Every reason.{" "}
            <span style={{ color: COLORS.blue }}>On record.</span>
          </div>
          <div style={{
            fontSize: 20,
            color: COLORS.textSecondary,
            fontFamily: "Inter, sans-serif",
            marginTop: 12,
          }}>
            Before you enter.
          </div>
        </div>

        {/* Journal entry writing itself */}
        <JournalEntry
          instrument="XAUUSD"
          direction="LONG"
          entryZone="2318.50 – 2321.00"
          stopLevel="2315.00 (P90 boundary)"
          thesis="MSS confirmed above 1H resistance. DXY weak. 187 matched setups — 74% historical continuation. Adverse move typically 8–22 pips."
          timestamp="2026-10-31  09:14:22 UTC  ·  London"
          startFrame={15}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
