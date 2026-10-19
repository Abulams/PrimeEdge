import React, { useState, useEffect } from 'react';
import {
  Zap, Shield, Server, Activity, ArrowUpRight, ArrowDownRight,
  Download, CheckCircle, AlertTriangle, Play, Pause, RefreshCw,
  Terminal, Lock, Check, Send, AlertCircle, Radio, Cpu, Settings, X, Eye, EyeOff, ShieldAlert
} from 'lucide-react';
import { useAuth, apiFetch } from './AuthContext';
import { FounderAdminDashboard } from './FounderAdminDashboard';

interface CloudAccountStatus {
  connected: boolean;
  account_id?: number;
  auto_execution_enabled: boolean;
  account_info: {
    login?: number;
    server?: string;
    balance?: number;
    equity?: number;
    currency?: string;
    leverage?: number;
    ping_ms?: number;
    allocated_worker?: string;
    last_heartbeat?: string;
  };
  open_positions_count: number;
  guardrail_config: {
    max_spread_pips: number;
    max_slippage_pips: number;
    early_invalidation_mae_r: number;
    mfe_disarm_r: number;
  };
}

interface Position {
  ticket_id: string;
  platform?: string;
  instrument: string;
  direction: 'LONG' | 'SHORT';
  open_price: number;
  current_price: number;
  stop_loss: number;
  take_profit: number;
  position_size_lots: number;
  max_mae_pips: number;
  max_mfe_pips: number;
  current_pnl_pips: number;
  current_pnl_r?: number;
  early_inval_armed: boolean;
  early_inval_pips: number;
  mfe_disarm_pips: number;
  open_time: string;
  comment?: string;
}

interface AdminOpsData {
  global_killswitch_active: boolean;
  total_subscribers: number;
  total_workers: number;
  workers: Array<{
    worker_id: string;
    hostname: string;
    ip_address: string;
    status: string;
    cpu_pct: number;
    ram_pct: number;
    active_terminals: number;
    max_terminals: number;
    last_heartbeat: string;
  }>;
  accounts: Array<{
    account_id: number;
    user_email: string;
    login: number;
    server: string;
    worker_id: string;
    balance: number;
    equity: number;
    ping_ms: number;
    is_active: boolean;
    auto_execution_enabled: boolean;
    killswitch_active: boolean;
    open_positions: number;
    last_heartbeat: string;
    error?: string;
  }>;
  recent_audits: Array<{
    id: number;
    ticket_id: string;
    signal_id: string;
    instrument: string;
    direction: string;
    entry_price: number;
    exit_price?: number;
    status: string;
    exit_reason?: string;
    pnl_r?: number;
    latency_ms: number;
    timestamp: string;
  }>;
}

interface ClosedTrade {
  id: number;
  ticket_id: string;
  instrument: string;
  direction: string;
  position_size_lots: number;
  entry_price: number;
  exit_price?: number;
  exit_reason: string;
  outcome: string;
  pnl_pips: number;
  pnl_r: number;
  entry_time: string;
  exit_time: string;
}

export const ExecutionTab: React.FC = () => {
  const { user } = useAuth();
  const [viewMode, setViewMode] = useState<'subscriber' | 'admin'>('subscriber');
  
  // Subscriber State
  const [cloudStatus, setCloudStatus] = useState<CloudAccountStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [closedHistory, setClosedHistory] = useState<ClosedTrade[]>([]);
  const [loading, setLoading] = useState(false);
  const [connectSuccess, setConnectSuccess] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  
  const [brokerServer, setBrokerServer] = useState('ICMarketsSC-Demo');
  const [loginAccount, setLoginAccount] = useState('8809124');
  const [loginPassword, setLoginPassword] = useState('DemoPassword123!');

  // Admin Ops State
  const [adminData, setAdminData] = useState<AdminOpsData | null>(null);
  const [adminLoading, setAdminLoading] = useState(false);

  // Risk & Asset Allocation Preferences
  const [riskMode, setRiskMode] = useState<'FIXED_LOT' | 'DYNAMIC_RISK_PCT'>('FIXED_LOT');
  const [riskPct, setRiskPct] = useState<number>(1.0);
  const [fixedLotSize, setFixedLotSize] = useState<number>(0.01);
  const [allowedInstruments, setAllowedInstruments] = useState<string[]>(['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US100', 'USDCHF']);
  const [maxConcurrentTrades, setMaxConcurrentTrades] = useState<number>(3);
  const [maxDailyLossPct, setMaxDailyLossPct] = useState<number>(3.0);
  const [prefSaving, setPrefSaving] = useState(false);
  const [prefSaveMessage, setPrefSaveMessage] = useState<string | null>(null);

  const fetchPreferences = async () => {
    try {
      const resPref = await apiFetch('/api/v1/execution/cloud/preferences');
      if (resPref.ok) {
        const prefData = await resPref.json();
        setRiskMode(prefData.risk_mode || 'FIXED_LOT');
        setRiskPct(prefData.risk_pct || 1.0);
        setFixedLotSize(prefData.fixed_lot_size || 0.01);
        if (Array.isArray(prefData.allowed_instruments)) {
          setAllowedInstruments(prefData.allowed_instruments);
        }
        setMaxConcurrentTrades(prefData.max_concurrent_trades || 3);
        setMaxDailyLossPct(prefData.max_daily_loss_pct || 3.0);
      }
    } catch (e) {
      console.error('Error fetching preferences:', e);
    }
  };

  const fetchSubscriberData = async () => {
    try {
      const [resStatus, resPos, resHist] = await Promise.all([
        apiFetch('/api/v1/execution/cloud/status'),
        apiFetch('/api/v1/execution/cloud/positions'),
        apiFetch('/api/v1/execution/cloud/history')
      ]);
      if (resStatus.ok) {
        const data = await resStatus.json();
        setCloudStatus(data);
      }
      if (resPos.ok) {
        const posData = await resPos.json();
        setPositions(posData);
      }
      if (resHist.ok) {
        const histData = await resHist.json();
        setClosedHistory(histData);
      }
    } catch (e) {
      console.error('Error fetching subscriber execution data:', e);
    }
  };

  const handleSavePreferences = async () => {
    setPrefSaving(true);
    setPrefSaveMessage(null);
    try {
      const res = await apiFetch('/api/v1/execution/cloud/preferences', {
        method: 'POST',
        body: JSON.stringify({
          risk_mode: riskMode,
          risk_pct: riskPct,
          fixed_lot_size: fixedLotSize,
          allowed_instruments: allowedInstruments,
          max_concurrent_trades: maxConcurrentTrades,
          max_daily_loss_pct: maxDailyLossPct,
        })
      });
      if (res.ok) {
        setPrefSaveMessage('✅ Risk & Asset preferences saved successfully!');
        setTimeout(() => setPrefSaveMessage(null), 4000);
      } else {
        setPrefSaveMessage('❌ Failed to save preferences.');
      }
    } catch (e) {
      console.error('Error saving preferences:', e);
      setPrefSaveMessage('❌ Error saving preferences.');
    } finally {
      setPrefSaving(false);
    }
  };

  const fetchAdminData = async () => {
    if (!user?.is_admin && viewMode !== 'admin') return;
    setAdminLoading(true);
    try {
      const res = await apiFetch('/api/v1/execution/admin/operations');
      if (res.ok) {
        const data = await res.json();
        setAdminData(data);
      }
    } catch (e) {
      console.error('Error fetching admin operations data:', e);
    } finally {
      setAdminLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscriberData();
    fetchPreferences();
    const interval = setInterval(() => {
      if (viewMode === 'subscriber') {
        fetchSubscriberData();
      } else {
        fetchAdminData();
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [viewMode]);

  const handleConnectCloud = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/execution/cloud/connect', {
        method: 'POST',
        body: JSON.stringify({
          broker_server: brokerServer,
          login: parseInt(loginAccount),
          password: loginPassword,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setConnectSuccess(`Successfully connected MT5 account ${data.login} on ${data.server} (Zero-Install Cloud Session)`);
        setShowConfig(false);
        await fetchSubscriberData();
      }
    } catch (e) {
      console.error('Connection error:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAuto = async () => {
    if (!cloudStatus) return;
    try {
      const res = await apiFetch('/api/v1/execution/cloud/toggle-auto', {
        method: 'POST',
        body: JSON.stringify({ enabled: !cloudStatus.auto_execution_enabled })
      });
      if (res.ok) {
        await fetchSubscriberData();
      }
    } catch (e) {
      console.error('Toggle error:', e);
    }
  };

  const handleAdminGlobalKillswitch = async (enabled: boolean) => {
    try {
      const res = await apiFetch('/api/v1/execution/admin/killswitch/global', {
        method: 'POST',
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        await fetchAdminData();
      }
    } catch (e) {
      console.error('Admin killswitch error:', e);
    }
  };

  const handleAdminAccountKillswitch = async (accountId: number, enabled: boolean) => {
    try {
      const res = await apiFetch(`/api/v1/execution/admin/killswitch/account/${accountId}`, {
        method: 'POST',
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        await fetchAdminData();
      }
    } catch (e) {
      console.error('Account killswitch error:', e);
    }
  };

  const [testTradeLoading, setTestTradeLoading] = useState(false);
  const [testTradeMessage, setTestTradeMessage] = useState<string | null>(null);

  const handleForceTestTrade = async (symbol: string = 'EURUSD', dir: string = 'LONG') => {
    setTestTradeLoading(true);
    setTestTradeMessage(null);
    try {
      const res = await apiFetch('/api/v1/execution/cloud/force-test-trade', {
        method: 'POST',
        body: JSON.stringify({ instrument: symbol, direction: dir, volume: 0.01 })
      });
      if (res.ok) {
        setTestTradeMessage(`🚀 Test trade dispatched: ${symbol} ${dir} (0.01 lots) queued for London MT5 Cloud Worker!`);
        setTimeout(() => fetchSubscriberData(), 1000);
      } else {
        setTestTradeMessage('❌ Failed to dispatch test trade. Check cloud worker status.');
      }
    } catch (e) {
      setTestTradeMessage('❌ Network error while dispatching test trade.');
    } finally {
      setTestTradeLoading(false);
    }
  };

  const isConnected = cloudStatus?.connected ?? false;
  const acc = cloudStatus?.account_info || {};

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header with Role View Mode Toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, margin: '0 0 4px 0', letterSpacing: '-0.5px' }}>
            EXECUTION — Cloud cTrader Gateway
          </h2>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
            Zero-install institutional trade copying via Spotware OpenAPI with sub-second early invalidation guardrails.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {user?.is_admin && (
            <div style={{
              display: 'flex',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              padding: '3px',
              border: '1px solid var(--border-color)'
            }}>
              <button
                onClick={() => { setViewMode('subscriber'); fetchSubscriberData(); }}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: viewMode === 'subscriber' ? 'var(--bg-tertiary)' : 'transparent',
                  color: viewMode === 'subscriber' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease',
                }}
              >
                Subscriber View
              </button>
              <button
                onClick={() => { setViewMode('admin'); fetchAdminData(); }}
                style={{
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 700,
                  background: viewMode === 'admin' ? 'var(--bg-tertiary)' : 'transparent',
                  color: viewMode === 'admin' ? 'var(--accent-teal)' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Cpu size={14} /> Admin Operations
              </button>
            </div>
          )}

          <button
            onClick={() => { viewMode === 'subscriber' ? fetchSubscriberData() : fetchAdminData(); }}
            style={{
              padding: '8px 12px',
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {testTradeMessage && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(0, 242, 254, 0.12)',
          border: '1px solid rgba(0, 242, 254, 0.35)',
          borderRadius: '8px',
          color: 'var(--accent-teal)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '13px',
          fontWeight: 700
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={16} /> {testTradeMessage}
          </div>
          <X size={16} style={{ cursor: 'pointer' }} onClick={() => setTestTradeMessage(null)} />
        </div>
      )}

      {connectSuccess && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(16,185,129,0.12)',
          border: '1px solid rgba(16,185,129,0.3)',
          borderRadius: '8px',
          color: 'var(--accent-green)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '13px',
          fontWeight: 600
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle size={16} /> {connectSuccess}
          </div>
          <X size={16} style={{ cursor: 'pointer' }} onClick={() => setConnectSuccess(null)} />
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. SUBSCRIBER VIEW (ZERO-INSTALL)                                         */}
      {/* ========================================================================= */}
      {viewMode === 'subscriber' && (
        <>
          {/* Top Gateway Status & Controls Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            
            {/* Terminal Status Card */}
            <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Server size={18} color="var(--accent-teal)" />
                  <span style={{ fontSize: '14px', fontWeight: 700 }}>Cloud cTrader Account</span>
                </div>
                <div style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 800,
                  letterSpacing: '0.5px',
                  background: isConnected ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                  color: isConnected ? 'var(--accent-green)' : 'var(--accent-red)',
                  border: `1px solid ${isConnected ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`
                }}>
                  {isConnected ? 'ONLINE & SYNCED' : 'DISCONNECTED'}
                </div>
              </div>

              {isConnected ? (
                <div className="why-grid-2col" style={{ gap: '10px' }}>
                  <div style={{ background: 'var(--bg-primary)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>cTrader Account</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, marginTop: '2px' }}>#{acc.login || '—'}</div>
                    <div style={{ fontSize: '10px', color: 'var(--accent-teal)', marginTop: '2px' }}>{acc.server || 'cTrader-Cloud'}</div>
                  </div>

                  <div style={{ background: 'var(--bg-primary)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Account Equity</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: (acc.equity ?? 0) > 0 ? 'var(--accent-green)' : 'var(--text-secondary)', marginTop: '2px' }}>
                      ${(acc.equity ?? 0.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Bal: ${(acc.balance ?? 0.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{
                  padding: '14px',
                  background: 'var(--bg-primary)',
                  borderRadius: '8px',
                  border: '1px dashed var(--border-color)',
                  textAlign: 'center',
                  color: 'var(--text-secondary)',
                  fontSize: '13px'
                }}>
                  No cTrader account connected yet. Click below to link via 1-click OAuth.
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <button
                  onClick={() => {
                    const userId = user?.id || 1;
                    window.location.href = `/api/v1/ctrader/auth?user_id=${userId}`;
                  }}
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                    color: '#08090d',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 800,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                    boxShadow: '0 2px 10px rgba(0, 242, 254, 0.25)'
                  }}
                >
                  <Zap size={14} /> {isConnected ? 'Re-authorize cTrader' : 'Connect with cTrader (OAuth)'}
                </button>
              </div>
            </div>

            {/* Auto Execution & Invalidation Rules Card */}
            <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Zap size={18} color="var(--accent-green)" />
                  <span style={{ fontSize: '14px', fontWeight: 700 }}>Auto-Execution Guardrails</span>
                </div>
                <div style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 800,
                  background: cloudStatus?.auto_execution_enabled ? 'rgba(16,185,129,0.15)' : 'rgba(148,163,184,0.15)',
                  color: cloudStatus?.auto_execution_enabled ? 'var(--accent-green)' : 'var(--text-secondary)',
                  border: `1px solid ${cloudStatus?.auto_execution_enabled ? 'rgba(16,185,129,0.3)' : 'var(--border-color)'}`
                }}>
                  {cloudStatus?.auto_execution_enabled ? 'EXECUTION ACTIVE' : 'PAUSED'}
                </div>
              </div>

              <div className="why-grid-3col">
                <div style={{ background: 'var(--bg-primary)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Early Inval</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--accent-red)', marginTop: '2px' }}>-0.35R</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-secondary)' }}>MAE Liquidate</div>
                </div>

                <div style={{ background: 'var(--bg-primary)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Disarm Level</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--accent-green)', marginTop: '2px' }}>+0.35R</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-secondary)' }}>MFE Runner</div>
                </div>

                <div style={{ background: 'var(--bg-primary)', padding: '8px 10px', borderRadius: '8px', border: '1px solid var(--border-color)', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Max Spread</div>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--accent-teal)', marginTop: '2px' }}>&le; 2.5 pips</div>
                  <div style={{ fontSize: '9px', color: 'var(--text-secondary)' }}>Pre-Trade</div>
                </div>
              </div>

              <button
                onClick={handleToggleAuto}
                style={{
                  marginTop: 'auto',
                  padding: '10px',
                  borderRadius: '8px',
                  border: 'none',
                  background: cloudStatus?.auto_execution_enabled
                    ? 'rgba(239,68,68,0.2)'
                    : 'linear-gradient(135deg, var(--accent-green), var(--accent-teal))',
                  color: cloudStatus?.auto_execution_enabled ? 'var(--accent-red)' : '#fff',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'all 0.15s ease'
                }}
              >
                {cloudStatus?.auto_execution_enabled ? (
                  <><Pause size={15} /> Pause Auto-Execution</>
                ) : (
                  <><Play size={15} /> Activate Cloud Auto-Execution</>
                )}
              </button>
            </div>
          </div>

          {/* Risk Sizing & Asset Preferences Card (Prop Desk Model) */}
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Shield size={18} color="var(--accent-teal)" />
                <h3 style={{ fontSize: '15px', fontWeight: 800, margin: 0 }}>Subscriber Risk & Asset Allocation Preferences</h3>
                <span style={{ fontSize: '11px', color: 'var(--accent-teal)', background: 'rgba(0, 242, 254, 0.1)', padding: '2px 8px', borderRadius: '10px', fontWeight: 700 }}>
                  PROP DESK MODEL
                </span>
              </div>

              {prefSaveMessage && (
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-green)', background: 'rgba(16,185,129,0.12)', padding: '4px 12px', borderRadius: '8px', border: '1px solid rgba(16,185,129,0.3)' }}>
                  {prefSaveMessage}
                </div>
              )}
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.5' }}>
              Customize your capital sizing and choose exactly which asset classes to auto-execute. Institutional entry corridors ($T_0$), -0.35R early loss-cutting, and structural stop losses remain automatically managed by Market OS.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {/* 1. Asset Selection & Filters */}
              <div style={{ background: 'var(--bg-primary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>🎯 Allowed Asset Classes</span>
                  <span style={{ fontSize: '11px', color: 'var(--accent-teal)' }}>{allowedInstruments.length} Selected</span>
                </div>

                {/* Quick Presets */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  <button
                    type="button"
                    onClick={() => setAllowedInstruments(['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US100', 'USDCHF'])}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: '1px solid var(--border-color)',
                      background: allowedInstruments.length === 6 ? 'rgba(0, 242, 254, 0.15)' : 'var(--bg-secondary)',
                      color: allowedInstruments.length === 6 ? 'var(--accent-teal)' : 'var(--text-secondary)'
                    }}
                  >
                    All Assets
                  </button>

                  <button
                    type="button"
                    onClick={() => setAllowedInstruments(['XAUUSD'])}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: '1px solid var(--border-color)',
                      background: (allowedInstruments.length === 1 && allowedInstruments.includes('XAUUSD')) ? 'rgba(234, 179, 8, 0.2)' : 'var(--bg-secondary)',
                      color: (allowedInstruments.length === 1 && allowedInstruments.includes('XAUUSD')) ? '#eab308' : 'var(--text-secondary)'
                    }}
                  >
                    🥇 Gold Only
                  </button>

                  <button
                    type="button"
                    onClick={() => setAllowedInstruments(['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF'])}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: '1px solid var(--border-color)',
                      background: (allowedInstruments.includes('EURUSD') && !allowedInstruments.includes('XAUUSD') && !allowedInstruments.includes('US100')) ? 'rgba(59, 130, 246, 0.2)' : 'var(--bg-secondary)',
                      color: (allowedInstruments.includes('EURUSD') && !allowedInstruments.includes('XAUUSD') && !allowedInstruments.includes('US100')) ? '#3b82f6' : 'var(--text-secondary)'
                    }}
                  >
                    💱 Forex Only
                  </button>

                  <button
                    type="button"
                    onClick={() => setAllowedInstruments(['XAUUSD', 'US100'])}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '6px',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      border: '1px solid var(--border-color)',
                      background: (allowedInstruments.length === 2 && allowedInstruments.includes('XAUUSD') && allowedInstruments.includes('US100')) ? 'rgba(168, 85, 247, 0.2)' : 'var(--bg-secondary)',
                      color: (allowedInstruments.length === 2 && allowedInstruments.includes('XAUUSD') && allowedInstruments.includes('US100')) ? '#c084fc' : 'var(--text-secondary)'
                    }}
                  >
                    Gold + US100
                  </button>
                </div>

                {/* Individual Asset Chips */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '6px', marginTop: '4px' }}>
                  {[
                    { sym: 'XAUUSD', label: 'Gold (XAU)' },
                    { sym: 'EURUSD', label: 'EUR / USD' },
                    { sym: 'GBPUSD', label: 'GBP / USD' },
                    { sym: 'USDJPY', label: 'USD / JPY' },
                    { sym: 'US100', label: 'Nasdaq (US100)' },
                    { sym: 'USDCHF', label: 'USD / CHF' },
                  ].map(({ sym, label }) => {
                    const isSelected = allowedInstruments.includes(sym);
                    return (
                      <button
                        key={sym}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            if (allowedInstruments.length > 1) {
                              setAllowedInstruments(allowedInstruments.filter(s => s !== sym));
                            }
                          } else {
                            setAllowedInstruments([...allowedInstruments, sym]);
                          }
                        }}
                        style={{
                          padding: '6px 8px',
                          borderRadius: '6px',
                          border: `1px solid ${isSelected ? 'var(--accent-teal)' : 'var(--border-color)'}`,
                          background: isSelected ? 'rgba(0, 242, 254, 0.12)' : 'var(--bg-secondary)',
                          color: isSelected ? 'var(--accent-teal)' : 'var(--text-secondary)',
                          fontSize: '11px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          textAlign: 'center',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        {isSelected ? '✓ ' : ''}{label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2. Sizing Mode & Capital Allocation */}
              <div style={{ background: 'var(--bg-primary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  📦 Position Sizing Model
                </div>

                <div className="why-grid-2col" style={{ gap: '6px' }}>
                  <button
                    type="button"
                    onClick={() => setRiskMode('FIXED_LOT')}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      border: `1px solid ${riskMode === 'FIXED_LOT' ? 'var(--accent-green)' : 'var(--border-color)'}`,
                      background: riskMode === 'FIXED_LOT' ? 'rgba(16,185,129,0.15)' : 'var(--bg-secondary)',
                      color: riskMode === 'FIXED_LOT' ? 'var(--accent-green)' : 'var(--text-secondary)',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Fixed Lot Size
                  </button>

                  <button
                    type="button"
                    onClick={() => setRiskMode('DYNAMIC_RISK_PCT')}
                    style={{
                      padding: '8px',
                      borderRadius: '6px',
                      border: `1px solid ${riskMode === 'DYNAMIC_RISK_PCT' ? 'var(--accent-teal)' : 'var(--border-color)'}`,
                      background: riskMode === 'DYNAMIC_RISK_PCT' ? 'rgba(0,242,254,0.15)' : 'var(--bg-secondary)',
                      color: riskMode === 'DYNAMIC_RISK_PCT' ? 'var(--accent-teal)' : 'var(--text-secondary)',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Dynamic Risk %
                  </button>
                </div>

                {riskMode === 'FIXED_LOT' ? (
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      Fixed Volume (Lots per Trade)
                    </label>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        max="5.0"
                        value={fixedLotSize}
                        onChange={e => setFixedLotSize(parseFloat(e.target.value) || 0.01)}
                        style={{ ...inputStyle, padding: '6px 10px', fontSize: '13px', fontWeight: 700, width: '100px' }}
                      />
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {[0.01, 0.02, 0.05, 0.10, 0.20].map(val => (
                          <button
                            key={val}
                            type="button"
                            onClick={() => setFixedLotSize(val)}
                            style={{
                              padding: '4px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                              background: fixedLotSize === val ? 'rgba(16,185,129,0.2)' : 'var(--bg-secondary)',
                              color: fixedLotSize === val ? 'var(--accent-green)' : 'var(--text-secondary)',
                              border: '1px solid var(--border-color)',
                              cursor: 'pointer'
                            }}
                          >
                            {val}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      Account Risk Percentage (% of Balance)
                    </label>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                      <input
                        type="number"
                        step="0.25"
                        min="0.25"
                        max="3.0"
                        value={riskPct}
                        onChange={e => setRiskPct(parseFloat(e.target.value) || 1.0)}
                        style={{ ...inputStyle, padding: '6px 10px', fontSize: '13px', fontWeight: 700, width: '100px' }}
                      />
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {[0.5, 1.0, 1.5, 2.0].map(val => (
                          <button
                            key={val}
                            type="button"
                            onClick={() => setRiskPct(val)}
                            style={{
                              padding: '4px 6px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 700,
                              background: riskPct === val ? 'rgba(0,242,254,0.2)' : 'var(--bg-secondary)',
                              color: riskPct === val ? 'var(--accent-teal)' : 'var(--text-secondary)',
                              border: '1px solid var(--border-color)',
                              cursor: 'pointer'
                            }}
                          >
                            {val}%
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 3. Prop Firm & Exposure Safety Guards */}
              <div style={{ background: 'var(--bg-primary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  🛡️ Prop Firm & Exposure Limits
                </div>

                <div className="why-grid-2col" style={{ gap: '10px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Max Concurrent Trades
                    </label>
                    <select
                      value={maxConcurrentTrades}
                      onChange={e => setMaxConcurrentTrades(parseInt(e.target.value) || 3)}
                      style={{ ...inputStyle, padding: '6px 8px', fontSize: '12px', fontWeight: 700 }}
                    >
                      <option value={1}>1 Trade at a time</option>
                      <option value={2}>Max 2 Trades</option>
                      <option value={3}>Max 3 Trades (Default)</option>
                      <option value={5}>Max 5 Trades</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                      Max Daily Drawdown
                    </label>
                    <select
                      value={maxDailyLossPct}
                      onChange={e => setMaxDailyLossPct(parseFloat(e.target.value) || 3.0)}
                      style={{ ...inputStyle, padding: '6px 8px', fontSize: '12px', fontWeight: 700 }}
                    >
                      <option value={2.0}>2.0% (Strict Prop Firm)</option>
                      <option value={3.0}>3.0% (Standard)</option>
                      <option value={4.0}>4.0% (Relaxed)</option>
                      <option value={5.0}>5.0% (Max Limit)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleSavePreferences}
                  disabled={prefSaving}
                  style={{
                    marginTop: 'auto',
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: 'none',
                    background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                    color: '#fff',
                    cursor: prefSaving ? 'not-allowed' : 'pointer',
                    fontSize: '12px',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  <Check size={14} /> {prefSaving ? 'Saving...' : 'Save Risk & Asset Preferences'}
                </button>
              </div>
            </div>
          </div>

          {/* Connect Account Config Modal / Slide-down */}
          {showConfig && (
            <div className="glass-panel" style={{ padding: '24px', border: '1px solid var(--accent-teal)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Lock size={18} color="var(--accent-teal)" /> Connect Your cTrader Broker Account (Zero Install)
                </h3>
                <X size={18} style={{ cursor: 'pointer' }} onClick={() => setShowConfig(false)} />
              </div>

              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
                PrimeEdge connects directly to your broker via the official Spotware cTrader OpenAPI. You never share your password — simply click below to grant secure, encrypted trade copying authorization.
              </p>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
                <button
                  onClick={() => setShowConfig(false)}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 600
                  }}
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    const userId = user?.id || 1;
                    window.location.href = `/api/v1/ctrader/auth?user_id=${userId}`;
                  }}
                  style={{
                    padding: '10px 24px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                    color: '#08090d',
                    cursor: 'pointer',
                    fontSize: '13px',
                    fontWeight: 800
                  }}
                >
                  Authorize with cTrader (OAuth)
                </button>
              </div>
            </div>
          )}

          {/* Active Live Positions & Excursions Table */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} color="var(--accent-teal)" />
                <h3 style={{ fontSize: '15px', fontWeight: 800, margin: 0 }}>Active Cloud Positions & Excursions</h3>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {positions.length} Open Position{positions.length === 1 ? '' : 's'}
              </span>
            </div>

            {positions.length === 0 ? (
              <div style={{
                padding: '30px',
                textAlign: 'center',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                background: 'var(--bg-primary)',
                borderRadius: '8px',
                border: '1px dashed var(--border-color)'
              }}>
                No active open positions. When Market OS corridors reach T0 inception, orders execute automatically with local -0.35R MAE invalidation.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '10px' }}>Ticket</th>
                      <th style={{ padding: '10px' }}>Asset</th>
                      <th style={{ padding: '10px' }}>Dir</th>
                      <th style={{ padding: '10px' }}>Entry</th>
                      <th style={{ padding: '10px' }}>Current</th>
                      <th style={{ padding: '10px' }}>SL / TP</th>
                      <th style={{ padding: '10px' }}>PnL</th>
                      <th style={{ padding: '10px' }}>MAE / MFE</th>
                      <th style={{ padding: '10px' }}>Early Inval Guard</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => {
                      const isLong = pos.direction === 'LONG';
                      return (
                        <tr key={pos.ticket_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 700 }}>{pos.ticket_id}</td>
                          <td style={{ padding: '10px', fontWeight: 800 }}>{pos.instrument}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: isLong ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                              color: isLong ? 'var(--accent-green)' : 'var(--accent-red)'
                            }}>
                              {pos.direction} ({pos.position_size_lots}L)
                            </span>
                          </td>
                          <td style={{ padding: '10px', fontFamily: 'monospace' }}>{pos.open_price.toFixed(4)}</td>
                          <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 700 }}>{pos.current_price.toFixed(4)}</td>
                          <td style={{ padding: '10px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                            SL: {pos.stop_loss.toFixed(4)}<br />TP: {pos.take_profit.toFixed(4)}
                          </td>
                          <td style={{ padding: '10px', fontWeight: 800, color: pos.current_pnl_pips >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {pos.current_pnl_pips >= 0 ? '+' : ''}{pos.current_pnl_pips} pips
                          </td>
                          <td style={{ padding: '10px', fontSize: '11px' }}>
                            <span style={{ color: 'var(--accent-red)' }}>MAE: -{pos.max_mae_pips}p</span><br />
                            <span style={{ color: 'var(--accent-green)' }}>MFE: +{pos.max_mfe_pips}p</span>
                          </td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '6px',
                              fontSize: '10px',
                              fontWeight: 700,
                              background: pos.early_inval_armed ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                              color: pos.early_inval_armed ? 'var(--accent-red)' : 'var(--accent-green)',
                              border: `1px solid ${pos.early_inval_armed ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`
                            }}>
                              {pos.early_inval_armed ? 'ARMED (-0.35R)' : 'DISARMED (RUNNER)'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Closed Auto-Execution History Table */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle size={18} color="var(--accent-teal)" />
                <h3 style={{ fontSize: '15px', fontWeight: 800, margin: 0 }}>Closed Auto-Execution History</h3>
              </div>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {closedHistory.length} Closed Trade{closedHistory.length === 1 ? '' : 's'}
              </span>
            </div>

            {closedHistory.length === 0 ? (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                color: 'var(--text-secondary)',
                fontSize: '13px',
                background: 'var(--bg-primary)',
                borderRadius: '8px',
                border: '1px dashed var(--border-color)'
              }}>
                No closed auto-executed trades recorded yet. Completed trades with exit prices and realized PnL will appear here.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '10px' }}>Ticket</th>
                      <th style={{ padding: '10px' }}>Asset</th>
                      <th style={{ padding: '10px' }}>Dir</th>
                      <th style={{ padding: '10px' }}>Entry</th>
                      <th style={{ padding: '10px' }}>Exit</th>
                      <th style={{ padding: '10px' }}>Outcome</th>
                      <th style={{ padding: '10px' }}>Net PnL</th>
                      <th style={{ padding: '10px' }}>Exit Reason</th>
                      <th style={{ padding: '10px' }}>Closed At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {closedHistory.map((item) => {
                      const isLong = item.direction === 'LONG';
                      const isWin = item.outcome === 'WIN' || item.pnl_pips > 0;
                      return (
                        <tr key={item.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 700 }}>{item.ticket_id}</td>
                          <td style={{ padding: '10px', fontWeight: 800 }}>{item.instrument}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: isLong ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                              color: isLong ? 'var(--accent-green)' : 'var(--accent-red)'
                            }}>
                              {item.direction} ({item.position_size_lots}L)
                            </span>
                          </td>
                          <td style={{ padding: '10px', fontFamily: 'monospace' }}>{item.entry_price.toFixed(4)}</td>
                          <td style={{ padding: '10px', fontFamily: 'monospace' }}>{item.exit_price ? item.exit_price.toFixed(4) : '—'}</td>
                          <td style={{ padding: '10px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '10px',
                              fontWeight: 800,
                              background: isWin ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                              color: isWin ? 'var(--accent-green)' : 'var(--accent-red)'
                            }}>
                              {item.outcome}
                            </span>
                          </td>
                          <td style={{ padding: '10px', fontWeight: 800, color: item.pnl_pips >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {item.pnl_pips >= 0 ? '+' : ''}{item.pnl_pips}p ({item.pnl_r >= 0 ? '+' : ''}{item.pnl_r}R)
                          </td>
                          <td style={{ padding: '10px', color: 'var(--text-secondary)' }}>{item.exit_reason}</td>
                          <td style={{ padding: '10px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                            {item.exit_time ? new Date(item.exit_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* 2. SOLO-FOUNDER OPERATIONS COMMAND CENTER                                  */}
      {/* ========================================================================= */}
      {viewMode === 'admin' && <FounderAdminDashboard />}

    </div>
  );
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border-color)',
  borderRadius: '7px',
  color: 'var(--text-primary)',
  fontSize: '13px',
  outline: 'none',
  boxSizing: 'border-box'
};
