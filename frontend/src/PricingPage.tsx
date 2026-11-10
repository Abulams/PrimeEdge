import React, { useState, useEffect } from 'react';

import {

  Check,

  X,

  ChevronRight,

  Zap,

  Shield,

  Star,

  Crown,

  Loader2,

  ArrowLeft,

  CheckCircle,

  HelpCircle,

  LogIn,

  Sparkles

} from 'lucide-react';

import { useAuth, apiFetch } from './AuthContext';



interface Tier {

  id: number;

  tier_id?: number;

  name: string;

  display_name: string;

  description: string;

  price_monthly: number;

  price_yearly: number | null;

  price_monthly_ngn?: number;

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

  const { user, isAuthenticated } = useAuth();

  const [tiers, setTiers] = useState<Tier[]>([]);

  const [currentSubscription, setCurrentSubscription] = useState<UserSubscription | null>(null);

  const [loading, setLoading] = useState(true);

  const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');

  const [currency, setCurrency] = useState<'NGN' | 'USD'>('NGN');

  const [processingTier, setProcessingTier] = useState<string | null>(null);

  const [authNotice, setAuthNotice] = useState<string | null>(null);

  const [activationNotice, setActivationNotice] = useState<string | null>(null);



  useEffect(() => {

    fetchTiers();

    fetchCurrentSubscription();



    // Check for success URL parameters or Paystack reference

    const params = new URLSearchParams(window.location.search);

    const reference = params.get('reference') || params.get('trxref');

    const activated = params.get('activated');



    if (reference) {

      const isFlutterwave = params.get('payment') === 'flutterwave' || reference.startsWith('pe_flw_');

      const verifyEndpoint = isFlutterwave

        ? `/api/v1/subscription/flutterwave/verify/${reference}`

        : `/api/v1/subscription/paystack/verify/${reference}`;

      setActivationNotice(isFlutterwave ? 'Verifying payment with Flutterwave...' : 'Verifying payment with Paystack...');

      apiFetch(verifyEndpoint)

        .then(async (res) => {

          if (res.ok) {

            await fetchCurrentSubscription();

            setActivationNotice(`🎉 Payment Successful! Welcome to PrimeEdge ${activated ? activated.toUpperCase() : 'Premium'}.`);

          } else {

            setActivationNotice('Payment received! Updating subscription details...');

            await fetchCurrentSubscription();

          }

        })

        .catch(async () => {

          await fetchCurrentSubscription();

        });

    } else if (activated) {

      setActivationNotice(`🎉 Subscription Active! Welcome to PrimeEdge ${activated.toUpperCase()}.`);

    }

  }, [isAuthenticated]);



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

      const response = await apiFetch('/api/v1/subscription/current');

      if (response.ok) {

        const data = await response.json();

        setCurrentSubscription(data);

      }

    } catch (error) {

      console.error('Failed to fetch subscription:', error);

    }

  };



  const handleSubscribe = async (tierName: string) => {

    // 1. If not authenticated, prompt user to sign in or create account first

    if (!isAuthenticated) {

      setAuthNotice(`Please sign in or create an account to activate your ${tierName.toUpperCase()} plan.`);

      window.scrollTo({ top: 0, behavior: 'smooth' });

      return;

    }



    setProcessingTier(tierName);

    setAuthNotice(null);



    try {

      const endpoint = '/api/v1/subscription/flutterwave/checkout';

      const response = await apiFetch(endpoint, {

        method: 'POST',

        body: JSON.stringify({

          tier_name: tierName,

          billing_interval: billingInterval,

          currency: currency

        })

      });



      if (response.ok) {

        const data = await response.json();

        if (data.checkout_url) {

          // If simulation callback

          if (data.checkout_url.includes('activated=') && !data.checkout_url.includes('paystack.com') && !data.checkout_url.includes('stripe.com')) {

            await fetchCurrentSubscription();

            setActivationNotice(`🎉 Subscription Active! Your ${tierName.toUpperCase()} plan has been activated.`);

            window.scrollTo({ top: 0, behavior: 'smooth' });

          } else {

            // External Paystack or Stripe checkout session

            window.location.href = data.checkout_url;

          }

        }

      } else {

        const error = await response.json().catch(() => ({}));

        alert('Could not start checkout: ' + (error.detail || 'Please try again.'));

      }

    } catch (error) {

      console.error('Checkout error:', error);

      alert('Network error while creating checkout session. Please try again.');

    } finally {

      setProcessingTier(null);

    }

  };



  const handleCancelSubscription = async () => {

    if (!confirm('Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.')) {

      return;

    }



    try {

      const response = await apiFetch('/api/v1/subscription/cancel', {

        method: 'POST'

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

      <div style={{

        minHeight: '100vh',

        backgroundColor: '#08090d',

        display: 'flex',

        flexDirection: 'column',

        alignItems: 'center',

        justifyContent: 'center',

        gap: '16px',

        color: '#94a3b8'

      }}>

        <Loader2 className="animate-spin" size={36} color="#00f2fe" />

        <span style={{ fontSize: '14px', letterSpacing: '0.5px' }}>Loading PrimeEdge Pricing...</span>

      </div>

    );

  }



  return (

    <div style={{

      minHeight: '100vh',

      backgroundColor: '#08090d',

      color: '#f1f5f9',

      fontFamily: "var(--font-sans, 'Outfit', sans-serif)",

      backgroundImage: 'radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.04) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(0, 242, 254, 0.04) 0px, transparent 50%)',

      display: 'flex',

      flexDirection: 'column'

    }}>

      {/* ========================================================================= */}

      {/* TOP HEADER / NAVBAR */}

      {/* ========================================================================= */}

      <header style={{

        position: 'sticky',

        top: 0,

        zIndex: 100,

        backdropFilter: 'blur(16px)',

        WebkitBackdropFilter: 'blur(16px)',

        backgroundColor: 'rgba(8, 9, 13, 0.85)',

        borderBottom: '1px solid rgba(255, 255, 255, 0.08)'

      }}>

        <div style={{

          maxWidth: '1200px',

          margin: '0 auto',

          padding: '16px 24px',

          display: 'flex',

          alignItems: 'center',

          justifyContent: 'space-between'

        }}>

          {/* Logo */}

          <div

            onClick={() => window.location.href = '/'}

            style={{

              display: 'flex',

              alignItems: 'center',

              gap: '12px',

              cursor: 'pointer'

            }}

          >

            <div style={{

              width: '36px',

              height: '36px',

              background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

              borderRadius: '8px',

              display: 'flex',

              alignItems: 'center',

              justifyContent: 'center',

              fontWeight: 900,

              fontSize: '18px',

              color: '#08090d',

              boxShadow: '0 0 16px rgba(0, 242, 254, 0.35)'

            }}>

              P

            </div>

            <div>

              <div style={{ fontSize: '18px', fontWeight: 800, letterSpacing: '-0.3px', color: '#fff' }}>

                PrimeEdge

              </div>

              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600 }}>

                Decision Intelligence

              </div>

            </div>

          </div>



          {/* Nav links */}

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>

            <button

              onClick={() => window.location.href = '/'}

              style={{

                display: 'inline-flex',

                alignItems: 'center',

                gap: '8px',

                background: 'transparent',

                border: '1px solid rgba(255, 255, 255, 0.12)',

                color: '#94a3b8',

                padding: '8px 16px',

                borderRadius: '8px',

                fontSize: '13px',

                fontWeight: 600,

                cursor: 'pointer',

                transition: 'all 0.2s'

              }}

              onMouseEnter={(e) => {

                e.currentTarget.style.borderColor = 'rgba(0, 242, 254, 0.4)';

                e.currentTarget.style.color = '#fff';

              }}

              onMouseLeave={(e) => {

                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';

                e.currentTarget.style.color = '#94a3b8';

              }}

            >

              <ArrowLeft size={15} />

              Back to Home

            </button>



            {isAuthenticated ? (

              <button

                onClick={() => window.location.href = '/'}

                style={{

                  background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                  border: 'none',

                  color: '#08090d',

                  padding: '8px 18px',

                  borderRadius: '8px',

                  fontSize: '13px',

                  fontWeight: 800,

                  cursor: 'pointer',

                  boxShadow: '0 2px 12px rgba(0, 242, 254, 0.3)',

                  transition: 'all 0.2s'

                }}

              >

                Open Terminal

              </button>

            ) : (

              <button

                onClick={() => window.location.href = '/login'}

                style={{

                  background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                  border: 'none',

                  color: '#08090d',

                  padding: '8px 18px',

                  borderRadius: '8px',

                  fontSize: '13px',

                  fontWeight: 800,

                  cursor: 'pointer',

                  boxShadow: '0 2px 12px rgba(0, 242, 254, 0.3)',

                  transition: 'all 0.2s'

                }}

              >

                Sign In

              </button>

            )}

          </div>

        </div>

      </header>



      {/* ========================================================================= */}

      {/* HERO SECTION */}

      {/* ========================================================================= */}

      <main style={{ flex: 1, padding: '40px 24px 80px', maxWidth: '1200px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>

        

        {/* Activation Success Banner */}

        {activationNotice && (

          <div style={{

            background: 'linear-gradient(135deg, rgba(0, 242, 254, 0.15), rgba(16, 185, 129, 0.15))',

            border: '1.5px solid #00f2fe',

            borderRadius: '14px',

            padding: '20px 24px',

            marginBottom: '32px',

            display: 'flex',

            alignItems: 'center',

            justifyContent: 'space-between',

            flexWrap: 'wrap',

            gap: '16px',

            boxShadow: '0 4px 24px rgba(0, 242, 254, 0.25)'

          }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

              <Sparkles size={24} color="#00f2fe" />

              <div>

                <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>

                  {activationNotice}

                </div>

                <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '2px' }}>

                  Your account privileges have been updated. You now have full access to this tier's features.

                </div>

              </div>

            </div>

            <button

              onClick={() => window.location.href = '/'}

              style={{

                background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                color: '#08090d',

                border: 'none',

                padding: '10px 22px',

                borderRadius: '8px',

                fontWeight: 800,

                fontSize: '13px',

                cursor: 'pointer'

              }}

            >

              Launch Trading Cockpit &rarr;

            </button>

          </div>

        )}



        {/* Auth Required Notice */}

        {authNotice && (

          <div style={{

            background: 'rgba(245, 158, 11, 0.12)',

            border: '1px solid rgba(245, 158, 11, 0.4)',

            borderRadius: '14px',

            padding: '20px 24px',

            marginBottom: '32px',

            display: 'flex',

            alignItems: 'center',

            justifyContent: 'space-between',

            flexWrap: 'wrap',

            gap: '16px'

          }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

              <LogIn size={24} color="#f59e0b" />

              <div>

                <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>

                  Sign In Required to Select Plan

                </div>

                <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px' }}>

                  {authNotice}

                </div>

              </div>

            </div>

            <button

              onClick={() => window.location.href = '/login?redirect=/pricing'}

              style={{

                background: '#f59e0b',

                color: '#08090d',

                border: 'none',

                padding: '10px 22px',

                borderRadius: '8px',

                fontWeight: 800,

                fontSize: '13px',

                cursor: 'pointer'

              }}

            >

              Sign In to Continue &rarr;

            </button>

          </div>

        )}



        {/* Launch-offer banner */}

        <div style={{

          background: 'linear-gradient(135deg, rgba(245,158,11,0.18), rgba(251,191,36,0.10))',

          border: '1px solid rgba(245, 158, 11, 0.55)',

          borderRadius: '14px',

          padding: '14px 24px',

          marginBottom: '28px',

          display: 'flex',

          alignItems: 'center',

          justifyContent: 'center',

          gap: '10px'

        }}>

          <Sparkles size={18} color="#fbbf24" />

          <span style={{ fontSize: '15px', fontWeight: 800, color: '#fbbf24', letterSpacing: '0.3px' }}>

            🎉 LIMITED-TIME LAUNCH OFFER — <span style={{ textDecoration: 'underline' }}>50% OFF ALL PLANS</span>

          </span>

          <Sparkles size={18} color="#fbbf24" />

        </div>



        <div style={{ textAlign: 'center', marginBottom: '48px' }}>

          <div style={{

            display: 'inline-flex',

            alignItems: 'center',

            gap: '6px',

            padding: '6px 14px',

            borderRadius: '20px',

            background: 'rgba(0, 242, 254, 0.08)',

            border: '1px solid rgba(0, 242, 254, 0.25)',

            color: '#00f2fe',

            fontSize: '11px',

            fontWeight: 800,

            letterSpacing: '1px',

            textTransform: 'uppercase',

            marginBottom: '16px'

          }}>

            <Zap size={13} />

            Evidence-Based Decision Intelligence

          </div>



          <h1 style={{

            fontSize: 'clamp(28px, 4.5vw, 48px)',

            fontWeight: 800,

            color: '#fff',

            letterSpacing: '-0.5px',

            margin: '0 0 16px 0',

            lineHeight: 1.15

          }}>

            Choose Your Trading Intelligence Tier

          </h1>



          <p style={{

            fontSize: '16px',

            color: '#94a3b8',

            maxWidth: '620px',

            margin: '0 auto 32px',

            lineHeight: 1.6

          }}>

            Evidence-based decision support with automated trade planning, historical replay, and execution controls for serious intraday traders.

          </p>



          {/* Billing Toggle Switch & Currency Selector */}

          <div style={{

            display: 'flex',

            flexDirection: 'column',

            alignItems: 'center',

            gap: '12px'

          }}>

            <div style={{

              display: 'inline-flex',

              alignItems: 'center',

              background: 'rgba(17, 19, 26, 0.9)',

              border: '1px solid rgba(36, 41, 54, 0.8)',

              borderRadius: '12px',

              padding: '4px',

              gap: '4px',

              boxShadow: '0 4px 16px rgba(0,0,0,0.4)'

            }}>

              <button

                onClick={() => setBillingInterval('month')}

                style={{

                  padding: '8px 20px',

                  borderRadius: '8px',

                  fontSize: '13px',

                  fontWeight: 700,

                  border: 'none',

                  cursor: 'pointer',

                  transition: 'all 0.2s',

                  background: billingInterval === 'month' ? 'linear-gradient(135deg, #00f2fe, #38bdf8)' : 'transparent',

                  color: billingInterval === 'month' ? '#08090d' : '#94a3b8'

                }}

              >

                Monthly Billing

              </button>

              <button

                onClick={() => setBillingInterval('year')}

                style={{

                  padding: '8px 20px',

                  borderRadius: '8px',

                  fontSize: '13px',

                  fontWeight: 700,

                  border: 'none',

                  cursor: 'pointer',

                  transition: 'all 0.2s',

                  display: 'inline-flex',

                  alignItems: 'center',

                  gap: '8px',

                  background: billingInterval === 'year' ? 'linear-gradient(135deg, #00f2fe, #38bdf8)' : 'transparent',

                  color: billingInterval === 'year' ? '#08090d' : '#94a3b8'

                }}

              >

                Annual Billing

                <span style={{

                  background: billingInterval === 'year' ? '#08090d' : '#10b981',

                  color: billingInterval === 'year' ? '#00f2fe' : '#fff',

                  fontSize: '10px',

                  fontWeight: 800,

                  padding: '2px 8px',

                  borderRadius: '12px'

                }}>

                  SAVE ~17%

                </span>

              </button>

            </div>



                        {/* Instant Activation Gateway Badge */}

            <div style={{

              display: 'inline-flex',

              alignItems: 'center',

              gap: '8px',

              padding: '8px 18px',

              borderRadius: '20px',

              background: 'rgba(16, 185, 129, 0.12)',

              border: '1px solid rgba(16, 185, 129, 0.35)',

              color: '#34d399',

              fontSize: '13px',

              fontWeight: 700

            }}>

              <span>Instant Card, Bank & USSD Activation (Flutterwave)</span>

            </div>

          </div>

        </div>



        {/* Current Subscription Banner */}

        {currentSubscription && currentSubscription.tier && (

          <div style={{

            background: 'rgba(0, 242, 254, 0.05)',

            border: '1px solid rgba(0, 242, 254, 0.25)',

            borderRadius: '14px',

            padding: '20px 24px',

            marginBottom: '36px',

            display: 'flex',

            alignItems: 'center',

            justifyContent: 'space-between',

            flexWrap: 'wrap',

            gap: '16px'

          }}>

            <div>

              <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>

                <CheckCircle size={18} color="#00f2fe" />

                Active Subscription: {currentSubscription.tier.display_name}

              </div>

              <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>

                Status: <strong style={{ color: '#10b981', textTransform: 'capitalize' }}>{currentSubscription.status}</strong>

                {currentSubscription.cancel_at_period_end && (

                  <span style={{ color: '#f59e0b', marginLeft: '8px' }}>(Cancels at period end)</span>

                )}

              </div>

            </div>



            {!currentSubscription.cancel_at_period_end && (

              <button

                onClick={handleCancelSubscription}

                style={{

                  background: 'rgba(239, 68, 68, 0.15)',

                  border: '1px solid rgba(239, 68, 68, 0.3)',

                  color: '#ef4444',

                  padding: '8px 18px',

                  borderRadius: '8px',

                  fontSize: '13px',

                  fontWeight: 600,

                  cursor: 'pointer',

                  transition: 'all 0.2s'

                }}

                onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'}

                onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'}

              >

                Cancel Subscription

              </button>

            )}

          </div>

        )}



        {/* ========================================================================= */}

        {/* PRICING CARDS */}

        {/* ========================================================================= */}

        <div style={{

          display: 'grid',

          gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))',

          gap: '24px',

          alignItems: 'stretch'

        }}>

          {tiers.map((tier) => {

            const isCurrentPlan = currentSubscription?.tier?.name?.toLowerCase() === tier.name.toLowerCase();

            const savings = getAnnualSavings(tier);

            const price = billingInterval === 'month' ? tier.price_monthly : (tier.price_yearly || tier.price_monthly * 12);

            const isPremium = tier.name === 'premium';

            const isPro = tier.name === 'pro';

            const isFree = tier.name === 'free';

            const Icon = isFree ? Zap : tier.name === 'starter' ? Star : isPro ? Shield : Crown;



            return (

              <div

                key={tier.id}

                style={{

                  position: 'relative',

                  borderRadius: '16px',

                  padding: '36px 28px',

                  display: 'flex',

                  flexDirection: 'column',

                  backgroundColor: isPremium

                    ? 'rgba(15, 23, 42, 0.85)'

                    : isPro

                    ? 'rgba(17, 24, 39, 0.85)'

                    : 'rgba(17, 20, 29, 0.7)',

                  border: isPremium

                    ? '1.5px solid #00f2fe'

                    : isPro

                    ? '1px solid rgba(0, 242, 254, 0.35)'

                    : '1px solid rgba(255, 255, 255, 0.08)',

                  boxShadow: isPremium

                    ? '0 12px 40px rgba(0, 242, 254, 0.15)'

                    : '0 8px 30px rgba(0, 0, 0, 0.4)',

                  transition: 'transform 0.2s, box-shadow 0.2s'

                }}

              >

                {/* Popular Pill */}

                {isPro && (

                  <div style={{

                    position: 'absolute',

                    top: '-13px',

                    left: '50%',

                    transform: 'translateX(-50%)',

                    background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                    color: '#08090d',

                    padding: '4px 14px',

                    borderRadius: '20px',

                    fontSize: '11px',

                    fontWeight: 800,

                    letterSpacing: '0.8px',

                    textTransform: 'uppercase',

                    boxShadow: '0 4px 12px rgba(0, 242, 254, 0.35)'

                  }}>

                    Most Popular

                  </div>

                )}



                {isPremium && (

                  <div style={{

                    position: 'absolute',

                    top: '-13px',

                    left: '50%',

                    transform: 'translateX(-50%)',

                    background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',

                    color: '#08090d',

                    padding: '4px 14px',

                    borderRadius: '20px',

                    fontSize: '11px',

                    fontWeight: 800,

                    letterSpacing: '0.8px',

                    textTransform: 'uppercase',

                    boxShadow: '0 4px 12px rgba(245, 158, 11, 0.35)'

                  }}>

                    Full Platform Access

                  </div>

                )}



                {/* Tier Name & Icon */}

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>

                  <div style={{

                    width: '36px',

                    height: '36px',

                    borderRadius: '8px',

                    background: isPremium ? 'rgba(245, 158, 11, 0.15)' : isPro ? 'rgba(0, 242, 254, 0.15)' : isFree ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.05)',

                    display: 'flex',

                    alignItems: 'center',

                    justifyContent: 'center'

                  }}>

                    <Icon size={20} color={isPremium ? '#fbbf24' : isPro ? '#00f2fe' : isFree ? '#10b981' : '#94a3b8'} />

                  </div>

                  <h3 style={{ fontSize: '22px', fontWeight: 800, color: '#fff', margin: 0 }}>

                    {tier.display_name}

                  </h3>

                </div>



                <p style={{

                  fontSize: '13px',

                  color: '#94a3b8',

                  minHeight: '38px',

                  margin: '0 0 20px 0',

                  lineHeight: 1.5

                }}>

                  {tier.description}

                </p>



                {/* Price — 50% launch offer */}

                <div style={{

                  paddingBottom: '20px',

                  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',

                  marginBottom: '20px'

                }}>

                  {tier.price_monthly > 0 && (

                    <div style={{

                      display: 'inline-flex',

                      alignItems: 'center',

                      gap: '5px',

                      background: 'rgba(245,158,11,0.15)',

                      border: '1px solid rgba(245,158,11,0.4)',

                      borderRadius: '12px',

                      padding: '3px 10px',

                      fontSize: '11px',

                      fontWeight: 800,

                      color: '#fbbf24',

                      letterSpacing: '0.5px',

                      textTransform: 'uppercase' as const,

                      marginBottom: '8px'

                    }}>

                      <Sparkles size={11} />

                      50% OFF - Launch Offer

                    </div>

                  )}

                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' as const }}>

                    <span style={{ fontSize: '38px', fontWeight: 900, color: '#fff', letterSpacing: '-1px' }}>

                      {tier.price_monthly === 0 ? '$0' : currency === 'NGN' ? `₦${(billingInterval === 'month' ? (tier.price_monthly_ngn || (tier.name === 'premium' ? 149500 : tier.name === 'pro' ? 49500 : 22500)) : (tier.price_monthly_ngn || (tier.name === 'premium' ? 149500 : tier.name === 'pro' ? 49500 : 22500)) * 10).toLocaleString()}` : `$${price}`}

                    </span>

                    <span style={{ fontSize: '15px', color: '#64748b', fontWeight: 600 }}>

                      /{billingInterval === 'month' ? 'month' : 'year'}

                    </span>

                    {tier.price_monthly > 0 && (

                      <span style={{ fontSize: '17px', color: '#94a3b8', fontWeight: 600, textDecoration: 'line-through' }}>

                        {currency === 'NGN'

                          ? `₦${(billingInterval === 'month' ? (tier.price_monthly_ngn || (tier.name === 'premium' ? 149500 : tier.name === 'pro' ? 49500 : 22500)) * 2 : (tier.price_monthly_ngn || (tier.name === 'premium' ? 149500 : tier.name === 'pro' ? 49500 : 22500)) * 20).toLocaleString()}`

                          : `$${billingInterval === 'month' ? (tier.price_monthly * 2).toFixed(2) : ((tier.price_yearly || tier.price_monthly * 10) * 2).toFixed(2)}`}

                      </span>

                    )}

                  </div>

                  {billingInterval === 'year' && savings > 0 && (

                    <div style={{ fontSize: '12px', color: '#10b981', fontWeight: 700, marginTop: '4px' }}>

                      Save {savings}% compared to monthly billing

                    </div>

                  )}

                  {currency === 'NGN' && (

                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>

                      Instant activation via Cards, USSD, or Bank Transfer

                    </div>

                  )}

                </div>



                {/* Feature List */}

                <div style={{ flex: 1, marginBottom: '28px' }}>

                  <div style={{

                    fontSize: '11px',

                    textTransform: 'uppercase',

                    letterSpacing: '0.8px',

                    color: '#64748b',

                    fontWeight: 700,

                    marginBottom: '12px'

                  }}>

                    Included Capabilities

                  </div>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>

                    {tier.features.map((feature, idx) => (

                      <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '13px', color: '#cbd5e1', lineHeight: 1.4 }}>

                        <Check size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />

                        <span>{feature}</span>

                      </li>

                    ))}

                  </ul>



                  {tier.auto_execution_enabled && (

                    <div style={{

                      marginTop: '16px',

                      display: 'flex',

                      alignItems: 'center',

                      gap: '8px',

                      padding: '8px 12px',

                      background: 'rgba(0, 242, 254, 0.08)',

                      border: '1px solid rgba(0, 242, 254, 0.25)',

                      borderRadius: '8px',

                      color: '#00f2fe',

                      fontSize: '12px',

                      fontWeight: 700

                    }}>

                      <Zap size={14} />

                      Automated Execution Controls

                    </div>

                  )}

                </div>



                {/* Subscribe CTA Button */}

                <button

                  onClick={() => handleSubscribe(tier.name)}

                  disabled={processingTier === tier.name || isCurrentPlan}

                  style={{

                    width: '100%',

                    padding: '14px',

                    borderRadius: '10px',

                    fontSize: '14px',

                    fontWeight: 800,

                    cursor: isCurrentPlan ? 'default' : 'pointer',

                    border: 'none',

                    display: 'flex',

                    alignItems: 'center',

                    justifyContent: 'center',

                    gap: '8px',

                    transition: 'all 0.2s',

                    background: isCurrentPlan

                      ? 'rgba(255, 255, 255, 0.05)'

                      : isPremium

                      ? 'linear-gradient(135deg, #00f2fe, #38bdf8)'

                      : isPro

                      ? 'linear-gradient(135deg, #00f2fe, #38bdf8)'

                      : 'rgba(255, 255, 255, 0.1)',

                    color: isCurrentPlan

                      ? '#64748b'

                      : isPremium || isPro

                      ? '#08090d'

                      : '#fff',

                    boxShadow: (!isCurrentPlan && (isPremium || isPro))

                      ? '0 4px 20px rgba(0, 242, 254, 0.3)'

                      : 'none',

                    opacity: processingTier === tier.name ? 0.7 : 1

                  }}

                  onMouseEnter={(e) => {

                    if (!isCurrentPlan) {

                      e.currentTarget.style.transform = 'translateY(-2px)';

                    }

                  }}

                  onMouseLeave={(e) => {

                    if (!isCurrentPlan) {

                      e.currentTarget.style.transform = 'translateY(0)';

                    }

                  }}

                >

                  {processingTier === tier.name ? (

                    <>

                      <Loader2 size={16} className="animate-spin" />

                      Preparing Checkout...

                    </>

                  ) : isCurrentPlan ? (

                    'Current Active Plan'

                  ) : tier.price_monthly === 0 ? (

                    <>

                      Included with Account

                      <ChevronRight size={16} />

                    </>

                  ) : (

                    <>

                      Get Started with {tier.display_name}

                      <ChevronRight size={16} />

                    </>

                  )}

                </button>

              </div>

            );

          })}

        </div>



        {/* ========================================================================= */}

        {/* FEATURE COMPARISON TABLE */}

        {/* ========================================================================= */}

        <section style={{

          marginTop: '72px',

          backgroundColor: 'rgba(17, 24, 39, 0.75)',

          border: '1px solid rgba(36, 41, 54, 0.8)',

          borderRadius: '16px',

          padding: '36px 28px',

          boxShadow: '0 8px 30px rgba(0,0,0,0.5)'

        }}>

          <div style={{ textAlign: 'center', marginBottom: '28px' }}>

            <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', margin: '0 0 8px 0' }}>

              Feature Comparison Matrix

            </h2>

            <p style={{ fontSize: '14px', color: '#94a3b8', margin: 0 }}>

              Compare capabilities side-by-side to find the right execution fit

            </p>

          </div>



          <div style={{ overflowX: 'auto' }}>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', minWidth: '600px' }}>

              <thead>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>

                  <th style={{ padding: '14px 16px', color: '#94a3b8', fontSize: '13px', fontWeight: 600 }}>Capability</th>

                  {tiers.map((t) => (

                    <th key={t.id} style={{ padding: '14px 16px', textAlign: 'center', color: '#fff', fontSize: '14px', fontWeight: 800 }}>

                      {t.display_name}

                    </th>

                  ))}

                </tr>

              </thead>

              <tbody>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>Real-time Market Signals (MSD Corridors)</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center' }}>

                      <CheckCircle size={18} color="#10b981" style={{ display: 'inline-block' }} />

                    </td>

                  ))}

                </tr>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>Opportunity Radar & Scorecard</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center' }}>

                      <CheckCircle size={18} color="#10b981" style={{ display: 'inline-block' }} />

                    </td>

                  ))}

                </tr>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>Trade Planner Cockpit & P90 Invalidation Boundaries</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center' }}>

                      <CheckCircle size={18} color="#10b981" style={{ display: 'inline-block' }} />

                    </td>

                  ))}

                </tr>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>Autonomous cTrader Execution (Cloud Worker Node)</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center' }}>

                      {t.auto_execution_enabled ? (

                        <CheckCircle size={18} color="#00f2fe" style={{ display: 'inline-block' }} />

                      ) : (

                        <X size={18} color="#64748b" style={{ display: 'inline-block' }} />

                      )}

                    </td>

                  ))}

                </tr>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>API Access & Webhooks</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center' }}>

                      {t.api_access_enabled ? (

                        <CheckCircle size={18} color="#10b981" style={{ display: 'inline-block' }} />

                      ) : (

                        <X size={18} color="#64748b" style={{ display: 'inline-block' }} />

                      )}

                    </td>

                  ))}

                </tr>

                <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>

                  <td style={{ padding: '14px 16px', fontSize: '13px', color: '#cbd5e1' }}>Connected cTrader Accounts (MT5 Coming Soon)</td>

                  {tiers.map((t) => (

                    <td key={t.id} style={{ padding: '14px 16px', textAlign: 'center', fontSize: '13px', fontWeight: 700, color: '#fff' }}>

                      {t.max_accounts >= 999 ? 'Unlimited' : `${t.max_accounts} Account${t.max_accounts > 1 ? 's' : ''}`}

                    </td>

                  ))}

                </tr>

              </tbody>

            </table>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* FAQ SECTION */}

        {/* ========================================================================= */}

        <section style={{ marginTop: '72px' }}>

          <div style={{ textAlign: 'center', marginBottom: '36px' }}>

            <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', margin: '0 0 8px 0' }}>

              Frequently Asked Questions

            </h2>

            <p style={{ fontSize: '14px', color: '#94a3b8', margin: 0 }}>

              Everything you need to know about PrimeEdge subscriptions

            </p>

          </div>



          <div style={{

            display: 'grid',

            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',

            gap: '20px'

          }}>

            {[

              {

                q: 'Can I upgrade or downgrade my tier later?',

                a: 'Yes. You can upgrade at any time and get instant access to higher-tier features. Billing is prorated automatically through Stripe.'

              },

              {

                q: 'How does Cloud cTrader Execution work in Premium?',

                a: 'PrimeEdge connects securely to your cTrader account via OpenAPI with dedicated, sandboxed execution workers for sub-millisecond execution and automated risk guardrails (MT5 support coming soon).'

              },

              {

                q: 'What happens if I cancel my subscription?',

                a: 'You retain full access to your plan until the end of your prepaid period. Your data and trading history remain safe and preserved.'

              },

              {

                q: 'What payment methods are supported?',

                a: 'We accept all major credit and debit cards, Apple Pay, and Google Pay through Stripe with 256-bit institutional encryption.'

              }

            ].map((faq, idx) => (

              <div

                key={idx}

                style={{

                  background: 'rgba(17, 24, 39, 0.6)',

                  border: '1px solid rgba(255, 255, 255, 0.08)',

                  borderRadius: '12px',

                  padding: '24px'

                }}

              >

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', marginBottom: '8px' }}>

                  <HelpCircle size={18} color="#00f2fe" style={{ flexShrink: 0, marginTop: '2px' }} />

                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: 0 }}>{faq.q}</h3>

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6, margin: 0, paddingLeft: '28px' }}>

                  {faq.a}

                </p>

              </div>

            ))}

          </div>

        </section>

      </main>



      {/* ========================================================================= */}

      {/* FOOTER */}

      {/* ========================================================================= */}

      <footer style={{

        borderTop: '1px solid rgba(255, 255, 255, 0.08)',

        backgroundColor: 'rgba(8, 9, 13, 0.95)',

        padding: '36px 24px',

        marginTop: '60px'

      }}>

        <div style={{

          maxWidth: '1200px',

          margin: '0 auto',

          display: 'flex',

          flexDirection: 'column',

          alignItems: 'center',

          gap: '16px',

          textAlign: 'center'

        }}>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

            <div style={{

              width: '24px',

              height: '24px',

              background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

              borderRadius: '6px',

              display: 'flex',

              alignItems: 'center',

              justifyContent: 'center',

              fontWeight: 900,

              fontSize: '12px',

              color: '#08090d'

            }}>

              P

            </div>

            <span style={{ fontSize: '15px', fontWeight: 800, color: '#fff' }}>PrimeEdge</span>

          </div>



          <div style={{ display: 'flex', gap: '20px', fontSize: '12px' }}>

            <a href="/terms.html" style={{ color: '#94a3b8', textDecoration: 'none' }}>Terms & Risk Disclosure</a>

            <span style={{ color: '#334155' }}>|</span>

            <a href="/privacy.html" style={{ color: '#94a3b8', textDecoration: 'none' }}>Privacy Policy</a>

            <span style={{ color: '#334155' }}>|</span>

            <a href="mailto:support@primeedge.app" style={{ color: '#94a3b8', textDecoration: 'none' }}>Contact Support</a>

          </div>



          <div style={{ fontSize: '11px', color: '#64748b', maxWidth: '720px', lineHeight: 1.5 }}>

            Trading foreign exchange, commodities, and CFDs carries a high level of risk and may not be suitable for all investors. PrimeEdge provides algorithmic decision support tools and does not guarantee financial returns.

          </div>



          <div style={{ fontSize: '11px', color: '#475569' }}>

            &copy; {new Date().getFullYear()} PrimeEdge Technologies. All rights reserved.

          </div>

        </div>

      </footer>

    </div>

  );

}

