import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CandlestickSeries, LineSeries, BaselineSeries, ColorType, CrosshairMode, LineStyle, PriceScaleMode } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { Activity, Eye, EyeOff, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Target, Clock, Zap } from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────────────
interface ChartOverlayData {
  symbol: string;
  trend: string;
  timeframe: string;
  candles: { time: number; open: number; high: number; low: number; close: number }[];
  mae_cloud: {
    mae_25_price?: number;
    mae_50_price: number;
    mae_75_price?: number;
    mae_90_price: number;
    mae_25_pips?: number;
    mae_50_pips: number;
    mae_75_pips?: number;
    mae_90_pips: number;
    setup_ref_price?: number;
    label_50: string;
    label_75?: string;
    label_90: string;
  };
  mfe_cloud: {
    mfe_50_price?: number;
    mfe_75_price?: number;
    mfe_90_price?: number;
    mfe_avg_price?: number;
    mfe_max_price?: number;
    mfe_50_pips?: number;
    mfe_75_pips?: number;
    mfe_90_pips?: number;
    mfe_avg_pips?: number;
    mfe_max_pips?: number;
    label_50?: string;
    label_75?: string;
    label_90?: string;
    label_avg?: string;
    label_max?: string;
  };
  execution_zones: {
    best: { start_hour: number; end_hour: number; label: string; session: string };
    worst: { start_hour: number; end_hour: number; label: string; session: string };
  };
  historical_ghosts: Array<{
    date: string;
    outcome: string;
    mae_pips: number;
    mfe_pips: number;
    session: string;
    trend: string;
    path: Array<{ day_offset: number; price: number; offset_pips: number }>;
  }>;
  trade_health: {
    status: string;
    label: string;
    color: string;
    current_price: number;
    trend: string;
    win_rate: number;
    sample_size: number;
  };
  entry_zone?: {
    distribution: Array<{
      pips_below: number;
      fill_probability: number;
      n_filled: number;
      conditional_win_prob: number;
      new_rr: number;
      new_risk: number;
      new_reward: number;
      expected_ev: number;
      ev_quality: string;
      price_level: number;
    }>;
    total_setups: number;
    profiles: {
      aggressive: { pips_below: number; fill_probability: number; conditional_win_prob: number; new_rr: number; expected_ev: number; ev_quality: string; label: string; description: string; color: string; price_level: number };
      optimal: { pips_below: number; fill_probability: number; conditional_win_prob: number; new_rr: number; expected_ev: number; ev_quality: string; label: string; description: string; color: string; price_level: number };
      conservative: { pips_below: number; fill_probability: number; conditional_win_prob: number; new_rr: number; expected_ev: number; ev_quality: string; label: string; description: string; color: string; price_level: number };
    };
    best_ev_entry: { pips_below: number; expected_ev: number; conditional_win_prob: number; new_rr: number; price_level: number; fill_probability: number; ev_quality: string };
    methodology_note: string;
    current_price: number;
    trend: string;
    regime_risk_pips: number;
    regime_reward_pips: number;
  };
  empirical_metadata?: {
    model_type: string;
    timeframe: string;
    sample_size: number;
    confidence_interval: string;
    percentiles: string[];
  };
}

interface OverlayToggles {
  maeCloud: boolean;
  mfeCloud: boolean;
  sessionZones: boolean;
  ghosts: boolean;
  healthHUD: boolean;
}

interface MSDTradingViewChartProps {
  symbol: string;
  onSymbolChange?: (symbol: string) => void;
  onDataLoaded?: (data: ChartOverlayData) => void;
}

const INSTRUMENTS = ['GBPUSD', 'EURUSD', 'XAUUSD', 'AUDUSD', 'USDJPY', 'US100', 'AUDJPY'];
const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

// ─── Helpers ────────────────────────────────────────────────────────────────
function healthColor(status: string) {
  switch (status) {
    case 'PROFIT_ZONE': return { bg: 'rgba(16,185,129,0.15)', border: '#10b981', text: '#10b981', icon: '🚀' };
    case 'HEALTHY': return { bg: 'rgba(0,242,254,0.12)', border: '#00f2fe', text: '#00f2fe', icon: '✅' };
    case 'DRAWDOWN_WARNING': return { bg: 'rgba(245,158,11,0.15)', border: '#f59e0b', text: '#f59e0b', icon: '⚠️' };
    case 'CRITICAL': return { bg: 'rgba(239,68,68,0.15)', border: '#ef4444', text: '#ef4444', icon: '🔴' };
    default: return { bg: 'rgba(100,116,139,0.15)', border: '#64748b', text: '#94a3b8', icon: '⚪' };
  }
}

// ─── Main Component ──────────────────────────────────────────────────────────
export type { ChartOverlayData };
export default function MSDTradingViewChart({ symbol, onSymbolChange, onDataLoaded }: MSDTradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const ghostSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const overlayLinesRef = useRef<any[]>([]);

  // Store callback in a ref so it never enters the useCallback dependency array
  // (avoids infinite re-render loop when parent passes an inline function)
  const onDataLoadedRef = useRef(onDataLoaded);
  useEffect(() => { onDataLoadedRef.current = onDataLoaded; }, [onDataLoaded]);

  const [data, setData] = useState<ChartOverlayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSymbol, setActiveSymbol] = useState(symbol);
  const [timeframe, setTimeframe] = useState<string>('1d');
  const [overlays, setOverlays] = useState<OverlayToggles>({
    maeCloud: false,
    mfeCloud: false,
    sessionZones: false,
    ghosts: false,
    healthHUD: true,
  });

  // Keep activeSymbol in sync with parent prop
  useEffect(() => {
    if (symbol) {
      setActiveSymbol(symbol);
    }
  }, [symbol]);

  // ── Fetch overlay data from backend ───────────────────────────────────────
  const fetchData = useCallback(async (sym: string, tf: string = '1d') => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/chart/${sym}/overlays?timeframe=${tf}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: ChartOverlayData = await res.json();
      setData(json);
      onDataLoadedRef.current?.(json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load chart data');
    } finally {
      setLoading(false);
    }
  }, []); // stable — callback accessed via ref, not closure


  useEffect(() => {
    fetchData(activeSymbol, timeframe);
    const interval = setInterval(() => fetchData(activeSymbol, timeframe), 60000);
    return () => clearInterval(interval);
  }, [activeSymbol, timeframe, fetchData]);

  // ── Build / rebuild chart when data changes ───────────────────────────────
  useEffect(() => {
    if (!chartContainerRef.current || !data) return;

    // Destroy previous chart instance
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      ghostSeriesRefs.current = [];
      overlayLinesRef.current = [];
    }

    const container = chartContainerRef.current;
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#0d1117' },
        textColor: '#94a3b8',
        fontFamily: "'Inter', 'DM Sans', sans-serif",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.03)', style: LineStyle.Dotted },
        horzLines: { color: 'rgba(255,255,255,0.05)', style: LineStyle.Dotted },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(0,242,254,0.4)', style: LineStyle.Dashed, labelBackgroundColor: '#0d1117' },
        horzLine: { color: 'rgba(0,242,254,0.4)', style: LineStyle.Dashed, labelBackgroundColor: '#0d1117' },
      },
      rightPriceScale: {
        mode: PriceScaleMode.Normal,
        borderColor: 'rgba(255,255,255,0.08)',
        textColor: '#64748b',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.08)',
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
      },
      width: container.clientWidth,
      height: 460,
    });

    chartRef.current = chart;

    // ── Candlestick Series ─────────────────────────────────────────────────
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    const candleData: CandlestickData[] = data.candles.map(c => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));
    candleSeries.setData(candleData);
    candleSeriesRef.current = candleSeries;

    const lastTime = data.candles[data.candles.length - 1].time as Time;
    const firstTime = data.candles[0].time as Time;

    // ── 1. Shaded Entry Zone Band (Point A to Point B) ─────────────────────────
    const p25Price = data.mae_cloud.mae_25_price ?? data.mae_cloud.setup_ref_price ?? data.mae_cloud.mae_50_price;
    const p75Price = data.mae_cloud.mae_75_price ?? data.mae_cloud.mae_90_price;

    const entryZoneBand = chart.addSeries(BaselineSeries, {
      baseValue: { type: 'price', price: p75Price },
      topFillColor1: 'rgba(0, 210, 255, 0.45)',
      topFillColor2: 'rgba(0, 210, 255, 0.12)',
      topLineColor: '#00d2ff',
      bottomFillColor1: 'rgba(0, 210, 255, 0.12)',
      bottomFillColor2: 'rgba(0, 210, 255, 0.45)',
      bottomLineColor: '#00d2ff',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      title: `Shaded Entry Zone (P25–P75 MAE: ${data.mae_cloud.mae_25_pips ?? 0}p–${data.mae_cloud.mae_75_pips ?? data.mae_cloud.mae_90_pips}p)`,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    entryZoneBand.setData([
      { time: firstTime, value: p25Price },
      { time: lastTime, value: p25Price },
    ]);
    overlayLinesRef.current.push(entryZoneBand);

    // ── 2. Invalidation Stop Boundary Line (P90 MAE - Solid Red) ───────────────────
    const mae90Line = chart.addSeries(LineSeries, {
      color: '#ef4444',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      title: `P90 Invalidation Stop (${data.mae_cloud.mae_90_pips}p)`,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    mae90Line.setData([
      { time: firstTime, value: data.mae_cloud.mae_90_price },
      { time: lastTime, value: data.mae_cloud.mae_90_price },
    ]);
    overlayLinesRef.current.push(mae90Line);

    // ── 3. Target Line (P50 MFE - Solid Green) ────────────────────────────────────
    const mfe50Price = data.mfe_cloud.mfe_50_price ?? data.mfe_cloud.mfe_avg_price ?? 0;
    const mfe50Pips = data.mfe_cloud.mfe_50_pips ?? data.mfe_cloud.mfe_avg_pips ?? 0;
    const mfe50Line = chart.addSeries(LineSeries, {
      color: '#10b981',
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      title: `P50 Target (${mfe50Pips}p)`,
      priceLineVisible: false,
      lastValueVisible: true,
    });
    mfe50Line.setData([
      { time: firstTime, value: mfe50Price },
      { time: lastTime, value: mfe50Price },
    ]);
    overlayLinesRef.current.push(mfe50Line);

    // ── Historical Ghost Lines ─────────────────────────────────────────────
    if (overlays.ghosts && data.historical_ghosts.length > 0) {
      data.historical_ghosts.forEach((ghost, idx) => {
        if (ghost.path.length < 2) return;
        const isWin = ghost.outcome === 'WIN';
        const ghostColor = isWin
          ? `rgba(16,185,129,${0.35 - idx * 0.05})`
          : `rgba(239,68,68,${0.3 - idx * 0.04})`;

        const ghostSeries = chart.addSeries(LineSeries, {
          color: ghostColor,
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          title: '', // Keep clean - no ghost badges on right price scale!
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });

        // Map ghost path relative to current last candle price
        const anchorPrice = data.candles[data.candles.length - 1].close;
        const anchorTime = data.candles[data.candles.length - 1].time;
        const dayMs = 86400;

        const ghostPoints = ghost.path.map((pt, i) => ({
          time: (anchorTime + i * dayMs) as Time,
          value: anchorPrice + pt.offset_pips * (activeSymbol.includes('JPY') ? 0.01 : activeSymbol.includes('XAU') ? 0.1 : 0.0001),
        }));

        ghostSeries.setData(ghostPoints);
        ghostSeriesRefs.current.push(ghostSeries);
      });
    }

    // ── Fit content ────────────────────────────────────────────────────────
    chart.timeScale().fitContent();

    // ── Resize observer ────────────────────────────────────────────────────
    const observer = new ResizeObserver(entries => {
      if (entries[0] && chartRef.current) {
        chartRef.current.applyOptions({ width: entries[0].contentRect.width });
      }
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, overlays, activeSymbol]);

  // ── Overlay toggle ─────────────────────────────────────────────────────────
  const toggleOverlay = (key: keyof OverlayToggles) =>
    setOverlays(prev => ({ ...prev, [key]: !prev[key] }));

  const handleSymbolChange = (sym: string) => {
    setActiveSymbol(sym);
    onSymbolChange?.(sym);
  };

  // ── Trade Health HUD ───────────────────────────────────────────────────────
  const health = data?.trade_health;
  const hColors = health ? healthColor(health.status) : healthColor('');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0', width: '100%' }}>

      {/* ── Header Bar ───────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '14px 20px',
        background: 'linear-gradient(135deg, rgba(13,17,23,0.95) 0%, rgba(21,28,39,0.98) 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.07)',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        {/* Symbol Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity size={16} style={{ color: '#00f2fe' }} />
          <span style={{ fontWeight: 700, fontSize: '15px', color: '#fff' }}>MSD Chart</span>
          <div style={{ display: 'flex', gap: '6px' }}>
            {INSTRUMENTS.map(inst => (
              <button
                key={inst}
                onClick={() => handleSymbolChange(inst)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  border: '1px solid',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  borderColor: activeSymbol === inst ? '#00f2fe' : 'rgba(255,255,255,0.1)',
                  backgroundColor: activeSymbol === inst ? 'rgba(0,242,254,0.12)' : 'transparent',
                  color: activeSymbol === inst ? '#00f2fe' : '#64748b',
                }}
              >
                {inst}
              </button>
            ))}
          </div>

          <div style={{ width: '1px', height: '18px', backgroundColor: 'rgba(255,255,255,0.1)', margin: '0 4px' }} />

          {/* Timeframe Selector */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {[
              { id: '5m', label: '5M' },
              { id: '15m', label: '15M' },
              { id: '1h', label: '1H' },
              { id: '4h', label: '4H' },
              { id: '1d', label: '1D' },
            ].map(tf => (
              <button
                key={tf.id}
                onClick={() => setTimeframe(tf.id)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 800,
                  border: '1px solid',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  borderColor: timeframe === tf.id ? 'var(--accent-teal)' : 'rgba(255,255,255,0.08)',
                  backgroundColor: timeframe === tf.id ? 'rgba(0, 242, 254, 0.15)' : 'transparent',
                  color: timeframe === tf.id ? 'var(--accent-teal)' : '#64748b',
                }}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>

        {/* Overlay Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { key: 'sessionZones' as keyof OverlayToggles, label: 'Sessions', color: '#38bdf8' },
            { key: 'ghosts' as keyof OverlayToggles, label: 'Ghosts', color: '#a855f7' },
            { key: 'healthHUD' as keyof OverlayToggles, label: 'Health HUD', color: '#f59e0b' },
          ].map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => toggleOverlay(key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 600,
                border: '1px solid',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                borderColor: overlays[key] ? color : 'rgba(255,255,255,0.08)',
                backgroundColor: overlays[key] ? `${color}18` : 'transparent',
                color: overlays[key] ? color : '#475569',
              }}
            >
              {overlays[key] ? <Eye size={11} /> : <EyeOff size={11} />}
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Trade Health HUD ───────────────────────────────────────────────── */}
      {overlays.healthHUD && health && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 20px',
          background: hColors.bg,
          borderBottom: `1px solid ${hColors.border}30`,
          flexWrap: 'wrap',
          gap: '12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px' }}>{hColors.icon}</span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: hColors.text }}>
                {health.label}
              </span>
              <span style={{
                padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700,
                backgroundColor: `${hColors.border}22`, color: hColors.text, border: `1px solid ${hColors.border}40`
              }}>
                {health.status.replace('_', ' ')}
              </span>
            </div>

            <div style={{ width: '1px', height: '20px', backgroundColor: 'rgba(255,255,255,0.1)' }} />

            <div style={{ display: 'flex', gap: '18px', fontSize: '12px', color: '#94a3b8' }}>
              <span>
                Price: <strong style={{ color: '#fff' }}>{health.current_price.toFixed(activeSymbol.includes('JPY') ? 3 : activeSymbol.includes('XAU') ? 2 : 5)}</strong>
              </span>
              <span>
                Trend: <strong style={{ color: health.trend === 'BULLISH' ? '#10b981' : '#ef4444' }}>
                  {health.trend === 'BULLISH' ? '▲' : '▼'} {health.trend}
                </strong>
              </span>
              <span>
                Win Rate: <strong style={{ color: health.win_rate >= 65 ? '#10b981' : health.win_rate >= 50 ? '#f59e0b' : '#ef4444' }}>
                  {health.win_rate.toFixed(1)}%
                </strong>
              </span>
              <span>
                N: <strong style={{ color: '#fff' }}>{health.sample_size}</strong> signatures
              </span>
            </div>
          </div>

          {/* MAE/MFE quick stats */}
          {data && (
            <div style={{ display: 'flex', gap: '16px', fontSize: '11px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#ef4444', fontWeight: 700 }}>MAE 50th</div>
                <div style={{ color: '#fff', fontFamily: 'monospace' }}>{data.mae_cloud.mae_50_pips}p</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#ef4444', fontWeight: 700 }}>MAE 90th</div>
                <div style={{ color: '#fff', fontFamily: 'monospace' }}>{data.mae_cloud.mae_90_pips}p</div>
              </div>
              <div style={{ width: '1px', backgroundColor: 'rgba(255,255,255,0.1)' }} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#00f2fe', fontWeight: 700 }}>MFE P50</div>
                <div style={{ color: '#fff', fontFamily: 'monospace' }}>
                  {data.mfe_cloud.mfe_50_pips ?? data.mfe_cloud.mfe_avg_pips ?? '—'}p
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ color: '#10b981', fontWeight: 700 }}>MFE P90</div>
                <div style={{ color: '#fff', fontFamily: 'monospace' }}>
                  {data.mfe_cloud.mfe_90_pips ?? data.mfe_cloud.mfe_max_pips ?? '—'}p
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Chart Canvas & Legend ── */}
      <div style={{ position: 'relative', background: '#0d1117' }}>
        <div style={{
          position: 'absolute',
          top: '12px',
          left: '14px',
          zIndex: 10,
          display: 'flex',
          gap: '12px',
          padding: '6px 12px',
          borderRadius: '6px',
          background: 'rgba(13,17,23,0.85)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(4px)',
          fontSize: '11px',
          fontWeight: 600
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#00f2fe' }}>
            <div style={{ width: '14px', height: '8px', borderRadius: '2px', backgroundColor: 'rgba(0,242,254,0.25)', border: '1px solid #00f2fe' }} />
            <span>Entry Zone (P25–P75 MAE)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#ef4444' }}>
            <div style={{ width: '14px', height: '2px', backgroundColor: '#ef4444' }} />
            <span>P90 Invalidation Stop</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#10b981' }}>
            <div style={{ width: '14px', height: '2px', backgroundColor: '#10b981' }} />
            <span>P50 MFE Target</span>
          </div>
        </div>

        {loading && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(13,17,23,0.85)', backdropFilter: 'blur(4px)',
          }}>
            <div style={{ textAlign: 'center', color: '#64748b' }}>
              <div style={{ width: '36px', height: '36px', border: '3px solid rgba(0,242,254,0.2)', borderTopColor: '#00f2fe', borderRadius: '50%', margin: '0 auto 12px', animation: 'spin 0.8s linear infinite' }} />
              <div style={{ fontSize: '13px' }}>Loading MSD chart overlays...</div>
            </div>
          </div>
        )}
        {error && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 10,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(13,17,23,0.9)',
          }}>
            <div style={{ textAlign: 'center', color: '#ef4444', padding: '24px' }}>
              <AlertTriangle size={32} style={{ margin: '0 auto 12px' }} />
              <div style={{ fontSize: '14px', fontWeight: 600 }}>Failed to load chart data</div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '6px' }}>{error}</div>
              <button
                onClick={() => fetchData(activeSymbol)}
                style={{ marginTop: '16px', padding: '8px 20px', borderRadius: '8px', background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
              >
                Retry
              </button>
            </div>
          </div>
        )}
        <div ref={chartContainerRef} style={{ width: '100%', height: '460px' }} />
      </div>

      {/* ── Session Execution Zones Legend ───────────────────────────────── */}
      {overlays.sessionZones && data && (
        <div style={{
          display: 'flex',
          gap: '16px',
          padding: '12px 20px',
          background: 'rgba(13,17,23,0.6)',
          borderTop: '1px solid rgba(255,255,255,0.06)',
          flexWrap: 'wrap',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#94a3b8' }}>
            <Clock size={12} style={{ color: '#94a3b8' }} />
            <span style={{ fontWeight: 600, color: '#64748b', textTransform: 'uppercase', fontSize: '10px' }}>Execution Corridors</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: 'rgba(56,189,248,0.4)', border: '1px solid #38bdf8' }} />
            <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 600 }}>
              ✅ BEST: {data.execution_zones.best.session} ({data.execution_zones.best.start_hour}:00–{data.execution_zones.best.end_hour}:00 UTC)
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: 'rgba(239,68,68,0.3)', border: '1px solid rgba(239,68,68,0.5)' }} />
            <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 600 }}>
              ❌ AVOID: {data.execution_zones.worst.session} ({data.execution_zones.worst.start_hour}:00–{data.execution_zones.worst.end_hour}:00 UTC)
            </span>
          </div>

          <div style={{ marginLeft: 'auto', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: '#94a3b8' }}>
              <div style={{ width: '24px', height: '2px', background: 'repeating-linear-gradient(90deg, #ef4444 0px, #ef4444 4px, transparent 4px, transparent 8px)' }} />
              <span>MAE Stop Zones</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: '#94a3b8' }}>
              <div style={{ width: '24px', height: '2px', background: 'repeating-linear-gradient(90deg, #10b981 0px, #10b981 4px, transparent 4px, transparent 8px)' }} />
              <span>MFE Target Zones</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', color: '#94a3b8' }}>
              <div style={{ width: '24px', height: '2px', background: 'repeating-linear-gradient(90deg, #a855f7 0px, #a855f7 2px, transparent 2px, transparent 5px)' }} />
              <span>Historical Ghosts</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Ghost Signatures Info ─────────────────────────────────────────── */}
      {overlays.ghosts && data && data.historical_ghosts.length > 0 && (
        <div style={{
          padding: '12px 20px',
          background: 'rgba(13,17,23,0.5)',
          borderTop: '1px solid rgba(255,255,255,0.05)',
        }}>
          <div style={{ fontSize: '10px', color: '#475569', textTransform: 'uppercase', fontWeight: 700, marginBottom: '8px', letterSpacing: '0.05em' }}>
            Historical Ghost Trajectories — Top Similar MSD Matches
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {data.historical_ghosts.map((ghost, idx) => (
              <div key={idx} style={{
                padding: '8px 12px',
                borderRadius: '8px',
                backgroundColor: ghost.outcome === 'WIN' ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                border: `1px solid ${ghost.outcome === 'WIN' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
                fontSize: '11px',
                minWidth: '140px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'monospace', color: '#94a3b8', fontSize: '10px' }}>{ghost.date}</span>
                  <span style={{
                    padding: '1px 6px', borderRadius: '3px', fontSize: '9px', fontWeight: 700,
                    backgroundColor: ghost.outcome === 'WIN' ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
                    color: ghost.outcome === 'WIN' ? '#10b981' : '#ef4444',
                  }}>
                    {ghost.outcome}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <span style={{ color: '#ef4444', fontSize: '10px' }}>MAE: {ghost.mae_pips}p</span>
                  <span style={{ color: '#10b981', fontSize: '10px' }}>MFE: {ghost.mfe_pips}p</span>
                </div>
                <div style={{ color: '#475569', fontSize: '10px', marginTop: '2px' }}>{ghost.session} · {ghost.trend}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Spinner animation style */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
