import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { Globe, KeyRound, ArrowLeft } from 'lucide-react';

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

export type Mode = 'login' | 'register' | 'forgot' | 'reset';

interface LoginPageProps {
  initialMode?: Mode;
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

  // Sync if parent changes the initial mode prop (e.g. /forgot-password or /register route)
  useEffect(() => {
    if (!resetTokenFromUrl) {
      setMode(initialMode);
    }
  }, [initialMode, resetTokenFromUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (mode === 'register') {
      if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
      if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    }

    if (mode === 'reset') {
      if (!resetToken.trim()) { setError('Please enter your password reset token.'); return; }
      if (password !== confirmPassword) { setError('Passwords do not match.'); return; }
      if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
        window.location.href = '/';

      } else if (mode === 'register') {
        await register(email, password, fullName.trim() || undefined);
        window.location.href = '/';

      } else if (mode === 'forgot') {
        const res = await fetch(`${API_BASE}/api/v1/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await res.json();
        setSuccessMsg(data.detail || 'If that email is registered, a password reset link has been dispatched.');
        setEmail('');

      } else if (mode === 'reset') {
        const res = await fetch(`${API_BASE}/api/v1/auth/reset-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: resetToken.trim(), password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Password reset failed. The token may be expired or invalid.');
        // Success — store tokens and redirect to workspace immediately
        if (data.access_token) {
          localStorage.setItem('pe_access_token', data.access_token);
          localStorage.setItem('pe_refresh_token', data.refresh_token || '');
          window.location.href = '/';
        } else {
          setSuccessMsg('Password updated successfully! You can now sign in.');
          setMode('login');
        }
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please check your credentials and try again.');
    } finally {
      setLoading(false);
    }
  };

  const switchToLogin = () => { 
    setMode('login'); 
    setError(''); 
    setSuccessMsg(''); 
    if (window.history.pushState) {
      window.history.pushState({}, '', '/login');
    }
  };

  const isAuthMode = mode === 'login' || mode === 'register';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 0' }}>
      <div style={{ width: '100%', maxWidth: '440px', padding: '0 24px' }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div style={{ width: '38px', height: '38px', background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))', borderRadius: '9px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '19px', fontWeight: 800, color: '#fff', boxShadow: '0 4px 12px rgba(0, 174, 239, 0.25)' }}>P</div>
            <span style={{ fontSize: '23px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.5px' }}>PrimeEdge</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: 0 }}>Institutional Decision Intelligence & Execution</p>
        </div>

        <div className="glass-panel" style={{ padding: '32px', borderRadius: '14px', border: '1px solid var(--border-color)', boxShadow: '0 12px 32px rgba(0, 0, 0, 0.35)' }}>

          {/* Mode header */}
          <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <h2 style={{ fontSize: '19px', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 10px 0' }}>
              {mode === 'login' && 'Welcome Back'}
              {mode === 'register' && 'Create Your Account'}
              {mode === 'forgot' && 'Reset Your Password'}
              {mode === 'reset' && 'Set a New Password'}
            </h2>

            {/* Tab toggle — only for login / register */}
            {isAuthMode && (
              <div style={{ display: 'inline-flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', marginTop: '4px' }}>
                <button type="button" onClick={() => { setMode('login'); setError(''); }}
                  style={{ padding: '8px 22px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer',
                    background: mode === 'login' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                    color: mode === 'login' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>
                  Sign In
                </button>
                <button type="button" onClick={() => { setMode('register'); setError(''); }}
                  style={{ padding: '8px 22px', fontSize: '12px', fontWeight: 700, border: 'none', cursor: 'pointer',
                    background: mode === 'register' ? 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' : 'transparent',
                    color: mode === 'register' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>
                  Create Account
                </button>
              </div>
            )}

            {(mode === 'forgot' || mode === 'reset') && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', margin: '4px 0 0 0', lineHeight: 1.5 }}>
                {mode === 'forgot'
                  ? "Enter your registered email and we'll dispatch a secure password reset link."
                  : 'Enter your reset token and new password to restore account access.'}
              </p>
            )}
          </div>

          {/* Success banner */}
          {successMsg && (
            <div style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.35)', borderRadius: '8px', padding: '14px 16px', fontSize: '13px', color: '#10b981', marginBottom: '20px', lineHeight: 1.5 }}>
              <div style={{ fontWeight: 600, marginBottom: '6px' }}>Instructions Sent</div>
              {successMsg}
              <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button type="button" onClick={() => { setMode('reset'); setSuccessMsg(''); setError(''); }}
                  style={{ padding: '9px 14px', background: 'rgba(16,185,129,0.2)', border: '1px solid rgba(16,185,129,0.4)', borderRadius: '6px', color: '#fff', fontSize: '12px', fontWeight: 700, cursor: 'pointer' }}>
                  Enter Reset Token & Set Password →
                </button>
                <button type="button" onClick={switchToLogin}
                  style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
                  ← Back to Sign In
                </button>
              </div>
            </div>
          )}

          {!successMsg && (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>

              {/* Full name — register only */}
              {mode === 'register' && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>Full Name</label>
                  <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="e.g. Abubakar Lamido" style={inputStyle} />
                </div>
              )}

              {/* Email — login, register, forgot */}
              {mode !== 'reset' && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>Email Address</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="abu1@gmail.com" required style={inputStyle} autoFocus={mode === 'forgot'} />
                </div>
              )}

              {/* Reset Token — reset mode only */}
              {mode === 'reset' && (
                <div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                    <KeyRound size={12} color="var(--accent-teal)" />
                    Reset Token / Code
                  </label>
                  <input type="text" value={resetToken} onChange={e => setResetToken(e.target.value)} placeholder="Paste token from email or security alert" required style={inputStyle} autoFocus />
                </div>
              )}

              {/* Password — login, register, reset */}
              {mode !== 'forgot' && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                    {mode === 'reset' ? 'New Password' : 'Password'}
                  </label>
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                    placeholder={mode === 'login' ? 'Your account password' : 'Min. 8 characters'} required style={inputStyle} />
                </div>
              )}

              {/* Confirm password — register, reset */}
              {(mode === 'register' || mode === 'reset') && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.6px' }}>Confirm Password</label>
                  <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="Re-enter password" required style={inputStyle} />
                </div>
              )}

              {/* Forgot password link — login mode only */}
              {mode === 'login' && (
                <div style={{ textAlign: 'right', marginTop: '-4px' }}>
                  <button type="button" onClick={() => { setMode('forgot'); setError(''); setSuccessMsg(''); }}
                    style={{ background: 'none', border: 'none', color: 'var(--accent-teal)', cursor: 'pointer', fontSize: '12px', fontWeight: 600, padding: 0 }}>
                    Forgot password?
                  </button>
                </div>
              )}

              {/* Toggle to enter token manually from forgot screen */}
              {mode === 'forgot' && (
                <div style={{ textAlign: 'center', marginTop: '-4px' }}>
                  <button type="button" onClick={() => { setMode('reset'); setError(''); setSuccessMsg(''); }}
                    style={{ background: 'none', border: 'none', color: 'var(--accent-teal)', cursor: 'pointer', fontSize: '12px', fontWeight: 600, padding: 0 }}>
                    Already have a reset token? Enter it here →
                  </button>
                </div>
              )}

              {/* Error */}
              {error && (
                <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.35)', borderRadius: '7px', padding: '10px 14px', fontSize: '13px', color: 'var(--accent-red)', lineHeight: 1.4 }}>
                  {error}
                </div>
              )}

              {/* Submit */}
              <button type="submit" disabled={loading}
                style={{ padding: '13px', background: loading ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                  border: 'none', borderRadius: '8px', color: '#fff', fontSize: '14px', fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1, marginTop: '6px', transition: 'all 0.2s' }}>
                {loading
                  ? (mode === 'forgot' ? 'Sending Link...' : mode === 'reset' ? 'Saving New Password...' : mode === 'login' ? 'Signing in...' : 'Creating Account...')
                  : (mode === 'forgot' ? 'Send Password Reset Link'
                    : mode === 'reset' ? 'Set New Password & Enter'
                    : mode === 'login' ? 'Sign In to Workspace'
                    : 'Create Account & Start Trading')}
              </button>

              {/* Back to login — forgot/reset modes */}
              {(mode === 'forgot' || mode === 'reset') && (
                <div style={{ textAlign: 'center', marginTop: '4px' }}>
                  <button type="button" onClick={switchToLogin}
                    style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '13px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <ArrowLeft size={14} />
                    Back to Sign In
                  </button>
                </div>
              )}
            </form>
          )}
        </div>

        {/* Footer links */}
        <div style={{ textAlign: 'center', marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
            PrimeEdge Institutional Systems · 256-bit Encrypted Session
          </p>
        </div>
      </div>
    </div>
  );
}
