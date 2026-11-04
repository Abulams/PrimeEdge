// ─────────────────────────────────────────────────────────────
// SignalNoiseField — chaotic alerts that collapse to silence
// ─────────────────────────────────────────────────────────────
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, spring } from "remotion";
import { COLORS } from "../../../utils/colors";

const SIGNALS = [
  "BUY GBPUSD", "SELL XAUUSD", "RSI OVERSOLD", "MACD CROSS", "EMA BREAK",
  "BUY EURUSD", "BEARISH DIV", "FIBO 61.8%", "SELL USDJPY", "BREAKOUT",
  "BUY AUDUSD", "SELL GBPUSD", "OVERBOUGHT", "GOLDEN CROSS", "BUY XAUUSD",
  "SELL EURUSD", "SUPPORT HIT", "RESISTANCE", "TREND BREAK", "SELL AUDUSD",
  "BULLISH DIV", "DEATH CROSS", "BUY USDJPY", "SELL XAUUSD", "REVERSAL",
];

const rand = (seed: number, min: number, max: number) => {
  const x = Math.sin(seed * 9301 + 49297) * 233280;
  return min + ((x - Math.floor(x)) * (max - min));
};

interface Props {
  collapseAtFrame?: number; // frame at which chaos collapses
}

export const SignalNoiseField: React.FC<Props> = ({ collapseAtFrame = 50 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chaos = interpolate(frame, [0, collapseAtFrame - 10, collapseAtFrame], [1, 1, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ overflow: "hidden", background: COLORS.bg }}>
      {SIGNALS.map((sig, i) => {
        const x = rand(i * 3 + 1, 2, 95);
        const y = rand(i * 3 + 2, 2, 95);
        const size = rand(i * 3 + 3, 11, 18);
        const speed = rand(i, 0.4, 1.2);
        const phase = rand(i * 7, 0, Math.PI * 2);
        const floatY = Math.sin(frame * 0.04 * speed + phase) * 6;
        const opacity = chaos * rand(i * 2, 0.3, 0.85) *
          Math.max(0, Math.sin((frame * 0.06 * speed) + phase));

        // Colour — mix of red/amber/muted
        const colours = [COLORS.red, COLORS.amber, COLORS.textMuted, "#60a5fa"];
        const color = colours[i % colours.length];

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `calc(${y}% + ${floatY}px)`,
              fontSize: size,
              fontFamily: "Inter, monospace",
              fontWeight: 700,
              color,
              opacity,
              letterSpacing: 1.5,
              whiteSpace: "nowrap",
              textShadow: `0 0 12px ${color}88`,
              transform: `rotate(${rand(i, -4, 4)}deg)`,
              transition: "opacity 0.1s",
            }}
          >
            {sig}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
