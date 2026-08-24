import React, { useState, useEffect } from 'react';
import {
  Play, Trash2, ShieldAlert, ShieldCheck, CheckCircle, AlertTriangle,
  Award, TrendingUp, Activity, BarChart2, Calendar, Target, Clock, Shield,
  Download, Archive, FolderDown, FileText, Check
} from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

interface ReplayBatchSummary {
  id: number;
  batch_name: string;
  execution_policy: string;
  start_date: string;
  end_date: string;
  instruments: any;
  friction_pips: number;
  total_setups_evaluated: number;
  total_trades_taken: number;
  total_setups_passed: number;
  status: string;
  created_at: string;
  completed_at: string;
  win_rate: number;
  average_r: number;
  expectancy_r: number;
  average_winner_r: number;
  average_loser_r: number;
  is_exported: boolean;
  zip_path?: string;
}

interface ReplayAnalytics {
  batch_id?: number;
  batch_name?: string;
  execution_policy?: string;
  total_setups_evaluated: number;
  total_trades_taken: number;
  total_setups_passed: number;
  total_unfilled_missed: number;
  simulated_trader_win_rate: number;
  predicted_vs_actual_win_rate_delta: number;
  setup_success_rate: number;
  p90_invalidation_survival_rate: number;
  p90_survival_winning_trades: number;
  average_r_multiple: number;
  average_winner_r?: number;
  average_loser_r?: number;
  expectancy_r?: number;
  average_mae_pips: number;
  average_mfe_pips: number;
  opportunity_missed_wins: number;
  opportunity_saved_losses: number;
  status_distribution: Record<string, number>;
  trajectory_milestones: Record<string, number>;
  sl_first_pessimistic_exits: number;
  friction_pips_applied: number;
  performance_by_instrument?: Record<string, any>;
  integrity_checksum?: {
    status: string;
    checks: Record<string, string>;
  };
}


interface ReplayTrade {
  id: number;
  replay_snapshot_id: number;
  lifecycle_state: string;
  decision_type?: string;
  actual_entry?: number;
  actual_sl?: number;
  actual_tp?: number;
  entry_type?: string;
  entry_deviation_pips?: number;
  max_mae_pips?: number;
  max_mfe_pips?: number;
  first_milestone?: string;
  exit_price?: number;
  exit_reason?: string;
  outcome?: string;
  pnl_pips?: number;
  pnl_r?: number;
  setup_outcome?: string;
  execution_outcome?: string;
  setup?: {
    instrument: string;
    date: string;
    direction: string;
    status_at_snapshot: string;
    setup_ref_price: number;
    continuation_prob?: number;
    confidence_score?: number;
  };
}

interface ReplaySnapshot {
  id: number;
  instrument: string;
  date: string;
  direction: string;
  status_at_snapshot: string;
  setup_ref_price: number;
  frozen_entry?: number;
  frozen_sl?: number;
  frozen_tp?: number;
  continuation_prob?: number;
  opportunity_outcome?: string;
  opportunity_max_mfe?: number;
  opportunity_max_mae?: number;
}

export function ReplayTab() {
  const [startDate, setStartDate] = useState<string>('2024-01-01');
  const [endDate, setEndDate] = useState<string>('2024-06-01');
  const [selectedInstruments, setSelectedInstruments] = useState<string[]>([
    'GBPUSD', 'EURUSD', 'XAUUSD', 'AUDUSD', 'USDJPY', 'US100', 'AUDJPY'
  ]);

  const [executionPolicy, setExecutionPolicy] = useState<string>('MARKET_ENTRY');
  const [frictionPips, setFrictionPips] = useState<string>('2.5');

  const [running, setRunning] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<ReplayAnalytics | null>(null);
  const [replayHistory, setReplayHistory] = useState<ReplayTrade[]>([]);
  const [replayPassed, setReplayPassed] = useState<ReplaySnapshot[]>([]);
  const [batches, setBatches] = useState<ReplayBatchSummary[]>([]);
  const [subTab, setSubTab] = useState<'history' | 'passed' | 'matrix' | 'checksum' | 'batches' | 'compare' | 'instruments'>('history');

  // Comparison State
  const [baselineBatchId, setBaselineBatchId] = useState<number | ''>('');
  const [candidateBatchId, setCandidateBatchId] = useState<number | ''>('');
  const [comparisonData, setComparisonData] = useState<any | null>(null);
  const [comparing, setComparing] = useState<boolean>(false);

  const fetchReplayData = async () => {
    try {
      const [analyticsRes, historyRes, passedRes, batchesRes] = await Promise.all([
        fetch(`${API_BASE}/replay/analytics`),
        fetch(`${API_BASE}/replay/history`),
        fetch(`${API_BASE}/replay/passed`),
        fetch(`${API_BASE}/replay/batches`)
      ]);
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (historyRes.ok) setReplayHistory(await historyRes.json());
      if (passedRes.ok) setReplayPassed(await passedRes.json());
      if (batchesRes.ok) {
        const bData = await batchesRes.json();
        setBatches(bData);
        if (bData.length >= 2 && !baselineBatchId && !candidateBatchId) {
          setBaselineBatchId(bData[1].id);
          setCandidateBatchId(bData[0].id);
        } else if (bData.length === 1 && !baselineBatchId) {
          setBaselineBatchId(bData[0].id);
          setCandidateBatchId(bData[0].id);
        }
      }
    } catch (e) {
      console.error('Failed to fetch replay data:', e);
    }
  };

  const handleRunComparison = async () => {
    if (!baselineBatchId || !candidateBatchId) {
      alert("Please select both a Baseline and a Candidate batch to compare.");
      return;
    }
    setComparing(true);
    try {
      const res = await fetch(`${API_BASE}/replay/compare?baseline_id=${baselineBatchId}&candidate_id=${candidateBatchId}`);
      if (res.ok) {
        const data = await res.json();
        setComparisonData(data);
      } else {
        const err = await res.json();
        alert(`Comparison failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Comparison error:', err);
    } finally {
      setComparing(false);
    }
  };


  useEffect(() => {
    fetchReplayData();
  }, []);

  const handleRunReplay = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setExportMsg(null);
    try {
      const res = await fetch(`${API_BASE}/replay/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_name: 'Backtest Simulation',
          start_date: startDate,
          end_date: endDate,
          instruments: selectedInstruments,
          execution_policy: executionPolicy,
          friction_pips: parseFloat(frictionPips) || 2.5
        })
      });
      if (res.ok) {
        await fetchReplayData();
      }
    } catch (err) {
      console.error('Replay execution error:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleExportResults = async () => {
    const targetBatchId = analytics?.batch_id || (batches.length > 0 ? batches[0].id : null);
    if (!targetBatchId) {
      alert("No active replay batch found to export. Run a replay first.");
      return;
    }
    setExporting(true);
    setExportMsg(null);
    try {
      const res = await fetch(`${API_BASE}/replay/${targetBatchId}/export`);
      if (res.ok) {
        const data = await res.json();
        setExportMsg(`Batch #${targetBatchId} successfully archived to ${data.archive_dir} (ZIP generated)`);
        await fetchReplayData();
        // Trigger file download
        window.open(`${API_BASE}/replay/${targetBatchId}/download`, '_blank');
      } else {
        const err = await res.json();
        alert(`Export failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Export error:', err);
      alert('Failed to export batch archive.');
    } finally {
      setExporting(false);
    }
  };

  const handleExportBatchById = async (batchId: number) => {
    setExporting(true);
    try {
      const res = await fetch(`${API_BASE}/replay/${batchId}/export`);
      if (res.ok) {
        const data = await res.json();
        setExportMsg(`Batch #${batchId} exported.`);
        await fetchReplayData();
        window.open(`${API_BASE}/replay/${batchId}/download`, '_blank');
      }
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setExporting(false);
    }
  };

  const handleResetReplay = async () => {
    if (!window.confirm('Wipe active replay simulation database tables? Note: All exported file archives in replay_archive/ will be preserved.')) return;
    try {
      const res = await fetch(`${API_BASE}/replay/reset`, { method: 'POST' });
      if (res.ok) {
        await fetchReplayData();
        setExportMsg("Replay database tables reset. Exported file archives preserved.");
      }
    } catch (err) {
      console.error('Replay reset error:', err);
    }
  };

  const toggleInstrument = (inst: string) => {
    setSelectedInstruments(prev =>
      prev.includes(inst) ? prev.filter(i => i !== inst) : [...prev, inst]
    );
  };

  const isVerified = analytics?.integrity_checksum?.status === 'INTEGRITY VERIFIED';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header & Controls Panel */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Play style={{ color: 'var(--accent-teal)', width: '24px', height: '24px' }} />
              <h2 className="dashboard-title" style={{ margin: 0 }}>Backtest & Simulation Engine</h2>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', margin: 0 }}>
              Point-in-time ($t \le T_0$) backtest simulation with realistic spread & slippage
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            {analytics?.integrity_checksum && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 800,
                background: isVerified ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                color: isVerified ? 'var(--accent-green)' : 'var(--accent-orange)',
                border: `1px solid ${isVerified ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`
              }}>
                {isVerified ? <ShieldCheck style={{ width: '14px', height: '14px' }} /> : <ShieldAlert style={{ width: '14px', height: '14px' }} />}
                {analytics.integrity_checksum.status}
              </div>
            )}

            <button
              className="btn"
              disabled={exporting}
              style={{
                padding: '8px 16px',
                background: 'rgba(0, 242, 254, 0.15)',
                border: '1px solid var(--accent-teal)',
                color: 'var(--accent-teal)',
                fontWeight: 800,
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                borderRadius: '6px'
              }}
              onClick={handleExportResults}
            >
              <FolderDown style={{ width: '14px', height: '14px' }} />
              {exporting ? 'EXPORTING...' : 'EXPORT RESULTS'}
            </button>

            <button
              className="btn"
              style={{ padding: '8px 14px', background: 'rgba(239,68,68,0.12)', border: '1px solid var(--accent-red)', color: 'var(--accent-red)', fontWeight: 700, fontSize: '11px' }}
              onClick={handleResetReplay}
            >
              <Trash2 style={{ width: '14px', height: '14px', marginRight: '6px' }} />
              Wipe Replay Data
            </button>
          </div>
        </div>

        {/* Export Notification Banner */}
        {exportMsg && (
          <div style={{
            padding: '10px 14px',
            borderRadius: '6px',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: 'var(--accent-green)',
            fontSize: '12px',
            fontWeight: 700,
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Check size={16} />
            {exportMsg}
          </div>
        )}


        {/* Replay Configuration Form */}
        <form onSubmit={handleRunReplay} style={{ background: '#0a0d14', padding: '18px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label className="form-label" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Start Date</label>
              <input
                type="date"
                className="form-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>End Date</label>
              <input
                type="date"
                className="form-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Execution Policy</label>
              <select
                className="form-input"
                value={executionPolicy}
                onChange={(e) => setExecutionPolicy(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="MARKET_ENTRY">★ Validated Market Open Entry (44.0% WR · +0.265R)</option>
                <option value="RETEST_LIMIT_ENTRY">Pullback to Open Retest Limit (44.0% WR · +0.265R)</option>
                <option value="RECALIBRATED_DEVIATION">Deviation Recovery: Recalibrated Stop (42.0% WR · +0.219R)</option>
                <option value="EXECUTION_DEVIATION">Deviation: Late Blind Chase [+5p] (43.1% WR · +0.180R)</option>
                <option value="DEPRECATED_DEEP_LIMIT">⚠️ [DEPRECATED] Old V4 Deep Limit (13.3% WR · Toxic Adverse Selection)</option>
              </select>
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Friction (Spread + Slippage)</label>
              <input
                type="number"
                step="0.5"
                className="form-input"
                value={frictionPips}
                onChange={(e) => setFrictionPips(e.target.value)}
                placeholder="2.5 pips"
                style={{ width: '100%' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginRight: '6px' }}>Instruments:</span>
              {['GBPUSD', 'EURUSD', 'XAUUSD', 'AUDUSD', 'USDJPY', 'US100', 'AUDJPY'].map(inst => (

                <button
                  type="button"
                  key={inst}
                  className="btn"
                  style={{
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: 700,
                    background: selectedInstruments.includes(inst) ? 'rgba(0,242,254,0.15)' : 'var(--bg-tertiary)',
                    color: selectedInstruments.includes(inst) ? 'var(--accent-teal)' : 'var(--text-muted)',
                    border: selectedInstruments.includes(inst) ? '1px solid var(--accent-teal)' : '1px solid var(--border-color)',
                    borderRadius: '4px'
                  }}
                  onClick={() => toggleInstrument(inst)}
                >
                  {inst}
                </button>
              ))}
            </div>

            <button
              type="submit"
              className="btn"
              disabled={running}
              style={{
                padding: '10px 24px',
                background: running ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-teal), #00c6ff)',
                color: running ? 'var(--text-muted)' : '#000',
                fontWeight: 800,
                fontSize: '12px'
              }}
            >
              {running ? <>Running Replay Harness...</> : <>🚀 RUN HISTORICAL REPLAY</>}
            </button>
          </div>
        </form>
      </div>

      {/* Results Dashboard */}
      {analytics && analytics.total_setups_evaluated > 0 && (
        <>
          {/* Key Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
            <div className="glass-panel" style={{ padding: '16px' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Simulated Trader Win Rate</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-green)', marginTop: '4px' }}>
                {analytics.simulated_trader_win_rate}%
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                {analytics.total_trades_taken} Executed Trades (Delta: {analytics.predicted_vs_actual_win_rate_delta >= 0 ? `+${analytics.predicted_vs_actual_win_rate_delta}` : analytics.predicted_vs_actual_win_rate_delta}%)
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '16px' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>P90 Invalidation Survival</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-teal)', marginTop: '4px' }}>
                {analytics.p90_invalidation_survival_rate}%
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                All Taken ({analytics.p90_survival_winning_trades}% in Winners)
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '16px' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Opportunity Outcomes</span>
              <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-green)', marginTop: '4px' }}>
                {analytics.opportunity_missed_wins} Missed Wins
              </div>
              <div style={{ fontSize: '12px', color: 'var(--accent-orange)', marginTop: '2px' }}>
                {analytics.opportunity_saved_losses} Saved Losses
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '16px' }}>
              <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Avg R-Multiple</span>
              <div style={{ fontSize: '24px', fontWeight: 800, color: analytics.average_r_multiple >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '4px' }}>
                {analytics.average_r_multiple >= 0 ? `+${analytics.average_r_multiple}` : analytics.average_r_multiple}R
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                Net after {analytics.friction_pips_applied}p friction penalty
              </div>
            </div>
          </div>

          {/* Navigation & Tables */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', flexWrap: 'wrap' }}>
              {[
                { key: 'history', label: `EXECUTED TRADES (${replayHistory.length})` },
                { key: 'passed', label: `MISSED & PASSED SETUPS (${replayPassed.length})` },
                { key: 'instruments', label: 'PERFORMANCE BY ASSET' },
                { key: 'matrix', label: 'PRICE REACH MATRIX' },
                { key: 'checksum', label: 'DATA INTEGRITY CHECKS' },
                { key: 'batches', label: `BACKTEST HISTORY & EXPORTS (${batches.length})` },
                { key: 'compare', label: 'STRATEGY COMPARISON' }
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
                  onClick={() => {
                    setSubTab(tab.key as any);
                    if (tab.key === 'compare' && !comparisonData && baselineBatchId && candidateBatchId) {
                      handleRunComparison();
                    }
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {subTab === 'history' && (
              <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>Date</th>
                    <th style={{ padding: '10px' }}>Instrument</th>
                    <th style={{ padding: '10px' }}>Entry Type</th>
                    <th style={{ padding: '10px' }}>Entry Price</th>
                    <th style={{ padding: '10px' }}>Max MAE</th>
                    <th style={{ padding: '10px' }}>Max MFE</th>
                    <th style={{ padding: '10px' }}>Net PnL</th>
                    <th style={{ padding: '10px' }}>Trajectory Order</th>
                    <th style={{ padding: '10px' }}>Exit Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {replayHistory.length === 0 ? (
                    <tr>
                      <td colSpan={9} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No executed trades recorded under strict execution policy. Limit setups remained unfilled.
                      </td>
                    </tr>
                  ) : (
                    replayHistory.map(trade => {
                      const isWin = trade.outcome === 'WIN';
                      return (
                        <tr key={trade.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{trade.setup?.date}</td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>
                            {trade.setup?.instrument} {trade.setup?.direction}
                          </td>
                          <td style={{ padding: '10px' }}>{trade.entry_type}</td>
                          <td style={{ padding: '10px' }}>{trade.actual_entry}</td>
                          <td style={{ padding: '10px', color: 'var(--accent-orange)' }}>{trade.max_mae_pips}p</td>
                          <td style={{ padding: '10px', color: 'var(--accent-green)' }}>+{trade.max_mfe_pips}p</td>
                          <td style={{ padding: '10px', fontWeight: 800, color: isWin ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {isWin ? '+' : ''}{trade.pnl_pips}p ({trade.pnl_r ? `${trade.pnl_r >= 0 ? '+' : ''}${trade.pnl_r}R` : ''})
                          </td>
                          <td style={{ padding: '10px' }}>
                            <span style={{ fontSize: '10px', fontWeight: 700, color: trade.first_milestone === 'MFE_FIRST' ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
                              {trade.first_milestone || 'N/A'}
                            </span>
                          </td>
                          <td style={{ padding: '10px', fontSize: '11px', color: 'var(--text-muted)' }}>{trade.exit_reason}</td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            )}

            {subTab === 'passed' && (
              <div>
                <div style={{ padding: '10px 14px', background: 'rgba(0,242,254,0.06)', borderRadius: '6px', marginBottom: '14px', fontSize: '11px', color: 'var(--accent-teal)' }}>
                  <strong>Strict Scientific Invariant Active:</strong> Passed setups do NOT create trade execution records. Opportunity outcomes are evaluated post-hoc from future price movement.
                </div>
                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '10px' }}>Date</th>
                      <th style={{ padding: '10px' }}>Instrument</th>
                      <th style={{ padding: '10px' }}>$T_0$ Status</th>
                      <th style={{ padding: '10px' }}>$T_0$ Ref Price</th>
                      <th style={{ padding: '10px' }}>Continuation Prob</th>
                      <th style={{ padding: '10px' }}>Opportunity Outcome</th>
                      <th style={{ padding: '10px' }}>Max MFE</th>
                      <th style={{ padding: '10px' }}>Max MAE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {replayPassed.map(snap => {
                      const isMissedWin = snap.opportunity_outcome === 'MISSED_WIN';
                      const isSavedLoss = snap.opportunity_outcome === 'SAVED_LOSS';
                      return (
                        <tr key={snap.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '10px', color: 'var(--text-muted)' }}>{snap.date}</td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>
                            {snap.instrument} {snap.direction}
                          </td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>{snap.status_at_snapshot}</td>
                          <td style={{ padding: '10px' }}>{snap.setup_ref_price}</td>
                          <td style={{ padding: '10px' }}>{snap.continuation_prob ? `${Math.round(snap.continuation_prob * 100)}%` : 'N/A'}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: isMissedWin ? 'rgba(239,68,68,0.12)' : isSavedLoss ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.06)',
                              color: isMissedWin ? 'var(--accent-red)' : isSavedLoss ? 'var(--accent-green)' : 'var(--text-muted)'
                            }}>
                              {snap.opportunity_outcome}
                            </span>
                          </td>
                          <td style={{ padding: '10px', color: 'var(--accent-green)' }}>+{snap.opportunity_max_mfe || 0}p</td>
                          <td style={{ padding: '10px', color: 'var(--accent-orange)' }}>{snap.opportunity_max_mae || 0}p</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {subTab === 'matrix' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-teal)', marginBottom: '12px' }}>
                    Status Frequency Distribution
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(analytics.status_distribution || {}).map(([st, cnt]) => (
                      <div key={st} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 700 }}>{st}</span>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{cnt} setups</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-green)', marginBottom: '12px' }}>
                    Trajectory Sequence Reaches
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {Object.entries(analytics.trajectory_milestones || {}).map(([ms, cnt]) => (
                      <div key={ms} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase' }}>{ms.replace('_', ' ')}</span>
                        <span style={{ fontSize: '12px', color: 'var(--accent-teal)', fontWeight: 700 }}>{cnt} times</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {subTab === 'instruments' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-teal)', margin: 0 }}>
                    Asset Performance & Empirical Edge Status
                  </h4>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Evaluated under {analytics.friction_pips_applied}p round-trip friction penalty
                  </div>
                </div>

                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '10px' }}>Instrument</th>
                      <th style={{ padding: '10px' }}>Edge Status</th>
                      <th style={{ padding: '10px' }}>Trades Taken</th>
                      <th style={{ padding: '10px' }}>Win Rate</th>
                      <th style={{ padding: '10px' }}>Avg Winner</th>
                      <th style={{ padding: '10px' }}>Avg Loser</th>
                      <th style={{ padding: '10px' }}>Expectancy R</th>
                      <th style={{ padding: '10px' }}>Profit Factor</th>
                      <th style={{ padding: '10px' }}>Net Cumulative R</th>
                      <th style={{ padding: '10px' }}>Max DD (R)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(analytics.performance_by_instrument || {}).map(([inst, iData]: [string, any]) => {
                      const isValidated = iData.edge_status === 'VALIDATED_EDGE';
                      const isNegative = iData.edge_status === 'NEGATIVE_EXPECTANCY';
                      const badgeColor = isValidated ? 'var(--accent-green)' : (isNegative ? 'var(--accent-red)' : 'var(--accent-orange)');
                      return (
                        <tr key={inst} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '10px', fontWeight: 800 }}>{inst}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: isValidated ? 'rgba(16,185,129,0.15)' : (isNegative ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)'),
                              color: badgeColor,
                              border: `1px solid ${badgeColor}`
                            }}>
                              {iData.edge_status || (iData.expectancy_r > 0 ? 'VALIDATED_EDGE' : 'NEGATIVE_EXPECTANCY')}
                            </span>
                          </td>
                          <td style={{ padding: '10px' }}>{iData.trades_taken}</td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>{iData.win_rate}%</td>
                          <td style={{ padding: '10px', color: 'var(--accent-green)' }}>+{iData.average_winner_r}R</td>
                          <td style={{ padding: '10px', color: 'var(--accent-red)' }}>{iData.average_loser_r}R</td>
                          <td style={{ padding: '10px', fontWeight: 800, color: iData.expectancy_r >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {iData.expectancy_r >= 0 ? `+${iData.expectancy_r}` : iData.expectancy_r}R
                          </td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>{iData.profit_factor}</td>
                          <td style={{ padding: '10px', fontWeight: 800, color: iData.net_r >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {iData.net_r >= 0 ? `+${iData.net_r}` : iData.net_r}R
                          </td>
                          <td style={{ padding: '10px', color: 'var(--accent-orange)' }}>{iData.max_drawdown_r}R</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {subTab === 'checksum' && analytics.integrity_checksum && (
              <div>
                <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-teal)', marginBottom: '12px' }}>
                  Automated Accounting & Data Integrity Verification
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '10px' }}>
                  {Object.entries(analytics.integrity_checksum.checks).map(([check, result]) => (
                    <div key={check} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px', background: '#0a0d14', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700 }}>{check.replace(/_/g, ' ')}</span>
                      <span style={{ fontSize: '11px', fontWeight: 800, color: result === 'PASS' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {result}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {subTab === 'batches' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent-teal)', margin: 0 }}>
                    Completed Backtests & Export Center
                  </h4>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Direct CSV and ZIP downloads for all completed backtests
                  </div>
                </div>

                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '10px' }}>Batch ID</th>
                      <th style={{ padding: '10px' }}>Name & Policy</th>
                      <th style={{ padding: '10px' }}>Date Range</th>
                      <th style={{ padding: '10px' }}>Instruments</th>
                      <th style={{ padding: '10px' }}>Trades Taken</th>
                      <th style={{ padding: '10px' }}>Win Rate</th>
                      <th style={{ padding: '10px' }}>Avg Win / Loss</th>
                      <th style={{ padding: '10px' }}>Expectancy</th>
                      <th style={{ padding: '10px' }}>Archive Status</th>
                      <th style={{ padding: '10px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batches.length === 0 ? (
                      <tr>
                        <td colSpan={10} style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No replay batches found in database. Run a simulation above to create a batch.
                        </td>
                      </tr>
                    ) : (
                      batches.map(b => (
                        <tr key={b.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                          <td style={{ padding: '10px', fontWeight: 800, color: 'var(--accent-teal)' }}>#{b.id}</td>
                          <td style={{ padding: '10px' }}>
                            <div style={{ fontWeight: 700, color: '#fff' }}>{b.batch_name}</div>
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{b.execution_policy}</div>
                          </td>
                          <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                            {b.start_date} → {b.end_date}
                          </td>
                          <td style={{ padding: '10px', fontSize: '11px', color: 'var(--text-muted)' }}>
                            {Array.isArray(b.instruments) ? b.instruments.join(', ') : b.instruments}
                          </td>
                          <td style={{ padding: '10px', fontWeight: 700 }}>
                            {b.total_trades_taken} / {b.total_setups_evaluated}
                          </td>
                          <td style={{ padding: '10px', fontWeight: 800, color: b.win_rate >= 50 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
                            {b.win_rate}%
                          </td>
                          <td style={{ padding: '10px', fontSize: '11px' }}>
                            <span style={{ color: 'var(--accent-green)' }}>+{b.average_winner_r}R</span> / <span style={{ color: 'var(--accent-red)' }}>{b.average_loser_r}R</span>
                          </td>
                          <td style={{ padding: '10px', fontWeight: 800, color: b.expectancy_r >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {b.expectancy_r >= 0 ? `+${b.expectancy_r}` : b.expectancy_r}R
                          </td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: b.is_exported ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
                              color: b.is_exported ? 'var(--accent-green)' : 'var(--text-muted)',
                              border: `1px solid ${b.is_exported ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.1)'}`
                            }}>
                              {b.is_exported ? 'ARCHIVED' : 'NOT ARCHIVED'}
                            </span>
                          </td>
                          <td style={{ padding: '10px', textAlign: 'right' }}>
                            <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                              <button
                                className="btn"
                                disabled={exporting}
                                style={{
                                  padding: '4px 10px',
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  background: 'rgba(0,242,254,0.1)',
                                  border: '1px solid var(--accent-teal)',
                                  color: 'var(--accent-teal)',
                                  borderRadius: '4px',
                                  display: 'flex', alignItems: 'center', gap: '4px'
                                }}
                                onClick={() => handleExportBatchById(b.id)}
                              >
                                <Download size={11} />
                                ZIP
                              </button>
                              <button
                                className="btn"
                                style={{
                                  padding: '4px 10px',
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  background: 'rgba(16,185,129,0.08)',
                                  border: '1px solid rgba(16,185,129,0.4)',
                                  color: 'var(--accent-green)',
                                  borderRadius: '4px',
                                  display: 'flex', alignItems: 'center', gap: '4px'
                                }}
                                onClick={() => window.open(`${API_BASE}/replay/${b.id}/download-trades-csv`, '_blank')}
                              >
                                <Download size={11} />
                                Trades CSV
                              </button>
                              <button
                                className="btn"
                                style={{
                                  padding: '4px 10px',
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  background: 'rgba(245,158,11,0.08)',
                                  border: '1px solid rgba(245,158,11,0.4)',
                                  color: 'var(--accent-orange)',
                                  borderRadius: '4px',
                                  display: 'flex', alignItems: 'center', gap: '4px'
                                }}
                                onClick={() => window.open(`${API_BASE}/replay/${b.id}/download-snapshots-csv`, '_blank')}
                              >
                                <Download size={11} />
                                Setups CSV
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {subTab === 'compare' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {/* Selector Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0a0d14', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div>
                      <label style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                        Baseline Batch (Control)
                      </label>
                      <select
                        className="form-input"
                        value={baselineBatchId}
                        onChange={(e) => setBaselineBatchId(Number(e.target.value))}
                        style={{ padding: '6px 12px', fontSize: '12px', background: '#111827', color: '#fff', border: '1px solid var(--border-color)', borderRadius: '4px' }}
                      >
                        {batches.map(b => (
                          <option key={b.id} value={b.id}>
                            #{b.id}: {b.batch_name} ({b.execution_policy})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-teal)', paddingTop: '16px' }}>
                      VS
                    </div>

                    <div>
                      <label style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                        Candidate Batch (Test)
                      </label>
                      <select
                        className="form-input"
                        value={candidateBatchId}
                        onChange={(e) => setCandidateBatchId(Number(e.target.value))}
                        style={{ padding: '6px 12px', fontSize: '12px', background: '#111827', color: '#fff', border: '1px solid var(--border-color)', borderRadius: '4px' }}
                      >
                        {batches.map(b => (
                          <option key={b.id} value={b.id}>
                            #{b.id}: {b.batch_name} ({b.execution_policy})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <button
                    className="btn"
                    disabled={comparing}
                    style={{
                      padding: '8px 18px',
                      background: 'linear-gradient(135deg, var(--accent-teal), #00c6ff)',
                      color: '#000',
                      fontWeight: 800,
                      fontSize: '11px',
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                    onClick={handleRunComparison}
                  >
                    <BarChart2 size={14} />
                    {comparing ? 'COMPARING...' : 'RUN COMPARISON'}
                  </button>
                </div>

                {/* Comparison Results */}
                {comparisonData && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {/* Validity & Summary Banner */}
                    <div style={{
                      padding: '16px',
                      borderRadius: '8px',
                      background: comparisonData.comparison_validity === 'CONTROLLED' ? 'rgba(16,185,129,0.08)' : 'rgba(245,158,11,0.08)',
                      border: `1px solid ${comparisonData.comparison_validity === 'CONTROLLED' ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)'}`
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 800,
                            background: comparisonData.comparison_validity === 'CONTROLLED' ? 'var(--accent-green)' : 'var(--accent-orange)',
                            color: '#000'
                          }}>
                            {comparisonData.comparison_validity === 'CONTROLLED' ? 'CONTROLLED COMPARISON' : 'CONTEXTUAL — NOT CONTROLLED'}
                          </span>
                          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                            {comparisonData.validity_reason}
                          </span>
                        </div>

                        <span style={{
                          fontSize: '11px',
                          fontWeight: 800,
                          color: comparisonData.breadth_summary === 'BROAD_IMPROVEMENT' ? 'var(--accent-green)' : (comparisonData.breadth_summary === 'BROAD_DETERIORATION' ? 'var(--accent-red)' : 'var(--accent-orange)')
                        }}>
                          BREADTH: {comparisonData.breadth_summary.replace(/_/g, ' ')}
                        </span>
                      </div>

                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginTop: '6px' }}>
                        {comparisonData.economic_verdict}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        {comparisonData.evidence_summary}
                      </div>
                    </div>

                    {/* Primary Economic KPIs */}
                    <div>
                      <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent-teal)', letterSpacing: '0.05em', marginBottom: '10px' }}>
                        Primary Economic KPIs (Core Decision Basis)
                      </h4>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                        {[
                          { key: 'expectancy_r', label: 'Expectancy R / Trade', unit: 'R' },
                          { key: 'profit_factor', label: 'Profit Factor', unit: '' },
                          { key: 'average_winner_r', label: 'Average Winner', unit: 'R' },
                          { key: 'average_loser_r', label: 'Average Loser', unit: 'R' },
                          { key: 'max_drawdown_r', label: 'Max Drawdown', unit: 'R' },
                        ].map(m => {
                          const deltaObj = comparisonData.primary_kpis[m.key] || {};
                          const isImproved = deltaObj.verdict === 'IMPROVED';
                          const isWorsened = deltaObj.verdict === 'WORSENED';
                          const deltaColor = isImproved ? 'var(--accent-green)' : (isWorsened ? 'var(--accent-red)' : 'var(--text-muted)');
                          return (
                            <div key={m.key} className="glass-panel" style={{ padding: '14px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{m.label}</span>
                                <span style={{
                                  fontSize: '9px',
                                  fontWeight: 800,
                                  padding: '2px 6px',
                                  borderRadius: '3px',
                                  background: isImproved ? 'rgba(16,185,129,0.15)' : (isWorsened ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.05)'),
                                  color: deltaColor
                                }}>
                                  {deltaObj.verdict}
                                </span>
                              </div>
                              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                                {deltaObj.baseline}{m.unit} → <strong style={{ color: '#fff' }}>{deltaObj.candidate}{m.unit}</strong>
                              </div>
                              <div style={{ fontSize: '18px', fontWeight: 800, color: deltaColor, marginTop: '4px' }}>
                                {deltaObj.delta_abs >= 0 ? `+${deltaObj.delta_abs}` : deltaObj.delta_abs}{m.unit}
                                <span style={{ fontSize: '11px', marginLeft: '6px', fontWeight: 600 }}>
                                  ({deltaObj.delta_pct >= 0 ? `+${deltaObj.delta_pct}` : deltaObj.delta_pct}%)
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Secondary Metrics */}
                    <div>
                      <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em', marginBottom: '10px' }}>
                        Secondary Metrics & Opportunity Counts
                      </h4>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                        {[
                          { key: 'win_rate', label: 'Win Rate', unit: '%' },
                          { key: 'net_r', label: 'Net Cumulative R', unit: 'R' },
                          { key: 'trades_taken', label: 'Trades Taken', unit: '' },
                          { key: 'p90_survival_rate', label: 'P90 Survival Rate', unit: '%' },
                          { key: 'saved_losses', label: 'Saved Losses', unit: '' },
                          { key: 'missed_wins', label: 'Missed Wins', unit: '' },
                        ].map(m => {
                          const deltaObj = comparisonData.secondary_kpis[m.key] || {};
                          const isImproved = deltaObj.verdict === 'IMPROVED';
                          const isWorsened = deltaObj.verdict === 'WORSENED';
                          const deltaColor = isImproved ? 'var(--accent-green)' : (isWorsened ? 'var(--accent-red)' : 'var(--text-muted)');
                          return (
                            <div key={m.key} style={{ padding: '10px', background: '#0a0d14', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                              <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{m.label}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                {deltaObj.baseline}{m.unit} → {deltaObj.candidate}{m.unit}
                              </div>
                              <div style={{ fontSize: '14px', fontWeight: 800, color: deltaColor, marginTop: '2px' }}>
                                {deltaObj.delta_abs >= 0 ? `+${deltaObj.delta_abs}` : deltaObj.delta_abs}{m.unit} ({deltaObj.delta_pct >= 0 ? `+${deltaObj.delta_pct}` : deltaObj.delta_pct}%)
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Per-Instrument Breadth Table */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <h4 style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent-teal)', letterSpacing: '0.05em', margin: 0 }}>
                          Per-Instrument Breakdown (Testing Robustness Across Universe)
                        </h4>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Improved: <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>{comparisonData.instruments_improved.join(', ') || 'None'}</span> |
                          Worsened: <span style={{ color: 'var(--accent-red)', fontWeight: 700 }}>{comparisonData.instruments_worsened.join(', ') || 'None'}</span>
                        </div>
                      </div>

                      <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                            <th style={{ padding: '10px' }}>Instrument</th>
                            <th style={{ padding: '10px' }}>Verdict</th>
                            <th style={{ padding: '10px' }}>Trades (Base → Cand)</th>
                            <th style={{ padding: '10px' }}>Expectancy R (Δ)</th>
                            <th style={{ padding: '10px' }}>Profit Factor (Δ)</th>
                            <th style={{ padding: '10px' }}>Net R (Δ)</th>
                            <th style={{ padding: '10px' }}>Win Rate (Δ)</th>
                            <th style={{ padding: '10px' }}>Max DD (Δ)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(comparisonData.instrument_comparisons || {}).map(([inst, iData]: [string, any]) => {
                            const isImp = iData.verdict === 'IMPROVED';
                            const isWor = iData.verdict === 'WORSENED';
                            const vColor = isImp ? 'var(--accent-green)' : (isWor ? 'var(--accent-red)' : 'var(--text-muted)');
                            return (
                              <tr key={inst} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                                <td style={{ padding: '10px', fontWeight: 800 }}>{inst}</td>
                                <td style={{ padding: '10px' }}>
                                  <span style={{
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    fontSize: '9px',
                                    fontWeight: 800,
                                    background: isImp ? 'rgba(16,185,129,0.15)' : (isWor ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.05)'),
                                    color: vColor
                                  }}>
                                    {iData.verdict}
                                  </span>
                                </td>
                                <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>
                                  {iData.baseline_trades} → {iData.candidate_trades}
                                </td>
                                <td style={{ padding: '10px', fontWeight: 700, color: iData.expectancy_r.delta_abs >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                  {iData.expectancy_r.delta_abs >= 0 ? `+${iData.expectancy_r.delta_abs}` : iData.expectancy_r.delta_abs}R
                                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                                    ({iData.expectancy_r.baseline} → {iData.expectancy_r.candidate})
                                  </span>
                                </td>
                                <td style={{ padding: '10px', color: iData.profit_factor.delta_abs >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                  {iData.profit_factor.delta_abs >= 0 ? `+${iData.profit_factor.delta_abs}` : iData.profit_factor.delta_abs}
                                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                                    ({iData.profit_factor.baseline} → {iData.profit_factor.candidate})
                                  </span>
                                </td>
                                <td style={{ padding: '10px', fontWeight: 700, color: iData.net_r.delta_abs >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                  {iData.net_r.delta_abs >= 0 ? `+${iData.net_r.delta_abs}` : iData.net_r.delta_abs}R
                                </td>
                                <td style={{ padding: '10px', color: iData.win_rate.delta_abs >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                  {iData.win_rate.delta_abs >= 0 ? `+${iData.win_rate.delta_abs}` : iData.win_rate.delta_abs}%
                                </td>
                                <td style={{ padding: '10px', color: iData.max_drawdown_r.delta_abs <= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                  {iData.max_drawdown_r.delta_abs >= 0 ? `+${iData.max_drawdown_r.delta_abs}` : iData.max_drawdown_r.delta_abs}R
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </>
      )}
    </div>
  );
}

