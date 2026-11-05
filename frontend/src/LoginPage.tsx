import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { Globe } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '';

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

type Mode = 'login' | 'register' | 'forgot' | 'reset';

interface LoginPageProps {
  initialMode?: 'login' | 'register';
}

export default function LoginPage({ initialMode = 'login' }: LoginPageProps) {
  const { login, register } = useAuth();

  // Detect ?token= in URL for password-reset deep links
  const urlParams = new URLSearchParams(window.location.search);
  const resetTokenFromUrl = urlParams.get('token');

  const [mode, setMode] = useState<Mode>(resetTokenFromUrl ? 'reset' : initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState(resetTokenFromUrl || '');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  // Sync if parent changes the initial mode prop (e.g. /register route)
  useEffect(() => {
    if (!resetTokenFromUrl) setMode(initialMode);
  }, [initialMode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (mode === 'register') {
      if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
      if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    }

    if (mode === 'reset') {
      if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
      if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);

      } else if (mode === 'register') {
        await register(email, password, fullName.trim() || undefined);

      } else if (mode === 'forgot') {
        const res = await fetch(`${API_BASE}/api/v1/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await res.json();
        setSuccessMsg(data.detail || 'If that email is registered, a reset link has been sent.');
        setEmail('');

      } else if (mode === 'reset') {
        const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: resetToken, password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Reset failed');
        // Success — store tokens and redirect to dashboard via AuthContext
        if (data.access_token) {
          localStorage.setItem('pe_access_token', data.access_token);
          localStorage.setItem('pe_refresh_token', data.refresh_token || '');
          window.location.href = '/dashboard';
        }
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchToLogin = () => { setMode('login'); setError(''); setSuccessMsg(''); };

  const isAuthMode = mode === 'login' || mode === 'register';

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

          {/* Mode header */}
          <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', margin: '0 0 12px 0' }}>
              {mode === 'login' && 'Welcome Back'}
              {mode === 'register' && 'Create Your Account'}
              {mode === 'forgot' && 'Reset Your Password'}
              {mode === 'reset' && 'Set a New Password'}
            </h2>

            {/* Tab toggle — only for login / register */}
            {isAuthMode && (
              <div style={{ display: 'inline-flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)' }}>
                <button type="button" onClick={() => { setMode('login'); setError(''); }}
                  style={{ padding: '7px 20px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer',
                    background: mode === 'login' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                    color: mode === 'login' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>
                  Sign In
                </button>
                <button type="button" onClick={() => { setMode('register'); setError(''); }}
                  style={{ padding: '7px 20px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer',
                    background: mode === 'register' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                    color: mode === 'register' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>
                  Create Account
                </button>
              </div>
            )}

            {(mode === 'forgot' || mode === 'reset') && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>
                {mode === 'forgot'
                  ? "Enter your email and we'll send a secure reset link."
                  : 'Enter and confirm your new password below.'}
              </p>
            )}
          </div>

          {/* Success banner */}
          {successMsg && (
            <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '8px', padding: '12px 16px', fontSize: '13px', color: '#10b981', marginBottom: '16px', textAlign: 'center' }}>
              {successMsg}
              <div style={{ marginTop: '10px' }}>
                <button type="button" onClick={switchToLogin}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-teal)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
                  ← Back to Sign In
                </button>
              </div>
            </div>
          )}

          {!successMsg && (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

              {/* Full name — register only */}
              {mode === 'register' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Full Name</label>
                  <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Your name (optional)" style={inputStyle} />
                </div>
              )}

              {/* Email — login, register, forgot */}
              {mode !== 'reset' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email Address</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="trader@firm.com" required style={inputStyle} />
                </div>
              )}

              {/* Password — login, register, reset */}
              {mode !== 'forgot' && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {mode === 'reset' ? 'New Password' : 'Password'}
                  </label>
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                    placeholder={mode === 'login' ? 'Your password' : 'Min. 8 characters'} required style={inputStyle} />
                </div>
              )}

              {/* Confirm password — register, reset */}
              {(mode === 'register' || mode === 'reset') && (
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Confirm Password</label>
                  <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter password" required style={inputStyle} />
                </div>
              )}

              {/* Forgot password link — login mode only */}
              {mode === 'login' && (
                <div style={{ textAlign: 'right', marginTop: '-6px' }}>
                  <button type="button" onClick={() => { setMode('forgot'); setError(''); setSuccessMsg(''); }}
                    style={{ background: 'none', border: 'none', color: 'var(--accent-teal)', cursor: 'pointer', fontSize: '12px', fontWeight: 600, padding: 0 }}>
                    Forgot password?
                  </button>
                </div>
              )}

              {/* Error */}
              {error && (
                <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '6px', padding: '10px 14px', fontSize: '13px', color: 'var(--accent-red)' }}>
                  {error}
                </div>
              )}

              {/* Submit */}
              <button type="submit" disabled={loading}
                style={{ padding: '12px', background: loading ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                  border: 'none', borderRadius: '8px', color: '#fff', fontSize: '14px', fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1, marginTop: '4px' }}>
                {loading
                  ? (mode === 'forgot' ? 'Sending...' : mode === 'reset' ? 'Saving...' : mode === 'login' ? 'Signing in...' : 'Creating account...')
                  : (mode === 'forgot' ? 'Send Reset Link'
                    : mode === 'reset' ? 'Set New Password & Sign In'
                    : mode === 'login' ? 'Sign In to Workspace'
                    : 'Create Account & Start Trading')}
              </button>

              {/* Back to login — forgot/reset modes */}
              {(mode === 'forgot' || mode === 'reset') && (
                <div style={{ textAlign: 'center' }}>
                  <button type="button" onClick={switchToLogin}
                    style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}>
                    ← Back to Sign In
                  </button>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Footer links */}
        <div style={{ textAlign: 'center', marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <a href="/"
            onClick={(e) => {
              if (window.history.pushState) {
                e.preventDefault();
                window.history.pushState({}, '', '/');
                window.dispatchEvent(new PopStateEvent('popstate'));
              }
            }}
            style={{ color: 'var(--accent-teal)', fontSize: '12px', textDecoration: 'none', fontWeight: 600 }}>
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
