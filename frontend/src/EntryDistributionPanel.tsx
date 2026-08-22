import React, { useState } from "react";
import { Target, ChevronDown, ChevronUp, Info, TrendingUp, History } from "lucide-react";

interface DistributionStep {
  pips_below: number;
  fill_probability: number;
  n_filled: number;
  n_wins: number;
  conditional_win_prob: number;
  win_rate_reliable: boolean;
  new_rr: number;
  new_risk: number;
  new_reward: number;
  rr_improvement_pct: number;
  expected_ev: number;
  stars: number;
  ev_quality: string;
  price_level: number;
}

interface EntryProfile {
  pips_below: number;
  fill_probability: number;
  n_filled: number;
  n_wins: number;
  conditional_win_prob: number;
  win_rate_reliable: boolean;
  new_rr: number;
  rr_improvement_pct: number;
  expected_ev: number;
  stars: number;
  ev_quality: string;
  label: string;
  reason: string;
  color: string;
  price_level: number;
}

export interface EntryZoneData {
  distribution: DistributionStep[];
  total_setups: number;
  baseline_rr: number;
  profiles: {
    aggressive: EntryProfile;
    optimal: EntryProfile;
    conservative: EntryProfile;
  };
  best_ev_entry: DistributionStep;
  methodology_note: string;
  current_price: number;
  trend: string;
  regime_risk_pips: number;
  regime_reward_pips: number;
}

interface Props {
  entryZone: EntryZoneData;
  symbol: string;
}

const pct = (v: number) => (v * 100).toFixed(0) + "%";
const starsLabel = (n: number) => "\u2605".repeat(n) + "\u2606".repeat(5 - n);

function ProfileCard({
  profile,
  isOptimal,
  showAdvanced,
}: {
  profile: EntryProfile;
  isOptimal: boolean;
  showAdvanced: boolean;
}) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        padding: "16px",
        borderRadius: "10px",
        border: `1px solid ${isOptimal ? profile.color : "rgba(255,255,255,0.08)"}`,
        backgroundColor: isOptimal ? `${profile.color}18` : "rgba(0,0,0,0.25)",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        position: "relative",
      }}
    >
      {isOptimal && (
        <div
          style={{
            position: "absolute",
            top: "-9px",
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: profile.color,
            color: "#000",
            fontSize: "9px",
            fontWeight: 900,
            padding: "2px 10px",
            borderRadius: "4px",
            whiteSpace: "nowrap",
            letterSpacing: "0.5px",
          }}
        >
          RECOMMENDED
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "13px", fontWeight: 800, color: profile.color }}>
          {profile.label}
        </span>
        <span style={{ fontSize: "16px", letterSpacing: "1px", color: profile.color }}>
          {starsLabel(profile.stars)}
        </span>
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}
      >
        {[
          {
            label: "Fill Chance",
            value: profile.pips_below === 0 ? "100%" : pct(profile.fill_probability),
            sub: profile.pips_below === 0 ? "always fills" : `${profile.n_filled} sessions retraced`,
            color: "#fff",
          },
          {
            label: profile.pips_below === 0 ? "Historical Success" : "Success If Filled",
            value: pct(profile.conditional_win_prob),
            sub: `${profile.n_wins} of ${profile.n_filled} won`,
            color:
              profile.conditional_win_prob >= 0.58
                ? "#10b981"
                : profile.conditional_win_prob >= 0.50
                ? "#f59e0b"
                : "#ef4444",
          },
          {
            label: "Entry Discount",
            value: profile.pips_below === 0 ? "0p" : `-${profile.pips_below}p`,
            sub: "below market price",
            color: "#fff",
          },
          {
            label: "Reward Improvement",
            value:
              profile.rr_improvement_pct > 0
                ? `+${profile.rr_improvement_pct.toFixed(0)}%`
                : "Baseline",
            sub: "vs market entry",
            color: profile.rr_improvement_pct > 0 ? "#10b981" : "var(--text-muted)",
          },
        ].map((m) => (
          <div
            key={m.label}
            style={{
              padding: "8px",
              borderRadius: "6px",
              backgroundColor: "rgba(255,255,255,0.04)",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "9px",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                marginBottom: "3px",
              }}
            >
              {m.label}
            </div>
            <div
              style={{
                fontSize: "18px",
                fontWeight: 900,
                color: m.color,
                fontFamily: "var(--font-mono)",
              }}
            >
              {m.value}
            </div>
            <div style={{ fontSize: "9px", color: "var(--text-muted)", marginTop: "2px" }}>
              {m.sub}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          fontSize: "10px",
          color: "var(--text-muted)",
          lineHeight: 1.5,
          borderTop: "1px solid rgba(255,255,255,0.06)",
          paddingTop: "8px",
        }}
      >
        {profile.reason}
      </div>

      {showAdvanced && (
        <div style={{ display: "flex", gap: "6px" }}>
          <span
            style={{
              fontSize: "9px",
              fontFamily: "var(--font-mono)",
              padding: "2px 6px",
              borderRadius: "3px",
              backgroundColor: "rgba(255,255,255,0.06)",
              color: "var(--text-muted)",
            }}
          >
            R:R {profile.new_rr.toFixed(2)}
          </span>
          <span
            style={{
              fontSize: "9px",
              fontFamily: "var(--font-mono)",
              padding: "2px 6px",
              borderRadius: "3px",
              backgroundColor: "rgba(255,255,255,0.06)",
              color: "var(--text-muted)",
            }}
          >
            EV {profile.expected_ev >= 0 ? "+" : ""}{profile.expected_ev.toFixed(3)}R
          </span>
        </div>
      )}
    </div>
  );
}

function WaterfallRow({
  step,
  isOptimal,
  showAdvanced,
}: {
  step: DistributionStep;
  isOptimal: boolean;
  showAdvanced: boolean;
}) {
  const fillPct = (step.fill_probability * 100).toFixed(0);
  const winPct = (step.conditional_win_prob * 100).toFixed(0);
  const barW = `${(step.fill_probability * 100).toFixed(1)}%`;
  const barColor =
    step.ev_quality === "EXCELLENT"
      ? "rgba(16,185,129,0.8)"
      : step.ev_quality === "GOOD"
      ? "rgba(0,242,254,0.7)"
      : step.ev_quality === "MARGINAL"
      ? "rgba(245,158,11,0.6)"
      : "rgba(239,68,68,0.5)";
  const winColor =
    step.conditional_win_prob >= 0.58
      ? "#10b981"
      : step.conditional_win_prob >= 0.50
      ? "#f59e0b"
      : "#ef4444";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: showAdvanced
          ? "52px 1fr 65px 75px 22px 46px 50px"
          : "52px 1fr 65px 75px 22px",
        gap: "4px",
        alignItems: "center",
        padding: "3px 4px",
        borderRadius: "4px",
        backgroundColor: isOptimal ? "rgba(16,185,129,0.07)" : "transparent",
        border: `1px solid ${isOptimal ? "rgba(16,185,129,0.2)" : "transparent"}`,
        marginBottom: "2px",
      }}
    >
      <div
        style={{
          fontSize: "10px",
          fontFamily: "var(--font-mono)",
          color: isOptimal ? "#10b981" : "var(--text-secondary)",
          fontWeight: isOptimal ? 800 : 400,
        }}
      >
        {step.pips_below === 0 ? "Market" : `-${step.pips_below}p`}
        {isOptimal && (
          <div style={{ fontSize: "7px", color: "#10b981", lineHeight: 1 }}>
            OPTIMAL
          </div>
        )}
      </div>

      <div
        style={{
          position: "relative",
          height: "10px",
          backgroundColor: "rgba(255,255,255,0.05)",
          borderRadius: "2px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: barW,
            backgroundColor: barColor,
            borderRadius: "2px",
          }}
        />
      </div>

      <div
        style={{
          fontSize: "10px",
          fontFamily: "var(--font-mono)",
          color: "var(--text-secondary)",
          textAlign: "right",
        }}
      >
        {step.n_filled} ({fillPct}%)
      </div>

      <div
        style={{
          fontSize: "10px",
          fontFamily: "var(--font-mono)",
          textAlign: "right",
          fontWeight: 700,
          color: winColor,
        }}
      >
        {step.n_wins}/{step.n_filled} ({winPct}%)
      </div>

      <div style={{ textAlign: "center", fontSize: "9px", color: barColor }}>
        {"_".repeat(step.stars).replace(/_/g, "\u2605")}{"_".repeat(5 - step.stars).replace(/_/g, "\u00b7")}
      </div>

      {showAdvanced && (
        <>
          <div
            style={{
              fontSize: "9px",
              fontFamily: "var(--font-mono)",
              color: "var(--text-muted)",
              textAlign: "right",
            }}
          >
            {step.rr_improvement_pct > 0
              ? `+${step.rr_improvement_pct.toFixed(0)}%`
              : "base"}
          </div>
          <div
            style={{
              fontSize: "9px",
              fontFamily: "var(--font-mono)",
              textAlign: "right",
              color:
                step.ev_quality === "EXCELLENT"
                  ? "#10b981"
                  : step.ev_quality === "GOOD"
                  ? "#00f2fe"
                  : step.ev_quality === "MARGINAL"
                  ? "#f59e0b"
                  : "#ef4444",
            }}
          >
            {step.expected_ev >= 0 ? "+" : ""}{step.expected_ev.toFixed(2)}R
          </div>
        </>
      )}
    </div>
  );
}

export function EntryDistributionPanel({ entryZone, symbol }: Props) {
  const [open, setOpen] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showMethodology, setShowMethodology] = useState(false);
  const { distribution, profiles, total_setups, methodology_note, trend } = entryZone;
  const isBuy = trend === "BULLISH";
  const optPips = profiles.optimal.pips_below;

  return (
    <div
      style={{
        backgroundColor: "var(--bg-secondary)",
        border: "1px solid var(--border-color)",
        borderTop: "none",
        borderRadius: "0 0 12px 12px",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          padding: "10px 16px",
          background: "transparent",
          border: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          color: "#fff",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Target size={14} style={{ color: "#10b981" }} />
          <span style={{ fontSize: "12px", fontWeight: 800 }}>
            Historical Entry Distribution \u2014 {isBuy ? "BUY" : "SELL"} {symbol}
          </span>
          <span
            style={{
              fontSize: "10px",
              padding: "1px 6px",
              borderRadius: "4px",
              backgroundColor: "rgba(16,185,129,0.12)",
              color: "#10b981",
              fontFamily: "var(--font-mono)",
            }}
          >
            Optimal: {optPips === 0 ? "At Market" : `-${optPips}p limit`} \u00b7{" "}
            {(profiles.optimal.conditional_win_prob * 100).toFixed(0)}% success if filled
          </span>
          <span
            style={{
              fontSize: "10px",
              color: "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            N={total_setups} sessions
          </span>
        </div>
        {open ? (
          <ChevronUp size={14} style={{ color: "var(--text-muted)" }} />
        ) : (
          <ChevronDown size={14} style={{ color: "var(--text-muted)" }} />
        )}
      </button>

      {open && (
        <div
          style={{
            padding: "0 16px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          {/* Historical Evidence Narrative Banner */}
          <div
            style={{
              backgroundColor: "rgba(0, 242, 254, 0.05)",
              border: "1px solid rgba(0, 242, 254, 0.15)",
              borderRadius: "8px",
              padding: "10px 14px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              fontSize: "11px",
              color: "var(--text-primary)",
            }}
          >
            <History size={16} style={{ color: "var(--accent-teal)", flexShrink: 0 }} />
            <div>
              <strong>Historical Evidence:</strong> On <strong>{total_setups}</strong> historical sessions matching today's macro regime for {symbol}, {distribution[0]?.n_filled || 0} reached market entry ({distribution[0]?.n_wins || 0} won = {( (distribution[0]?.conditional_win_prob || 0) * 100).toFixed(0)}%). As price retraced deeper, historical fill counts and success rates varied across entry levels below:
            </div>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <ProfileCard
              profile={profiles.aggressive}
              isOptimal={false}
              showAdvanced={showAdvanced}
            />
            <ProfileCard
              profile={profiles.optimal}
              isOptimal={true}
              showAdvanced={showAdvanced}
            />
            <ProfileCard
              profile={profiles.conservative}
              isOptimal={false}
              showAdvanced={showAdvanced}
            />
          </div>

          <div
            style={{
              backgroundColor: "rgba(0,0,0,0.3)",
              borderRadius: "8px",
              border: "1px solid var(--border-color)",
              padding: "12px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "8px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: 800,
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <TrendingUp size={13} style={{ color: "#00f2fe" }} />
                Empirical Retracement & Win Rate Breakdown
              </div>
              <button
                onClick={() => setShowAdvanced((a) => !a)}
                style={{
                  background: "none",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "4px",
                  padding: "2px 8px",
                  cursor: "pointer",
                  fontSize: "9px",
                  color: "var(--text-muted)",
                  fontWeight: 700,
                }}
              >
                {showAdvanced ? "Hide" : "Advanced"} Metrics
              </button>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: showAdvanced
                  ? "52px 1fr 65px 75px 22px 46px 50px"
                  : "52px 1fr 65px 75px 22px",
                gap: "4px",
                fontSize: "9px",
                color: "var(--text-muted)",
                fontWeight: 700,
                textTransform: "uppercase",
                marginBottom: "6px",
                padding: "0 4px",
              }}
            >
              <span>Depth</span>
              <span>Retracement</span>
              <span style={{ textAlign: "right" }}>Reached (N)</span>
              <span style={{ textAlign: "right" }}>Won / Reached</span>
              <span style={{ textAlign: "center" }}>Rtg</span>
              {showAdvanced && (
                <>
                  <span style={{ textAlign: "right" }}>RR+</span>
                  <span style={{ textAlign: "right" }}>EV</span>
                </>
              )}
            </div>

            {distribution.map((step) => (
              <WaterfallRow
                key={step.pips_below}
                step={step}
                isOptimal={step.pips_below === optPips}
                showAdvanced={showAdvanced}
              />
            ))}

            <div
              style={{
                fontSize: "9px",
                color: "var(--text-muted)",
                marginTop: "8px",
                lineHeight: 1.5,
              }}
            >
              <strong>Reached (N)</strong> = count & % of historical sessions that retraced to this depth.{" "}
              <strong>Won / Reached</strong> = count & % of those retraced sessions that resulted in a winning trade.
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
            <button
              onClick={() => setShowMethodology((m) => !m)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
                color: "var(--text-muted)",
                flexShrink: 0,
                marginTop: "1px",
              }}
            >
              <Info size={12} />
            </button>
            {showMethodology ? (
              <div
                style={{
                  fontSize: "10px",
                  color: "var(--text-muted)",
                  lineHeight: 1.6,
                }}
              >
                <strong style={{ color: "var(--text-secondary)" }}>
                  Methodology:
                </strong>{" "}
                {methodology_note}
              </div>
            ) : (
              <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                <span
                  style={{ textDecoration: "underline", cursor: "pointer" }}
                  onClick={() => setShowMethodology(true)}
                >
                  How is this calculated?
                </span>{" "}
                \u2014 Pure empirical calculation from {total_setups} comparable historical sessions
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
