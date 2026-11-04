// ─────────────────────────────────────────────────────────────
// PrimeEdge Video Engine · Font Utilities
// ─────────────────────────────────────────────────────────────
import { continueRender, delayRender } from "remotion";

/**
 * Primary font stack used across all PrimeEdge compositions.
 * Inter is loaded via Google Fonts CSS; falls back to system UI fonts.
 */
export const FONT_FAMILY = "'Inter', 'SF Pro Display', 'Segoe UI', system-ui, sans-serif";

/**
 * Mono stack for numeric readouts and ticker symbols.
 */
export const FONT_MONO = "'JetBrains Mono', 'Fira Code', 'Consolas', monospace";

/**
 * Call this once at the top of a composition to load Inter from Google Fonts.
 * Returns a cleanup function (not strictly needed for Remotion, but harmless).
 *
 * Usage:
 *   const fontHandle = delayRender("Loading fonts");
 *   loadGoogleFonts().then(() => continueRender(fontHandle));
 */
export function loadGoogleFonts(): Promise<void> {
  return new Promise((resolve) => {
    if (typeof document === "undefined") {
      resolve();
      return;
    }
    const id = "primeedge-google-fonts";
    if (document.getElementById(id)) {
      resolve();
      return;
    }
    const link = document.createElement("link");
    link.id = id;
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap";
    link.onload = () => resolve();
    link.onerror = () => resolve(); // non-fatal — system fallback kicks in
    document.head.appendChild(link);
  });
}

/**
 * Hook that triggers font loading and returns when fonts are ready.
 * Use inside a React component inside useEffect.
 */
export function useFonts(): void {
  // Remotion renders in a headless Chrome — we use delayRender / continueRender
  // to pause rendering until the font link is parsed.
  // This is called once per composition mount.
  const handle = delayRender("Loading PrimeEdge fonts");
  loadGoogleFonts().then(() => continueRender(handle));
}
