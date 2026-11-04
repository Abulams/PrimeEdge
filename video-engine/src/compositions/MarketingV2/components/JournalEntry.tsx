// ─────────────────────────────────────────────────────────────
// JournalEntry — self-writing journal row
// ─────────────────────────────────────────────────────────────
import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

interface Props {
  instrument: string;
  direction: "LONG" | "SHORT";
  entryZone: string;
  stopLevel: string;
  thesis: string;
  timestamp: string;
  startFrame?: number;
}

const TypedText: React.FC<{ text: string; startFrame: number; speed?: number }> = ({
  text,
  startFrame,
  speed = 2,
}) => {
  const frame = useCurrentFrame();
  const charsShown = Math.min(text.length, Math.max(0, Math.floor((frame - startFrame) * speed)));
  return (
    <span style={{ fontFamily: "Inter, monospace" }}>
      {text.slice(0, charsShown)}
      {charsShown < text.length && (
        <span style={{
          opacity: Math.sin(frame * 0.4) > 0 ? 1 : 0,
          color: COLORS.green,
        }}>|</span>
      )}
    </span>
  );
};

export const JournalEntry: React.FC<Props> = ({
  instrument,
  direction,
  entryZone,
  stopLevel,
  thesis,
  timestamp,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rowScale = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 18, stiffness: 120 },
  });

  const opacity = interpolate(frame - startFrame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  const dirColor = direction === "LONG" ? COLORS.green : COLORS.red;

  const fields = [
    { label: "INSTRUMENT", value: instrument, color: COLORS.textPrimary, delay: 0, weight: 800 },
    { label: "DIRECTION",  value: `${direction === "LONG" ? "▲" : "▼"} ${direction}`, color: dirColor, delay: 5, weight: 700 },
    { label: "ENTRY ZONE", value: entryZone, color: COLORS.blue, delay: 10, weight: 600 },
    { label: "STOP LEVEL", value: stopLevel, color: COLORS.red, delay: 15, weight: 600 },
  ];

  return (
    <div style={{
      opacity,
      transform: `scale(${rowScale})`,
      background: COLORS.bgCard,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 16,
      overflow: "hidden",
    }}>
      {/* Header bar */}
      <div style={{
        background: COLORS.bgAccent,
        padding: "10px 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: `1px solid ${COLORS.border}`,
      }}>
        <span style={{ fontSize: 13, color: COLORS.textMuted, letterSpacing: 2, fontFamily: "Inter, sans-serif" }}>
          TRADE LOG
        </span>
        <span style={{ fontSize: 13, color: COLORS.textMuted, fontFamily: "Inter, monospace" }}>
          <TypedText text={timestamp} startFrame={startFrame + 2} speed={3} />
        </span>
      </div>

      {/* Field grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1, background: COLORS.border }}>
        {fields.map((f, i) => (
          <div key={f.label} style={{
            background: COLORS.bgCard,
            padding: "14px 20px",
          }}>
            <div style={{ fontSize: 11, color: COLORS.textMuted, letterSpacing: 2, fontFamily: "Inter, sans-serif", marginBottom: 4 }}>
              {f.label}
            </div>
            <div style={{ fontSize: 18, fontWeight: f.weight, color: f.color, fontFamily: "Inter, sans-serif" }}>
              <TypedText text={f.value} startFrame={startFrame + f.delay} speed={3} />
            </div>
          </div>
        ))}
      </div>

      {/* Thesis */}
      <div style={{ padding: "14px 20px", borderTop: `1px solid ${COLORS.border}` }}>
        <div style={{ fontSize: 11, color: COLORS.textMuted, letterSpacing: 2, fontFamily: "Inter, sans-serif", marginBottom: 6 }}>
          DECISION THESIS
        </div>
        <div style={{ fontSize: 15, color: COLORS.textSecondary, fontFamily: "Inter, sans-serif", lineHeight: 1.5 }}>
          <TypedText text={thesis} startFrame={startFrame + 20} speed={1.5} />
        </div>
      </div>

      {/* Status row */}
      <div style={{
        padding: "10px 20px",
        background: `${COLORS.green}11`,
        borderTop: `1px solid ${COLORS.green}33`,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS.green }} />
        <span style={{ fontSize: 13, color: COLORS.green, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>
          LOGGED — reason on record before entry
        </span>
      </div>
    </div>
  );
};
