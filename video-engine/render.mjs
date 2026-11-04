#!/usr/bin/env node
/**
 * PrimeEdge Remotion Render CLI
 * Usage:
 *   node render.mjs --composition SignalCard --props '{"instrument":"XAUUSD",...}' --output /tmp/out.mp4
 *   node render.mjs --composition WeeklyWrapped --props '{...}' --output /tmp/wrapped.mp4
 *   node render.mjs --composition MacroDaily --props '{...}' --output /tmp/macro.mp4
 */

import { renderMedia, selectComposition } from '@remotion/renderer';
import { bundle } from '@remotion/bundler';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import os from 'os';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── Parse CLI args ───────────────────────────────────────────────
const args = process.argv.slice(2);
const getArg = (flag) => {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : null;
};

const composition = getArg('--composition');
const propsRaw    = getArg('--props');
const outputPath  = getArg('--output');

if (!composition || !outputPath) {
  console.error('Usage: node render.mjs --composition <name> --props <json> --output <path>');
  process.exit(1);
}

let inputProps = {};
if (propsRaw) {
  try {
    inputProps = JSON.parse(propsRaw);
  } catch (e) {
    console.error('Invalid JSON in --props:', e.message);
    process.exit(1);
  }
}

// ── Default props per composition ───────────────────────────────
const DEFAULTS = {
  SignalCard: {
    instrument: 'XAUUSD',
    direction: 'LONG',
    status_state: 'READY',
    why_this_now: 'MSS confirmed above 1-hour structure with DXY weakness aligning.',
    evidence_strength: 'Strong',
    mss_score: 0.82,
    current_regime: 'RISK_ON | DXY_WEAK',
    continuation_probability: 0.74,
    best_session: 'London',
    historical_sample_size: 147,
    acceptable_corridor: { p25_price: 2318.5, p75_price: 2321.0, p90_invalidation: 2315.0 },
    preferred_zone: { low: 2318.5, high: 2320.0 },
    mae_data: { p25_pips: 8, p50_pips: 14, p75_pips: 22, p90_pips: 31 },
    trade_thesis: 'Gold bullish continuation on DXY weakness. MSS confirmed.',
  },
  WeeklyWrapped: {
    user_name: 'Trader',
    week_label: 'Week 44 · Oct 2026',
    total_setups: 23,
    setups_taken: 7,
    win_rate: 0.71,
    avg_r_multiple: 1.4,
    total_pnl_pips: 87.5,
    best_trade: { instrument: 'XAUUSD', pnl_pips: 42.0, direction: 'LONG' },
    instruments_traded: ['XAUUSD', 'GBPUSD', 'EURUSD'],
    mae_discipline: 0.84,
  },
  MacroDaily: {
    date_label: new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }),
    dxy_level: 104.32,
    dxy_change_pct: -0.34,
    vix_level: 18.4,
    vix_change_pct: -1.2,
    risk_sentiment: 'RISK_ON',
    macro_headline: 'Dollar weakness persists as Fed signals rate pause. Risk assets bid, gold supported above 2300. London session shows momentum.',
    key_instruments: [
      { symbol: 'XAUUSD', status: 'READY',   direction: 'LONG',  mss_score: 0.82 },
      { symbol: 'GBPUSD', status: 'WAIT',    direction: 'LONG',  mss_score: 0.61 },
      { symbol: 'EURUSD', status: 'READY',   direction: 'LONG',  mss_score: 0.74 },
      { symbol: 'USDJPY', status: 'INVALID', direction: 'SHORT', mss_score: 0.38 },
      { symbol: 'AUDUSD', status: 'WAIT',    direction: 'LONG',  mss_score: 0.55 },
    ],
    session_open: 'London',
  },
  MarketingHero: {},
  MarketingV2: {},
  MarketingHybrid: {},
  MarketingHybridVertical: {},
};

// Merge defaults with provided props
const finalProps = { ...DEFAULTS[composition], ...inputProps };

// ── Ensure output directory exists ──────────────────────────────
const outDir = path.dirname(outputPath);
fs.mkdirSync(outDir, { recursive: true });

// ── Bundle ──────────────────────────────────────────────────────
console.log(`[PrimeEdge Video] Bundling ${composition}...`);
const bundleLocation = await bundle({
  entryPoint: path.resolve(__dirname, 'src/index.ts'),
  publicDir: path.resolve(__dirname, 'public'),
  onProgress: (p) => process.stdout.write(`\r  Bundle: ${p}%   `),
});
console.log('\n[PrimeEdge Video] Bundle complete.');

// ── Select composition ───────────────────────────────────────────
const comp = await selectComposition({
  serveUrl: bundleLocation,
  id: composition,
  inputProps: finalProps,
});

// ── Render ───────────────────────────────────────────────────────
console.log(`[PrimeEdge Video] Rendering ${composition} → ${outputPath}`);
await renderMedia({
  composition: comp,
  serveUrl: bundleLocation,
  codec: 'h264',
  audioCodec: 'aac',
  outputLocation: outputPath,
  inputProps: finalProps,
  onProgress: ({ progress }) => {
    process.stdout.write(`\r  Render: ${Math.round(progress * 100)}%   `);
  },
  chromiumOptions: {
    disableWebSecurity: true,
  },
  concurrency: 2,
});

console.log(`\n[PrimeEdge Video] Done! → ${outputPath}`);
const stat = fs.statSync(outputPath);
console.log(`[PrimeEdge Video] File size: ${(stat.size / 1024 / 1024).toFixed(2)} MB`);
