import React, { useState, useEffect } from 'react';
import {
  BookOpen, Activity, CheckCircle, AlertTriangle, ShieldCheck,
  TrendingUp, TrendingDown, Clock, Target, Layers, ArrowRight, X, AlertCircle
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

interface TradeRecord {
  id: number;
  setup_snapshot_id: number;
  lifecycle_state: string;
  decision_at?: string;
  decision_type?: string;
  actual_entry?: number;
  entry_timestamp?: string;
  entry_type?: string;
  entry_in_corridor?: string;
  entry_deviation_pips?: number;
  actual_sl?: number;
  actual_tp?: number;
  system_suggested_sl?: number;
  system_suggested_tp?: number;
  sl_deviation_pips?: number;
  tp_deviation_pips?: number;
  position_size_lots?: number;
  max_mae_pips?: number;
  max_mfe_pips?: number;
  mae_p25_reached?: number;
  mae_p50_reached?: number;
  mae_p75_reached?: number;
  mae_p90_reached?: number;
  mfe_p25_reached?: number;
  mfe_p50_reached?: number;
  mfe_p75_reached?: number;
  mfe_p90_reached?: number;
  exit_price?: number;
  exit_timestamp?: string;
  exit_reason?: string;
  outcome?: string;
  pnl_pips?: number;
  pnl_r?: number;
  setup_outcome?: string;
  execution_outcome?: string;
  notes?: string;
  setup?: {
    instrument: string;
    direction: string;
    trend: string;
    status_at_snapshot: string;
    setup_ref_price: number;
    mae_p25_pips?: number;
    mae_p50_pips?: number;
    mae_p75_pips?: number;
    mae_p90_pips?: number;
    mfe_p50_pips?: number;
    mfe_p75_pips?: number;
    mfe_p90_pips?: number;
    corridor_p25_price?: number;
    corridor_p75_price?: number;
    p90_invalidation?: number;
    historical_n?: number;
    continuation_prob?: number;
    confidence_score?: number;
  };
}

interface PerformanceSummary {
  total_trades_logged: number;
  total_passed_setups: number;
  trader_win_rate: number;
  setup_success_rate: number;
  average_r_multiple: number;
  average_mae_endured_pips: number;
  average_mfe_captured_pips: number;
  avoidable_losses_from_poor_execution: number;
  win_count: number;
  loss_count: number;
}

export function AutoJournalTab() {
  const [subTab, setSubTab] = useState<'today' | 'history' | 'performance' | 'passed'>('today');
  const [activeTrades, setActiveTrades] = useState<TradeRecord[]>([]);
  const [historyTrades, setHistoryTrades] = useState<TradeRecord[]>([]);
  const [passedTrades, setPassedTrades] = useState<TradeRecord[]>([]);
  const [performance, setPerformance] = useState<PerformanceSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Close Trade Modal State
  const [closeTradeId, setCloseTradeId] = useState<number | null>(null);
  const [closeExitPrice, setCloseExitPrice] = useState<string>('');
  const [closeReason, setCloseReason] = useState<string>('MANUAL');

  const fetchJournalData = async () => {
    setLoading(true);
    try {
      const [activeRes, historyRes, passedRes, perfRes] = await Promise.all([
        fetch(`${API_BASE}/journal/active`),
        fetch(`${API_BASE}/journal/history`),
        fetch(`${API_BASE}/journal/passed`),
        fetch(`${API_BASE}/journal/performance`),
      ]);
      const activeData = await activeRes.json();
      const historyData = await historyRes.json();
      const passedData = await passedRes.json();
      const perfData = await perfRes.json();

      setActiveTrades(activeData);
      setHistoryTrades(historyData);
      setPassedTrades(passedData);
      setPerformance(perfData);
    } catch (e) {
      console.error('Failed to fetch auto journal data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJournalData();
    // Auto refresh active trades every 15 seconds
    const interval = setInterval(fetchJournalData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleCloseTradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!closeTradeId || !closeExitPrice) return;

    try {
      const res = await fetch(`${API_BASE}/journal/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          trade_id: closeTradeId,
          exit_price: parseFloat(closeExitPrice),
          exit_reason: closeReason
        })
      });
      if (res.ok) {
        setCloseTradeId(null);
        fetchJournalData();
      }
    } catch (err) {
      console.error('Failed to close trade:', err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header / Performance Summary Banner */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen style={{ color: 'var(--accent-teal)', width: '22px', height: '22px' }} />
              <h2 className="dashboard-title" style={{ margin: 0 }}>Market OS Auto Journal</h2>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
              Closed-Loop Decision & Trajectory Audit — Grounded in T₀ Setup Snapshots
            </p>
          </div>

          {/* Key Metrics Quick Stats */}
          {performance && (
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Trader Win Rate</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--accent-green)' }}>
                  {performance.trader_win_rate}%
                </div>
              </div>
              <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Setup Success Rate</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: 'var(--accent-teal)' }}>
                  {performance.setup_success_rate}%
                </div>
              </div>
              <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Avg R-Multiple</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: performance.average_r_multiple >= 1.0 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                  {performance.average_r_multiple >= 0 ? `+${performance.average_r_multiple}` : performance.average_r_multiple}R
                </div>
              </div>
              <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Avoidable Losses</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: performance.avoidable_losses_from_poor_execution > 0 ? 'var(--accent-orange)' : 'var(--accent-green)' }}>
                  {performance.avoidable_losses_from_poor_execution}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Sub Navigation Bar */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
          {[
            { key: 'today', label: `ACTIVE TRADES (${activeTrades.length})` },
            { key: 'history', label: `TRADE HISTORY (${historyTrades.length})` },
            { key: 'performance', label: 'EXECUTION & TRAJECTORY ANALYTICS' },
            { key: 'passed', label: `PASSED SETUPS (${passedTrades.length})` }
          ].map(tab => (
            <button
              key={tab.key}
              className="btn"
              style={{
                padding: '6px 14px',
                fontSize: '11px',
                fontWeight: 700,
                background: subTab === tab.key ? 'var(--accent-teal)' : 'var(--bg-tertiary)',
                color: subTab === tab.key ? '#000' : 'var(--text-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px'
              }}
              onClick={() => setSubTab(tab.key as any)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* SUB TAB 1: ACTIVE TRADES (TODAY) */}
      {subTab === 'today' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-primary)', marginBottom: '16px', letterSpacing: '0.5px' }}>
            Live Active Trades — MAE/MFE Trajectory Monitoring
          </h3>

          {activeTrades.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No active trades currently being tracked. Click <strong>[ TAKE SETUP ]</strong> on any READY or WAIT setup to begin auto journaling.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {activeTrades.map(trade => {
                const setup = trade.setup;
                const isLong = (setup?.direction || 'LONG').toUpperCase() === 'LONG';
                return (
                  <div key={trade.id} style={{
                    padding: '16px',
                    background: 'rgba(255,255,255,0.02)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)' }}>
                          {setup?.instrument} {setup?.direction}
                        </span>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(0,242,254,0.1)', color: 'var(--accent-teal)', fontWeight: 700 }}>
                          ACTIVE ({trade.entry_type})
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Entry: <strong>{trade.actual_entry}</strong> | Size: {trade.position_size_lots} lots
                        </span>
                      </div>

                      <button
                        className="btn"
                        style={{ padding: '4px 12px', fontSize: '11px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', fontWeight: 700 }}
                        onClick={() => {
                          setCloseTradeId(trade.id);
                          setCloseExitPrice(trade.actual_entry?.toString() || '');
                        }}
                      >
                        CLOSE TRADE
                      </button>
                    </div>

                    {/* Trajectory Threshold Indicators */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', background: '#0a0d14', padding: '12px', borderRadius: '6px' }}>
                      <div>
                        <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--accent-orange)', fontWeight: 700 }}>
                          MAX ADVERSE EXCURSION (MAE): {trade.max_mae_pips || 0} pips
                        </span>
                        <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mae_p25_reached ? 'var(--accent-orange)' : 'rgba(255,255,255,0.05)', color: trade.mae_p25_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mae_p25_reached ? '✓ P25' : 'P25'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mae_p50_reached ? 'var(--accent-orange)' : 'rgba(255,255,255,0.05)', color: trade.mae_p50_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mae_p50_reached ? '✓ P50' : 'P50'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mae_p75_reached ? 'var(--accent-orange)' : 'rgba(255,255,255,0.05)', color: trade.mae_p75_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mae_p75_reached ? '✓ P75' : 'P75'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mae_p90_reached ? 'var(--accent-red)' : 'rgba(255,255,255,0.05)', color: trade.mae_p90_reached ? '#fff' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mae_p90_reached ? '⚠️ P90 BREACH' : 'P90'}
                          </span>
                        </div>
                      </div>

                      <div>
                        <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--accent-green)', fontWeight: 700 }}>
                          MAX FAVORABLE EXCURSION (MFE): +{trade.max_mfe_pips || 0} pips
                        </span>
                        <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mfe_p25_reached ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)', color: trade.mfe_p25_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mfe_p25_reached ? '✓ P25' : 'P25'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mfe_p50_reached ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)', color: trade.mfe_p50_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mfe_p50_reached ? '✓ P50' : 'P50'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mfe_p75_reached ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)', color: trade.mfe_p75_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mfe_p75_reached ? '✓ P75' : 'P75'}
                          </span>
                          <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', background: trade.mfe_p90_reached ? 'var(--accent-green)' : 'rgba(255,255,255,0.05)', color: trade.mfe_p90_reached ? '#000' : 'var(--text-muted)', fontWeight: 700 }}>
                            {trade.mfe_p90_reached ? '🌟 P90 TARGET' : 'P90'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SUB TAB 2: TRADE HISTORY */}
      {subTab === 'history' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-primary)', marginBottom: '16px', letterSpacing: '0.5px' }}>
            Closed Trade Journal — Setup Outcome vs Execution Outcome
          </h3>

          {historyTrades.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No closed trade history recorded yet.
            </div>
          ) : (
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>Instrument</th>
                  <th style={{ padding: '10px' }}>Decision</th>
                  <th style={{ padding: '10px' }}>Entry Dev</th>
                  <th style={{ padding: '10px' }}>Max MAE</th>
                  <th style={{ padding: '10px' }}>Max MFE</th>
                  <th style={{ padding: '10px' }}>PnL</th>
                  <th style={{ padding: '10px' }}>Setup Outcome</th>
                  <th style={{ padding: '10px' }}>Execution Outcome</th>
                </tr>
              </thead>
              <tbody>
                {historyTrades.map(trade => {
                  const isWin = trade.outcome === 'WIN';
                  return (
                    <tr key={trade.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                      <td style={{ padding: '10px', fontWeight: 700 }}>
                        {trade.setup?.instrument} {trade.setup?.direction}
                      </td>
                      <td style={{ padding: '10px' }}>{trade.entry_type} ({trade.entry_in_corridor})</td>
                      <td style={{ padding: '10px' }}>{trade.entry_deviation_pips} pips</td>
                      <td style={{ padding: '10px', color: 'var(--accent-orange)' }}>{trade.max_mae_pips} pips</td>
                      <td style={{ padding: '10px', color: 'var(--accent-green)' }}>+{trade.max_mfe_pips} pips</td>
                      <td style={{ padding: '10px', fontWeight: 800, color: isWin ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {isWin ? '+' : ''}{trade.pnl_pips}p ({trade.pnl_r ? `${trade.pnl_r >= 0 ? '+' : ''}${trade.pnl_r}R` : ''})
                      </td>
                      <td style={{ padding: '10px' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700,
                          background: trade.setup_outcome === 'SUCCESSFUL' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                          color: trade.setup_outcome === 'SUCCESSFUL' ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                          {trade.setup_outcome}
                        </span>
                      </td>
                      <td style={{ padding: '10px' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700,
                          background: trade.execution_outcome === 'POOR_EXECUTION_SETUP_WORKED' ? 'rgba(249,115,22,0.2)' : 'rgba(0,242,254,0.1)',
                          color: trade.execution_outcome === 'POOR_EXECUTION_SETUP_WORKED' ? 'var(--accent-orange)' : 'var(--accent-teal)'
                        }}>
                          {trade.execution_outcome}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* SUB TAB 3: PERFORMANCE ANALYTICS */}
      {subTab === 'performance' && performance && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-primary)', marginBottom: '16px', letterSpacing: '0.5px' }}>
            System Expectation vs Trader Execution Analytics
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-teal)', marginBottom: '12px' }}>
                Statistical System Baseline
              </h4>
              <div style={{ fontSize: '13px', lineHeight: 1.8, color: 'var(--text-secondary)' }}>
                <div>• Setup Success Rate: <strong style={{ color: 'var(--text-primary)' }}>{performance.setup_success_rate}%</strong></div>
                <div>• Total Setups Logged: <strong style={{ color: 'var(--text-primary)' }}>{performance.total_trades_logged}</strong></div>
                <div>• Total Passed Setups: <strong style={{ color: 'var(--text-primary)' }}>{performance.total_passed_setups}</strong></div>
                <div>• Avg MFE Available: <strong style={{ color: 'var(--accent-green)' }}>+{performance.average_mfe_captured_pips} pips</strong></div>
              </div>
            </div>

            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-green)', marginBottom: '12px' }}>
                Trader Actual Execution
              </h4>
              <div style={{ fontSize: '13px', lineHeight: 1.8, color: 'var(--text-secondary)' }}>
                <div>• Actual Trader Win Rate: <strong style={{ color: 'var(--accent-green)' }}>{performance.trader_win_rate}%</strong></div>
                <div>• Avg R-Multiple Captured: <strong style={{ color: 'var(--accent-green)' }}>+{performance.average_r_multiple}R</strong></div>
                <div>• Avg MAE Endured: <strong style={{ color: 'var(--accent-orange)' }}>{performance.average_mae_endured_pips} pips</strong></div>
                <div>• Avoidable Execution Losses: <strong style={{ color: 'var(--accent-orange)' }}>{performance.avoidable_losses_from_poor_execution}</strong></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB TAB 4: PASSED SETUPS */}
      {subTab === 'passed' && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '14px', textTransform: 'uppercase', color: 'var(--text-primary)', marginBottom: '16px', letterSpacing: '0.5px' }}>
            Passed Setups — Opportunity Cost & Trust Audit
          </h3>

          {passedTrades.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No passed setups recorded yet.
            </div>
          ) : (
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <th style={{ padding: '10px' }}>Instrument</th>
                  <th style={{ padding: '10px' }}>Passed At</th>
                  <th style={{ padding: '10px' }}>Status at Pass</th>
                  <th style={{ padding: '10px' }}>Ref Price</th>
                  <th style={{ padding: '10px' }}>Trader Notes</th>
                </tr>
              </thead>
              <tbody>
                {passedTrades.map(trade => (
                  <tr key={trade.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '10px', fontWeight: 700 }}>
                      {trade.setup?.instrument} {trade.setup?.direction}
                    </td>
                    <td style={{ padding: '10px' }}>{trade.decision_at ? new Date(trade.decision_at).toLocaleTimeString() : 'N/A'}</td>
                    <td style={{ padding: '10px' }}>{trade.setup?.status_at_snapshot}</td>
                    <td style={{ padding: '10px' }}>{trade.setup?.setup_ref_price}</td>
                    <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{trade.notes || 'No notes'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Close Trade Modal */}
      {closeTradeId && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', padding: '24px', borderRadius: '10px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '16px' }}>
              Close Active Trade
            </h3>

            <form onSubmit={handleCloseTradeSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label className="form-label">Actual Exit Price</label>
                <input
                  type="number"
                  step="0.00001"
                  className="form-input"
                  value={closeExitPrice}
                  onChange={(e) => setCloseExitPrice(e.target.value)}
                  required
                  style={{ width: '100%' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label className="form-label">Exit Reason</label>
                <select
                  className="form-input"
                  value={closeReason}
                  onChange={(e) => setCloseReason(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="MANUAL">Manual Discretionary Exit</option>
                  <option value="TAKE_PROFIT">Take Profit Hit</option>
                  <option value="STOP_LOSS">Stop Loss Hit</option>
                  <option value="EOD">End of Session Exit</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setCloseTradeId(null)}
                  style={{ padding: '6px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn"
                  style={{ padding: '6px 16px', background: 'var(--accent-red)', color: '#fff', fontWeight: 700 }}
                >
                  Confirm Exit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
