// ─────────────────────────────────────────────────────────────
// PrimeEdge · Aha marketing film
// Problem → exaggerate → wait/ready aha → effortless solve → CTA
// ─────────────────────────────────────────────────────────────
import React, { useEffect } from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  delayRender,
  continueRender,
} from "remotion";
import { COLORS } from "../../utils/colors";
import { FONT_FAMILY, FONT_MONO, loadGoogleFonts } from "../../utils/fonts";
import { MARKETING_SCENES, MARKETING_TIMELINE } from "./timing";

const CYAN = "#00f2fe";
const SKY = "#38bdf8";
const BG = "#05070c";
const clamp = {
  extrapolateLeft: "clamp" as const,
  extrapolateRight: "clamp" as const,
};

export type MarketingHeroData = Record<string, never>;
export const defaultMarketingHeroProps: MarketingHeroData = {};

const useFonts = () => {
  useEffect(() => {
    const handle = delayRender("Fonts");
    loadGoogleFonts().then(() => continueRender(handle));
  }, []);
};

const Grid: React.FC<{ color?: string }> = ({ color = "rgba(255,255,255,0.045)" }) => (
  <AbsoluteFill style={{ pointerEvents: "none" }}>
    {Array.from({ length: 12 }).map((_, i) => (
      <div
        key={`h${i}`}
        style={{
          position: "absolute",
          top: `${(i / 12) * 100}%`,
          left: 0,
          right: 0,
          height: 1,
          background: color,
        }}
      />
    ))}
    {Array.from({ length: 20 }).map((_, i) => (
      <div
        key={`v${i}`}
        style={{
          position: "absolute",
          left: `${(i / 20) * 100}%`,
          top: 0,
          bottom: 0,
          width: 1,
          background: color,
        }}
      />
    ))}
  </AbsoluteFill>
);

const WordMark: React.FC<{ size?: number }> = ({ size = 22 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
    <div
      style={{
        width: size + 10,
        height: size + 10,
        borderRadius: 8,
        background: `linear-gradient(135deg, ${CYAN}, ${SKY})`,
        color: BG,
        fontWeight: 900,
        fontSize: size,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: `0 0 22px ${CYAN}66`,
      }}
    >
      P
    </div>
    <div>
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontWeight: 800,
          fontSize: size,
          color: "#fff",
          letterSpacing: -0.6,
          lineHeight: 1,
        }}
      >
        PrimeEdge
      </div>
      <div
        style={{
          fontFamily: FONT_FAMILY,
          fontSize: Math.max(11, size * 0.42),
          color: CYAN,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          fontWeight: 700,
          marginTop: 5,
        }}
      >
        Clear calls. Real stops.
      </div>
    </div>
  </div>
);

const Caption: React.FC<{ text: string; appear?: number }> = ({ text, appear = 8 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [appear, appear + 12], [0, 1], clamp);
  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        bottom: 54,
        textAlign: "center",
        fontFamily: FONT_FAMILY,
        fontSize: 28,
        fontWeight: 700,
        color: "#fff",
        lineHeight: 1.35,
        opacity: o,
        textShadow: "0 8px 28px rgba(0,0,0,0.85)",
      }}
    >
      {text}
    </div>
  );
};

const Kicker: React.FC<{ text: string; color?: string }> = ({ text, color = COLORS.red }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        fontFamily: FONT_MONO,
        fontSize: 18,
        fontWeight: 800,
        color,
        letterSpacing: "0.28em",
        opacity: interpolate(frame, [0, 10], [0, 1], clamp),
        marginBottom: 18,
      }}
    >
      {text}
    </div>
  );
};

const SceneHook: React.FC = () => {
  const frame = useCurrentFrame();
  const shake = Math.sin(frame * 1.4) * interpolate(frame, [0, 50, 90], [5, 2, 0], clamp);
  const spam = [
    { t: "VIP GOLD 92% WIN RATE", y: 10, x: 6, delay: 0 },
    { t: "BUY XAUUSD NOW NOW NOW", y: 22, x: 52, delay: 6 },
    { t: "ACCOUNT  −$4,821", y: 74, x: 8, delay: 12 },
    { t: "RSI SAYS LONG   MACD SAYS SHORT", y: 84, x: 42, delay: 16 },
    { t: "GURU: ENTER HERE 🔥🔥🔥", y: 14, x: 28, delay: 20 },
  ];
  return (
    <AbsoluteFill style={{ background: BG, transform: `translate(${shake}px, ${-shake * 0.35}px)` }}>
      <Grid color="rgba(255,59,92,0.09)" />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 40%, ${COLORS.red}40 0%, transparent 58%)`,
        }}
      />
      {spam.map((s) => (
        <div
          key={s.t}
          style={{
            position: "absolute",
            top: `${s.y}%`,
            left: `${s.x}%`,
            fontFamily: FONT_MONO,
            fontSize: 22,
            fontWeight: 700,
            color: s.t.includes("−") ? COLORS.red : "rgba(255,255,255,0.72)",
            opacity: interpolate(frame, [s.delay, s.delay + 10], [0, 0.9], clamp),
            letterSpacing: 0.6,
          }}
        >
          {s.t}
        </div>
      ))}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 80px",
          opacity: interpolate(frame, [4, 14], [0, 1], clamp),
        }}
      >
        <Kicker text="LONDON OPEN  ·  NO PROCESS" />
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 76,
            fontWeight: 900,
            color: "#fff",
            textAlign: "center",
            lineHeight: 1.05,
            letterSpacing: -2.2,
            maxWidth: 1500,
          }}
        >
          Forty-seven signals.
          <br />
          Zero decisions.
        </div>
      </div>
      <Caption text="Forty-seven signals screaming buy. You still freeze." appear={18} />
    </AbsoluteFill>
  );
};

const SceneProblem: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = spring({ frame, fps, config: { damping: 16, stiffness: 70 } });
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Grid />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "0 90px",
          transform: `translateY(${interpolate(a, [0, 1], [24, 0])}px)`,
          opacity: a,
        }}
      >
        <Kicker text="THE REAL PROBLEM" color={COLORS.amber} />
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 72,
            fontWeight: 900,
            color: "#fff",
            letterSpacing: -2,
            lineHeight: 1.08,
          }}
        >
          You don’t lack charts.
        </div>
        <div
          style={{
            marginTop: 16,
            fontFamily: FONT_FAMILY,
            fontSize: 64,
            fontWeight: 900,
            background: `linear-gradient(135deg, ${CYAN}, ${SKY})`,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          You lack a decision.
        </div>
      </div>
      <Caption text="You're not missing charts. You're missing a yes or no." appear={8} />
    </AbsoluteFill>
  );
};

const ScenePain: React.FC = () => {
  const frame = useCurrentFrame();
  const painFrames = MARKETING_SCENES.find((s) => s.id === "pain")?.frames ?? 310;
  const mid = Math.floor(painFrames * 0.48);
  const chase = frame >= mid;
  const local = chase ? frame - mid : frame;
  const hit = !chase && local > Math.floor(mid * 0.42);
  const run = interpolate(local, [0, Math.max(12, painFrames - mid - 18)], [0, 34], clamp);
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Grid color={chase ? "rgba(245,158,11,0.08)" : "rgba(255,59,92,0.07)"} />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: chase
            ? `radial-gradient(ellipse at 20% 80%, ${COLORS.amber}24 0%, transparent 50%)`
            : `radial-gradient(ellipse at 80% 70%, ${COLORS.red}28 0%, transparent 50%)`,
        }}
      />
      <div style={{ position: "absolute", top: 64, left: 80, right: 80 }}>
        <Kicker
          text={chase ? "THEN YOU CHASE" : "FIRST YOU GET STOPPED"}
          color={chase ? COLORS.amber : COLORS.red}
        />
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 62,
            fontWeight: 900,
            color: "#fff",
            letterSpacing: -1.6,
            lineHeight: 1.08,
            maxWidth: 1300,
          }}
        >
          {chase
            ? local > 36
              ? "That's not trading. That's panic."
              : "Gold is running. You chase."
            : hit
              ? "Then it rips without you."
              : "Stop on a round number."}
        </div>
      </div>
      {!chase ? (
        <div style={{ position: "absolute", right: 80, bottom: 130, textAlign: "right", fontFamily: FONT_MONO }}>
          <div style={{ fontSize: 18, color: COLORS.textMuted, letterSpacing: "0.2em" }}>EURUSD</div>
          <div
            style={{
              fontSize: 84,
              fontWeight: 800,
              color: hit ? COLORS.red : "#fff",
              textShadow: hit ? `0 0 40px ${COLORS.red}` : "none",
            }}
          >
            {hit ? "STOPPED OUT" : "1.30000"}
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, color: hit ? COLORS.green : COLORS.amber, marginTop: 6 }}>
            {hit ? "THEN +47 PIPS WITHOUT YOU" : "CLEAN NUMBER. DIRTY STOP."}
          </div>
        </div>
      ) : (
        <div style={{ position: "absolute", right: 80, bottom: 130, width: 560 }}>
          <div style={{ fontFamily: FONT_MONO, fontSize: 16, color: COLORS.textMuted, marginBottom: 10 }}>
            XAUUSD  ·  LONDON
          </div>
          <div
            style={{
              height: 18,
              background: COLORS.bgAccent,
              borderRadius: 99,
              overflow: "hidden",
              border: `1px solid ${COLORS.border}`,
            }}
          >
            <div
              style={{
                width: `${Math.min(100, run * 2.6)}%`,
                height: "100%",
                background: local > 36 ? COLORS.red : COLORS.green,
              }}
            />
          </div>
          <div
            style={{
              marginTop: 16,
              fontFamily: FONT_MONO,
              fontSize: 60,
              fontWeight: 800,
              color: local > 36 ? COLORS.red : COLORS.green,
            }}
          >
            {local > 36 ? "CHASE −12" : `+${run.toFixed(0)} PIPS`}
          </div>
        </div>
      )}
      <Caption
        text={
          chase
            ? "You chase. Instant red. That's panic."
            : "Round-number stop. Tagged. Then it leaves without you."
        }
        appear={6}
      />
    </AbsoluteFill>
  );
};

const SceneAha: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const waitIn = spring({ frame: Math.max(0, frame - 8), fps, config: { damping: 14, stiffness: 110 } });
  const readyIn = spring({ frame: Math.max(0, frame - 38), fps, config: { damping: 13, stiffness: 100 } });
  const evidence = interpolate(frame, [70, 92], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: BG }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 45%, ${CYAN}26 0%, transparent 58%)`,
        }}
      />
      <Grid color="rgba(0,242,254,0.06)" />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 22,
        }}
      >
        <div
          style={{
            fontFamily: FONT_MONO,
            fontSize: 20,
            fontWeight: 800,
            color: CYAN,
            letterSpacing: "0.34em",
            opacity: interpolate(frame, [0, 16], [0, 1], clamp),
          }}
        >
          THE AHA
        </div>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 36,
            color: COLORS.textSecondary,
            opacity: interpolate(frame, [8, 24], [0, 1], clamp),
          }}
        >
          PrimeEdge doesn’t shout BUY.
        </div>
        <div style={{ display: "flex", gap: 28, alignItems: "center", marginTop: 8 }}>
          <div
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 110,
              fontWeight: 900,
              color: COLORS.amber,
              letterSpacing: -3,
              opacity: waitIn,
              transform: `scale(${interpolate(waitIn, [0, 1], [0.8, 1])})`,
              textShadow: `0 0 40px ${COLORS.amber}88`,
            }}
          >
            WAIT
          </div>
          <div
            style={{
              fontFamily: FONT_FAMILY,
              fontSize: 92,
              fontWeight: 900,
              color: COLORS.green,
              letterSpacing: -3,
              opacity: readyIn,
              transform: `scale(${interpolate(readyIn, [0, 1], [0.8, 1])})`,
              textShadow: `0 0 48px ${COLORS.green}99`,
            }}
          >
            TAKE IT
          </div>
        </div>
        <div
          style={{
            display: "flex",
            gap: 14,
            opacity: evidence,
            transform: `translateY(${interpolate(evidence, [0, 1], [16, 0])}px)`,
            marginTop: 8,
          }}
        >
          {[
            ["HISTORY", "187 similar trades"],
            ["STOP", "31 pips from history"],
            ["ENTRY ZONE", "2338 – 2344"],
            ["WHY NOW", "Dollar weak, gold bid"],
          ].map(([l, v]) => (
            <div
              key={l}
              style={{
                background: COLORS.bgCard,
                border: `1px solid ${CYAN}44`,
                borderRadius: 14,
                padding: "14px 22px",
                minWidth: 180,
                textAlign: "center",
              }}
            >
              <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: COLORS.textMuted, letterSpacing: "0.14em" }}>
                {l}
              </div>
              <div style={{ fontFamily: FONT_MONO, fontSize: 22, color: "#fff", marginTop: 6, fontWeight: 700 }}>
                {v}
              </div>
            </div>
          ))}
        </div>
      </div>
      <Caption text="It tells you wait. Or take the trade. And shows you why." appear={10} />
    </AbsoluteFill>
  );
};

const RadarRow: React.FC<{
  symbol: string;
  status: string;
  dir: string;
  score: number;
  delay: number;
}> = ({ symbol, status, dir, score, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({
    frame: Math.max(0, frame - delay),
    fps,
    config: { damping: 14, stiffness: 80 },
  });
  const color =
    status === "TAKE IT" || status === "READY"
      ? COLORS.green
      : status === "WAIT"
        ? COLORS.amber
        : COLORS.red;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "150px 160px 90px 1fr",
        alignItems: "center",
        gap: 14,
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderLeft: `4px solid ${color}`,
        borderRadius: 12,
        padding: "14px 20px",
        transform: `translateX(${interpolate(s, [0, 1], [36, 0])}px)`,
        opacity: s,
      }}
    >
      <div style={{ fontFamily: FONT_MONO, fontSize: 26, fontWeight: 800, color: "#fff" }}>{symbol}</div>
      <div style={{ fontFamily: FONT_MONO, fontSize: 16, fontWeight: 800, color, letterSpacing: "0.12em" }}>
        {status}
      </div>
      <div style={{ fontFamily: FONT_MONO, fontSize: 16, color: dir === "LONG" ? COLORS.green : COLORS.red }}>
        {dir}
      </div>
      <div>
        <div style={{ height: 8, background: "#1a2230", borderRadius: 99, overflow: "hidden" }}>
          <div style={{ width: `${score * 100}%`, height: "100%", background: color }} />
        </div>
        <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: COLORS.textMuted, marginTop: 5 }}>
          Strength {Math.round(score * 100)}
        </div>
      </div>
    </div>
  );
};

const SceneSolve: React.FC = () => {
  const frame = useCurrentFrame();
  const gates = ["FIND", "PLAN STOP", "WHY", "TRADE", "REVIEW"];
  return (
    <AbsoluteFill style={{ background: BG }}>
      <Grid color="rgba(0,242,254,0.05)" />
      <div style={{ position: "absolute", top: 36, left: 56 }}>
        <WordMark size={20} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 44,
          right: 56,
          fontFamily: FONT_MONO,
          fontSize: 14,
          color: COLORS.green,
        }}
      >
        ●  LIVE  ·  EFFORTLESS ON PURPOSE
      </div>
      <div style={{ position: "absolute", top: 110, left: 56, right: 620 }}>
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 48,
            fontWeight: 900,
            color: "#fff",
            letterSpacing: -1.3,
            lineHeight: 1.08,
          }}
        >
          One screen. Clear call.
          <br />
          Wait, take it, or stand down.
        </div>
        <div style={{ marginTop: 22, display: "flex", flexDirection: "column", gap: 10 }}>
          <RadarRow symbol="XAUUSD" status="TAKE IT" dir="LONG" score={0.82} delay={4} />
          <RadarRow symbol="GBPUSD" status="WAIT" dir="LONG" score={0.61} delay={10} />
          <RadarRow symbol="USDJPY" status="NO TRADE" dir="SHORT" score={0.31} delay={16} />
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 118,
          right: 48,
          width: 540,
          background: "rgba(17,24,39,0.92)",
          border: `1px solid ${CYAN}44`,
          borderRadius: 18,
          padding: 26,
          boxShadow: `0 20px 60px ${CYAN}22`,
          opacity: interpolate(frame, [16, 36], [0, 1], clamp),
        }}
      >
        <div style={{ fontFamily: FONT_MONO, fontSize: 13, color: CYAN, letterSpacing: "0.2em" }}>WHY THIS TRADE</div>
        <div style={{ fontFamily: FONT_FAMILY, fontSize: 24, color: "#fff", marginTop: 10, lineHeight: 1.4 }}>
          Dollar is weak. Gold is holding the zone. 187 similar days in the book.
        </div>
        <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {[
            ["STOP FROM HISTORY", "31 pips"],
            ["ENTRY ZONE", "2338 – 2344"],
            ["USUALLY HOLDS", "74%"],
            ["TRADE LOG", "Writes itself"],
          ].map(([l, v]) => (
            <div key={l} style={{ background: COLORS.bgAccent, borderRadius: 12, padding: "12px 14px" }}>
              <div style={{ fontFamily: FONT_MONO, fontSize: 11, color: COLORS.textMuted }}>{l}</div>
              <div style={{ fontFamily: FONT_MONO, fontSize: 20, color: "#fff", marginTop: 4 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          left: 56,
          right: 56,
          bottom: 108,
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 12,
        }}
      >
        {gates.map((g, i) => {
          const o = interpolate(frame, [18 + i * 5, 28 + i * 5], [0, 1], clamp);
          return (
            <div
              key={g}
              style={{
                border: `1px solid ${CYAN}33`,
                background: COLORS.bgCard,
                borderRadius: 12,
                padding: "12px 16px",
                opacity: o,
              }}
            >
              <div style={{ fontFamily: FONT_MONO, fontSize: 12, color: CYAN }}>0{i + 1}</div>
              <div style={{ fontFamily: FONT_FAMILY, fontSize: 22, fontWeight: 800, color: "#fff" }}>{g}</div>
            </div>
          );
        })}
      </div>
      <Caption text="History-based stop. Real entry zone. The log writes itself." appear={8} />
    </AbsoluteFill>
  );
};

const SceneCta: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14, stiffness: 70 } });
  return (
    <AbsoluteFill style={{ background: BG }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 40%, ${CYAN}30 0%, transparent 55%)`,
        }}
      />
      <Grid color="rgba(0,242,254,0.06)" />
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${interpolate(s, [0, 1], [0.92, 1])})`,
          opacity: s,
          gap: 22,
        }}
      >
        <WordMark size={28} />
        <div
          style={{
            fontFamily: FONT_FAMILY,
            fontSize: 72,
            fontWeight: 900,
            color: "#fff",
            textAlign: "center",
            letterSpacing: -2,
            lineHeight: 1.05,
          }}
        >
          Stop guessing.
          <br />
          Trade with a reason.
        </div>
        <div
          style={{
            marginTop: 4,
            background: `linear-gradient(135deg, ${CYAN}, ${SKY})`,
            color: BG,
            fontFamily: FONT_FAMILY,
            fontWeight: 900,
            fontSize: 30,
            padding: "16px 40px",
            borderRadius: 12,
            boxShadow: `0 8px 40px ${CYAN}55`,
          }}
        >
          Get Started
        </div>
        <div style={{ fontFamily: FONT_MONO, fontSize: 18, color: COLORS.textSecondary, letterSpacing: "0.12em" }}>
          PRIMEEDGE  ·  CLEAR CALLS. REAL STOPS.
        </div>
      </div>
    </AbsoluteFill>
  );
};

const SCENES: Record<string, React.FC> = {
  hook: SceneHook,
  problem: SceneProblem,
  pain: ScenePain,
  aha: SceneAha,
  solve: SceneSolve,
  cta: SceneCta,
};

export const MarketingHero: React.FC<MarketingHeroData> = () => {
  useFonts();
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const bedVol = interpolate(frame, [0, 20, durationInFrames - 40, durationInFrames], [0, 0.2, 0.2, 0], clamp);

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT_FAMILY }}>
      <Audio src={staticFile("audio/bed.wav")} volume={bedVol} />
      {MARKETING_TIMELINE.map((scene) => {
        const Comp = SCENES[scene.id];
        return (
          <Sequence key={scene.id} from={scene.from} durationInFrames={scene.frames}>
            <Comp />
            <Audio src={staticFile(`audio/${scene.id}.mp3`)} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
