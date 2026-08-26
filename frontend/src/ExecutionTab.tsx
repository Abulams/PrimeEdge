import React, { useState, useEffect } from 'react';
import {
  Zap, Shield, Server, Activity, ArrowUpRight, ArrowDownRight,
  Download, CheckCircle, AlertTriangle, Play, Pause, RefreshCw,
  Terminal, Lock, Check, Send, AlertCircle, Radio, Cpu, Settings, X, Eye, EyeOff, ShieldAlert
} from 'lucide-react';
import { useAuth, apiFetch } from './AuthContext';

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

export const ExecutionTab: React.FC = () => {
  const { user } = useAuth();
  const [viewMode, setViewMode] = useState<'subscriber' | 'admin'>('subscriber');
  
  // Subscriber State
  const [cloudStatus, setCloudStatus] = useState<CloudAccountStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
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

  const fetchSubscriberData = async () => {
    try {
      const [resStatus, resPos] = await Promise.all([
        apiFetch('/api/v1/execution/cloud/status'),
        apiFetch('/api/v1/execution/cloud/positions')
      ]);
      if (resStatus.ok) {
        const data = await resStatus.json();
        setCloudStatus(data);
      }
      if (resPos.ok) {
        const posData = await resPos.json();
        setPositions(posData);
      }
    } catch (e) {
      console.error('Error fetching subscriber execution data:', e);
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
            EXECUTION — Cloud MT5 Gateway
          </h2>
          <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
            Zero-install cloud execution with sub-second -0.35R local MAE early invalidation guardrails.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
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

          <button
            onClick={() => handleForceTestTrade('EURUSD', 'LONG')}
            disabled={testTradeLoading}
            style={{
              padding: '8px 14px',
              background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
              border: 'none',
              borderRadius: '8px',
              color: '#000',
              cursor: testTradeLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 800,
              boxShadow: '0 0 12px rgba(0, 242, 254, 0.35)',
              opacity: testTradeLoading ? 0.7 : 1
            }}
          >
            <Zap size={14} /> {testTradeLoading ? 'Executing...' : '⚡ Test Cloud Trade'}
          </button>

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
                  <span style={{ fontSize: '14px', fontWeight: 700 }}>Cloud MT5 Terminal</span>
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
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div style={{ background: 'var(--bg-primary)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Login Account</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, marginTop: '2px' }}>#{acc.login || '8809124'}</div>
                    <div style={{ fontSize: '10px', color: 'var(--accent-teal)', marginTop: '2px' }}>{acc.server || 'MarketOS-Cloud'}</div>
                  </div>

                  <div style={{ background: 'var(--bg-primary)', padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Account Equity</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--accent-green)', marginTop: '2px' }}>
                      ${(acc.equity || 100000.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Bal: ${(acc.balance || 100000.0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
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
                  No MetaTrader 5 account connected yet.
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
                <button
                  onClick={() => setShowConfig(!showConfig)}
                  style={{
                    flex: 1,
                    padding: '10px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  <Settings size={14} /> {isConnected ? 'Change MT5 Account' : 'Connect MT5 Account'}
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

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
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

          {/* Connect Account Config Modal / Slide-down */}
          {showConfig && (
            <div className="glass-panel" style={{ padding: '24px', border: '1px solid var(--accent-teal)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Lock size={18} color="var(--accent-teal)" /> Connect Your MetaTrader 5 Broker Account (Zero Install)
                </h3>
                <X size={18} style={{ cursor: 'pointer' }} onClick={() => setShowConfig(false)} />
              </div>

              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
                Your broker credentials are encrypted at rest with AES-256 encryption. Market OS manages an isolated, dedicated MT5 session for your account on our low-latency Windows execution bridge.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>
                    Broker Server Name
                  </label>
                  <input
                    type="text"
                    value={brokerServer}
                    onChange={e => setBrokerServer(e.target.value)}
                    placeholder="e.g. ICMarketsSC-Demo, FTMO-Demo"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>
                    MT5 Account Number / Login
                  </label>
                  <input
                    type="number"
                    value={loginAccount}
                    onChange={e => setLoginAccount(e.target.value)}
                    placeholder="e.g. 8809124"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase' }}>
                    MT5 Master / Investor Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={loginPassword}
                      onChange={e => setLoginPassword(e.target.value)}
                      placeholder="Password"
                      style={{ ...inputStyle, paddingRight: '36px' }}
                    />
                    <div
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ position: 'absolute', right: '10px', top: '10px', cursor: 'pointer', color: 'var(--text-secondary)' }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
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
                  Cancel
                </button>
                <button
                  onClick={handleConnectCloud}
                  disabled={loading}
                  style={{
                    padding: '10px 24px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                    color: '#fff',
                    cursor: loading ? 'not-allowed' : 'pointer',
                    fontSize: '13px',
                    fontWeight: 700
                  }}
                >
                  {loading ? 'Initializing Cloud Session...' : 'Save & Connect Cloud MT5'}
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
        </>
      )}

      {/* ========================================================================= */}
      {/* 2. SOLO-FOUNDER ADMIN OPERATIONS CONSOLE                                  */}
      {/* ========================================================================= */}
      {viewMode === 'admin' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Master Emergency Killswitch Banner */}
          <div style={{
            padding: '16px 20px',
            borderRadius: '10px',
            background: adminData?.global_killswitch_active ? 'rgba(239,68,68,0.2)' : 'var(--bg-secondary)',
            border: `1px solid ${adminData?.global_killswitch_active ? 'var(--accent-red)' : 'var(--border-color)'}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px'
          }}>
            <div>
              <div style={{ fontSize: '15px', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', color: adminData?.global_killswitch_active ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                <ShieldAlert size={20} /> MASTER GLOBAL EXECUTION KILLSWITCH
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {adminData?.global_killswitch_active
                  ? 'CRITICAL: Global killswitch is ENGAGED. All order routing across all workers is halted immediately.'
                  : 'System operational. Order routing is active for authorized subscriber terminals.'}
              </div>
            </div>

            <button
              onClick={() => handleAdminGlobalKillswitch(!adminData?.global_killswitch_active)}
              style={{
                padding: '10px 20px',
                borderRadius: '8px',
                border: 'none',
                background: adminData?.global_killswitch_active ? 'var(--accent-green)' : 'var(--accent-red)',
                color: '#fff',
                fontWeight: 800,
                fontSize: '13px',
                cursor: 'pointer',
                letterSpacing: '0.5px'
              }}
            >
              {adminData?.global_killswitch_active ? 'RE-ENABLE GLOBAL EXECUTION' : 'TRIGGER EMERGENCY HALT'}
            </button>
          </div>

          {/* Worker Node Fleet Health */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 800, margin: '0 0 14px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} color="var(--accent-teal)" /> Windows VPS Worker Fleet
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
              {adminData?.workers.map((w) => (
                <div key={w.worker_id} style={{ background: 'var(--bg-primary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ fontWeight: 800, fontSize: '13px' }}>{w.worker_id}</div>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '10px',
                      fontSize: '10px',
                      fontWeight: 800,
                      background: w.status === 'ONLINE' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                      color: w.status === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)'
                    }}>
                      {w.status}
                    </span>
                  </div>

                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                    <div>CPU: <strong style={{ color: 'var(--text-primary)' }}>{w.cpu_pct.toFixed(1)}%</strong></div>
                    <div>RAM: <strong style={{ color: 'var(--text-primary)' }}>{w.ram_pct.toFixed(1)}%</strong></div>
                    <div>Terminals: <strong style={{ color: 'var(--accent-teal)' }}>{w.active_terminals} / {w.max_terminals}</strong></div>
                    <div>IP: <strong style={{ color: 'var(--text-primary)' }}>{w.ip_address}</strong></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Subscriber Accounts Grid */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 800, margin: '0 0 14px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={18} color="var(--accent-teal)" /> Subscriber Accounts & Isolated MT5 Sessions ({adminData?.accounts.length || 0})
            </h3>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Subscriber</th>
                    <th style={{ padding: '8px' }}>Broker & Login</th>
                    <th style={{ padding: '8px' }}>Worker</th>
                    <th style={{ padding: '8px' }}>Equity / Balance</th>
                    <th style={{ padding: '8px' }}>Ping</th>
                    <th style={{ padding: '8px' }}>Auto-Exec</th>
                    <th style={{ padding: '8px' }}>Account Killswitch</th>
                  </tr>
                </thead>
                <tbody>
                  {adminData?.accounts.map((acc) => (
                    <tr key={acc.account_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '8px', fontWeight: 600 }}>{acc.user_email}</td>
                      <td style={{ padding: '8px' }}>
                        <strong>#{acc.login}</strong><br />
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{acc.server}</span>
                      </td>
                      <td style={{ padding: '8px', fontSize: '11px', color: 'var(--accent-teal)' }}>{acc.worker_id}</td>
                      <td style={{ padding: '8px' }}>
                        <strong style={{ color: 'var(--accent-green)' }}>${acc.equity.toLocaleString()}</strong><br />
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Bal: ${acc.balance.toLocaleString()}</span>
                      </td>
                      <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>{acc.ping_ms}ms</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700,
                          background: acc.auto_execution_enabled ? 'rgba(16,185,129,0.15)' : 'rgba(148,163,184,0.15)',
                          color: acc.auto_execution_enabled ? 'var(--accent-green)' : 'var(--text-secondary)'
                        }}>
                          {acc.auto_execution_enabled ? 'ON' : 'PAUSED'}
                        </span>
                      </td>
                      <td style={{ padding: '8px' }}>
                        <button
                          onClick={() => handleAdminAccountKillswitch(acc.account_id, !acc.killswitch_active)}
                          style={{
                            padding: '4px 10px',
                            borderRadius: '6px',
                            border: 'none',
                            background: acc.killswitch_active ? 'var(--accent-green)' : 'rgba(239,68,68,0.2)',
                            color: acc.killswitch_active ? '#fff' : 'var(--accent-red)',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          {acc.killswitch_active ? 'Re-enable' : 'Halt Account'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Execution Audits */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 800, margin: '0 0 14px 0' }}>Recent Execution Receipts & Latencies</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '8px' }}>Ticket</th>
                    <th style={{ padding: '8px' }}>Signal</th>
                    <th style={{ padding: '8px' }}>Asset</th>
                    <th style={{ padding: '8px' }}>Entry</th>
                    <th style={{ padding: '8px' }}>Exit</th>
                    <th style={{ padding: '8px' }}>PnL R</th>
                    <th style={{ padding: '8px' }}>Latency</th>
                    <th style={{ padding: '8px' }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {adminData?.recent_audits.map((a) => (
                    <tr key={a.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{a.ticket_id}</td>
                      <td style={{ padding: '8px', color: 'var(--accent-teal)' }}>{a.signal_id}</td>
                      <td style={{ padding: '8px', fontWeight: 700 }}>{a.instrument} {a.direction}</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{a.entry_price}</td>
                      <td style={{ padding: '8px', fontFamily: 'monospace' }}>{a.exit_price || '—'}</td>
                      <td style={{ padding: '8px', fontWeight: 800, color: (a.pnl_r || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {a.pnl_r !== null && a.pnl_r !== undefined ? `${a.pnl_r > 0 ? '+' : ''}${a.pnl_r}R` : 'OPEN'}
                      </td>
                      <td style={{ padding: '8px', color: 'var(--accent-teal)' }}>{a.latency_ms.toFixed(1)}ms</td>
                      <td style={{ padding: '8px', fontSize: '11px', color: 'var(--text-secondary)' }}>{a.exit_reason || 'IN_FLIGHT'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

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
