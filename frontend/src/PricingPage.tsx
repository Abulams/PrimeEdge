import React, { useState, useEffect } from 'react';
import {
  Check,
  X,
  ChevronRight,
  CreditCard,
  Zap,
  Shield,
  TrendingUp,
  Star,
  Crown,
  Loader2
} from 'lucide-react';

interface Tier {
  id: number;
  name: string;
  display_name: string;
  description: string;
  price_monthly: number;
  price_yearly: number | null;
  features: string[];
  max_accounts: number;
  auto_execution_enabled: boolean;
  api_access_enabled: boolean;
}

interface UserSubscription {
  tier: Tier | null;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  trial_used: boolean;
}

export default function PricingPage() {
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [currentSubscription, setCurrentSubscription] = useState<UserSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');
  const [processingTier, setProcessingTier] = useState<string | null>(null);

  useEffect(() => {
    fetchTiers();
    fetchCurrentSubscription();
  }, []);

  const fetchTiers = async () => {
    try {
      const response = await fetch('/api/v1/subscription/tiers');
      if (response.ok) {
        const data = await response.json();
        setTiers(data);
      }
    } catch (error) {
      console.error('Failed to fetch tiers:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentSubscription = async () => {
    try {
      const response = await fetch('/api/v1/subscription/current', {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentSubscription(data);
      }
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    }
  };

  const handleSubscribe = async (tierName: string) => {
    setProcessingTier(tierName);
    try {
      const response = await fetch('/api/v1/subscription/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          tier_name: tierName,
          billing_interval: billingInterval
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Redirect to Stripe checkout
        window.location.href = data.checkout_url;
      } else {
        const error = await response.json();
        alert('Failed to create checkout session: ' + (error.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Checkout error:', error);
      alert('Failed to create checkout session');
    } finally {
      setProcessingTier(null);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.')) {
      return;
    }

    try {
      const response = await fetch('/api/v1/subscription/cancel', {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        alert('Subscription canceled successfully');
        fetchCurrentSubscription();
      } else {
        alert('Failed to cancel subscription');
      }
    } catch (error) {
      console.error('Cancel error:', error);
      alert('Failed to cancel subscription');
    }
  };

  const getAnnualSavings = (tier: Tier) => {
    if (!tier.price_yearly) return 0;
    const yearlyMonthly = tier.price_monthly * 12;
    return Math.round(((yearlyMonthly - tier.price_yearly) / yearlyMonthly) * 100);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#08090d] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#00f2fe]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#08090d] py-20 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-white mb-4">
            Choose Your Trading Intelligence Tier
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Institutional-grade market intelligence and execution capabilities for every trader level
          </p>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center mt-8 space-x-4">
            <button
              onClick={() => setBillingInterval('month')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                billingInterval === 'month'
                  ? 'bg-[#00f2fe] text-[#08090d]'
                  : 'bg-[#111318] text-gray-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingInterval('year')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                billingInterval === 'year'
                  ? 'bg-[#00f2fe] text-[#08090d]'
                  : 'bg-[#111318] text-gray-400 hover:text-white'
              }`}
            >
              Yearly
              <span className="ml-2 text-xs bg-[#10b981] text-white px-2 py-0.5 rounded-full">
                Save ~17%
              </span>
            </button>
          </div>
        </div>

        {/* Current Subscription Status */}
        {currentSubscription && currentSubscription.tier && (
          <div className="bg-[#111318] border border-[#242936] rounded-xl p-6 mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white mb-1">
                  Current Plan: {currentSubscription.tier.display_name}
                </h3>
                <p className="text-gray-400">
                  Status: {currentSubscription.status}
                  {currentSubscription.cancel_at_period_end && (
                    <span className="ml-2 text-orange-400">(Cancels at period end)</span>
                  )}
                </p>
              </div>
              {!currentSubscription.cancel_at_period_end && (
                <button
                  onClick={handleCancelSubscription}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  Cancel Subscription
                </button>
              )}
            </div>
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-8">
          {tiers.map((tier) => {
            const isCurrentPlan = currentSubscription?.tier?.id === tier.id;
            const savings = getAnnualSavings(tier);
            const price = billingInterval === 'month' ? tier.price_monthly : (tier.price_yearly || tier.price_monthly * 12);

            return (
              <div
                key={tier.id}
                className={`relative rounded-2xl p-8 border-2 transition-all ${
                  tier.name === 'premium'
                    ? 'bg-gradient-to-b from-[#1a1f35] to-[#0d1220] border-[#00f2fe] shadow-lg shadow-[#00f2fe]/20'
                    : 'bg-[#111318] border-[#242936] hover:border-[#00f2fe]/50'
                }`}
              >
                {tier.name === 'premium' && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-[#00f2fe] text-[#08090d] px-4 py-1 rounded-full text-sm font-bold">
                      MOST POPULAR
                    </span>
                  </div>
                )}

                <div className="flex items-center mb-4">
                  {tier.name === 'starter' && <Star className="w-6 h-6 text-gray-400 mr-2" />}
                  {tier.name === 'pro' && <Shield className="w-6 h-6 text-[#00f2fe] mr-2" />}
                  {tier.name === 'premium' && <Crown className="w-6 h-6 text-[#00f2fe] mr-2" />}
                  <h3 className="text-2xl font-bold text-white">{tier.display_name}</h3>
                </div>

                <p className="text-gray-400 mb-6 h-12">{tier.description}</p>

                <div className="mb-6">
                  <div className="flex items-baseline">
                    <span className="text-4xl font-bold text-white">${price}</span>
                    <span className="text-gray-400 ml-2">/{billing_interval === 'month' ? 'month' : 'year'}</span>
                  </div>
                  {billingInterval === 'year' && savings > 0 && (
                    <p className="text-green-400 text-sm mt-1">Save {savings}% vs monthly</p>
                  )}
                </div>

                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <Check className="w-5 h-5 text-green-400 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSubscribe(tier.name)}
                  disabled={processingTier === tier.name || isCurrentPlan}
                  className={`w-full py-3 rounded-lg font-semibold transition-all ${
                    tier.name === 'premium'
                      ? 'bg-[#00f2fe] hover:bg-[#38bdf8] text-[#08090d]'
                      : 'bg-[#242936] hover:bg-[#2d3446] text-white'
                  } ${isCurrentPlan ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {processingTier === tier.name ? (
                    <div className="flex items-center justify-center">
                      <Loader2 className="w-5 h-5 animate-spin mr-2" />
                      Processing...
                    </div>
                  ) : isCurrentPlan ? (
                    'Current Plan'
                  ) : (
                    <div className="flex items-center justify-center">
                      Get Started
                      <ChevronRight className="w-5 h-5 ml-2" />
                    </div>
                  )}
                </button>

                {tier.auto_execution_enabled && (
                  <div className="mt-4 flex items-center justify-center text-[#00f2fe] text-sm">
                    <Zap className="w-4 h-4 mr-1" />
                    Includes Auto-Execution
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Feature Comparison */}
        <div className="mt-16 bg-[#111318] border border-[#242936] rounded-xl p-8">
          <h2 className="text-2xl font-bold text-white mb-6 text-center">Feature Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#242936]">
                  <th className="text-left py-3 px-4 text-gray-400">Feature</th>
                  {tiers.map(tier => (
                    <th key={tier.id} className="text-center py-3 px-4 text-white font-semibold">
                      {tier.display_name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#242936]">
                  <td className="py-3 px-4 text-gray-300">Real-time Market Signals</td>
                  {tiers.map(tier => (
                    <td key={tier.id} className="text-center py-3 px-4">
                      <Check className="w-5 h-5 text-green-400 mx-auto" />
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-[#242936]">
                  <td className="py-3 px-4 text-gray-300">Auto-Execution</td>
                  {tiers.map(tier => (
                    <td key={tier.id} className="text-center py-3 px-4">
                      {tier.auto_execution_enabled ? (
                        <Check className="w-5 h-5 text-green-400 mx-auto" />
                      ) : (
                        <X className="w-5 h-5 text-red-400 mx-auto" />
                      )}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-[#242936]">
                  <td className="py-3 px-4 text-gray-300">API Access</td>
                  {tiers.map(tier => (
                    <td key={tier.id} className="text-center py-3 px-4">
                      {tier.api_access_enabled ? (
                        <Check className="w-5 h-5 text-green-400 mx-auto" />
                      ) : (
                        <X className="w-5 h-5 text-red-400 mx-auto" />
                      )}
                    </td>
                  ))}
                </tr>
                <tr className="border-b border-[#242936]">
                  <td className="py-3 px-4 text-gray-300">Max MT5 Accounts</td>
                  {tiers.map(tier => (
                    <td key={tier.id} className="text-center py-3 px-4 text-white">
                      {tier.max_accounts === 999 ? 'Unlimited' : tier.max_accounts}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mt-16">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">Frequently Asked Questions</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-[#111318] border border-[#242936] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-2">Can I change my plan later?</h3>
              <p className="text-gray-400">Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately for upgrades and at the next billing cycle for downgrades.</p>
            </div>
            <div className="bg-[#111318] border border-[#242936] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-2">What happens if I cancel?</h3>
              <p className="text-gray-400">You retain access to your current plan until the end of your billing period. Your data is preserved and you can resubscribe at any time.</p>
            </div>
            <div className="bg-[#111318] border border-[#242936] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-2">Is there a free trial?</h3>
              <p className="text-gray-400">We offer a complimentary trial period for new users. After the trial, you can choose the plan that best fits your trading needs.</p>
            </div>
            <div className="bg-[#111318] border border-[#242936] rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-2">What payment methods do you accept?</h3>
              <p className="text-gray-400">We accept all major credit cards through Stripe. Your payment information is secure and never stored on our servers.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}