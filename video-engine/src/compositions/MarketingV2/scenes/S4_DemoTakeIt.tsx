// S4_DemoTakeIt — 0:09–0:17 (240 frames)
// Full causal chain: XAUUSD setup → history → MAE → entry zone → stop → TAKE IT
// Each step triggers the next — camera language: wide → zoom in
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";
import { HistoricalSampleCounter } from "../components/HistoricalSampleCounter";
import { AdverseExcursionChart } from "../components/AdverseExcursionChart";
import { ReasonPanel } from "../components/ReasonPanel";
import { DecisionCard } from "../components/DecisionCard";

// Step timing within scene (relative frames)
const STEPS = {
  setupEnter:    0,
  histExpand:    30,
  maeChart:      60,
  entryZone:     90,
  stopZone:     120,
  reason:       150,
  decision:     180,
};

const EntryZoneVisual: React.FC<{ startFrame: number; p25: number; p75: number; p90: number }> = ({
  startFrame, p25, p75, p90
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sc = spring({ frame: frame - startFrame, fps, config: { damping: 20, stiffness: 80 } });
  const op = interpolate(frame, [startFrame, startFrame + 12], [0, 1], { extrapolateRight: "clamp" });
  const stopOp = interpolate(frame, [startFrame + 30, startFrame + 44], [0, 1], { extrapolateRight: "clamp" });

  const H = 220;
  const totalRange = p90 + 20;
  const toY = (pips: number) => (1 - pips / totalRange) * H;

  const entryTop = toY(p75);
  const entryBot = toY(p25);
  const stopY = toY(p90);

  return (
    <div style={{ opacity: op, transform: `scaleY(${sc})`, transformOrigin: "bottom" }}>
      <div style={{ fontSize: 12, color: COLORS.textMuted, letterSpacing: 3, textTransform: "uppercase", fontFamily: "Inter, sans-serif", marginBottom: 8 }}>
        Price Zone
      </div>
      <div style={{ position: "relative", width: 120, height: H, background: COLORS.bgAccent, borderRadius: 8, overflow: "hidden" }}>
        {/* Entry zone (green band) */}
        <div style={{
          position: "absolute",
          top: entryTop,
          height: entryBot - entryTop,
          left: 0, right: 0,
          background: `${COLORS.green}33`,
          borderTop: `2px solid ${COLORS.green}`,
          borderBottom: `2px solid ${COLORS.green}`,
        }} />
        {/* P25 label */}
        <div style={{ position: "absolute", top: entryBot - 4, left: 8, fontSize: 11, color: COLORS.green, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>P25</div>
        {/* P75 label */}
        <div style={{ position: "absolute", top: entryTop - 16, left: 8, fontSize: 11, color: COLORS.green, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>P75</div>

        {/* Stop zone (red dashed) */}
        <div style={{
          opacity: stopOp,
          position: "absolute",
          top: stopY,
          left: 0, right: 0,
          borderTop: `2px dashed ${COLORS.red}`,
        }} />
        <div style={{ opacity: stopOp, position: "absolute", top: stopY + 4, right: 8, fontSize: 11, color: COLORS.red, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>P90 STOP</div>
      </div>
    </div>
  );
};

export const S4_DemoTakeIt: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgOp = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  // Setup card entrance
  const setupScale = spring({ frame: frame - STEPS.setupEnter, fps, config: { damping: 18, stiffness: 120 } });
  const setupOp = interpolate(frame, [STEPS.setupEnter, STEPS.setupEnter + 12], [0, 1], { extrapolateRight: "clamp" });

  // Historical panel expand
  const histOp = interpolate(frame, [STEPS.histExpand, STEPS.histExpand + 12], [0, 1], { extrapolateRight: "clamp" });

  // Spotlight effect — dims everything except current focus
  const focusPhase = frame < STEPS.entryZone ? "hist" : frame < STEPS.decision ? "zone" : "decision";

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOp }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, ${COLORS.green}08 0%, transparent 60%)` }} />

      <AbsoluteFill style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 80px",
        gap: 32,
      }}>

        {/* Step label */}
        <div style={{
          fontSize: 12,
          color: COLORS.textMuted,
          letterSpacing: 4,
          textTransform: "uppercase",
          fontFamily: "Inter, sans-serif",
        }}>
          Live Setup Evaluation · XAUUSD
        </div>

        {/* Main content — left column: setup + history, right: zones + decision */}
        <div style={{ display: "flex", gap: 48, alignItems: "flex-start", width: "100%" }}>

          {/* LEFT — Setup info + history */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>

            {/* Setup card */}
            <div style={{
              opacity: setupOp,
              transform: `scale(${setupScale})`,
              background: COLORS.bgCard,
              border: `1.5px solid ${COLORS.border}`,
              borderRadius: 16,
              padding: "20px 24px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 32, fontWeight: 900, color: COLORS.textPrimary, fontFamily: "Inter, sans-serif" }}>XAUUSD</div>
                  <div style={{ fontSize: 16, color: COLORS.green, fontWeight: 700, fontFamily: "Inter, sans-serif" }}>▲ LONG · London Session</div>
                </div>
                <div style={{
                  background: `${COLORS.blue}22`,
                  border: `1px solid ${COLORS.blue}`,
                  borderRadius: 8,
                  padding: "6px 14px",
                  fontSize: 13,
                  color: COLORS.blue,
                  fontFamily: "Inter, sans-serif",
                  fontWeight: 700,
                }}>
                  MSS · 0.82
                </div>
              </div>
            </div>

            {/* Historical sample counter */}
            <div style={{ opacity: histOp }}>
              <HistoricalSampleCounter
                targetN={187}
                startFrame={STEPS.histExpand}
                label="matched historical setups"
              />
            </div>
          </div>

          {/* RIGHT — Zone visual + MAE chart + Reason + Decision */}
          <div style={{ flex: 1.2, display: "flex", flexDirection: "column", gap: 20 }}>

            <div style={{ display: "flex", gap: 32, alignItems: "flex-start" }}>
              {/* Entry/Stop zone visual */}
              <EntryZoneVisual startFrame={STEPS.entryZone} p25={8} p75={22} p90={31} />

              {/* MAE chart */}
              <AdverseExcursionChart p25={8} p75={22} p90={31} startFrame={STEPS.maeChart} />
            </div>

            {/* Reason panel */}
            {frame >= STEPS.reason && (
              <ReasonPanel
                startFrame={STEPS.reason}
                accentColor={COLORS.green}
                lines={[
                  { label: "Structure",    value: "MSS confirmed above 1H resistance", color: COLORS.green },
                  { label: "Macro",        value: "DXY weak · RISK_ON regime",         color: COLORS.blue },
                  { label: "History",      value: "74% continuation in 187 matches" },
                  { label: "Adverse move", value: "Typical dip: 8–22 pips (P25–P75)" },
                  { label: "Stop basis",   value: "Below P90 at 31 pips — historical noise boundary" },
                ]}
              />
            )}

            {/* Decision card */}
            {frame >= STEPS.decision && (
              <div style={{ display: "flex", justifyContent: "center", marginTop: 8 }}>
                <DecisionCard
                  state="TAKE IT"
                  resolveAtFrame={STEPS.decision + 20}
                  instrument="XAUUSD"
                  direction="LONG"
                  size="lg"
                />
              </div>
            )}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
