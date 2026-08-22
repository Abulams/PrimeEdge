import React, { useState } from 'react';
import { Target, AlertTriangle, ShieldCheck, Check, X, ArrowRight, Activity } from 'lucide-react';

interface TakeSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  instrument: string;
  setupData: {
    status_state?: string;
    direction?: string;
    setup_ref_price?: number;
    corridor_p25_price?: number;
    corridor_p75_price?: number;
    p90_invalidation?: number;
    expected_mfe?: number;
    continuation_prob?: number;
    trade_thesis?: string;
  };
  onConfirm: (payload: {
    actual_entry: number;
    actual_sl: number;
    actual_tp: number;
    entry_type: string;
    position_size_lots: number;
    risk_pct: number;
    account_balance: number;
    notes?: string;
  }) => void;
}

export function TakeSetupModal({ isOpen, onClose, instrument, setupData, onConfirm }: TakeSetupModalProps) {
  if (!isOpen) return null;

  const isLong = (setupData.direction || 'LONG').toUpperCase() === 'LONG';
  const refPrice = setupData.setup_ref_price || 1.3465;
  const p25Price = setupData.corridor_p25_price || refPrice;
  const p90Price = setupData.p90_invalidation || (isLong ? refPrice - 0.0035 : refPrice + 0.0035);
  const isJpyOrGold = instrument.includes('JPY') || instrument.includes('XAU') || instrument.includes('GOLD');
  const pipMult = isJpyOrGold ? (instrument.includes('JPY') ? 100 : 10) : 10000;
  const pipUnit = 1 / pipMult;

  // Recommended TP is P75 MFE (~1.4x expected MFE)
  const defaultMfePips = setupData.expected_mfe ? setupData.expected_mfe * 1.4 : 25;
  const defaultTpPrice = isLong
    ? Number((refPrice + defaultMfePips * pipUnit).toFixed(5))
    : Number((refPrice - defaultMfePips * pipUnit).toFixed(5));

  // Form State pre-filled with V4 recommendations
  const [actualEntry, setActualEntry] = useState<string>(p25Price.toString());
  const [actualSl, setActualSl] = useState<string>(p90Price.toString());
  const [actualTp, setActualTp] = useState<string>(defaultTpPrice.toString());
  const [entryType, setEntryType] = useState<string>('LIMIT');
  const [positionSize, setPositionSize] = useState<string>('0.10');
  const [riskPct, setRiskPct] = useState<string>('1.0');
  const [accountBalance, setAccountBalance] = useState<string>('10000');
  const [notes, setNotes] = useState<string>('');

  const numEntry = parseFloat(actualEntry) || p25Price;
  const numSl = parseFloat(actualSl) || p90Price;
  const numTp = parseFloat(actualTp) || defaultTpPrice;

  // Live deviation calculations
  const entryDevPips = Number((Math.abs(numEntry - p25Price) * pipMult).toFixed(1));
  const slDevPips = Number((Math.abs(numSl - p90Price) * pipMult).toFixed(1));
  const riskPips = Number((Math.abs(numEntry - numSl) * pipMult).toFixed(1));
  const rewardPips = Number((Math.abs(numTp - numEntry) * pipMult).toFixed(1));
  const rrRatio = riskPips > 0 ? Number((rewardPips / riskPips).toFixed(2)) : 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm({
      actual_entry: numEntry,
      actual_sl: numSl,
      actual_tp: numTp,
      entry_type: entryType,
      position_size_lots: parseFloat(positionSize) || 0.1,
      risk_pct: parseFloat(riskPct) || 1.0,
      account_balance: parseFloat(accountBalance) || 10000,
      notes: notes.trim() || undefined
    });
  };

  return (
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
      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '640px',
        maxHeight: '90vh',
        overflowY: 'auto',
        borderRadius: '12px',
        border: '1px solid var(--accent-teal)',
        boxShadow: '0 20px 50px rgba(0,242,254,0.15)',
        padding: '24px'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{
                fontSize: '18px',
                fontWeight: 800,
                color: isLong ? 'var(--accent-green)' : 'var(--accent-red)',
                letterSpacing: '0.5px'
              }}>
                TAKE SETUP — {instrument} {setupData.direction || 'LONG'}
              </span>
              <span className={`status-badge badge-${(setupData.status_state || 'WAIT').toLowerCase()}`}>
                {setupData.status_state || 'WAIT'}
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Grounding execution in Market OS V4 T₀ Statistical Distribution
            </p>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X style={{ width: '20px', height: '20px' }} />
          </button>
        </div>

        {/* System Recommended vs Trader Input */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px',
          marginBottom: '20px',
          padding: '14px',
          background: 'rgba(255,255,255,0.02)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)'
        }}>
          <div>
            <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--accent-teal)', fontWeight: 700, letterSpacing: '0.5px' }}>
              MARKET OS V4 RECOMMENDATION
            </span>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.6 }}>
              <div>• <strong>Ref (T₀):</strong> {refPrice}</div>
              <div>• <strong>P25 Corridor Entry:</strong> {p25Price}</div>
              <div>• <strong>P90 Invalidation SL:</strong> {p90Price}</div>
              <div>• <strong>P75 MFE Target:</strong> {defaultTpPrice}</div>
            </div>
          </div>

          <div>
            <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--accent-green)', fontWeight: 700, letterSpacing: '0.5px' }}>
              LIVE EXECUTION DEVIATION
            </span>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.6 }}>
              <div>
                • Entry Dev: <strong style={{ color: entryDevPips > 5 ? 'var(--accent-orange)' : 'var(--accent-green)' }}>
                  {entryDevPips} pips
                </strong> {entryDevPips === 0 ? '(Exact P25)' : entryDevPips > 5 ? '(Out-of-corridor)' : '(Near P25)'}
              </div>
              <div>
                • SL Dev: <strong style={{ color: slDevPips > 10 ? 'var(--accent-orange)' : 'var(--text-primary)' }}>
                  {slDevPips} pips
                </strong> from P90
              </div>
              <div>• Risk/Reward: <strong style={{ color: rrRatio >= 1.5 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>1:{rrRatio}</strong></div>
              <div>• Risk Distance: <strong>{riskPips} pips</strong></div>
            </div>
          </div>
        </div>

        {/* Execution Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '16px' }}>
            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Execution Type
              </label>
              <select
                className="form-input"
                value={entryType}
                onChange={(e) => setEntryType(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="LIMIT">LIMIT (P25 Corridor Limit)</option>
                <option value="MARKET">MARKET (Immediate Fill)</option>
              </select>
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Actual Entry Price
              </label>
              <input
                type="number"
                step="0.00001"
                className="form-input"
                value={actualEntry}
                onChange={(e) => setActualEntry(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Stop Loss (SL)
              </label>
              <input
                type="number"
                step="0.00001"
                className="form-input"
                value={actualSl}
                onChange={(e) => setActualSl(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Take Profit (TP)
              </label>
              <input
                type="number"
                step="0.00001"
                className="form-input"
                value={actualTp}
                onChange={(e) => setActualTp(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Position Size (Lots)
              </label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={positionSize}
                onChange={(e) => setPositionSize(e.target.value)}
                required
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Risk % / Account ($)
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="number"
                  step="0.1"
                  className="form-input"
                  value={riskPct}
                  onChange={(e) => setRiskPct(e.target.value)}
                  placeholder="Risk %"
                  style={{ width: '50%' }}
                />
                <input
                  type="number"
                  step="100"
                  className="form-input"
                  value={accountBalance}
                  onChange={(e) => setAccountBalance(e.target.value)}
                  placeholder="Balance"
                  style={{ width: '50%' }}
                />
              </div>
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Execution Notes (Optional)
            </label>
            <input
              type="text"
              className="form-input"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Entering at limit P25 corridor after London open displacement"
              style={{ width: '100%' }}
            />
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="btn"
              onClick={onClose}
              style={{ padding: '8px 18px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn"
              style={{
                padding: '8px 22px',
                background: 'linear-gradient(135deg, var(--accent-teal), #00c6ff)',
                color: '#000',
                fontWeight: 700
              }}
            >
              <Check style={{ width: '16px', height: '16px', marginRight: '6px' }} />
              Confirm & Record Trade
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
