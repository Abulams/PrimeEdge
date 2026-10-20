import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { Globe } from 'lucide-react';

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

interface LoginPageProps {
  initialMode?: 'login' | 'register';
}

export default function LoginPage({ initialMode = 'login' }: LoginPageProps) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Sync if parent changes the initial mode prop (e.g. /register route)
  useEffect(() => { setMode(initialMode); }, [initialMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (mode === 'register') {
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters.');
        return;
      }
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName.trim() || undefined);
      }
    } catch (err: any) {
      setError(err.message || (mode === 'login' ? 'Authentication failed' : 'Registration failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: '440px', padding: '0 24px' }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '36px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', fontWeight: 800, color: '#fff' }}>P</div>
            <span style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.5px' }}>PrimeEdge</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>Institutional Decision Intelligence Platform</p>
        </div>

        <div className="glass-panel" style={{ padding: '32px' }}>

          {/* Mode badge */}
          <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 12px 0' }}>
              {mode === 'login' ? 'Welcome Back' : 'Create Your Account'}
            </h2>
            {/* Tab toggle */}
            <div style={{ display: 'inline-flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
              <button
                type="button"
                onClick={() => { setMode('login'); setError(''); }}
                style={{
                  padding: '7px 20px', fontSize: '12px', fontWeight: 700,
                  border: 'none', cursor: 'pointer',
                  background: mode === 'login' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                  color: mode === 'login' ? '#fff' : 'var(--text-secondary)',
                  transition: 'all 0.2s',
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setMode('register'); setError(''); }}
                style={{
                  padding: '7px 20px', fontSize: '12px', fontWeight: 700,
                  border: 'none', cursor: 'pointer',
                  background: mode === 'register' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                  color: mode === 'register' ? '#fff' : 'var(--text-secondary)',
                  transition: 'all 0.2s',
                }}
              >
                Create Account
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

            {mode === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="Your name (optional)"
                  style={inputStyle}
                />
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email Address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="trader@firm.com" required style={inputStyle} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder={mode === 'register' ? 'Min. 8 characters' : 'Your password'} required style={inputStyle} />
            </div>

            {mode === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Confirm Password</label>
                <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter password" required style={inputStyle} />
              </div>
            )}

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
                marginTop: '4px',
              }}
            >
              {loading
                ? (mode === 'login' ? 'Signing in...' : 'Creating account...')
                : (mode === 'login' ? 'Sign In to Workspace' : 'Create Account & Start Trading')}
            </button>
          </form>
        </div>

        {/* Footer links */}
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
          <p style={{ color: 'var(--text-muted)', fontSize: '10px', margin: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
            <Globe size={10} />
            PrimeEdge Institutional Decision Systems · Encrypted Session · Open to All Traders
          </p>
        </div>
      </div>
    </div>
  );
}
