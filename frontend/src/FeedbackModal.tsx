import React, { useState } from 'react';
import { MessageSquare, X, Bug, Zap, Lightbulb, Sparkles, MessageCircle, Star, CheckCircle, Send, AlertTriangle } from 'lucide-react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: string;
  selectedInstrument: string;
  userEmail?: string;
}

const CATEGORIES = [
  { id: 'BUG', label: 'Bug / Issue', icon: Bug, color: '#ef4444' },
  { id: 'EXECUTION', label: 'Execution / MT5', icon: Zap, color: 'var(--accent-teal)' },
  { id: 'FEATURE', label: 'Feature Idea', icon: Lightbulb, color: '#f59e0b' },
  { id: 'UI_UX', label: 'UI / Polish', icon: Sparkles, color: '#a855f7' },
  { id: 'GENERAL', label: 'General Feedback', icon: MessageCircle, color: '#38bdf8' },
];

const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

export default function FeedbackModal({
  isOpen,
  onClose,
  activeTab,
  selectedInstrument,
  userEmail
}: FeedbackModalProps) {
  const [category, setCategory] = useState<string>('BUG');
  const [rating, setRating] = useState<number>(5);
  const [message, setMessage] = useState<string>('');
  const [contactEmail, setContactEmail] = useState<string>(userEmail || '');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitted, setSubmitted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    setSubmitting(true);
    setError(null);

    const systemInfo = {
      userAgent: navigator.userAgent,
      screenWidth: window.innerWidth,
      screenHeight: window.innerHeight,
      language: navigator.language,
      platform: navigator.platform,
      submittedAt: new Date().toISOString()
    };

    try {
      const res = await fetch(`${API_BASE}/feedback/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category,
          rating,
          active_tab: activeTab,
          selected_instrument: selectedInstrument,
          message: message.trim(),
          system_info: systemInfo,
          contact_email: contactEmail || userEmail
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to submit feedback');
      }

      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setMessage('');
        onClose();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Error submitting feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'rgba(0, 0, 0, 0.82)',
      backdropFilter: 'blur(6px)',
      padding: '20px'
    }}>
      <div className="glass-panel animate-fade-in" style={{
        width: '100%',
        maxWidth: '560px',
        borderRadius: '16px',
        border: '1px solid rgba(0, 242, 254, 0.25)',
        backgroundColor: '#0c1017',
        padding: '28px',
        position: 'relative',
        boxShadow: '0 25px 60px rgba(0,0,0,0.85)'
      }}>
        {/* Close Button */}
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'rgba(255,255,255,0.06)',
            border: 'none',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
            cursor: 'pointer'
          }}
        >
          <X size={16} />
        </button>

        {submitted ? (
          <div style={{ textAlign: 'center', padding: '30px 10px' }}>
            <div style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              backgroundColor: 'rgba(16,185,129,0.15)',
              border: '1px solid rgba(16,185,129,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
              color: 'var(--accent-green)'
            }}>
              <CheckCircle size={32} />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: '0 0 8px 0' }}>
              Feedback Logged Successfully!
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>
              Thank you for helping us polish Market OS. Our engineering team reviews all beta telemetry directly.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <div style={{
                padding: '6px',
                borderRadius: '8px',
                backgroundColor: 'rgba(0,242,254,0.12)',
                color: 'var(--accent-teal)'
              }}>
                <MessageSquare size={18} />
              </div>
              <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#fff', margin: 0 }}>
                Market OS Beta Feedback
              </h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '0 0 20px 0' }}>
              Share bugs, execution telemetry notes, or feature requests. Context is automatically captured.
            </p>

            {/* Category Selector */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Feedback Category
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                {CATEGORIES.map((cat) => {
                  const Icon = cat.icon;
                  const isSelected = category === cat.id;
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => setCategory(cat.id)}
                      style={{
                        padding: '9px 10px',
                        borderRadius: '8px',
                        border: `1px solid ${isSelected ? cat.color : 'rgba(255,255,255,0.08)'}`,
                        backgroundColor: isSelected ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.02)',
                        color: isSelected ? '#fff' : 'var(--text-secondary)',
                        fontSize: '11px',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <Icon size={14} style={{ color: cat.color }} />
                      <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cat.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Rating Stars */}
            <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(255,255,255,0.02)', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Overall Experience</div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>How smoothly did this session perform?</div>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: '2px',
                      color: star <= rating ? '#f59e0b' : 'rgba(255,255,255,0.2)'
                    }}
                  >
                    <Star size={18} fill={star <= rating ? '#f59e0b' : 'none'} />
                  </button>
                ))}
              </div>
            </div>

            {/* Message Area */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Your Observation or Suggestion <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What happened? What were you expecting to see? (e.g. XAUUSD corridor was clean, but order execution delayed 2 seconds...)"
                rows={4}
                required
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  padding: '12px',
                  backgroundColor: '#080b11',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '13px',
                  lineHeight: 1.5,
                  resize: 'none',
                  outline: 'none',
                  fontFamily: 'inherit'
                }}
              />
            </div>

            {/* Auto-Captured Environment Context Footer */}
            <div style={{
              padding: '10px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(0, 242, 254, 0.04)',
              border: '1px solid rgba(0, 242, 254, 0.15)',
              fontSize: '11px',
              color: 'var(--text-muted)',
              marginBottom: '20px',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '12px',
              alignItems: 'center'
            }}>
              <span>📍 Tab: <strong style={{ color: 'var(--accent-teal)' }}>{activeTab.toUpperCase()}</strong></span>
              <span>📊 Asset: <strong style={{ color: '#fff' }}>{selectedInstrument}</strong></span>
              <span>👤 Tester: <strong style={{ color: '#fff' }}>{userEmail || 'Tester'}</strong></span>
            </div>

            {error && (
              <div style={{
                padding: '10px 12px',
                borderRadius: '6px',
                backgroundColor: 'rgba(239,68,68,0.1)',
                border: '1px solid rgba(239,68,68,0.3)',
                color: 'var(--accent-red)',
                fontSize: '12px',
                marginBottom: '16px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <AlertTriangle size={14} />
                <span>{error}</span>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '10px 16px',
                  borderRadius: '8px',
                  background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.12)',
                  color: 'var(--text-secondary)',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={submitting || !message.trim()}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
                  border: 'none',
                  color: '#000',
                  fontSize: '12px',
                  fontWeight: 800,
                  cursor: submitting || !message.trim() ? 'not-allowed' : 'pointer',
                  opacity: submitting || !message.trim() ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {submitting ? 'Submitting...' : (
                  <>
                    <Send size={14} /> Submit Feedback
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
