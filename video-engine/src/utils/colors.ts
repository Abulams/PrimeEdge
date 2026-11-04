// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · Color System
// ─────────────────────────────────────────────────────────────

export const COLORS = {
  bg: "#0A0E1A",
  bgCard: "#111827",
  bgAccent: "#1E2A3B",
  green: "#00C896",
  red: "#FF3B5C",
  amber: "#F59E0B",
  blue: "#3B82F6",
  textPrimary: "#F9FAFB",
  textSecondary: "#9CA3AF",
  textMuted: "#4B5563",
  gold: "#F6C90E",
  border: "#1F2937",
  gridLine: "rgba(255,255,255,0.04)",
  greenGlow: "rgba(0,200,150,0.25)",
  redGlow: "rgba(255,59,92,0.25)",
  amberGlow: "rgba(245,158,11,0.25)",
} as const;

export type ColorKey = keyof typeof COLORS;

/** Returns the correct accent color for a given signal status. */
export const statusColor = (status: string): string => {
  switch (status.toUpperCase()) {
    case "READY":
      return COLORS.green;
    case "WAIT":
      return COLORS.amber;
    case "INVALID":
    case "NO EDGE":
    case "NO SETUP":
      return COLORS.red;
    default:
      return COLORS.textSecondary;
  }
};

/** Returns LONG=green, SHORT=red. */
export const directionColor = (direction: string): string =>
  direction.toUpperCase() === "LONG" ? COLORS.green : COLORS.red;

/** Returns regime-appropriate accent color. */
export const regimeColor = (regime: string): string => {
  const upper = regime.toUpperCase();
  if (upper.includes("RISK_ON")) return COLORS.green;
  if (upper.includes("RISK_OFF")) return COLORS.red;
  return COLORS.amber;
};

/** Glow shadow string for a status. */
export const statusGlow = (status: string): string => {
  const c = statusColor(status);
  return `0 0 24px ${c}88, 0 0 48px ${c}44`;
};

/** Evidence badge color. */
export const evidenceColor = (strength: string): string => {
  switch (strength.toLowerCase()) {
    case "strong":
      return COLORS.green;
    case "moderate":
      return COLORS.amber;
    case "weak":
      return COLORS.red;
    default:
      return COLORS.textSecondary;
  }
};
