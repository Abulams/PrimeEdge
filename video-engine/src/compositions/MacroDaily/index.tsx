// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · MacroDaily Composition
// Duration: 8 s (240 frames @ 30fps) · 1080×1920
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
  interpolate,
  delayRender,
  continueRender,
} from "remotion";
import { COLORS, regimeColor, statusColor, directionColor } from "../../utils/colors";
import { FONT_FAMILY, FONT_MONO, loadGoogleFonts } from "../../utils/fonts";

// ── Types ───────────────────────────────────────────────────
export interface MacroDailyInstrument {
  symbol: string;
  status: string;
  direction: string;
  mss_score: number;
}

export interface MacroDailyData {
  date_label: string;
  dxy_level: number;
  dxy_change_pct: number;
  vix_level: number;
  vix_change_pct: number;
  risk_sentiment: string;
  macro_headline: string;
  key_instruments: MacroDailyInstrument[];
  session_open: string;
}

export const defaultMacroDailyProps: MacroDailyData = {
  date_label: "Mon 28 Oct 2026",
  dxy_level: 104.32,
  dxy_change_pct: -0.34,
  vix_level: 18.4,
  vix_change_pct: -1.2,
  risk_sentiment: "RISK_ON",
  macro_headline:
    "DXY weakness extends as NFP miss weighs on USD. Gold and risk assets bid into London open.",
  key_instruments: [
    { symbol: "XAUUSD", status: "READY", direction: "LONG", mss_score: 0.82 },
    { symbol: "GBPUSD", status: "WAIT", direction: "LONG", mss_score: 0.61 },
    { symbol: "USDJPY", status: "READY", direction: "SHORT", mss_score: 0.74 },
  ],
  session_open: "London",
};

// ── Sub-components ──────────────────────────────────────────

const ChangeTag: React.FC<{ value: number; suffix?: string }> = ({ value, suffix = "%" }) => {
  const isPos = value >= 0;
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize: 22,
        fontWeight: 600,
        color: isPos ? COLORS.green : COLORS.red,
        background: isPos ? `${COLORS.green}22` : `${COLORS.red}22`,
        borderRadius: 8,
        padding: "3px 12px",
        marginLeft: 12,
      }}
    >
      {isPos ? "+" : ""}
      {value.toFixed(2)}
      {suffix}
    </span>
  );
};

const InstrumentRow: React.FC<{
  inst: MacroDailyInstrument;
  frame: number;
  fps: number;
  delay: number;
}> = ({ inst, frame, fps, delay }) => {
  const rowSpring = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 70, stiffness: 60 },
    durationInFrames: 30,
  });
  const statColor = statusColor(inst.status);
  const dirColor =
    inst.direction === "FLAT" ? COLORS.textMuted : directionColor(inst.direction);
  const dirArrow =
    inst.direction === "LONG" ? "▲" : inst.direction === "SHORT" ? "▼" : "—";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 20,
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderLeft: `4px solid ${statColor}`,
        borderRadius: 16,
        padding: "24px 28px",
        opacity: rowSpring,
        transform: `translateX(${interpolate(rowSpring, [0, 1], [-60, 0])}px)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 30,
          fontWeight: 800,
          color: COLORS.textPrimary,
          flex: 1,
        }}
      >
        {inst.symbol}
      </div>
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 22,
          fontWeight: 700,
          color: dirColor,
          display: "flex",
          alignItems: "center",
          gap: 6,
          minWidth: 110,
        }}
      >
        <span style={{ fontSize: 20 }}>{dirArrow}</span>
        {inst.direction}
      </div>
      <div
        style={{
          background: `${statColor}22`,
          border: `1px solid ${statColor}88`,
          borderRadius: 20,
          padding: "6px 18px",
          fontFamily: FONT_FAMILY,
          fontSize: 18,
          fontWeight: 700,
          color: statColor,
          letterSpacing: "0.06em",
          minWidth: 100,
          textAlign: "center",
        }}
      >
        {inst.status}
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, minWidth: 80 }}>
        <span style={{ fontFamily: FONT_MONO, fontSize: 18, color: COLORS.textSecondary }}>
          {inst.mss_score.toFixed(2)}
        </span>
        <div
          style={{
            width: 80,
            height: 5,
            background: COLORS.bgAccent,
            borderRadius: 3,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${
                spring({
                  frame: Math.max(0, frame - delay - 10),
                  fps,
                  config: { damping: 60, stiffness: 40 },
                  durationInFrames: 40,
                }) *
                inst.mss_score *
                100
              }%`,
              background: statColor,
              borderRadius: 3,
            }}
          />
        </div>
      </div>
    </div>
  );
};

// ── Main Composition ────────────────────────────────────────
export const MacroDaily: React.FC<MacroDailyData> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);

  const regColor = regimeColor(props.risk_sentiment);

  const globalOpacity = interpolate(frame, [0, 20, 210, 240], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const headerSpring = spring({ frame, fps, config: { damping: 80, stiffness: 70 }, durationInFrames: 30 });
  const sentimentSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: { damping: 60, stiffness: 50, mass: 1.2 },
    durationInFrames: 40,
  });
  const metricsSpring = spring({
    frame: Math.max(0, frame - 25),
    fps,
    config: { damping: 70, stiffness: 55 },
    durationInFrames: 40,
  });
  const headlineOpacity = interpolate(frame, [40, 65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        fontFamily: FONT_FAMILY,
        background: COLORS.bg,
        overflow: "hidden",
        opacity: globalOpacity,
      }}
    >
      {/* Regime background wash */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 640,
          background: `radial-gradient(ellipse at 50% 0%, ${regColor}18 0%, transparent 70%)`,
          pointerEvents: "none",
        }}
      />

      {/* Grid */}
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              top: `${(i / 20) * 100}%`,
              left: 0,
              right: 0,
              height: 1,
              background: COLORS.gridLine,
            }}
          />
        ))}
      </AbsoluteFill>

      {/* ── HEADER ─────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 160,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 48px",
          background: `linear-gradient(180deg, ${COLORS.bgCard}EE, transparent)`,
          borderBottom: `1px solid ${COLORS.border}`,
          opacity: headerSpring,
          transform: `translateY(${interpolate(headerSpring, [0, 1], [-30, 0])}px)`,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: COLORS.gold,
              letterSpacing: "0.18em",
            }}
          >
            PRIMEEDGE
          </div>
          <div
            style={{
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.1em",
              marginTop: 2,
            }}
          >
            MACRO DAILY
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              fontFamily: FONT_MONO,
              fontSize: 22,
              fontWeight: 700,
              color: COLORS.textPrimary,
            }}
          >
            {props.date_label}
          </div>
          <div style={{ fontSize: 18, color: COLORS.textMuted, marginTop: 4 }}>
            {props.session_open} Open
          </div>
        </div>
      </div>

      {/* ── RISK SENTIMENT HERO ──────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 180,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
          padding: "0 48px",
          opacity: sentimentSpring,
          transform: `scale(${interpolate(sentimentSpring, [0, 1], [0.85, 1])})`,
        }}
      >
        <div
          style={{
            fontSize: 18,
            color: COLORS.textMuted,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
          }}
        >
          Risk Sentiment
        </div>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 88,
            fontWeight: 900,
            color: regColor,
            letterSpacing: "0.04em",
            textShadow: `0 0 40px ${regColor}88`,
            lineHeight: 1,
            textAlign: "center",
          }}
        >
          {props.risk_sentiment.replace(/_/g, " ")}
        </div>
      </div>

      {/* ── DXY + VIX METRICS ───────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 440,
          left: 48,
          right: 48,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
          opacity: metricsSpring,
          transform: `translateY(${interpolate(metricsSpring, [0, 1], [30, 0])}px)`,
        }}
      >
        {[
          {
            label: "DXY Index",
            value: props.dxy_level.toFixed(2),
            change: props.dxy_change_pct,
            icon: "💵",
            description: "US Dollar Index",
          },
          {
            label: "VIX",
            value: props.vix_level.toFixed(1),
            change: props.vix_change_pct,
            icon: "⚡",
            description: "Volatility Index",
          },
        ].map((metric) => (
          <div
            key={metric.label}
            style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 20,
              padding: "28px 24px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 12,
              }}
            >
              <span style={{ fontSize: 28 }}>{metric.icon}</span>
              <div>
                <div
                  style={{
                    fontSize: 14,
                    color: COLORS.textMuted,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  {metric.label}
                </div>
                <div style={{ fontSize: 12, color: COLORS.textMuted }}>
                  {metric.description}
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
              <span
                style={{
                  fontFamily: FONT_MONO,
                  fontSize: 48,
                  fontWeight: 900,
                  color: COLORS.textPrimary,
                }}
              >
                {metric.value}
              </span>
              <ChangeTag value={metric.change} />
            </div>
          </div>
        ))}
      </div>

      {/* ── MACRO HEADLINE ──────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 700,
          left: 48,
          right: 48,
          opacity: headlineOpacity,
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, ${COLORS.bgCard}CC, ${COLORS.bgAccent}88)`,
            border: `1px solid ${COLORS.border}`,
            borderLeft: `3px solid ${regColor}`,
            borderRadius: 16,
            padding: "28px 32px",
          }}
        >
          <div
            style={{
              fontSize: 14,
              fontWeight: 700,
              color: regColor,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              marginBottom: 12,
            }}
          >
            Macro Context
          </div>
          <div
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 26,
              fontStyle: "italic",
              color: COLORS.textPrimary,
              lineHeight: 1.5,
            }}
          >
            {props.macro_headline}
          </div>
        </div>
      </div>

      {/* ── INSTRUMENT WATCHLIST ────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 940,
          left: 48,
          right: 48,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        <div
          style={{
            fontSize: 16,
            fontWeight: 700,
            color: COLORS.textMuted,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            opacity: headlineOpacity,
          }}
        >
          Key Instruments
        </div>
        {props.key_instruments.map((inst, i) => (
          <InstrumentRow
            key={inst.symbol}
            inst={inst}
            frame={frame}
            fps={fps}
            delay={60 + i * 15}
          />
        ))}
      </div>

      {/* ── BOTTOM BAR ─────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 90,
          background: `linear-gradient(0deg, ${COLORS.bgCard}FF, transparent)`,
          borderTop: `1px solid ${COLORS.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: interpolate(frame, [80, 110], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <span
          style={{
            fontSize: 20,
            fontWeight: 500,
            color: COLORS.textMuted,
            letterSpacing: "0.14em",
          }}
        >
          PrimeEdge · Quantitative FX · primeedge.app
        </span>
      </div>
    </AbsoluteFill>
  );
};
