import React, { useState, useEffect } from 'react';
import { 
  Shield, AlertTriangle, CheckCircle2, XCircle, ArrowUpRight, ArrowDownRight, 
  ChevronDown, ChevronUp, Zap, Scale, RefreshCw, BarChart2, CheckCircle
} from 'lucide-react';

interface DecisionAudit {
  positive_factors: string[];
  warnings: string[];
  blockers: string[];
}

interface EvaluationResult {
  instrument: string;
  direction: string;
  timeframe: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_pips: number;
  reward_pips: number;
  risk_reward_ratio: number;
  position_size_lots: number;
  risk_amount_usd: number;
  raw_win_probability: number;
  calibrated_win_probability: number;
  expected_r_multiple: number;
  execution_grade: string;
  recommendation: 'PROCEED' | 'WAIT' | 'AVOID';
  recommendation_color: string;
  recommendation_summary: string;
  entry_zone_recommendation: {
    aggressive_entry: number;
    optimal_zone_min: number;
    optimal_zone_max: number;
    mae_p75_pips: number;
    explanation: string;
  };
  empirical_mae: {
    p50: number;
    p75: number;
    p90: number;
    survival_rate: number;
    p50_ci: [number, number];
  };
  empirical_mfe: {
    p50: number;
    p75: number;
    p90: number;
    p50_ci: [number, number];
  };
  sample_size: number;
  sample_quality: {
    rating: string;
    color: string;
    description: string;
  };
  low_confidence: boolean;
  decision_audit: DecisionAudit;
}

const INSTRUMENT_DEFAULTS: Record<string, { entry: number; stop: number; target: number }> = {
  GBPUSD: { entry: 1.2850, stop: 1.2825, target: 1.2910 },
  EURUSD: { entry: 1.0880, stop: 1.0860, target: 1.0930 },
  XAUUSD: { entry: 2410.0, stop: 2398.0, target: 2435.0 },
  AUDUSD: { entry: 0.6680, stop: 0.6660, target: 0.6725 },
  USDJPY: { entry: 154.50, stop: 154.10, target: 155.40 }
};

const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

export const TradePlanner: React.FC = () => {
  const [symbol, setSymbol] = useState<string>('GBPUSD');
  const [direction, setDirection] = useState<'BUY' | 'SELL'>('BUY');
  const [timeframe, setTimeframe] = useState<string>('15M');
  const [entryPrice, setEntryPrice] = useState<number>(1.2850);
  const [stopLoss, setStopLoss] = useState<number>(1.2825);
  const [takeProfit, setTakeProfit] = useState<number>(1.2910);
  const [accountBalance, setAccountBalance] = useState<number>(10000);
  const [riskPct, setRiskPct] = useState<number>(1.0);
  const [sessionName, setSessionName] = useState<string>('LONDON');
  
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [auditOpen, setAuditOpen] = useState<boolean>(true);

  const handleSymbolChange = (newSymbol: string) => {
    setSymbol(newSymbol);
    const defaults = INSTRUMENT_DEFAULTS[newSymbol] || { entry: 1.0, stop: 0.99, target: 1.02 };
    setEntryPrice(defaults.entry);
    setStopLoss(defaults.stop);
    setTakeProfit(defaults.target);
  };

  const evaluateSetup = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/planner/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instrument: symbol,
          direction,
          timeframe,
          entry_price: entryPrice,
          stop_loss: stopLoss,
          take_profit: takeProfit,
          account_balance: accountBalance,
          risk_pct: riskPct,
          session_name: sessionName
        })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to evaluate setup');
      }
      const data: EvaluationResult = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Evaluation request failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    evaluateSetup();
  }, [symbol, direction, timeframe, sessionName]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Banner */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ padding: '10px', backgroundColor: 'rgba(0, 242, 254, 0.1)', borderRadius: '8px', border: '1px solid rgba(0, 242, 254, 0.3)', color: 'var(--accent-teal)' }}>
            <Scale size={24} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '10px' }}>
              Quantitative Trade Planner
              <span className="badge" style={{ backgroundColor: 'rgba(16, 185, 129, 0.2)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.4)', fontSize: '10px' }}>
                Centerpiece Engine
              </span>
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
              Evaluates trade parameters against historical MAE/MFE envelopes, Isotonic Calibration &amp; Decision Audit
            </p>
          </div>
        </div>

        <button
          onClick={evaluateSetup}
          disabled={loading}
          className="btn"
          style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: 'var(--accent-teal)', color: '#000', fontWeight: 800, padding: '10px 18px', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          <span>Evaluate Setup</span>
        </button>
      </div>

      <div className="dashboard-grid">
        {/* Left Column: Parameter Inputs */}
        <div className="col-5 glass-panel widget">
          <h3 className="widget-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={16} style={{ color: 'var(--accent-teal)' }} /> Setup Parameters
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '14px' }}>
            {/* Instrument & Direction */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Instrument</label>
                <select
                  value={symbol}
                  onChange={(e) => handleSymbolChange(e.target.value)}
                  className="form-input"
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  <option value="GBPUSD">GBPUSD</option>
                  <option value="EURUSD">EURUSD</option>
                  <option value="XAUUSD">XAUUSD (Gold)</option>
                  <option value="AUDUSD">AUDUSD</option>
                  <option value="USDJPY">USDJPY</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Direction</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', padding: '4px', backgroundColor: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <button
                    type="button"
                    onClick={() => setDirection('BUY')}
                    style={{
                      padding: '6px',
                      fontSize: '11px',
                      fontWeight: 800,
                      borderRadius: '6px',
                      border: 'none',
                      cursor: 'pointer',
                      backgroundColor: direction === 'BUY' ? '#10b981' : 'transparent',
                      color: direction === 'BUY' ? '#fff' : 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '4px'
                    }}
                  >
                    <ArrowUpRight size={14} /> BUY
                  </button>
                  <button
                    type="button"
                    onClick={() => setDirection('SELL')}
                    style={{
                      padding: '6px',
                      fontSize: '11px',
                      fontWeight: 800,
                      borderRadius: '6px',
                      border: 'none',
                      cursor: 'pointer',
                      backgroundColor: direction === 'SELL' ? '#ef4444' : 'transparent',
                      color: direction === 'SELL' ? '#fff' : 'var(--text-muted)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '4px'
                    }}
                  >
                    <ArrowDownRight size={14} /> SELL
                  </button>
                </div>
              </div>
            </div>

            {/* Timeframe & Session */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Timeframe</label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="form-input"
                >
                  <option value="5M">5M (Scalp)</option>
                  <option value="15M">15M (Execution)</option>
                  <option value="1H">1H (Day Trade)</option>
                  <option value="4H">4H (Swing)</option>
                  <option value="1D">1D (Macro)</option>
                </select>
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Session Corridor</label>
                <select
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  className="form-input"
                >
                  <option value="LONDON">London (07-13 UTC)</option>
                  <option value="NEW_YORK">New York (13-21 UTC)</option>
                  <option value="ASIA">Asia (00-07 UTC)</option>
                </select>
              </div>
            </div>

            {/* Prices */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Planned Entry Price</label>
              <input
                type="number"
                step="any"
                value={entryPrice}
                onChange={(e) => setEntryPrice(parseFloat(e.target.value) || 0)}
                className="form-input"
                style={{ fontFamily: 'var(--font-mono)' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ color: 'var(--accent-red)' }}>Stop Loss (SL)</label>
                <input
                  type="number"
                  step="any"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(parseFloat(e.target.value) || 0)}
                  className="form-input"
                  style={{ fontFamily: 'var(--font-mono)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label" style={{ color: 'var(--accent-green)' }}>Take Profit (TP)</label>
                <input
                  type="number"
                  step="any"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(parseFloat(e.target.value) || 0)}
                  className="form-input"
                  style={{ fontFamily: 'var(--font-mono)', borderColor: 'rgba(16, 185, 129, 0.3)' }}
                />
              </div>
            </div>

            {/* Account & Risk */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Account Balance ($)</label>
                <input
                  type="number"
                  value={accountBalance}
                  onChange={(e) => setAccountBalance(parseFloat(e.target.value) || 0)}
                  className="form-input"
                  style={{ fontFamily: 'var(--font-mono)' }}
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Risk Percentage (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={riskPct}
                  onChange={(e) => setRiskPct(parseFloat(e.target.value) || 0)}
                  className="form-input"
                  style={{ fontFamily: 'var(--font-mono)' }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Evaluation Output */}
        <div className="col-7 glass-panel widget" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: 'var(--accent-red)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          {result && (
            <>
              {/* Low Sample Size Warning Banner (N < 30) */}
              {result.low_confidence && (
                <div style={{ padding: '14px', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', color: 'var(--accent-orange)', fontSize: '12px', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <strong style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>Low Statistical Confidence Safeguard Active (N = {result.sample_size} &lt; 30)</strong>
                    <p style={{ margin: '4px 0 0 0', lineHeight: 1.4, color: 'var(--text-secondary)' }}>
                      Historical match count is under 30 observations. Statistical targets are grayed out to prevent over-reliance on small-sample noise. Consider reducing position sizing.
                    </p>
                  </div>
                </div>
              )}

              {/* Recommendation Hero Card */}
              <div 
                style={{
                  padding: '20px',
                  borderRadius: '12px',
                  backgroundColor: result.recommendation === 'PROCEED' ? 'rgba(16, 185, 129, 0.06)' : result.recommendation === 'WAIT' ? 'rgba(245, 158, 11, 0.06)' : 'rgba(239, 68, 68, 0.06)',
                  border: `1px solid ${result.recommendation_color}50`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span 
                        style={{
                          padding: '4px 10px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: 900,
                          textTransform: 'uppercase',
                          letterSpacing: '1px',
                          backgroundColor: result.recommendation_color,
                          color: '#000'
                        }}
                      >
                        {result.recommendation}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 700 }}>
                        Execution Grade: <strong style={{ color: '#fff', fontSize: '14px' }}>{result.execution_grade}</strong>
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        N = {result.sample_size} matches
                      </span>
                    </div>

                    <h3 style={{ margin: '10px 0 4px 0', fontSize: '18px', fontWeight: 800, color: '#fff' }}>
                      Should I take this trade? → <span style={{ color: result.recommendation_color }}>{result.recommendation}</span>
                    </h3>
                    <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {result.recommendation_summary}
                    </p>
                  </div>

                  {/* Expected Value Callout */}
                  <div style={{ padding: '12px 18px', backgroundColor: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border-color)', textAlign: 'center', minWidth: '120px' }}>
                    <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Expected Value</div>
                    <div style={{ fontSize: '24px', fontWeight: 900, fontFamily: 'var(--font-mono)', color: result.expected_r_multiple >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: '2px' }}>
                      {result.expected_r_multiple > 0 ? `+${result.expected_r_multiple}` : result.expected_r_multiple}R
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>per 1.0R risked</div>
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Calibrated WR</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-green)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {(result.calibrated_win_probability * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Raw: {(result.raw_win_probability * 100).toFixed(1)}%</div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Risk-Reward</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {result.risk_reward_ratio}:1
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{result.risk_pips}p / {result.reward_pips}p</div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Position Size</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {result.position_size_lots} Lots
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Risk: ${result.risk_amount_usd.toFixed(2)}</div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>MAE Survival</div>
                    <div style={{ fontSize: '16px', fontWeight: 800, color: '#c084fc', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                      {(result.empirical_mae.survival_rate * 100).toFixed(0)}%
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>P75 MAE: {result.empirical_mae.p75}p</div>
                  </div>
                </div>
              </div>

              {/* Decision Audit Accordion Card */}
              <div style={{ backgroundColor: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                <button
                  onClick={() => setAuditOpen(!auditOpen)}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    backgroundColor: 'rgba(255,255,255,0.02)',
                    border: 'none',
                    borderBottom: auditOpen ? '1px solid var(--border-color)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    color: '#fff'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Shield size={16} style={{ color: 'var(--accent-teal)' }} />
                    <span style={{ fontSize: '13px', fontWeight: 800 }}>Decision Audit &amp; Quantitative Reasoning Breakdown</span>
                    <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.06)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {result.decision_audit.positive_factors.length} positive · {result.decision_audit.warnings.length} warnings
                    </span>
                  </div>
                  {auditOpen ? <ChevronUp size={16} style={{ color: 'var(--text-muted)' }} /> : <ChevronDown size={16} style={{ color: 'var(--text-muted)' }} />}
                </button>

                {auditOpen && (
                  <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {/* Blockers */}
                    {result.decision_audit.blockers.length > 0 && (
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-red)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                          <XCircle size={14} /> Critical Blockers ({result.decision_audit.blockers.length})
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {result.decision_audit.blockers.map((b, idx) => (
                            <div key={idx} style={{ fontSize: '12px', color: 'var(--accent-red)', padding: '8px 12px', borderRadius: '6px', backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', fontFamily: 'var(--font-mono)' }}>
                              {b}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Positive Drivers */}
                    {result.decision_audit.positive_factors.length > 0 && (
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-green)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                          <CheckCircle2 size={14} /> Supporting Quantitative Drivers ({result.decision_audit.positive_factors.length})
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {result.decision_audit.positive_factors.map((p, idx) => (
                            <div key={idx} style={{ fontSize: '12px', color: 'var(--accent-green)', padding: '8px 12px', borderRadius: '6px', backgroundColor: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', fontFamily: 'var(--font-mono)' }}>
                              {p}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Warnings */}
                    {result.decision_audit.warnings.length > 0 && (
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-orange)', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                          <AlertTriangle size={14} /> Quantitative Warnings &amp; Risks ({result.decision_audit.warnings.length})
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {result.decision_audit.warnings.map((w, idx) => (
                            <div key={idx} style={{ fontSize: '12px', color: 'var(--accent-orange)', padding: '8px 12px', borderRadius: '6px', backgroundColor: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', fontFamily: 'var(--font-mono)' }}>
                              {w}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Entry Zone Recommendation */}
              {result.entry_zone_recommendation && (
                <div style={{ backgroundColor: 'rgba(0, 242, 254, 0.04)', borderRadius: '10px', border: '1px solid rgba(0, 242, 254, 0.2)', padding: '16px' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 800, color: 'var(--accent-teal)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Zap size={15} /> Quantitative Entry Zone (Based on Winning-Trade Historical Drawdown)
                  </h4>

                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5, marginBottom: '12px' }}>
                    The entry zone is derived from the <strong style={{ color: 'var(--text-secondary)' }}>P75 MAE drawdown</strong> of historical winning trades in this regime.
                    Rather than just following price, we look at <em>where winning trades actually retrace before running</em> — and recommend entering anywhere inside that zone.
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '12px' }}>
                    <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Aggressive Entry</div>
                      <div style={{ fontSize: '15px', fontWeight: 800, color: '#fff', fontFamily: 'var(--font-mono)' }}>
                        {result.entry_zone_recommendation.aggressive_entry.toFixed(result.instrument === 'USDJPY' ? 3 : result.instrument === 'XAUUSD' ? 2 : 5)}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>At market (planned)</div>
                    </div>

                    <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: 'rgba(0, 242, 254, 0.06)', border: '1px solid rgba(0, 242, 254, 0.25)', textAlign: 'center' }}>
                      <div style={{ fontSize: '10px', color: 'var(--accent-teal)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>Optimal Zone</div>
                      <div style={{ fontSize: '12px', fontWeight: 800, color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)', lineHeight: 1.4 }}>
                        {result.entry_zone_recommendation.optimal_zone_min.toFixed(result.instrument === 'USDJPY' ? 3 : result.instrument === 'XAUUSD' ? 2 : 5)}
                        <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>→</span>
                        {result.entry_zone_recommendation.optimal_zone_max.toFixed(result.instrument === 'USDJPY' ? 3 : result.instrument === 'XAUUSD' ? 2 : 5)}
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>Limit order zone</div>
                    </div>

                    <div style={{ padding: '10px', borderRadius: '8px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Zone Width (P75 MAE)</div>
                      <div style={{ fontSize: '15px', fontWeight: 800, color: '#c084fc', fontFamily: 'var(--font-mono)' }}>
                        {result.entry_zone_recommendation.mae_p75_pips} pips
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>75th %ile adverse pull</div>
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '8px 12px', borderRadius: '6px', backgroundColor: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', lineHeight: 1.6 }}>
                    💡 <strong style={{ color: 'var(--text-secondary)' }}>How to use:</strong> Place a limit order between the zone boundaries.
                    If {result.direction === 'BUY' ? 'price dips into this zone' : 'price rallies into this zone'}, historical winning trades show this is a statistically favourable entry window, not just noise.
                    Entries beyond the P75 zone ({result.empirical_mae.p90} pips) begin entering stop-out territory.
                  </div>
                </div>
              )}

              {/* Empirical MAE/MFE Envelope Comparison */}
              <div style={{ backgroundColor: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border-color)', padding: '16px' }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <BarChart2 size={16} style={{ color: '#c084fc' }} />
                  Empirical Excursion Envelope vs Planned Targets
                </h4>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {/* MAE Envelope */}
                  <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-red)', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Adverse Excursion (MAE)</span>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>SL: {result.risk_pips}p</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                        <span>P50 MAE (Median Drawdown)</span>
                        <strong style={{ color: '#fff' }}>{result.empirical_mae.p50} pips</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                        <span>P75 MAE (High Volatility)</span>
                        <span>{result.empirical_mae.p75} pips</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                        <span>P90 Survival Stop</span>
                        <span>{result.empirical_mae.p90} pips</span>
                      </div>
                    </div>
                  </div>

                  {/* MFE Envelope */}
                  <div style={{ padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-green)', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Favorable Expansion (MFE)</span>
                      <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>TP: {result.reward_pips}p</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '8px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                        <span>P50 MFE (Target 1)</span>
                        <strong style={{ color: '#fff' }}>{result.empirical_mfe.p50} pips</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                        <span>P75 MFE (Target 2)</span>
                        <span>{result.empirical_mfe.p75} pips</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                        <span>P90 Max Target</span>
                        <span>{result.empirical_mfe.p90} pips</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
