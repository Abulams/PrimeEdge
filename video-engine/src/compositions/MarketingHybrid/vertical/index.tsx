// ─────────────────────────────────────────────────────────────
// PrimeEdge Hybrid Film — Vertical Social Cut (9:16)
// 1080×1920 · 30fps · 918 frames (~30.6s)
// Stacked mobile composition for Reels / TikTok / Shorts
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  delayRender,
  continueRender,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS } from "../../../utils/colors";
import { loadGoogleFonts } from "../../../utils/fonts";
import { HYBRID_SCENES, HYBRID_TOTAL_FRAMES } from "../timing";
import { HistoricalSampleCounter } from "../../MarketingV2/components/HistoricalSampleCounter";
import { AdverseExcursionChart } from "../../MarketingV2/components/AdverseExcursionChart";
import { ReasonPanel } from "../../MarketingV2/components/ReasonPanel";
import { DecisionCard } from "../../MarketingV2/components/DecisionCard";
import { JournalEntry } from "../../MarketingV2/components/JournalEntry";

export type MarketingHybridVerticalData = Record<string, never>;
export const defaultMarketingHybridVerticalProps: MarketingHybridVerticalData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

// ── Vertical Scene 1: Human Pain (0–90f) ─────────────────────────
const V_Pain: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = interpolate(frame, [0, 90], [1.0, 1.08], { extrapolateRight: "clamp" });
  const showLoss = frame >= 45;
  const cutOp = interpolate(frame, [45, 48], [0, 1], { extrapolateRight: "clamp" });
  const redPulse = 0.25 + 0.15 * Math.sin(frame * 0.18);
  const textScale = spring({ frame: frame - 10, fps, config: { damping: 16, stiffness: 140 } });
  const textOp = interpolate(frame, [10, 22], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: "#05070c", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "center 60%" }}>
        <Img src={staticFile("footage/trader_hesitation.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      {showLoss && (
        <AbsoluteFill style={{ opacity: cutOp, transform: `scale(${scale})`, transformOrigin: "center" }}>
          <Img src={staticFile("footage/trader_loss_phone.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 60%, rgba(255, 59, 92, ${redPulse}) 0%, transparent 65%)`, pointerEvents: "none" }} />
      <AbsoluteFill style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", paddingBottom: 180, opacity: textOp, zIndex: 4, paddingLeft: 40, paddingRight: 40 }}>
        <div style={{ transform: `scale(${textScale})`, background: "rgba(10, 14, 26, 0.9)", backdropFilter: "blur(12px)", border: `2px solid rgba(255, 59, 92, 0.45)`, borderRadius: 24, padding: "28px 40px", textAlign: "center", width: "100%" }}>
          <div style={{ fontSize: 44, fontWeight: 900, color: "#FFFFFF", fontFamily: "Inter, sans-serif", letterSpacing: 2, lineHeight: 1.25 }}>
            RIGHT DIRECTION.<br />
            <span style={{ color: COLORS.red, textShadow: `0 0 25px ${COLORS.red}88` }}>WRONG ENTRY.</span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Vertical Scene 2: Product Action (90–210f) ──────────────────
const V_Action: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 40], [1.3, 1.8], { extrapolateRight: "clamp" });
  const panY = interpolate(frame, [0, 60], [0, 120], { extrapolateRight: "clamp" });
  const cursorX = interpolate(frame, [15, 60], [600, 480], { extrapolateRight: "clamp" });
  const cursorY = interpolate(frame, [15, 60], [1100, 850], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${zoom}) translateY(${panY}px)`, transformOrigin: "center center" }}>
        <Img src={staticFile("footage/product_cockpit.png")} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left: cursorX, top: cursorY, zIndex: 10 }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
          <path d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87c.45 0 .67-.54.35-.85L6.35 2.85a.5.5 0 0 0-.85.36z" fill="#FFFFFF" stroke="#000000" strokeWidth="1.5" />
        </svg>
      </div>
      <AbsoluteFill style={{ display: "flex", justifyContent: "flex-start", padding: "100px 50px", zIndex: 5 }}>
        <div style={{ background: "rgba(10, 14, 26, 0.92)", border: `2px solid ${COLORS.blue}`, borderRadius: 16, padding: "18px 32px", display: "inline-flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: COLORS.blue }} />
          <span style={{ fontSize: 20, fontWeight: 800, color: "#FFFFFF", letterSpacing: 2 }}>DECISION FILTER ACTIVE</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Vertical Scene 3: Remotion Explain (210–540f) ───────────────
const V_Explain: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: COLORS.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-between", padding: "100px 50px 80px" }}>
      <div style={{ width: "100%", textAlign: "center" }}>
        <div style={{ fontSize: 16, color: COLORS.textMuted, letterSpacing: 4, textTransform: "uppercase", marginBottom: 16 }}>Quantitative Analysis</div>
        <div style={{ background: COLORS.bgCard, border: `1.5px solid ${COLORS.border}`, borderRadius: 20, padding: "24px 32px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 44, fontWeight: 900, color: COLORS.textPrimary }}>XAUUSD</div>
            <div style={{ fontSize: 20, color: COLORS.green, fontWeight: 700, marginTop: 4 }}>▲ LONG · London</div>
          </div>
          <div style={{ background: `${COLORS.blue}22`, border: `1.5px solid ${COLORS.blue}`, borderRadius: 12, padding: "10px 20px", fontSize: 18, color: COLORS.blue, fontWeight: 800 }}>MSS · 0.82</div>
        </div>
      </div>
      <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 24, alignItems: "center" }}>
        <HistoricalSampleCounter targetN={187} startFrame={15} label="matched historical setups" />
        <AdverseExcursionChart p25={8} p75={22} p90={31} startFrame={75} maxPips={40} />
      </div>
      <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
        {frame >= 200 && (
          <div style={{ width: "100%" }}>
            <ReasonPanel startFrame={200} accentColor={COLORS.amber} lines={[
              { label: "Adverse Move", value: "8–22 pips across 187 matches" },
              { label: "Valid Entry", value: "2318.50 – 2321.00 corridor" },
              { label: "Execution Rule", value: "WAIT for preferred pullback", color: COLORS.amber },
            ]} />
          </div>
        )}
        {frame >= 240 && (
          <DecisionCard state="WAIT" resolveAtFrame={260} instrument="XAUUSD" direction="LONG" size="lg" />
        )}
      </div>
    </AbsoluteFill>
  );
};

// ── Vertical Scene 4: Human Restraint (540–690f) ─────────────────
const V_Restraint: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 150], [1.06, 1.0], { extrapolateRight: "clamp" });
  const glow = 0.2 + 0.08 * Math.sin(frame * 0.12);
  return (
    <AbsoluteFill style={{ background: "#05070c", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "center 50%" }}>
        <Img src={staticFile("footage/trader_restraint.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, rgba(0, 200, 150, ${glow}) 0%, transparent 65%)`, pointerEvents: "none" }} />
      <AbsoluteFill style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", paddingBottom: 180, paddingLeft: 40, paddingRight: 40 }}>
        <div style={{ background: "rgba(10, 14, 26, 0.9)", border: `2px solid ${COLORS.green}66`, borderRadius: 24, padding: "28px 40px", textAlign: "center", width: "100%", boxShadow: `0 0 35px ${COLORS.green}33` }}>
          <div style={{ fontSize: 44, fontWeight: 900, color: "#FFFFFF", letterSpacing: 2, lineHeight: 1.25 }}>
            NO CHASE.<br />
            <span style={{ color: COLORS.green, textShadow: `0 0 25px ${COLORS.green}88` }}>NO GUESSING.</span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ── Main Export ──────────────────────────────────────────────────
export const MarketingHybridVertical: React.FC<MarketingHybridVerticalData> = () => {
  useFonts();
  const sc = HYBRID_SCENES;

  return (
    <AbsoluteFill style={{ background: COLORS.bg, fontFamily: "Inter, SF Pro Display, sans-serif" }}>
      <Audio src={staticFile("audio/bed.wav")} volume={(f) => (f < 30 ? (f / 30) * 0.16 : f > HYBRID_TOTAL_FRAMES - 30 ? ((HYBRID_TOTAL_FRAMES - f) / 30) * 0.16 : 0.16)} />
      <Sequence from={sc.humanPain.from} durationInFrames={sc.humanPain.frames}>
        <Audio src={staticFile("audio/hybrid_hook.mp3")} />
        <V_Pain />
      </Sequence>
      <Sequence from={sc.productAction.from} durationInFrames={sc.productAction.frames}>
        <Audio src={staticFile("audio/hybrid_check.mp3")} />
        <V_Action />
      </Sequence>
      <Sequence from={sc.remotionExplain.from} durationInFrames={sc.remotionExplain.frames}>
        <Audio src={staticFile("audio/hybrid_explain.mp3")} />
        <V_Explain />
      </Sequence>
      <Sequence from={sc.humanRestraint.from} durationInFrames={sc.humanRestraint.frames}>
        <Audio src={staticFile("audio/hybrid_restraint.mp3")} />
        <V_Restraint />
      </Sequence>
      <Sequence from={sc.productJournal.from} durationInFrames={sc.productJournal.frames}>
        <Audio src={staticFile("audio/hybrid_journal.mp3")} />
        <AbsoluteFill style={{ padding: "100px 40px", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <JournalEntry instrument="XAUUSD" direction="LONG" entryZone="2318.50 – 2321.00" stopLevel="2315.00 (P90 Invalidation)" thesis="187 matched trades. Adverse dip: 8–22 pips. Execution rule: WAIT for corridor." timestamp="2026-11-01  08:14:00 UTC" startFrame={15} />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={sc.brandCta.from} durationInFrames={sc.brandCta.frames}>
        <Audio src={staticFile("audio/hybrid_cta.mp3")} />
        <AbsoluteFill style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "0 50px", textAlign: "center" }}>
          <div style={{ fontSize: 64, fontWeight: 900, color: COLORS.textPrimary, marginBottom: 16 }}>PrimeEdge</div>
          <div style={{ fontSize: 24, color: COLORS.textSecondary, marginBottom: 50 }}>Trade with evidence. Execute with discipline.</div>
          <div style={{ background: COLORS.green, borderRadius: 60, padding: "24px 56px", fontSize: 26, fontWeight: 800, color: COLORS.bg, boxShadow: `0 0 40px ${COLORS.green}66`, marginBottom: 36 }}>Run a historical replay →</div>
          <div style={{ fontSize: 22, color: COLORS.textSecondary, fontFamily: "monospace", marginBottom: 40 }}>primeedge.app</div>
          <div style={{ fontSize: 14, color: COLORS.textMuted, lineHeight: 1.5 }}>Decision support system. Stops are statistical boundaries informed by historical distributions.</div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
