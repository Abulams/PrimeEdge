import React, { useState, useEffect } from 'react';
import { 
  Shield, Server, Users, Activity, AlertTriangle, Play, Pause, 
  Trash2, UserPlus, RefreshCw, CheckCircle2, XCircle, Zap, Terminal, Lock, Compass, ArrowLeft
} from 'lucide-react';
import { apiFetch } from './AuthContext';

interface FounderAdminDashboardProps {
  onNavigateTerminal?: () => void;
}

interface WorkerSummary {
  worker_id: string;
  hostname: string;
  ip_address?: string;
  status: string;
  cpu_pct: number;
  ram_pct: number;
  active_terminals: number;
  max_terminals: number;
  last_heartbeat?: string;
}

interface AccountSummary {
  account_id: number;
  user_id: number;
  user_email: string;
  user_role: string;
  login: number;
  server: string;
  worker_id: string;
  balance: number;
  equity: number;
  ping_ms: number;
  is_active: boolean;
  auto_execution_enabled: boolean;
  execution_mode: 'LIVE_BROKER' | 'SANDBOX_FALLBACK';
  killswitch_active: boolean;
  open_positions: number;
  allowed_instruments?: string;
  risk_pct?: number;
  fixed_lot_size?: number;
  last_heartbeat?: string;
  error?: string;
}

interface UserSummary {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_admin: boolean;
  is_active: boolean;
  has_broker_linked: boolean;
  linked_login?: number;
  created_at?: string;
  last_login?: string;
}

interface AuditSummary {
  id: number;
  user_id: number;
  ticket_id: string;
  is_sandbox: boolean;
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
}

interface WaitlistLeadSummary {
  id: number;
  full_name: string;
  email: string;
  broker_platform: string;
  contact_method: string;
  why_interested: string;
  consent_given: boolean;
  status: string;
  created_at: string;
}

interface AdminDashboardData {
  global_killswitch_active: boolean;
  total_users: number;
  total_subscribers: number;
  total_workers: number;
  workers: WorkerSummary[];
  accounts: AccountSummary[];
  users: UserSummary[];
  recent_audits: AuditSummary[];
}

export const FounderAdminDashboard: React.FC<FounderAdminDashboardProps> = ({ onNavigateTerminal }) => {
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [waitlistLeads, setWaitlistLeads] = useState<WaitlistLeadSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // New user modal state
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUserEmail, setNewUserEmail] = useState('');
  const [newUserPassword, setNewUserPassword] = useState('');
  const [newUserName, setNewUserName] = useState('');
  const [newUserRole, setNewUserRole] = useState('trader');

  const fetchDashboardData = async () => {
    try {
      const res = await apiFetch('/api/v1/execution/admin/operations');
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch (e) {
      console.error('Failed to fetch admin data:', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchWaitlistLeads = async () => {
    try {
      const res = await apiFetch('/api/v1/execution/admin/waitlist');
      if (res.ok) {
        const json = await res.json();
        setWaitlistLeads(json);
      }
    } catch (e) {
      console.error('Failed to fetch waitlist:', e);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchWaitlistLeads();
    const interval = setInterval(() => {
      fetchDashboardData();
      fetchWaitlistLeads();
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleApproveWaitlist = async (leadId: number) => {
    setActionLoading(`lead_${leadId}`);
    try {
      const res = await apiFetch(`/api/v1/execution/admin/waitlist/${leadId}/approve`, { method: 'POST' });
      if (res.ok) {
        showToast('✅ Lead marked as INVITED');
        fetchWaitlistLeads();
      }
    } catch (e) {
      showToast('❌ Failed to update lead');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteWaitlist = async (leadId: number) => {
    if (!window.confirm('Delete this waitlist submission?')) return;
    setActionLoading(`lead_${leadId}`);
    try {
      const res = await apiFetch(`/api/v1/execution/admin/waitlist/${leadId}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Lead removed');
        fetchWaitlistLeads();
      }
    } catch (e) {
      showToast('Delete failed');
    } finally {
      setActionLoading(null);
    }
  };

  // Toggle Global Killswitch
  const handleToggleGlobalKillswitch = async () => {
    if (!data) return;
    const newState = !data.global_killswitch_active;
    if (newState && !window.confirm('⚠️ WARNING: Enable Global Killswitch? This will immediately HALT all order routing across all subscriber accounts!')) {
      return;
    }
    setActionLoading('global_killswitch');
    try {
      const res = await apiFetch('/api/v1/execution/admin/killswitch/global', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newState }),
      });
      if (res.ok) {
        showToast(newState ? '🔴 GLOBAL KILLSWITCH ENGAGED' : '🟢 GLOBAL KILLSWITCH DISARMED');
        fetchDashboardData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  // Emergency Flatten Fleet
  const handleFlattenFleet = async () => {
    if (!window.confirm('🚨 EMERGENCY ACTION: Are you sure you want to LIQUIDATE ALL OPEN POSITIONS across all subscriber accounts at market price?')) {
      return;
    }
    setActionLoading('flatten_fleet');
    try {
      const res = await apiFetch('/api/v1/execution/admin/flatten-fleet', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        showToast(`✅ Queued close orders for ${json.liquidated_positions_queued} open positions.`);
        fetchDashboardData();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  // Manage User Action
  const handleUserAction = async (userId: number, action: string, userEmail: string) => {
    if (action === 'delete' && !window.confirm(`Permanently delete user ${userEmail}? This will remove all their records.`)) {
      return;
    }
    setActionLoading(`user_${userId}_${action}`);
    try {
      const res = await apiFetch(`/api/v1/execution/admin/users/${userId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      if (res.ok) {
        showToast(`User ${userEmail}: ${action} executed successfully.`);
        fetchDashboardData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Action failed');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  // Create User
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading('create_user');
    try {
      const res = await apiFetch('/api/v1/execution/admin/users/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: newUserEmail,
          password: newUserPassword,
          full_name: newUserName,
          role: newUserRole,
        }),
      });
      if (res.ok) {
        showToast(`✅ Created new account for ${newUserEmail}`);
        setShowAddUserModal(false);
        setNewUserEmail('');
        setNewUserPassword('');
        setNewUserName('');
        fetchDashboardData();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create user');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading && !data) {
    return (
      <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <RefreshCw size={24} className="spin-icon" style={{ marginBottom: '12px' }} />
        <div>Loading Founder Command Center...</div>
      </div>
    );
  }

  const primaryWorker = data?.workers[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
          background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--accent-teal)',
          color: '#fff', padding: '12px 20px', borderRadius: '8px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.5)', fontSize: '13px', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: '10px'
        }}>
          <Zap size={16} color="var(--accent-teal)" />
          {toastMessage}
        </div>
      )}

      {/* Top Header & Emergency Controls Bar */}
      <div className="glass-panel" style={{ padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', borderLeft: '4px solid var(--accent-teal)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={22} color="var(--accent-teal)" />
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 800, letterSpacing: '-0.3px', color: 'var(--text-primary)' }}>
              FOUNDER OPERATIONS COMMAND CENTER
            </h2>
            <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '4px', background: 'rgba(56,189,248,0.15)', color: 'var(--accent-teal)', fontWeight: 700 }}>
              ROOT ACCESS
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Real-time fleet telemetry, multi-tenant MT5 bridge supervisor, and user governance.
          </p>
        </div>

        <div className="admin-header-actions">
          {/* Back to Trader Terminal Button */}
          {onNavigateTerminal && (
            <button
              onClick={onNavigateTerminal}
              style={{
                padding: '8px 14px', borderRadius: '6px', border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '12px', fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
              }}
            >
              <ArrowLeft size={14} color="var(--accent-teal)" /> Trader Terminal
            </button>
          )}

          {/* Add User Button */}
          <button
            onClick={() => setShowAddUserModal(true)}
            style={{
              padding: '8px 14px', borderRadius: '6px', border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '12px', fontWeight: 600,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <UserPlus size={14} color="var(--accent-teal)" /> Add Beta Trader
          </button>

          {/* Flatten Fleet Button */}
          <button
            onClick={handleFlattenFleet}
            disabled={actionLoading === 'flatten_fleet'}
            style={{
              padding: '8px 14px', borderRadius: '6px', border: '1px solid rgba(239,68,68,0.4)',
              background: 'rgba(239,68,68,0.15)', color: 'var(--accent-red)', fontSize: '12px', fontWeight: 700,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <AlertTriangle size={14} /> Flatten Fleet
          </button>

          {/* Global Killswitch Button */}
          <button
            onClick={handleToggleGlobalKillswitch}
            disabled={actionLoading === 'global_killswitch'}
            className="full-width-mobile"
            style={{
              padding: '8px 16px', borderRadius: '6px', border: 'none',
              background: data?.global_killswitch_active ? 'var(--accent-green)' : 'var(--accent-red)',
              color: '#fff', fontSize: '12px', fontWeight: 800, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '6px',
              boxShadow: data?.global_killswitch_active ? '0 0 15px rgba(16,185,129,0.4)' : '0 0 15px rgba(239,68,68,0.4)'
            }}
          >
            {data?.global_killswitch_active ? <Play size={14} /> : <Pause size={14} />}
            {data?.global_killswitch_active ? 'RESUME EXECUTION' : 'GLOBAL KILLSWITCH'}
          </button>
        </div>
      </div>

      {/* KPI Overview Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        
        <div className="glass-panel" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
            <span>WORKER NODE</span>
            <Server size={16} color={primaryWorker?.status === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)'} />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, margin: '8px 0 4px 0', color: primaryWorker?.status === 'ONLINE' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            {primaryWorker?.status || 'UNKNOWN'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            CPU: {primaryWorker?.cpu_pct ?? 0}% | RAM: {primaryWorker?.ram_pct ?? 0}% | Terminals: {primaryWorker?.active_terminals ?? 0}/{primaryWorker?.max_terminals ?? 20}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
            <span>CONNECTED BROKERS</span>
            <Activity size={16} color="var(--accent-blue)" />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, margin: '8px 0 4px 0', color: 'var(--text-primary)' }}>
            {data?.total_subscribers ?? 0} Accounts
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            Total Capital: ${data?.accounts.reduce((acc: number, a: AccountSummary) => acc + (a.balance || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
            <span>REGISTERED TRADERS</span>
            <Users size={16} color="var(--accent-teal)" />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, margin: '8px 0 4px 0', color: 'var(--text-primary)' }}>
            {data?.total_users ?? 0} Users
          </div>
          <div style={{ fontSize: '11px', color: 'var(--accent-green)', fontWeight: 600 }}>
            Lockdown: Private / Invite-Only
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
            <span>ROUTER STATUS</span>
            <Zap size={16} color={data?.global_killswitch_active ? 'var(--accent-red)' : 'var(--accent-green)'} />
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, margin: '8px 0 4px 0', color: data?.global_killswitch_active ? 'var(--accent-red)' : 'var(--accent-green)' }}>
            {data?.global_killswitch_active ? 'PAUSED' : 'AUTO-ROUTING LIVE'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
            1-Trade Per Signal Guard: ACTIVE
          </div>
        </div>

      </div>

      {/* SECTION 1: Subscriber Fleet & MT5 Terminal Matrix */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
              SUBSCRIBER FLEET & MT5 TERMINAL MATRIX
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Real-time balance, ping latency, and broker authentication state.
            </span>
          </div>
          <button 
            onClick={fetchDashboardData} 
            style={{ background: 'transparent', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-secondary)', padding: '6px 10px', fontSize: '12px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '10px 12px' }}>User / Email</th>
                <th style={{ padding: '10px 12px' }}>MT5 Login</th>
                <th style={{ padding: '10px 12px' }}>Broker Server</th>
                <th style={{ padding: '10px 12px' }}>Live Balance / Equity</th>
                <th style={{ padding: '10px 12px' }}>Execution Mode</th>
                <th style={{ padding: '10px 12px' }}>Auto-Exec</th>
                <th style={{ padding: '10px 12px' }}>Latency</th>
                <th style={{ padding: '10px 12px' }}>Risk / Lots</th>
              </tr>
            </thead>
            <tbody>
              {data?.accounts.map((acc: AccountSummary) => {
                const isLive = acc.execution_mode === 'LIVE_BROKER';
                return (
                  <tr key={acc.account_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{acc.user_email}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>ID #{acc.account_id} • User #{acc.user_id}</div>
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 700 }}>
                      {acc.login}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {acc.server}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                        ${acc.balance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                        Eq: ${acc.equity?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      {isLive ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700, background: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)', border: '1px solid rgba(16,185,129,0.3)' }}>
                          <CheckCircle2 size={12} /> LIVE MT5 BROKER
                        </span>
                      ) : (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700, background: 'rgba(234,179,8,0.15)', color: 'var(--accent-yellow)', border: '1px solid rgba(234,179,8,0.3)' }} title="Account credentials failed broker login. Executions falling back to sandbox simulation.">
                          <AlertTriangle size={12} /> SANDBOX SIMULATION
                        </span>
                      )}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ color: acc.auto_execution_enabled ? 'var(--accent-green)' : 'var(--text-secondary)', fontWeight: 600 }}>
                        {acc.auto_execution_enabled ? '🟢 ON' : '⚪ OFF'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: acc.ping_ms < 200 ? 'var(--accent-green)' : (acc.ping_ms > 2000 ? 'var(--accent-red)' : 'var(--accent-yellow)') }}>
                      {acc.ping_ms ? `${acc.ping_ms.toFixed(1)}ms` : '—'}
                    </td>
                    <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {acc.fixed_lot_size || 0.01} lots ({acc.risk_pct || 1.0}%)
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 2: User Governance & Beta Tester Management */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
              USER GOVERNANCE & ACCESS CONTROL
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Manage registered traders, admin privileges, and access revocation.
            </span>
          </div>
          <button
            onClick={() => setShowAddUserModal(true)}
            style={{
              padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--accent-teal)',
              background: 'rgba(56,189,248,0.1)', color: 'var(--accent-teal)', fontSize: '12px', fontWeight: 600,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <UserPlus size={14} /> Create Invite Account
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '10px 12px' }}>ID</th>
                <th style={{ padding: '10px 12px' }}>Email Address</th>
                <th style={{ padding: '10px 12px' }}>Role</th>
                <th style={{ padding: '10px 12px' }}>Linked MT5</th>
                <th style={{ padding: '10px 12px' }}>Account Status</th>
                <th style={{ padding: '10px 12px' }}>Registered At</th>
                <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.users.map((u: UserSummary) => (
                <tr key={u.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '12px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    #{u.id}
                  </td>
                  <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {u.email}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                      background: u.is_admin ? 'rgba(56,189,248,0.15)' : 'rgba(255,255,255,0.05)',
                      color: u.is_admin ? 'var(--accent-teal)' : 'var(--text-secondary)',
                    }}>
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '12px' }}>
                    {u.has_broker_linked ? (
                      <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>Login: {u.linked_login}</span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>None</span>
                    )}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{
                      padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                      background: u.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                      color: u.is_active ? 'var(--accent-green)' : 'var(--accent-red)',
                    }}>
                      {u.is_active ? 'ACTIVE' : 'DISABLED'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '8px' }}>
                      <button
                        onClick={() => handleUserAction(u.id, 'toggle_active', u.email)}
                        disabled={actionLoading?.startsWith(`user_${u.id}`)}
                        style={{
                          padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border-color)',
                          background: 'var(--bg-secondary)', color: u.is_active ? 'var(--accent-yellow)' : 'var(--accent-green)',
                          fontSize: '11px', fontWeight: 600, cursor: 'pointer'
                        }}
                      >
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => handleUserAction(u.id, 'delete', u.email)}
                        disabled={actionLoading?.startsWith(`user_${u.id}`)}
                        style={{
                          padding: '4px 8px', borderRadius: '4px', border: '1px solid rgba(239,68,68,0.3)',
                          background: 'rgba(239,68,68,0.1)', color: 'var(--accent-red)',
                          fontSize: '11px', fontWeight: 600, cursor: 'pointer'
                        }}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION: Waitlist Priority Cohort Applicants */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                WAITLIST PRIORITY COHORT APPLICANTS
              </h3>
              <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)', fontWeight: 700 }}>
                {waitlistLeads.length} / 20 SPOTS
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Prospective traders who signed up at /waitlist. Review credentials and mark as INVITED to grant access.
            </span>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '12px' }}>Applicant</th>
                <th style={{ padding: '12px' }}>Broker Platform</th>
                <th style={{ padding: '12px' }}>Interest / Notes</th>
                <th style={{ padding: '12px' }}>Applied Date</th>
                <th style={{ padding: '12px' }}>Status</th>
                <th style={{ padding: '12px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {waitlistLeads.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                    No waitlist submissions received yet. Live entries from /waitlist will appear here automatically.
                  </td>
                </tr>
              ) : (
                waitlistLeads.map((lead: WaitlistLeadSummary) => (
                  <tr key={lead.id} style={{ borderBottom: '1px solid var(--border-color)', transition: 'background 0.2s' }}>
                    <td style={{ padding: '12px' }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{lead.full_name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{lead.email}</div>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                        {lead.broker_platform || 'MT5'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)', maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {lead.why_interested || '—'}
                    </td>
                    <td style={{ padding: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        padding: '3px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700,
                        background: lead.status === 'INVITED' ? 'rgba(16,185,129,0.15)' : 'rgba(234,179,8,0.15)',
                        color: lead.status === 'INVITED' ? 'var(--accent-green)' : 'var(--accent-yellow)',
                      }}>
                        {lead.status || 'PENDING'}
                      </span>
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        {lead.status !== 'INVITED' && (
                          <button
                            onClick={() => handleApproveWaitlist(lead.id)}
                            disabled={actionLoading === `lead_${lead.id}`}
                            style={{
                              padding: '5px 10px', borderRadius: '4px', border: '1px solid var(--accent-green)',
                              background: 'rgba(16,185,129,0.1)', color: 'var(--accent-green)',
                              fontSize: '11px', fontWeight: 700, cursor: 'pointer'
                            }}
                          >
                            Invite Trader
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteWaitlist(lead.id)}
                          disabled={actionLoading === `lead_${lead.id}`}
                          style={{
                            padding: '5px 8px', borderRadius: '4px', border: '1px solid rgba(239,68,68,0.3)',
                            background: 'rgba(239,68,68,0.1)', color: 'var(--accent-red)',
                            fontSize: '11px', fontWeight: 600, cursor: 'pointer'
                          }}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SECTION 3: Live Execution Audit Stream */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
              LIVE MULTI-ACCOUNT EXECUTION AUDIT STREAM
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Chronological log of orders routed, MT5 fill confirmations, and broker tickets.
            </span>
          </div>
        </div>

        <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
            <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-primary)', zIndex: 1 }}>
              <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <th style={{ padding: '8px 10px' }}>Timestamp (UTC)</th>
                <th style={{ padding: '8px 10px' }}>Signal / Setup</th>
                <th style={{ padding: '8px 10px' }}>Instrument</th>
                <th style={{ padding: '8px 10px' }}>Direction</th>
                <th style={{ padding: '8px 10px' }}>Ticket ID</th>
                <th style={{ padding: '8px 10px' }}>Fill / Exit Price</th>
                <th style={{ padding: '8px 10px' }}>Status</th>
                <th style={{ padding: '8px 10px' }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {data?.recent_audits.map((a: AuditSummary) => {
                const isRealBroker = !a.is_sandbox;
                return (
                  <tr key={a.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '8px 10px', color: 'var(--text-secondary)' }}>
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '8px 10px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {a.signal_id}
                    </td>
                    <td style={{ padding: '8px 10px', fontWeight: 700 }}>
                      {a.instrument}
                    </td>
                    <td style={{ padding: '8px 10px', color: a.direction === 'LONG' ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 700 }}>
                      {a.direction}
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'monospace' }}>
                      {isRealBroker ? (
                        <span style={{ color: 'var(--accent-green)', fontWeight: 700 }}>{a.ticket_id} (Real)</span>
                      ) : (
                        <span style={{ color: 'var(--accent-yellow)' }}>{a.ticket_id} (Sandbox)</span>
                      )}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      {a.entry_price} {a.exit_price ? `→ ${a.exit_price}` : ''}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span style={{
                        padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 700,
                        background: a.status === 'FILLED' ? 'rgba(16,185,129,0.15)' : 'rgba(56,189,248,0.15)',
                        color: a.status === 'FILLED' ? 'var(--accent-green)' : 'var(--accent-teal)'
                      }}>
                        {a.status} {a.exit_reason ? `(${a.exit_reason})` : ''}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-secondary)' }}>
                      {a.latency_ms}ms
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL: Create New Beta Trader */}
      {showAddUserModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10000,
          backdropFilter: 'blur(4px)'
        }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '420px', padding: '28px', borderRadius: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)' }}>
                Add Beta Trader Account
              </h3>
              <button onClick={() => setShowAddUserModal(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Full Name</label>
                <input
                  type="text"
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="e.g. Alex Henderson"
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Email Address</label>
                <input
                  type="email"
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="trader@fund.com"
                  required
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Temporary Password</label>
                <input
                  type="password"
                  value={newUserPassword}
                  onChange={(e) => setNewUserPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  required
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '13px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Role</label>
                <select
                  value={newUserRole}
                  onChange={(e) => setNewUserRole(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '13px' }}
                >
                  <option value="trader">Trader (Subscriber)</option>
                  <option value="admin">Admin (Full Access)</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading === 'create_user'}
                  style={{ flex: 1, padding: '10px', borderRadius: '6px', border: 'none', background: 'var(--accent-teal)', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: '13px' }}
                >
                  {actionLoading === 'create_user' ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
