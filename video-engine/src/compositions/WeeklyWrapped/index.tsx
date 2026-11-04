// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · WeeklyWrapped Composition
// Duration: 15 s (450 frames @ 30fps) · 1080×1920
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
import { COLORS, directionColor } from "../../utils/colors";
import { FONT_FAMILY, FONT_MONO, loadGoogleFonts } from "../../utils/fonts";

// ── Types ───────────────────────────────────────────────────
export interface WeeklyWrappedData {
  user_name: string;
  week_label: string;
  total_setups: number;
  setups_taken: number;
  win_rate: number;
  avg_r_multiple: number;
  total_pnl_pips: number;
  best_trade: { instrument: string; pnl_pips: number; direction: string };
  instruments_traded: string[];
  mae_discipline: number;
}

export const defaultWeeklyWrappedProps: WeeklyWrappedData = {
  user_name: "Alex",
  week_label: "Week 44 · Oct 2026",
  total_setups: 12,
  setups_taken: 7,
  win_rate: 0.71,
  avg_r_multiple: 2.4,
  total_pnl_pips: 347,
  best_trade: { instrument: "XAUUSD", pnl_pips: 148, direction: "LONG" },
  instruments_traded: ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY"],
  mae_discipline: 0.88,
};

// ── Helpers ─────────────────────────────────────────────────

const AnimatedCounter: React.FC<{
  to: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  frame: number;
  fps: number;
  startFrame: number;
  fontSize?: number;
  color?: string;
  fontFamily?: string;
}> = ({
  to,
  decimals = 0,
  prefix = "",
  suffix = "",
  frame,
  fps,
  startFrame,
  fontSize = 120,
  color = COLORS.textPrimary,
  fontFamily = FONT_MONO,
}) => {
  const p = spring({
    frame: Math.max(0, frame - startFrame),
    fps,
    config: { damping: 70, stiffness: 50, mass: 1 },
    durationInFrames: 55,
  });
  return (
    <span style={{ fontFamily, fontSize, fontWeight: 900, color, letterSpacing: "-0.03em" }}>
      {prefix}{(p * to).toFixed(decimals)}{suffix}
    </span>
  );
};

/** Particle burst for the best-trade scene */
const ParticleBurst: React.FC<{ frame: number; fps: number; startFrame: number }> = ({
  frame,
  fps,
  startFrame,
}) => {
  const elapsed = frame - startFrame;
  if (elapsed < 0) return null;
  const particles = Array.from({ length: 24 });
  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {particles.map((_, i) => {
        const angle = (i / particles.length) * Math.PI * 2;
        const speed = 3 + (i % 4) * 1.5;
        const p = spring({
          frame: Math.max(0, elapsed),
          fps,
          config: { damping: 40, stiffness: 30, mass: 0.5 },
          durationInFrames: 45,
        });
        const dist = p * speed * 80;
        const opacity = interpolate(elapsed, [0, 30, 70], [1, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const colors = [COLORS.gold, COLORS.green, COLORS.blue, COLORS.amber];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: "50%",
              top: "50%",
              width: 10 + (i % 3) * 6,
              height: 10 + (i % 3) * 6,
              borderRadius: "50%",
              background: colors[i % colors.length],
              opacity,
              transform: `translate(calc(-50% + ${Math.cos(angle) * dist}px), calc(-50% + ${Math.sin(angle) * dist}px))`,
              boxShadow: `0 0 8px ${colors[i % colors.length]}`,
            }}
          />
        );
      })}
    </div>
  );
};

// ── Scenes ──────────────────────────────────────────────────

/** Frames 0-60: Intro */
const SceneIntro: React.FC<{ data: WeeklyWrappedData; frame: number; fps: number }> = ({
  data,
  frame,
  fps,
}) => {
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const titleY = spring({ frame, fps, config: { damping: 70, stiffness: 60 }, durationInFrames: 40 });
  const subtitleSpring = spring({ frame: Math.max(0, frame - 15), fps, config: { damping: 70, stiffness: 60 }, durationInFrames: 40 });

  // Particles floating up
  const particles = Array.from({ length: 40 });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 60%, ${COLORS.bgAccent} 0%, ${COLORS.bg} 70%)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 0,
      }}
    >
      {/* Floating particles */}
      {particles.map((_, i) => {
        const startY = 1920 - (i * 53 % 1000);
        const speed = 0.8 + (i % 5) * 0.3;
        const x = (i * 79 % 900) + 90;
        const pY = interpolate(frame, [0, 60], [0, -speed * 120], { extrapolateRight: "clamp" });
        const pOpacity = interpolate(frame, [0, 10, 50, 60], [0, 0.6, 0.6, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: startY + pY,
              width: 3 + (i % 4),
              height: 3 + (i % 4),
              borderRadius: "50%",
              background: [COLORS.gold, COLORS.green, COLORS.blue, COLORS.amber, COLORS.textMuted][i % 5],
              opacity: pOpacity,
            }}
          />
        );
      })}

      {/* Week label */}
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 26,
          fontWeight: 600,
          color: COLORS.textMuted,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          opacity: subtitleSpring,
          marginBottom: 24,
        }}
      >
        {data.week_label}
      </div>

      {/* Main headline */}
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 80,
          fontWeight: 900,
          color: COLORS.textPrimary,
          textAlign: "center",
          lineHeight: 1.1,
          transform: `translateY(${interpolate(titleY, [0, 1], [60, 0])}px)`,
          opacity: titleY,
          padding: "0 60px",
        }}
      >
        Your Week in
        <br />
        <span style={{ color: COLORS.gold }}>Trading</span>
      </div>

      {/* User name */}
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 40,
          fontWeight: 400,
          color: COLORS.textSecondary,
          marginTop: 32,
          opacity: subtitleSpring,
          transform: `translateY(${interpolate(subtitleSpring, [0, 1], [20, 0])}px)`,
        }}
      >
        Hey, <span style={{ color: COLORS.gold, fontWeight: 700 }}>{data.user_name}</span> 👋
      </div>

      {/* PrimeEdge branding */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONT_FAMILY,
          fontSize: 22,
          fontWeight: 800,
          color: COLORS.gold,
          letterSpacing: "0.2em",
          opacity: subtitleSpring,
        }}
      >
        PRIMEEDGE
      </div>
    </AbsoluteFill>
  );
};

/** Frames 60-150: Setup stats */
const SceneStats: React.FC<{ data: WeeklyWrappedData; frame: number; fps: number }> = ({
  data,
  frame,
  fps,
}) => {
  const localFrame = frame - 60;
  const opacity = interpolate(localFrame, [0, 15, 75, 90], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 60px",
        gap: 48,
      }}
    >
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 28,
          fontWeight: 700,
          color: COLORS.textMuted,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
        }}
      >
        Setup Performance
      </div>

      {/* Win Rate — big hero number */}
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 22,
            color: COLORS.textMuted,
            letterSpacing: "0.12em",
            marginBottom: 8,
          }}
        >
          WIN RATE
        </div>
        <AnimatedCounter
          to={data.win_rate * 100}
          decimals={0}
          suffix="%"
          frame={frame}
          fps={fps}
          startFrame={70}
          fontSize={160}
          color={COLORS.green}
        />
        {/* Progress arc (simplified as a bar) */}
        <div
          style={{
            height: 8,
            background: COLORS.bgAccent,
            borderRadius: 4,
            overflow: "hidden",
            marginTop: 16,
            width: "100%",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${spring({ frame: Math.max(0, localFrame - 10), fps, config: { damping: 60, stiffness: 40 }, durationInFrames: 50 }) * data.win_rate * 100}%`,
              background: `linear-gradient(90deg, ${COLORS.green}, ${COLORS.gold})`,
              borderRadius: 4,
            }}
          />
        </div>
      </div>

      {/* Stats grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          width: "100%",
        }}
      >
        {[
          { label: "Setups Taken", value: data.setups_taken, total: data.total_setups, color: COLORS.blue },
          { label: "Total Setups", value: data.total_setups, color: COLORS.textSecondary },
          { label: "Avg R-Multiple", value: data.avg_r_multiple, decimals: 1, prefix: "", suffix: "R", color: COLORS.gold },
          { label: "Total P&L", value: data.total_pnl_pips, suffix: " pips", color: data.total_pnl_pips >= 0 ? COLORS.green : COLORS.red },
        ].map((stat, idx) => (
          <div
            key={idx}
            style={{
              background: COLORS.bgCard,
              border: `1px solid ${COLORS.border}`,
              borderRadius: 20,
              padding: "28px 24px",
              display: "flex",
              flexDirection: "column",
              gap: 8,
              opacity: spring({
                frame: Math.max(0, localFrame - idx * 8),
                fps,
                config: { damping: 70, stiffness: 60 },
                durationInFrames: 30,
              }),
              transform: `translateY(${interpolate(
                spring({ frame: Math.max(0, localFrame - idx * 8), fps, config: { damping: 70, stiffness: 60 }, durationInFrames: 30 }),
                [0, 1],
                [30, 0]
              )}px)`,
            }}
          >
            <span style={{ fontFamily: FONT_FAMILY, fontSize: 16, color: COLORS.textMuted, letterSpacing: "0.1em", textTransform: "uppercase" }}>
              {stat.label}
            </span>
            <AnimatedCounter
              to={stat.value}
              decimals={(stat as any).decimals ?? 0}
              suffix={(stat as any).suffix ?? ""}
              frame={frame}
              fps={fps}
              startFrame={75 + idx * 5}
              fontSize={52}
              color={stat.color}
            />
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/** Frames 150-270: Best trade spotlight */
const SceneBestTrade: React.FC<{ data: WeeklyWrappedData; frame: number; fps: number }> = ({
  data,
  frame,
  fps,
}) => {
  const localFrame = frame - 150;
  const opacity = interpolate(localFrame, [0, 15, 100, 115], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const heroSpring = spring({
    frame: Math.max(0, localFrame - 10),
    fps,
    config: { damping: 60, stiffness: 50, mass: 1.2 },
    durationInFrames: 50,
  });
  const dirColor = directionColor(data.best_trade.direction);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 40%, ${dirColor}18 0%, ${COLORS.bg} 65%)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 32,
      }}
    >
      {/* Particle burst on entry */}
      <ParticleBurst frame={frame} fps={fps} startFrame={160} />

      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 22,
          fontWeight: 700,
          color: COLORS.gold,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
        }}
      >
        🏆 Best Trade of the Week
      </div>

      {/* Instrument */}
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 100,
          fontWeight: 900,
          color: COLORS.textPrimary,
          letterSpacing: "-0.03em",
          transform: `scale(${interpolate(heroSpring, [0, 1], [0.6, 1])})`,
          opacity: heroSpring,
        }}
      >
        {data.best_trade.instrument}
      </div>

      {/* Direction */}
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 12,
          background: `${dirColor}22`,
          border: `2px solid ${dirColor}`,
          borderRadius: 16,
          padding: "14px 40px",
          transform: `translateY(${interpolate(heroSpring, [0, 1], [30, 0])}px)`,
          opacity: heroSpring,
        }}
      >
        <span style={{ fontSize: 40, color: dirColor }}>
          {data.best_trade.direction === "LONG" ? "▲" : "▼"}
        </span>
        <span
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 40,
            fontWeight: 800,
            color: dirColor,
            letterSpacing: "0.1em",
          }}
        >
          {data.best_trade.direction}
        </span>
      </div>

      {/* Pip profit — big number */}
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 20,
            color: COLORS.textMuted,
            letterSpacing: "0.12em",
            marginBottom: 4,
          }}
        >
          PIPS CAPTURED
        </div>
        <AnimatedCounter
          to={data.best_trade.pnl_pips}
          decimals={0}
          suffix=" pips"
          frame={frame}
          fps={fps}
          startFrame={170}
          fontSize={130}
          color={dirColor}
        />
      </div>

      {/* Explosion rings */}
      {[1, 2, 3].map((ring) => {
        const ringProgress = spring({
          frame: Math.max(0, frame - (155 + ring * 6)),
          fps,
          config: { damping: 40, stiffness: 25, mass: 0.8 },
          durationInFrames: 50,
        });
        const ringOpacity = interpolate(ringProgress, [0, 0.3, 1], [0, 0.5, 0]);
        return (
          <div
            key={ring}
            style={{
              position: "absolute",
              left: "50%",
              top: "42%",
              width: 100 + ring * 180 * ringProgress,
              height: 100 + ring * 180 * ringProgress,
              borderRadius: "50%",
              border: `2px solid ${dirColor}`,
              opacity: ringOpacity,
              transform: "translate(-50%, -50%)",
              pointerEvents: "none",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Frames 270-390: MAE discipline */
const SceneMAEDiscipline: React.FC<{ data: WeeklyWrappedData; frame: number; fps: number }> = ({
  data,
  frame,
  fps,
}) => {
  const localFrame = frame - 270;
  const opacity = interpolate(localFrame, [0, 15, 100, 115], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const barProgress = spring({
    frame: Math.max(0, localFrame - 20),
    fps,
    config: { damping: 60, stiffness: 40, mass: 1.2 },
    durationInFrames: 70,
  });

  const disciplineColor =
    data.mae_discipline >= 0.8
      ? COLORS.green
      : data.mae_discipline >= 0.6
      ? COLORS.amber
      : COLORS.red;

  const disciplineLabel =
    data.mae_discipline >= 0.8
      ? "Excellent"
      : data.mae_discipline >= 0.6
      ? "Good"
      : "Needs Work";

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 60px",
        gap: 48,
      }}
    >
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 28,
          fontWeight: 700,
          color: COLORS.textMuted,
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          textAlign: "center",
        }}
      >
        Risk Discipline
      </div>

      {/* Big score */}
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 22,
            color: COLORS.textMuted,
            letterSpacing: "0.1em",
            marginBottom: 8,
          }}
        >
          MAE DISCIPLINE SCORE
        </div>
        <AnimatedCounter
          to={data.mae_discipline * 100}
          decimals={0}
          suffix="%"
          frame={frame}
          fps={fps}
          startFrame={285}
          fontSize={150}
          color={disciplineColor}
        />
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 36,
            fontWeight: 700,
            color: disciplineColor,
            marginTop: 8,
          }}
        >
          {disciplineLabel}
        </div>
      </div>

      {/* Animated progress bar */}
      <div style={{ width: "100%" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 12,
            fontFamily: FONT_MONO,
            fontSize: 18,
            color: COLORS.textMuted,
          }}
        >
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
        <div
          style={{
            height: 24,
            background: COLORS.bgAccent,
            borderRadius: 12,
            overflow: "hidden",
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: `${barProgress * data.mae_discipline * 100}%`,
              background: `linear-gradient(90deg, ${disciplineColor}88, ${disciplineColor})`,
              borderRadius: 12,
              boxShadow: `0 0 16px ${disciplineColor}88`,
            }}
          />
        </div>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 20,
            color: COLORS.textSecondary,
            textAlign: "center",
            marginTop: 16,
          }}
        >
          You stayed within your MAE corridor{" "}
          <span style={{ color: disciplineColor, fontWeight: 700 }}>
            {Math.round(data.mae_discipline * 100)}%
          </span>{" "}
          of the time.
        </div>
      </div>

      {/* Instruments traded */}
      <div style={{ width: "100%" }}>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 18,
            color: COLORS.textMuted,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: 16,
            textAlign: "center",
          }}
        >
          Instruments Traded
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
            justifyContent: "center",
          }}
        >
          {data.instruments_traded.map((inst, i) => (
            <div
              key={inst}
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${COLORS.border}`,
                borderRadius: 12,
                padding: "12px 28px",
                fontFamily: FONT_MONO,
                fontSize: 24,
                fontWeight: 700,
                color: COLORS.textPrimary,
                opacity: spring({
                  frame: Math.max(0, localFrame - 30 - i * 10),
                  fps,
                  config: { damping: 70, stiffness: 60 },
                  durationInFrames: 25,
                }),
              }}
            >
              {inst}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Frames 390-450: Outro */
const SceneOutro: React.FC<{ data: WeeklyWrappedData; frame: number; fps: number }> = ({
  data,
  frame,
  fps,
}) => {
  const localFrame = frame - 390;
  const opacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const logoSpring = spring({
    frame: Math.max(0, localFrame - 5),
    fps,
    config: { damping: 70, stiffness: 60 },
    durationInFrames: 35,
  });
  const ctaSpring = spring({
    frame: Math.max(0, localFrame - 25),
    fps,
    config: { damping: 70, stiffness: 60 },
    durationInFrames: 35,
  });

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at 50% 50%, ${COLORS.bgAccent} 0%, ${COLORS.bg} 70%)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 40,
      }}
    >
      {/* Logo */}
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 72,
          fontWeight: 900,
          color: COLORS.gold,
          letterSpacing: "0.12em",
          transform: `scale(${interpolate(logoSpring, [0, 1], [0.7, 1])})`,
          opacity: logoSpring,
        }}
      >
        PrimeEdge
      </div>

      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: 28,
          color: COLORS.textSecondary,
          letterSpacing: "0.08em",
          opacity: logoSpring,
        }}
      >
        Quantitative FX · primeedge.app
      </div>

      {/* Share CTA */}
      <div
        style={{
          background: `linear-gradient(135deg, ${COLORS.gold}22, ${COLORS.bgCard})`,
          border: `2px solid ${COLORS.gold}88`,
          borderRadius: 24,
          padding: "32px 60px",
          textAlign: "center",
          transform: `translateY(${interpolate(ctaSpring, [0, 1], [40, 0])}px)`,
          opacity: ctaSpring,
        }}
      >
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 32,
            fontWeight: 700,
            color: COLORS.textPrimary,
            marginBottom: 12,
          }}
        >
          Share Your Week
        </div>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 22,
            color: COLORS.textSecondary,
          }}
        >
          Let the numbers speak for themselves.
        </div>
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 20,
            color: COLORS.gold,
            marginTop: 20,
            letterSpacing: "0.1em",
          }}
        >
          #PrimeEdge · #{data.week_label.replace(/\s·\s/g, "_").replace(/\s/g, "")}
        </div>
      </div>

      {/* Summary strip */}
      <div
        style={{
          display: "flex",
          gap: 40,
          opacity: ctaSpring,
        }}
      >
        {[
          { label: "Win Rate", value: `${Math.round(data.win_rate * 100)}%`, color: COLORS.green },
          { label: "Avg R", value: `${data.avg_r_multiple.toFixed(1)}R`, color: COLORS.gold },
          { label: "Pips", value: `+${data.total_pnl_pips}`, color: COLORS.blue },
        ].map((s) => (
          <div key={s.label} style={{ textAlign: "center" }}>
            <div style={{ fontFamily: FONT_MONO, fontSize: 44, fontWeight: 900, color: s.color }}>
              {s.value}
            </div>
            <div style={{ fontFamily: FONT_FAMILY, fontSize: 16, color: COLORS.textMuted, marginTop: 4 }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ── Main Composition ────────────────────────────────────────
export const WeeklyWrapped: React.FC<WeeklyWrappedData> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);

  return (
    <AbsoluteFill style={{ background: COLORS.bg, overflow: "hidden" }}>
      {/* Render the scene that matches the current frame range.
          Each scene uses AbsoluteFill + opacity so crossfades are smooth. */}
      {frame < 70 && <SceneIntro data={props} frame={frame} fps={fps} />}
      {frame >= 55 && frame < 160 && <SceneStats data={props} frame={frame} fps={fps} />}
      {frame >= 145 && frame < 280 && <SceneBestTrade data={props} frame={frame} fps={fps} />}
      {frame >= 265 && frame < 400 && <SceneMAEDiscipline data={props} frame={frame} fps={fps} />}
      {frame >= 385 && <SceneOutro data={props} frame={frame} fps={fps} />}
    </AbsoluteFill>
  );
};
