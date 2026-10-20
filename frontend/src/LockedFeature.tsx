import React from 'react';
import { Lock, Zap, ArrowRight } from 'lucide-react';

interface LockedFeatureProps {
  featureName: string;
  requiredTier: 'starter' | 'pro' | 'premium';
  currentTier: string;
  description: string;
  upgradeUrl?: string;
}

const TIER_LABELS: Record<string, { label: string; color: string; price: string }> = {
  starter: { label: 'Starter', color: '#94a3b8', price: '$29/mo' },
  pro:     { label: 'Pro',     color: '#00f2fe', price: '$99/mo' },
  premium: { label: 'Premium', color: '#fbbf24', price: '$299/mo' },
};

export function LockedFeature({
  featureName,
  requiredTier,
  currentTier,
  description,
  upgradeUrl = '/pricing',
}: LockedFeatureProps) {
  const info = TIER_LABELS[requiredTier];

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        padding: '40px 24px',
      }}
    >
      <div
        style={{
          maxWidth: '460px',
          width: '100%',
          textAlign: 'center',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '16px',
          padding: '48px 36px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '20px',
        }}
      >
        {/* Lock icon */}
        <div
          style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'rgba(0,242,254,0.08)',
            border: '1px solid rgba(0,242,254,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Lock size={26} color="var(--accent-teal)" />
        </div>

        {/* Tier badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 14px',
            borderRadius: '999px',
            background: `${info.color}18`,
            border: `1px solid ${info.color}44`,
            fontSize: '11px',
            fontWeight: 700,
            color: info.color,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}
        >
          <Zap size={10} />
          {info.label} Plan Required
        </div>

        <div>
          <h3
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: 'var(--text-primary)',
              margin: '0 0 10px 0',
              letterSpacing: '-0.3px',
            }}
          >
            {featureName}
          </h3>
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '14px',
              lineHeight: 1.6,
              margin: 0,
            }}
          >
            {description}
          </p>
        </div>

        <div
          style={{
            width: '100%',
            padding: '14px 16px',
            background: 'var(--bg-tertiary)',
            borderRadius: '8px',
            fontSize: '12px',
            color: 'var(--text-muted)',
            lineHeight: 1.5,
          }}
        >
          You are on the{' '}
          <strong style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
            {currentTier === 'none' ? 'Free' : currentTier}
          </strong>{' '}
          plan. Upgrade to{' '}
          <strong style={{ color: info.color }}>{info.label}</strong> ({info.price}) to unlock
          this feature.
        </div>

        <a
          href={upgradeUrl}
          onClick={(e) => {
            if (window.history.pushState) {
              e.preventDefault();
              window.history.pushState({}, '', upgradeUrl);
              window.dispatchEvent(new PopStateEvent('popstate'));
            }
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '12px 28px',
            background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))',
            borderRadius: '8px',
            color: '#fff',
            fontWeight: 700,
            fontSize: '14px',
            textDecoration: 'none',
            transition: 'opacity 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '0.85')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '1')}
        >
          View Plans & Upgrade
          <ArrowRight size={16} />
        </a>

        <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)' }}>
          Instant activation · Cancel anytime
        </p>
      </div>
    </div>
  );
}
