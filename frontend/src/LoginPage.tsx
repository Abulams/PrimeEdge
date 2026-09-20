import React, { useState } from 'react';
import { useAuth } from './AuthContext';
import { Lock } from 'lucide-react';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 14px',
  background: 'var(--bg-primary)',
  border: '1px solid var(--border-color)',
  borderRadius: '7px',
  color: 'var(--text-primary)',
  fontSize: '14px',
  outline: 'none',
  boxSizing: 'border-box',
};

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '420px', padding: '0 24px' }}>

        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', fontWeight: 800, color: '#fff' }}>P</div>
            <span style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.5px' }}>PrimeEdge</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>Institutional Decision Intelligence Platform</p>
        </div>

        <div className="glass-panel" style={{ padding: '32px' }}>
          <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 6px 0' }}>Trader Sign In</h2>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '999px', backgroundColor: 'rgba(0, 242, 254, 0.08)', border: '1px solid rgba(0, 242, 254, 0.2)', fontSize: '11px', fontWeight: 700, color: '#00f2fe', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              <Lock size={10} />
              Invite-Only Platform
            </div>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email Address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="trader@firm.com" required style={inputStyle} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Your password" required style={inputStyle} />
            </div>

            {error && (
              <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px', padding: '10px 14px', fontSize: '13px', color: 'var(--accent-red)' }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '12px',
                background: loading ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                border: 'none', borderRadius: '8px', color: '#fff',
                fontSize: '14px', fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
              }}
            >
              {loading ? 'Signing in...' : 'Sign In to Workspace'}
            </button>
          </form>
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <a
            href="/"
            onClick={(e) => {
              if (window.history.pushState) {
                e.preventDefault();
                window.history.pushState({}, '', '/');
                window.dispatchEvent(new PopStateEvent('popstate'));
              }
            }}
            style={{ color: 'var(--accent-teal)', fontSize: '12px', textDecoration: 'none', fontWeight: 600 }}
          >
            ← Back to PrimeEdge Overview
          </a>
          <a
            href="/waitlist"
            style={{ color: 'var(--text-secondary)', fontSize: '11px', textDecoration: 'none' }}
          >
            Don't have access? Apply for the Founder Alpha Cohort →
          </a>
          <p style={{ color: 'var(--text-muted)', fontSize: '10px', margin: 0 }}>
            PrimeEdge Institutional Decision Systems · Encrypted Session
          </p>
        </div>
      </div>
    </div>
  );
}
