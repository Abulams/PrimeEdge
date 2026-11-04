// S2_Pain — 0:02–0:06 (120 frames)
// Fast cuts: stop-out → price rips → chase → red
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../../../utils/colors";

const Flash: React.FC<{ startFrame: number; color: string }> = ({ startFrame, color }) => {
  const frame = useCurrentFrame();
  const op = interpolate(frame, [startFrame, startFrame + 4, startFrame + 12], [0.6, 0.6, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ background: color, opacity: op, pointerEvents: "none" }} />;
};

const PainEvent: React.FC<{
  startFrame: number;
  headline: string;
  sub: string;
  amount?: string;
  amountColor?: string;
}> = ({ startFrame, headline, sub, amount, amountColor = COLORS.red }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const op = interpolate(frame, [startFrame, startFrame + 8, startFrame + 28, startFrame + 38], [0, 1, 1, 0], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const y = spring({ frame: frame - startFrame, fps, config: { damping: 18, stiffness: 200 } });
  const translateY = interpolate(y, [0, 1], [20, 0]);

  return (
    <div style={{
      opacity: op,
      transform: `translateY(${translateY}px)`,
      textAlign: "center",
    }}>
      <div style={{
        fontSize: 52,
        fontWeight: 900,
        color: COLORS.textPrimary,
        fontFamily: "Inter, SF Pro Display, sans-serif",
        lineHeight: 1.1,
      }}>
        {headline}
      </div>
      {amount && (
        <div style={{
          fontSize: 72,
          fontWeight: 900,
          color: amountColor,
          fontFamily: "Inter, SF Pro Display, sans-serif",
          marginTop: 8,
          textShadow: `0 0 40px ${amountColor}66`,
        }}>
          {amount}
        </div>
      )}
      <div style={{
        fontSize: 22,
        color: COLORS.textSecondary,
        fontFamily: "Inter, sans-serif",
        marginTop: 12,
        maxWidth: 640,
      }}>
        {sub}
      </div>
    </div>
  );
};

export const S2_Pain: React.FC = () => {
  const frame = useCurrentFrame();

  const bgOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: COLORS.bg, opacity: bgOpacity }}>
      {/* Subtle red tint throughout */}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 60%, ${COLORS.red}12 0%, transparent 70%)` }} />

      <AbsoluteFill style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 100px",
      }}>
        {/* Event 1: Stop placed at round number */}
        <PainEvent
          startFrame={0}
          headline="Stop placed at a round number."
          sub="Looks clean. Feels logical."
        />
        {/* Event 2: Stop gets tagged */}
        <PainEvent
          startFrame={30}
          headline="Stop tagged."
          amount="−28 pips"
          sub="Price wicked straight through it."
        />
        {/* Event 3: Price rips without you */}
        <PainEvent
          startFrame={60}
          headline="Price rips — without you."
          amount="↑ +41 pips"
          amountColor={COLORS.green}
          sub="You were right. Your stop was wrong."
        />
        {/* Event 4: Chase → instant red */}
        <PainEvent
          startFrame={88}
          headline="You chase."
          amount="−19 pips"
          sub={`That's not trading. That's panic.`}
        />
      </AbsoluteFill>

      {/* Flash on stop-out */}
      <Flash startFrame={30} color={COLORS.red} />
      <Flash startFrame={88} color={COLORS.red} />
    </AbsoluteFill>
  );
};
