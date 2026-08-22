import React from 'react';
import { X, Calendar, Clock, Activity, CheckCircle, AlertTriangle, Target, ShieldAlert } from 'lucide-react';

interface HistoricalMatchModalProps {
  isOpen: boolean;
  onClose: () => void;
  signature: {
    date: string;
    outcome: string;
    mae_pips: number;
    mfe_pips: number;
    session: string;
    trend: string;
    dxy_state?: string;
    risk_sentiment?: string;
    holding_time_minutes?: number;
    supporting_macro_conditions?: {
      dxy_index?: number;
      us10y_yield?: number;
      vix?: number;
    };
  } | null;
  instrument: string;
}

export default function HistoricalMatchModal({ isOpen, onClose, signature, instrument }: HistoricalMatchModalProps) {
  if (!isOpen || !signature) return null;

  const isWin = signature.outcome === 'WIN';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      backdropFilter: 'blur(6px)',
      padding: '20px'
    }}>
      <div className="animate-fade-in glass-panel" style={{
        width: '100%',
        maxWidth: '540px',
        borderRadius: '16px',
        border: `1px solid ${isWin ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
        padding: '24px',
        position: 'relative',
        backgroundColor: '#0d1117',
        boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            background: 'rgba(255,255,255,0.05)',
            border: 'none',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#94a3b8',
            cursor: 'pointer'
          }}
        >
          <X size={16} />
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <span style={{
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: 800,
            backgroundColor: isWin ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)',
            color: isWin ? '#10b981' : '#ef4444',
            border: `1px solid ${isWin ? 'rgba(16,185,129,0.4)' : 'rgba(239,68,68,0.4)'}`,
            display: 'flex',
            alignItems: 'center',
            gap: '5px'
          }}>
            {isWin ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
            {signature.outcome} SIGNATURE
          </span>

          <span style={{ fontSize: '15px', fontWeight: 700, color: '#fff' }}>
            {instrument} · {signature.date}
          </span>
        </div>

        {/* Core Metrics Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '10px', color: '#ef4444', fontWeight: 700, textTransform: 'uppercase' }}>Max Adverse (MAE)</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginTop: '2px' }}>{signature.mae_pips} pips</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Drawdown before exit</div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '10px', color: '#10b981', fontWeight: 700, textTransform: 'uppercase' }}>Max Favorable (MFE)</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginTop: '2px' }}>{signature.mfe_pips} pips</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Maximum upside expansion</div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase' }}>Execution Session</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{signature.session}</div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '10px', color: 'var(--accent-teal)', fontWeight: 700, textTransform: 'uppercase' }}>Holding Duration</div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>{signature.holding_time_minutes != null ? `${signature.holding_time_minutes} min` : 'N/A'}</div>
          </div>
        </div>

        {/* Macro Context Snapshot */}
        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)', marginBottom: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Activity size={12} style={{ color: 'var(--accent-teal)' }} /> Supporting Macro Environment
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
            <span>Macro Trend: <strong style={{ color: signature.trend === 'BULLISH' ? '#10b981' : '#ef4444' }}>{signature.trend}</strong></span>
            <span>DXY Regime: <strong style={{ color: '#fff' }}>{signature.dxy_state || 'BEARISH'}</strong></span>
            <span>Risk Sentiment: <strong style={{ color: '#fff' }}>{signature.risk_sentiment || 'NEUTRAL'}</strong></span>
          </div>
        </div>

        {/* Signature Failure / Success Explanation */}
        <div style={{
          padding: '12px',
          borderRadius: '8px',
          backgroundColor: isWin ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
          border: `1px solid ${isWin ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
          fontSize: '12px',
          color: 'var(--text-secondary)'
        }}>
          <strong>{isWin ? '✅ Success Driver:' : '❌ Failure Reason:'}</strong>{' '}
          {isWin 
            ? `Price expanded cleanly during ${signature.session} session in alignment with structural ${signature.trend} macro momentum with minimal drawdown (${signature.mae_pips} pips).`
            : `Drawdown breached 90th percentile survival stop (${signature.mae_pips} pips) during ${signature.session} session prior to MFE expansion.`
          }
        </div>
      </div>
    </div>
  );
}
