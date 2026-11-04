// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · SignalCard Composition
// Duration: 5 s (150 frames @ 30fps) · 1080×1920
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
import {
  COLORS,
  statusColor,
  directionColor,
  regimeColor,
  statusGlow,
  evidenceColor,
} from "../../utils/colors";
import { FONT_FAMILY, FONT_MONO, loadGoogleFonts } from "../../utils/fonts";

// ── Types ───────────────────────────────────────────────────
export interface SignalCardData {
  instrument: string;
  direction: string;
  status_state: string;
  why_this_now: string;
  evidence_strength: string;
  mss_score: number;
  current_regime: string;
  continuation_probability: number;
  best_session: string;
  historical_sample_size: number;
  acceptable_corridor?: {
    p25_price: number;
    p75_price: number;
    p90_invalidation: number;
  };
  preferred_zone?: {
    low: number;
    high: number;
  };
  mae_data?: {
    p25_pips: number;
    p50_pips: number;
    p75_pips: number;
    p90_pips: number;
  };
  trade_thesis?: string;
}

export const defaultSignalCardProps: SignalCardData = {
  instrument: "XAUUSD",
  direction: "LONG",
  status_state: "READY",
  why_this_now:
    "DXY broke below 104.20 structure with volume confirmation. Gold reclaiming 2340 demand zone with MSS printed on H1.",
  evidence_strength: "Strong",
  mss_score: 0.82,
  current_regime: "RISK_ON | DXY_WEAK",
  continuation_probability: 0.74,
  best_session: "London",
  historical_sample_size: 187,
  acceptable_corridor: {
    p25_price: 2338.5,
    p75_price: 2344.0,
    p90_invalidation: 2329.8,
  },
  preferred_zone: { low: 2338.5, high: 2344.0 },
  mae_data: {
    p25_pips: 12,
    p50_pips: 24,
    p75_pips: 38,
    p90_pips: 57,
  },
  trade_thesis: "Structural demand + macro tailwind = asymmetric long opportunity.",
};

// ── Sub-components ──────────────────────────────────────────

/** Animated noise / grid background */
const GridBackground: React.FC = () => (
  <AbsoluteFill style={{ background: COLORS.bg }}>
    {/* Horizontal grid lines */}
    {Array.from({ length: 30 }).map((_, i) => (
      <div
        key={`h${i}`}
        style={{
          position: "absolute",
          top: `${(i / 30) * 100}%`,
          left: 0,
          right: 0,
          height: 1,
          background: COLORS.gridLine,
        }}
      />
    ))}
    {/* Vertical grid lines */}
    {Array.from({ length: 16 }).map((_, i) => (
      <div
        key={`v${i}`}
        style={{
          position: "absolute",
          left: `${(i / 16) * 100}%`,
          top: 0,
          bottom: 0,
          width: 1,
          background: COLORS.gridLine,
        }}
      />
    ))}
    {/* Bottom radial glow */}
    <div
      style={{
        position: "absolute",
        bottom: -200,
        left: "50%",
        transform: "translateX(-50%)",
        width: 900,
        height: 600,
        borderRadius: "50%",
        background:
          "radial-gradient(ellipse at center, rgba(0,200,150,0.08) 0%, transparent 70%)",
        pointerEvents: "none",
      }}
    />
  </AbsoluteFill>
);

/** Animated number counter using spring */
const AnimatedNumber: React.FC<{
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  frame: number;
  startFrame?: number;
  fps: number;
  fontSize?: number;
  color?: string;
}> = ({
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  frame,
  startFrame = 0,
  fps,
  fontSize = 56,
  color = COLORS.textPrimary,
}) => {
  const progress = spring({
    frame: Math.max(0, frame - startFrame),
    fps,
    config: { damping: 80, stiffness: 60, mass: 1 },
    durationInFrames: 60,
  });
  const displayed = progress * value;
  return (
    <span
      style={{
        fontFamily: FONT_MONO,
        fontSize,
        fontWeight: 700,
        color,
        letterSpacing: "-0.02em",
      }}
    >
      {prefix}
      {displayed.toFixed(decimals)}
      {suffix}
    </span>
  );
};

/** Corridor / price zone visualizer */
const CorridorVisualizer: React.FC<{
  corridor?: SignalCardData["acceptable_corridor"];
  maeData?: SignalCardData["mae_data"];
  frame: number;
  fps: number;
}> = ({ corridor, maeData, frame, fps }) => {
  if (!corridor) return null;

  const barProgress = spring({
    frame: Math.max(0, frame - 10),
    fps,
    config: { damping: 60, stiffness: 40, mass: 1.2 },
    durationInFrames: 50,
  });

  const dotProgress = spring({
    frame: Math.max(0, frame - 30),
    fps,
    config: { damping: 50, stiffness: 35, mass: 1 },
    durationInFrames: 60,
  });

  const TOTAL_H = 420;
  const priceRange = corridor.p25_price - corridor.p90_invalidation;
  const pctP25 = 0; // top of green zone (entry low)
  const pctP75 =
    ((corridor.p75_price - corridor.p25_price) / priceRange) * TOTAL_H;
  const pctP90 = TOTAL_H; // bottom = invalidation

  const currentDotY = interpolate(dotProgress, [0, 1], [0, pctP75 * 0.5]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "stretch",
        gap: 32,
        padding: "0 60px",
        height: TOTAL_H,
      }}
    >
      {/* Left price labels */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          alignItems: "flex-end",
          fontFamily: FONT_MONO,
          fontSize: 24,
          color: COLORS.textSecondary,
          paddingTop: 0,
          paddingBottom: 0,
        }}
      >
        <span style={{ color: COLORS.green }}>P75 · {corridor.p75_price.toFixed(1)}</span>
        <span style={{ color: COLORS.green }}>P25 · {corridor.p25_price.toFixed(1)}</span>
        <span style={{ color: COLORS.red }}>P90 · {corridor.p90_invalidation.toFixed(1)}</span>
      </div>

      {/* The vertical bar */}
      <div
        style={{
          position: "relative",
          width: 80,
          height: TOTAL_H,
          background: COLORS.bgAccent,
          borderRadius: 12,
          overflow: "visible",
        }}
      >
        {/* Entry zone (P25 → P75) — green fill */}
        <div
          style={{
            position: "absolute",
            bottom:
              ((corridor.p25_price - corridor.p90_invalidation) / priceRange) *
              TOTAL_H,
            left: 0,
            right: 0,
            height:
              ((corridor.p75_price - corridor.p25_price) / priceRange) *
              TOTAL_H *
              barProgress,
            background: `linear-gradient(180deg, ${COLORS.green}88 0%, ${COLORS.green}33 100%)`,
            borderRadius: 8,
            boxShadow: `0 0 20px ${COLORS.green}44`,
            transformOrigin: "bottom",
          }}
        />
        {/* P90 invalidation dashed line */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: -12,
            right: -12,
            height: 2,
            background: `repeating-linear-gradient(90deg, ${COLORS.red} 0, ${COLORS.red} 8px, transparent 8px, transparent 16px)`,
          }}
        />
        {/* Animated current price dot */}
        <div
          style={{
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
            bottom:
              ((corridor.p25_price - corridor.p90_invalidation) / priceRange) *
                TOTAL_H +
              currentDotY,
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: COLORS.gold,
            boxShadow: `0 0 16px ${COLORS.gold}CC`,
            border: `3px solid ${COLORS.bg}`,
          }}
        />
      </div>

      {/* Right MAE pip labels */}
      {maeData && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-around",
            fontFamily: FONT_MONO,
            fontSize: 22,
            color: COLORS.textSecondary,
          }}
        >
          <div>
            <span style={{ color: COLORS.textMuted, fontSize: 18 }}>MAE P90</span>
            <br />
            <span style={{ color: COLORS.red }}>{maeData.p90_pips} pips</span>
          </div>
          <div>
            <span style={{ color: COLORS.textMuted, fontSize: 18 }}>MAE P75</span>
            <br />
            <span style={{ color: COLORS.amber }}>{maeData.p75_pips} pips</span>
          </div>
          <div>
            <span style={{ color: COLORS.textMuted, fontSize: 18 }}>MAE P50</span>
            <br />
            <span style={{ color: COLORS.textSecondary }}>{maeData.p50_pips} pips</span>
          </div>
          <div>
            <span style={{ color: COLORS.textMuted, fontSize: 18 }}>MAE P25</span>
            <br />
            <span style={{ color: COLORS.green }}>{maeData.p25_pips} pips</span>
          </div>
        </div>
      )}
    </div>
  );
};

/** Pulsing status indicator ring */
const StatusRing: React.FC<{ status: string; frame: number; fps: number }> = ({
  status,
  frame,
  fps,
}) => {
  const color = statusColor(status);
  const isReady = status.toUpperCase() === "READY";
  // Pulse: 0→1→0 cycle every 60 frames
  const pulse = isReady
    ? Math.sin((frame / fps) * Math.PI * 2) * 0.5 + 0.5
    : 0;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        background: `${color}22`,
        border: `2px solid ${color}`,
        borderRadius: 40,
        padding: "10px 28px",
        boxShadow: isReady
          ? `0 0 ${16 + pulse * 24}px ${color}${Math.round(pulse * 200 + 55)
              .toString(16)
              .padStart(2, "0")}`
          : "none",
      }}
    >
      <div
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: color,
          boxShadow: isReady ? `0 0 ${8 + pulse * 12}px ${color}` : "none",
        }}
      />
      <span
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 26,
          fontWeight: 700,
          color,
          letterSpacing: "0.12em",
        }}
      >
        {status}
      </span>
    </div>
  );
};

// ── Main Composition ────────────────────────────────────────
export const SignalCard: React.FC<SignalCardData> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Font loading
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);

  // Global entrance spring
  const headerSpring = spring({
    frame,
    fps,
    config: { damping: 80, stiffness: 80, mass: 0.8 },
    durationInFrames: 30,
  });

  const contentSpring = spring({
    frame: Math.max(0, frame - 10),
    fps,
    config: { damping: 70, stiffness: 60, mass: 1 },
    durationInFrames: 40,
  });

  // Why this now fades in at 2s (60 frames)
  const whyOpacity = interpolate(frame, [55, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const dirColor = directionColor(props.direction);
  const regColor = regimeColor(props.current_regime);
  const evColor = evidenceColor(props.evidence_strength);

  const sessionIcon: Record<string, string> = {
    London: "🇬🇧",
    "New York": "🗽",
    Asian: "🏮",
  };

  return (
    <AbsoluteFill style={{ fontFamily: FONT_FAMILY, overflow: "hidden" }}>
      <GridBackground />

      {/* ── HEADER BAR ─────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 180,
          background: `linear-gradient(180deg, ${COLORS.bgCard}EE 0%, ${COLORS.bgCard}00 100%)`,
          borderBottom: `1px solid ${COLORS.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 48px",
          transform: `translateY(${interpolate(headerSpring, [0, 1], [-40, 0])}px)`,
          opacity: headerSpring,
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: COLORS.gold,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
            }}
          >
            PrimeEdge
          </span>
          <span
            style={{
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.08em",
            }}
          >
            SIGNAL CARD
          </span>
        </div>

        {/* Regime badge */}
        <div
          style={{
            background: `${regColor}22`,
            border: `1.5px solid ${regColor}88`,
            borderRadius: 30,
            padding: "8px 20px",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: regColor,
            }}
          />
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: 18,
              fontWeight: 600,
              color: regColor,
              letterSpacing: "0.06em",
            }}
          >
            {props.current_regime}
          </span>
        </div>
      </div>

      {/* ── INSTRUMENT + DIRECTION ──────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 190,
          left: 0,
          right: 0,
          padding: "0 48px",
          opacity: contentSpring,
          transform: `translateY(${interpolate(contentSpring, [0, 1], [20, 0])}px)`,
        }}
      >
        {/* Instrument name */}
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 96,
            fontWeight: 900,
            color: COLORS.textPrimary,
            letterSpacing: "-0.03em",
            lineHeight: 1,
          }}
        >
          {props.instrument}
        </div>

        {/* Direction + Status row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 24,
            marginTop: 20,
          }}
        >
          {/* Direction badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              background: `${dirColor}22`,
              border: `2px solid ${dirColor}`,
              borderRadius: 12,
              padding: "10px 28px",
            }}
          >
            <span style={{ fontSize: 32, color: dirColor }}>
              {props.direction === "LONG" ? "▲" : "▼"}
            </span>
            <span
              style={{
                fontFamily: FONT_FAMILY,
                fontSize: 32,
                fontWeight: 800,
                color: dirColor,
                letterSpacing: "0.1em",
              }}
            >
              {props.direction}
            </span>
          </div>

          {/* Status badge */}
          <StatusRing status={props.status_state} frame={frame} fps={fps} />
        </div>

        {/* Evidence strength */}
        <div style={{ marginTop: 16 }}>
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 20,
              fontWeight: 600,
              color: evColor,
              background: `${evColor}22`,
              border: `1px solid ${evColor}55`,
              borderRadius: 20,
              padding: "4px 16px",
              letterSpacing: "0.08em",
            }}
          >
            {props.evidence_strength.toUpperCase()} EVIDENCE
          </span>
        </div>
      </div>

      {/* ── DIVIDER ─────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 430,
          left: 48,
          right: 48,
          height: 1,
          background: `linear-gradient(90deg, transparent, ${COLORS.border}, transparent)`,
          opacity: contentSpring,
        }}
      />

      {/* ── CORRIDOR VISUALIZER ─────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 460,
          left: 0,
          right: 0,
          opacity: contentSpring,
        }}
      >
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 18,
            fontWeight: 600,
            color: COLORS.textMuted,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            paddingLeft: 60,
            marginBottom: 16,
          }}
        >
          Price Corridor
        </div>
        <CorridorVisualizer
          corridor={props.acceptable_corridor}
          maeData={props.mae_data}
          frame={frame}
          fps={fps}
        />
      </div>

      {/* ── STATS ROW ──────────────────────────────────────────
          MSS Score | Win Prob | Session | N=
      ───────────────────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 960,
          left: 0,
          right: 0,
          padding: "0 48px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr 1fr",
          gap: 16,
          opacity: contentSpring,
        }}
      >
        {/* MSS Score */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "24px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            MSS Score
          </span>
          <AnimatedNumber
            value={props.mss_score}
            decimals={2}
            frame={frame}
            fps={fps}
            fontSize={40}
            color={COLORS.green}
          />
          {/* Score bar */}
          <div
            style={{
              height: 4,
              background: COLORS.bgAccent,
              borderRadius: 2,
              overflow: "hidden",
              marginTop: 4,
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${spring({ frame: Math.max(0, frame - 20), fps, config: { damping: 60, stiffness: 40 }, durationInFrames: 50 }) * props.mss_score * 100}%`,
                background: `linear-gradient(90deg, ${COLORS.green}, ${COLORS.gold})`,
                borderRadius: 2,
              }}
            />
          </div>
        </div>

        {/* Win Probability */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "24px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            Win Prob
          </span>
          <AnimatedNumber
            value={props.continuation_probability * 100}
            decimals={0}
            suffix="%"
            frame={frame}
            fps={fps}
            fontSize={40}
            color={COLORS.blue}
          />
          <div
            style={{
              height: 4,
              background: COLORS.bgAccent,
              borderRadius: 2,
              overflow: "hidden",
              marginTop: 4,
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${spring({ frame: Math.max(0, frame - 20), fps, config: { damping: 60, stiffness: 40 }, durationInFrames: 50 }) * props.continuation_probability * 100}%`,
                background: `linear-gradient(90deg, ${COLORS.blue}, ${COLORS.green})`,
                borderRadius: 2,
              }}
            />
          </div>
        </div>

        {/* Best Session */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "24px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            Session
          </span>
          <span style={{ fontSize: 36 }}>
            {sessionIcon[props.best_session] ?? "🌐"}
          </span>
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 18,
              fontWeight: 700,
              color: COLORS.textPrimary,
            }}
          >
            {props.best_session}
          </span>
        </div>

        {/* Sample size */}
        <div
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: 16,
            padding: "24px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 14,
              color: COLORS.textMuted,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            Sample N
          </span>
          <AnimatedNumber
            value={props.historical_sample_size}
            decimals={0}
            prefix="N="
            frame={frame}
            fps={fps}
            fontSize={32}
            color={COLORS.textSecondary}
          />
          <span
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 13,
              color: COLORS.textMuted,
            }}
          >
            historical trades
          </span>
        </div>
      </div>

      {/* ── WHY THIS NOW ───────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          top: 1160,
          left: 48,
          right: 48,
          opacity: whyOpacity,
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, ${COLORS.bgCard}CC, ${COLORS.bgAccent}88)`,
            border: `1px solid ${COLORS.border}`,
            borderLeft: `3px solid ${COLORS.gold}`,
            borderRadius: 16,
            padding: "28px 32px",
          }}
        >
          <div
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 14,
              fontWeight: 700,
              color: COLORS.gold,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              marginBottom: 12,
            }}
          >
            Why This Now
          </div>
          <div
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 28,
              fontStyle: "italic",
              fontWeight: 400,
              color: COLORS.textPrimary,
              lineHeight: 1.5,
            }}
          >
            {props.why_this_now}
          </div>
          {props.trade_thesis && (
            <div
              style={{
                fontFamily: FONT_FAMILY,
                fontSize: 22,
                fontStyle: "italic",
                color: COLORS.textSecondary,
                marginTop: 12,
                lineHeight: 1.4,
              }}
            >
              {props.trade_thesis}
            </div>
          )}
        </div>
      </div>

      {/* ── BOTTOM BAR ─────────────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 90,
          background: `linear-gradient(0deg, ${COLORS.bgCard}FF 0%, transparent 100%)`,
          borderTop: `1px solid ${COLORS.border}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: interpolate(frame, [100, 130], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <span
          style={{
            fontFamily: FONT_FAMILY,
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
