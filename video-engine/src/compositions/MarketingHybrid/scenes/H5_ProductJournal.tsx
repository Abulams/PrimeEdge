// ─────────────────────────────────────────────────────────────
// H5_ProductJournal — 0:23–0:27 (120 frames)
// Real product workflow: Auto-logging thesis & execution rules
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
import { JournalEntry } from "../../MarketingV2/components/JournalEntry";

export const H5_ProductJournal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle zoom on the execution log
  const bgScale = interpolate(frame, [0, 120], [1.1, 1.18], { extrapolateRight: "clamp" });
  const bgOp = interpolate(frame, [0, 12], [0, 0.45], { extrapolateRight: "clamp" });

  const titleScale = spring({ frame: frame - 5, fps, config: { damping: 16, stiffness: 130 } });
  const titleOp = interpolate(frame, [5, 18], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, overflow: "hidden" }}>
      {/* Background: real execution screenshot with subtle blur */}
      <AbsoluteFill
        style={{
          transform: `scale(${bgScale})`,
          opacity: bgOp,
          filter: "blur(4px)",
          transformOrigin: "center center",
        }}
      >
        <Img
          src={staticFile("footage/product_execution.png")}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </AbsoluteFill>

      {/* Main Journal Card floating in center */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 100px",
          gap: 24,
          zIndex: 4,
        }}
      >
        <div style={{ opacity: titleOp, transform: `scale(${titleScale})`, textAlign: "center" }}>
          <div
            style={{
              fontSize: 36,
              fontWeight: 900,
              color: "#FFFFFF",
              fontFamily: "Inter, SF Pro Display, sans-serif",
            }}
          >
            Every decision.{" "}
            <span style={{ color: COLORS.blue, textShadow: `0 0 25px ${COLORS.blue}66` }}>
              Recorded with the reason.
            </span>
          </div>
        </div>

        <div style={{ width: "100%", maxWidth: 880 }}>
          <JournalEntry
            instrument="XAUUSD"
            direction="LONG"
            entryZone="2318.50 – 2321.00 (P75 Limit Zone)"
            stopLevel="2315.00 (P90 Invalidation)"
            thesis="187 matched historical setups. Typical adverse dip: 8–22 pips. Execution policy: WAIT for preferred zone fill."
            timestamp="2026-11-01  08:14:00 UTC  ·  London"
            startFrame={15}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
