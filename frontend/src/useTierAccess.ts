/**
 * useTierAccess — fetches the current user's subscription tier from the backend
 * and returns a resolved access object that can be used to gate features.
 *
 * Tier hierarchy (lowest → highest):
 *   free  →  starter  →  pro  →  premium
 *
 * Feature gates:
 *   free    : FIND + WHY only
 *   starter : + PLAN, Auto-Journal, AI Analyst (no Replay, no Execution)
 *   pro     : + REPLAY (no Execution)
 *   premium : full access including EXECUTION
 */

import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from './AuthContext';

export type TierName = 'free' | 'starter' | 'pro' | 'premium' | 'none';

export interface TierAccess {
  tier: TierName;
  isLoading: boolean;
  // Feature flags
  canUsePlan: boolean;
  canUseJournal: boolean;
  canUseChat: boolean;
  canUseReplay: boolean;
  canUseExecution: boolean;
  // Helper
  upgradeUrl: string;
}

const TIER_RANK: Record<TierName, number> = {
  none: 0,
  free: 1,
  starter: 2,
  pro: 3,
  premium: 4,
};

function gte(tier: TierName, required: TierName): boolean {
  return TIER_RANK[tier] >= TIER_RANK[required];
}

export function useTierAccess(isAuthenticated: boolean): TierAccess {
  const [tier, setTier] = useState<TierName>('none');
  const [isLoading, setIsLoading] = useState(true);

  const fetchTier = useCallback(async () => {
    if (!isAuthenticated) {
      setTier('none');
      setIsLoading(false);
      return;
    }
    try {
      const res = await apiFetch('/api/v1/subscription/current');
      if (res.ok) {
        const data = await res.json();
        const name = (data?.tier?.name ?? 'free') as TierName;
        setTier(name);
      } else {
        setTier('free');
      }
    } catch {
      setTier('free');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    setIsLoading(true);
    fetchTier();
  }, [fetchTier]);

  return {
    tier,
    isLoading,
    canUsePlan:      gte(tier, 'starter'),
    canUseJournal:   gte(tier, 'starter'),
    canUseChat:      gte(tier, 'starter'),
    canUseReplay:    gte(tier, 'pro'),
    canUseExecution: gte(tier, 'premium'),
    upgradeUrl: '/pricing',
  };
}
