import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle2, ShieldCheck, ArrowRight, AlertCircle } from 'lucide-react';

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 14px',
  background: 'var(--bg-primary, #0c0e14)',
  border: '1px solid var(--border-color, #242936)',
  borderRadius: '8px',
  color: 'var(--text-primary, #f1f5f9)',
  fontSize: '14px',
  outline: 'none',
  boxSizing: 'border-box',
};

export default function ActivatePage() {
  const [token, setToken] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [fullName, setFullName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<boolean>(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get('token');
    if (t) {
      setToken(t);
    } else {
      setError('Missing invitation token. Please use the activation link sent to your email.');
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!token) {
      setError('Invalid or missing activation token.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/v1/auth/activate-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          password,
          full_name: fullName.trim() || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Activation failed. The link may have expired.');
      }

      // Store auth credentials and set session
      if (data.access_token) {
        localStorage.setItem('marketos_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('marketos_refresh_token', data.refresh_token);
        }
      }

      setSuccess(true);
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to activate account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#08090d', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>

        {/* Branding Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <div style={{ width: '36px', height: '36px', background: 'linear-gradient(135deg, #00f2fe, #38bdf8)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', fontWeight: 800, color: '#08090d' }}>P</div>
            <span style={{ fontSize: '22px', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' }}>PrimeEdge</span>
          </div>
          <p style={{ color: '#94a3b8', fontSize: '13px', margin: 0 }}>Founder Alpha Cohort · Account Activation</p>
        </div>

        <div style={{
          backgroundColor: '#111318',
          border: '1px solid #242936',
          borderRadius: '14px',
          padding: '32px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)'
        }}>

          {success ? (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ width: '56px', height: '56px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', color: '#10b981' }}>
                <CheckCircle2 size={32} />
              </div>
              <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: '0 0 8px 0' }}>Account Activated!</h2>
              <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.5, margin: '0 0 20px 0' }}>
                Your private workspace credentials have been configured. Launching your terminal now...
              </p>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: '#00f2fe', fontSize: '13px', fontWeight: 600 }}>
                Redirecting to Workspace <ArrowRight size={14} />
              </div>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: '24px', textAlign: 'center' }}>
                <h2 style={{ fontSize: '19px', fontWeight: 700, color: '#fff', margin: '0 0 6px 0' }}>Choose Your Password</h2>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '999px', backgroundColor: 'rgba(0, 242, 254, 0.08)', border: '1px solid rgba(0, 242, 254, 0.2)', fontSize: '11px', fontWeight: 700, color: '#00f2fe', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <ShieldCheck size={12} />
                  Verified Alpha Allocation
                </div>
              </div>

              {error && (
                <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', padding: '12px 14px', fontSize: '13px', color: '#ef4444', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={16} style={{ flexShrink: 0 }} />
                  <div>{error}</div>
                </div>
              )}

              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Full Name <span style={{ fontSize: '10px', color: '#64748b' }}>(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Trader Name"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Create Password
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 8 characters"
                    required
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat password"
                    required
                    style={inputStyle}
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    padding: '13px',
                    background: loading ? '#1e2532' : 'linear-gradient(135deg, #00f2fe, #38bdf8)',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#08090d',
                    fontSize: '14px',
                    fontWeight: 800,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    marginTop: '8px',
                    boxShadow: '0 4px 16px rgba(0, 242, 254, 0.3)',
                    transition: 'all 0.2s'
                  }}
                >
                  {loading ? 'Securing Account...' : 'Set Password & Enter Workspace'}
                </button>
              </form>
            </>
          )}

        </div>

        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '11px', color: '#64748b' }}>
          Protected by PrimeEdge Institutional Security & End-to-End Encryption
        </div>

      </div>
    </div>
  );
}
