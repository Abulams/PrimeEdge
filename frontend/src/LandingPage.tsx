import React, { useState, useEffect } from 'react';

import {

  Compass,

  Sliders,

  TrendingUp,

  Zap,

  BookOpen,

  CheckCircle,

  XCircle,

  ShieldCheck,

  ChevronDown,

  ChevronUp,

  ArrowRight,

  Activity,

  Layers,

  Database,

  Lock,

  LineChart,

  RefreshCw,

  Eye,

  Crosshair,

  Award,

  Terminal,

  Server,

  FileCheck,

  Star as StarIcon,

  Shield,

  Crown,

  ChevronRight,

  Sparkles

} from 'lucide-react';



interface LandingPageProps {

  onEnterApp?: () => void;

  onOpenWaitlist?: () => void;

  isAuthenticated?: boolean;

}



export default function LandingPage({ onEnterApp, onOpenWaitlist, isAuthenticated }: LandingPageProps) {

  const [tiers, setTiers] = useState<any[]>([]);



  useEffect(() => {

    fetch('/api/v1/subscription/tiers')

      .then(res => res.json())

      .then(data => setTiers(data))

      .catch(err => console.error('Failed to fetch tiers:', err));

  }, []);



  // Navigation helper

  const handleAppClick = () => {

    if (onEnterApp) {

      onEnterApp();

    } else {

      window.location.href = isAuthenticated ? '/' : '/login';

    }

  };



  const handleWaitlistClick = () => {

    if (onOpenWaitlist) {

      onOpenWaitlist();

    } else {

      window.location.href = '/register';

    }

  };



  // Section 3: Interactive Tab state for FIND -> PLAN -> WHY -> EXECUTE -> LEARN

  const [activeWorkflowTab, setActiveWorkflowTab] = useState<'find' | 'plan' | 'why' | 'execute' | 'learn'>('find');



  // Section 5: Show Product interactive preview state

  const [activeProductTab, setActiveProductTab] = useState<'radar' | 'planner' | 'journal'>('radar');



  // Section 12: Accordion state for FAQs

  const [openFaq, setOpenFaq] = useState<number | null>(0);



  const toggleFaq = (index: number) => {

    setOpenFaq(openFaq === index ? null : index);

  };



  return (

    <div style={{

      minHeight: '100vh',

      backgroundColor: '#08090d',

      color: '#f1f5f9',

      fontFamily: "'Outfit', -apple-system, BlinkMacSystemFont, sans-serif",

      overflowX: 'hidden',

      lineHeight: 1.6

    }}>

      {/* BACKGROUND GLOW ACCENTS */}

      <div style={{

        position: 'fixed',

        top: 0,

        left: 0,

        right: 0,

        bottom: 0,

        backgroundImage: 'radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.04) 0px, transparent 60%), radial-gradient(at 100% 100%, rgba(0, 242, 254, 0.04) 0px, transparent 60%)',

        pointerEvents: 'none',

        zIndex: 0

      }} />



      {/* STICKY TOP NAVIGATION BAR */}

      <header style={{

        position: 'sticky',

        top: 0,

        zIndex: 50,

        backgroundColor: 'rgba(8, 9, 13, 0.85)',

        backdropFilter: 'blur(16px)',

        WebkitBackdropFilter: 'blur(16px)',

        borderBottom: '1px solid rgba(36, 41, 54, 0.8)',

        padding: '14px 24px'

      }}>

        <div style={{

          maxWidth: '1200px',

          margin: '0 auto',

          display: 'flex',

          alignItems: 'center',

          justifyContent: 'space-between',

          gap: '16px'

        }}>

          {/* Logo */}

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

            <div style={{

              width: '34px',

              height: '34px',

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



          {/* Quick Nav Anchor Links (Desktop) */}

          <nav style={{ display: 'flex', alignItems: 'center', gap: '24px' }} className="landing-nav-links">

            <a href="#problem" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '13px', fontWeight: 500, transition: 'color 0.2s' }}>

              The Challenge

            </a>

            <a href="#workflow" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '13px', fontWeight: 500, transition: 'color 0.2s' }}>

              The 5-Step System

            </a>

            <a href="#differentiation" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '13px', fontWeight: 500, transition: 'color 0.2s' }}>

              How It Differs

            </a>

            <a href="#product" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '13px', fontWeight: 500, transition: 'color 0.2s' }}>

              Live System

            </a>

            <a href="/pricing" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '13px', fontWeight: 500, transition: 'color 0.2s' }}>

              Pricing

            </a>

          </nav>



          {/* Right Action Buttons */}

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>

            <button

              onClick={handleAppClick}

              style={{

                background: 'transparent',

                border: '1px solid rgba(255, 255, 255, 0.15)',

                color: '#f1f5f9',

                padding: '8px 16px',

                borderRadius: '8px',

                fontSize: '13px',

                fontWeight: 600,

                cursor: 'pointer',

                transition: 'all 0.2s'

              }}

              onMouseEnter={(e) => {

                e.currentTarget.style.borderColor = 'rgba(0, 242, 254, 0.5)';

                e.currentTarget.style.color = '#00f2fe';

              }}

              onMouseLeave={(e) => {

                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';

                e.currentTarget.style.color = '#f1f5f9';

              }}

            >

              {isAuthenticated ? 'Open Terminal' : 'Sign In'}

            </button>



            <button

              onClick={() => window.location.href = '/pricing'}

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

                display: 'flex',

                alignItems: 'center',

                gap: '6px',

                transition: 'transform 0.15s, box-shadow 0.15s'

              }}

              onMouseEnter={(e) => {

                e.currentTarget.style.transform = 'translateY(-1px)';

                e.currentTarget.style.boxShadow = '0 4px 18px rgba(0, 242, 254, 0.45)';

              }}

              onMouseLeave={(e) => {

                e.currentTarget.style.transform = 'none';

                e.currentTarget.style.boxShadow = '0 2px 12px rgba(0, 242, 254, 0.3)';

              }}

            >

              View Pricing

              <ArrowRight size={14} />

            </button>

          </div>

        </div>

      </header>



      {/* MAIN CONTAINER */}

      <main style={{ position: 'relative', zIndex: 1 }}>



        {/* ========================================================================= */}

        {/* SECTION 1: HERO (5-Second Clarity & Primary CTA) */}

        {/* ========================================================================= */}

        <section style={{

          padding: '72px 24px 60px',

          maxWidth: '1200px',

          margin: '0 auto',

          textAlign: 'center'

        }}>

          {/* Launch Offer Banner */}

          <div

            onClick={() => window.location.href = '/pricing'}

            style={{

              display: 'inline-flex',

              alignItems: 'center',

              gap: '10px',

              background: 'linear-gradient(135deg, rgba(245,158,11,0.18), rgba(251,191,36,0.10))',

              border: '1px solid rgba(245, 158, 11, 0.55)',

              borderRadius: '14px',

              padding: '10px 20px',

              marginBottom: '24px',

              cursor: 'pointer'

            }}

          >

            <Sparkles size={15} color="#fbbf24" />

            <span style={{ fontSize: '13px', fontWeight: 800, color: '#fbbf24' }}>

              50% OFF ALL PLANS  -  Limited-Time Launch Offer

            </span>

            <ArrowRight size={13} color="#fbbf24" />

          </div>



          {/* Top Badge */}

          <div style={{

            display: 'inline-flex',

            alignItems: 'center',

            gap: '8px',

            padding: '6px 14px',

            borderRadius: '999px',

            backgroundColor: 'rgba(0, 242, 254, 0.1)',

            border: '1px solid rgba(0, 242, 254, 0.3)',

            fontSize: '12px',

            fontWeight: 700,

            color: '#00f2fe',

            marginBottom: '24px'

          }}>

            <span style={{

              width: '8px',

              height: '8px',

              borderRadius: '50%',

              backgroundColor: '#00f2fe',

              boxShadow: '0 0 8px #00f2fe'

            }} />

            <span>EVIDENCE-BASED DECISION SUPPORT</span>

          </div>



          {/* Main Headline */}

          <h1 style={{

            fontSize: 'clamp(32px, 5.5vw, 56px)',

            fontWeight: 800,

            letterSpacing: '-1.5px',

            lineHeight: 1.15,

            maxWidth: '960px',

            margin: '0 auto 20px',

            color: '#ffffff'

          }}>

            Turn Trading Setups Into <br />

            <span style={{

              background: 'linear-gradient(135deg, #00f2fe 0%, #38bdf8 50%, #818cf8 100%)',

              WebkitBackgroundClip: 'text',

              WebkitTextFillColor: 'transparent'

            }}>

              Evidence-Based Decisions.

            </span>

          </h1>



          {/* Subheadline */}

          <p style={{

            fontSize: 'clamp(16px, 2vw, 19px)',

            color: '#94a3b8',

            maxWidth: '760px',

            margin: '0 auto 36px',

            lineHeight: 1.6

          }}>

            PrimeEdge helps intraday FX and gold traders evaluate setups with historical evidence, define risk-aware entry and invalidation zones, replay past conditions and record every decision before execution.

          </p>



          {/* Hero CTAs */}

          <div style={{

            display: 'flex',

            alignItems: 'center',

            justifyContent: 'center',

            gap: '16px',

            flexWrap: 'wrap',

            marginBottom: '48px'

          }}>

            <button

              onClick={() => window.location.href = '/pricing'}

              style={{

                background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                border: 'none',

                color: '#08090d',

                padding: '14px 32px',

                borderRadius: '10px',

                fontSize: '15px',

                fontWeight: 800,

                cursor: 'pointer',

                boxShadow: '0 4px 20px rgba(0, 242, 254, 0.4)',

                display: 'inline-flex',

                alignItems: 'center',

                gap: '10px',

                transition: 'all 0.2s'

              }}

              onMouseEnter={(e) => {

                e.currentTarget.style.transform = 'translateY(-2px)';

                e.currentTarget.style.boxShadow = '0 6px 26px rgba(0, 242, 254, 0.55)';

              }}

              onMouseLeave={(e) => {

                e.currentTarget.style.transform = 'none';

                e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 242, 254, 0.4)';

              }}

            >

              Get Started

              <ArrowRight size={18} />

            </button>



            <button

              onClick={handleAppClick}

              style={{

                background: 'rgba(17, 24, 39, 0.8)',

                border: '1px solid rgba(255, 255, 255, 0.15)',

                color: '#f1f5f9',

                padding: '14px 26px',

                borderRadius: '10px',

                fontSize: '15px',

                fontWeight: 700,

                cursor: 'pointer',

                display: 'inline-flex',

                alignItems: 'center',

                gap: '8px',

                backdropFilter: 'blur(8px)',

                transition: 'all 0.2s'

              }}

              onMouseEnter={(e) => {

                e.currentTarget.style.borderColor = 'rgba(0, 242, 254, 0.5)';

                e.currentTarget.style.background = 'rgba(25, 33, 50, 0.9)';

              }}

              onMouseLeave={(e) => {

                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.15)';

                e.currentTarget.style.background = 'rgba(17, 24, 39, 0.8)';

              }}

            >

              <Terminal size={17} color="#00f2fe" />

              {isAuthenticated ? 'Enter Trading Terminal' : 'Sign In to Workspace'}

            </button>

          </div>



          {/* Micro Proof Bar */}

          <div style={{

            display: 'flex',

            alignItems: 'center',

            justifyContent: 'center',

            gap: '32px',

            flexWrap: 'wrap',

            fontSize: '12px',

            color: '#64748b',

            paddingBottom: '32px'

          }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>

              <ShieldCheck size={16} color="#10b981" />

              <span>Zero Black-Box Guarantees</span>

            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>

              <Activity size={16} color="#00f2fe" />

              <span>Historical MAE/MFE Distributions</span>

            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>

              <Server size={16} color="#38bdf8" />

              <span>Isolated Execution Nodes</span>

            </div>

          </div>



          {/* REAL TERMINAL PREVIEW */}

          <div style={{ position: 'relative', borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 242, 254, 0.1)' }}>

            {/* Window chrome bar */}

            <div style={{ padding: '10px 18px', backgroundColor: 'rgba(15, 23, 42, 0.95)', borderBottom: '1px solid rgba(255, 255, 255, 0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#ef4444' }} />

                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />

                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#10b981' }} />

                <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '12px', fontFamily: 'monospace' }}>PrimeEdge Terminal v2.4 | London Core</span>

              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#10b981' }}>

                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10b981' }} />

                LIVE

              </div>

            </div>

            <img

              src="/screenshots/radar.png"

              alt="PrimeEdge Live Opportunity Radar showing GBPUSD READY, EURUSD WAIT, and AUDUSD setups with evidence scores"

              style={{ width: '100%', display: 'block' }}

            />

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 2: THE PROBLEM (StoryBrand - The Villain) */}

        {/* ========================================================================= */}

        <section id="problem" style={{

          padding: '80px 24px',

          backgroundColor: '#0c0e14',

          borderTop: '1px solid rgba(255, 255, 255, 0.05)',

          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'

        }}>

          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            <div style={{ textAlign: 'center', marginBottom: '48px' }}>

              <span style={{ fontSize: '12px', fontWeight: 700, color: '#00f2fe', textTransform: 'uppercase', letterSpacing: '1px' }}>

                The Decision Paradox

              </span>

              <h2 style={{ fontSize: 'clamp(26px, 4vw, 40px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

                Trading Information Isn't the Problem. <br />

                Turning It Into a Decision Is.

              </h2>

              <p style={{ fontSize: '16px', color: '#94a3b8', maxWidth: '700px', margin: '14px auto 0' }}>

                Traders don't blow accounts because they lack indicators. They struggle because their decision process is fragmented across disjointed tools, discretionary second-guessing, and uncontrolled execution slip.

              </p>

            </div>



            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>

              {/* Friction 1 */}

              <div style={{

                backgroundColor: 'rgba(17, 24, 39, 0.6)',

                border: '1px solid rgba(239, 68, 68, 0.2)',

                borderRadius: '12px',

                padding: '24px'

              }}>

                <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>

                  <XCircle size={22} color="#ef4444" />

                </div>

                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>

                  Arbitrary Invalidation & Hope

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Setting stop losses at "random round numbers" or tight arbitrary swings leads to premature stops on normal intraday noise. You lack historical evidence on whether price excursions are routine or thesis-breaking.

                </p>

              </div>



              {/* Friction 2 */}

              <div style={{

                backgroundColor: 'rgba(17, 24, 39, 0.6)',

                border: '1px solid rgba(245, 158, 11, 0.2)',

                borderRadius: '12px',

                padding: '24px'

              }}>

                <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>

                  <Eye size={22} color="#f59e0b" />

                </div>

                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>

                  FOMO vs. Waiting Cost Paralysis

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Should you market execute right now, or set a limit order deeper in the corridor? Without empirical fill rates vs. miss rate costs, every entry is an emotional guess that causes chasing.

                </p>

              </div>



              {/* Friction 3 */}

              <div style={{

                backgroundColor: 'rgba(17, 24, 39, 0.6)',

                border: '1px solid rgba(129, 140, 248, 0.2)',

                borderRadius: '12px',

                padding: '24px'

              }}>

                <div style={{ width: '40px', height: '40px', borderRadius: '8px', backgroundColor: 'rgba(129, 140, 248, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>

                  <RefreshCw size={22} color="#818cf8" />

                </div>

                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>

                  Manual & Sloppy Journaling

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.6 }}>

                  By the time you open a spreadsheet hours later, your memory of the setup context, regime alignment, and intra-trade drawdowns is distorted. You cannot systematically compound what you do not objectively record.

                </p>

              </div>

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 3: THE PRIMEEDGE WORKFLOW (StoryBrand - The Plan) */}

        {/* ========================================================================= */}

        <section id="workflow" style={{ padding: '80px 24px', maxWidth: '1200px', margin: '0 auto' }}>

          <div style={{ textAlign: 'center', marginBottom: '40px' }}>

            <span style={{ fontSize: '12px', fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '1px' }}>

              The 5-Stage Disciplined System

            </span>

            <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

              From Market Noise to Objective Execution

            </h2>

            <p style={{ fontSize: '15px', color: '#94a3b8', maxWidth: '680px', margin: '12px auto 0' }}>

              Every trade in PrimeEdge moves sequentially through a 5-step gate. No skipping. No guessing. Complete institutional rigor from signal discovery to post-trade review.

            </p>

          </div>



          {/* Workflow Step Selector Tabs */}

          <div style={{

            display: 'flex',

            justifyContent: 'center',

            gap: '8px',

            flexWrap: 'wrap',

            marginBottom: '32px'

          }}>

            {[

              { id: 'find', label: '1. FIND', desc: 'Opportunity Radar' },

              { id: 'plan', label: '2. PLAN', desc: 'Empirical Cockpit' },

              { id: 'why', label: '3. WHY', desc: 'Quantitative Evidence' },

              { id: 'execute', label: '4. EXECUTE', desc: 'Process Bridge' },

              { id: 'learn', label: '5. LEARN', desc: 'Auto-Journal & Replay' }

            ].map((step) => {

              const active = activeWorkflowTab === step.id;

              return (

                <button

                  key={step.id}

                  onClick={() => setActiveWorkflowTab(step.id as any)}

                  style={{

                    padding: '10px 14px',

                    borderRadius: '10px',

                    border: active ? '1px solid #00f2fe' : '1px solid rgba(255,255,255,0.08)',

                    background: active ? 'rgba(0, 242, 254, 0.12)' : 'rgba(17, 24, 39, 0.6)',

                    color: active ? '#00f2fe' : '#94a3b8',

                    cursor: 'pointer',

                    display: 'flex',

                    flexDirection: 'column',

                    alignItems: 'center',

                    gap: '2px',

                    transition: 'all 0.2s',

                    minWidth: '110px',

                    flex: '1 1 auto'

                  }}

                >

                  <span style={{ fontSize: '13px', fontWeight: 800 }}>{step.label}</span>

                  <span style={{ fontSize: '10px', opacity: 0.8 }}>{step.desc}</span>

                </button>

              );

            })}

          </div>



          {/* Workflow Interactive Content Detail */}

          <div style={{

            backgroundColor: 'rgba(17, 24, 39, 0.8)',

            border: '1px solid rgba(0, 242, 254, 0.25)',

            borderRadius: '16px',

            padding: '24px 16px',

            boxShadow: '0 12px 30px rgba(0,0,0,0.5)'

          }}>

            {activeWorkflowTab === 'find' && (

              <div className="landing-workflow-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'center' }}>

                <div>

                  <div style={{ display: 'inline-flex', padding: '4px 10px', borderRadius: '6px', background: 'rgba(0,242,254,0.1)', color: '#00f2fe', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>

                    STAGE 1: OPPORTUNITY RADAR

                  </div>

                  <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

                    Continuous Session Regime Scanning

                  </h3>

                  <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.7, marginBottom: '16px' }}>

                    PrimeEdge monitors Asian, London, and New York session opens across major FX and commodities. It synthesizes Dollar Index (DXY) momentum, Treasury yield slopes, and session liquidity sweeps into a unified <strong>Market Signature Score (MSS)</strong>.

                  </p>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Strict session filtering  -  zero chasing during off-hours chop.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Triple-state qualification: READY, WAIT, or MONITOR.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Direct explanation of why this symbol is flagged right now.

                    </li>

                  </ul>

                </div>

                <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 8px 24px rgba(0, 242, 254, 0.12)' }}>

                  <img src="/screenshots/radar.png" alt="PrimeEdge Opportunity Radar - Live MSS Scanning" style={{ width: '100%', display: 'block' }} />

                </div>

              </div>

            )}



            {activeWorkflowTab === 'plan' && (

              <div className="landing-workflow-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'center' }}>

                <div>

                  <div style={{ display: 'inline-flex', padding: '4px 10px', borderRadius: '6px', background: 'rgba(0,242,254,0.1)', color: '#00f2fe', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>

                    STAGE 2: TRADE PLANNER COCKPIT

                  </div>

                  <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

                    Empirical Invalidations & Entry Corridors

                  </h3>

                  <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.7, marginBottom: '16px' }}>

                    Stop guessing where to place your stop-loss. PrimeEdge computes the exact <strong>P90 Adverse Excursion Boundary</strong> from historical analogs. If price hits the P90 level, the thesis is statistically dead.

                  </p>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Acceptable entry corridor: P25 to P75 retracement zones.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Real waiting cost comparison: Market order vs. Limit order.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Auto-computed lot sizes pegged strictly to your % account risk.

                    </li>

                  </ul>

                </div>

                <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 8px 24px rgba(0, 242, 254, 0.12)' }}>

                  <img src="/screenshots/cockpit.png" alt="PrimeEdge Trade Planner Cockpit" style={{ width: '100%', display: 'block' }} />

                </div>

              </div>

            )}



            {activeWorkflowTab === 'why' && (

              <div className="landing-workflow-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'center' }}>

                <div>

                  <div style={{ display: 'inline-flex', padding: '4px 10px', borderRadius: '6px', background: 'rgba(0,242,254,0.1)', color: '#00f2fe', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>

                    STAGE 3: WHY (EVIDENCE AUDIT)

                  </div>

                  <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

                    Historical Similarity & Distribution Audit

                  </h3>

                  <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.7, marginBottom: '16px' }}>

                    Never enter on a blind hunch. PrimeEdge matches current market microstructure against a point-in-time database of historical session signatures. You inspect the exact historical trading days with identical volatility, trend slope, and DXY context.

                  </p>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Complete MAE/MFE histograms showing outcome dispersion.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Zero look-ahead bias  -  all historical analogies evaluated point-in-time.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Full transparency into sample size confidence penalties.

                    </li>

                  </ul>

                </div>

                <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 8px 24px rgba(0, 242, 254, 0.12)' }}>

                  <img src="/screenshots/why.png" alt="PrimeEdge WHY Evidence Audit" style={{ width: '100%', display: 'block' }} />

                </div>

              </div>

            )}



            {activeWorkflowTab === 'execute' && (

              <div className="landing-workflow-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'center' }}>

                <div>

                  <div style={{ display: 'inline-flex', padding: '4px 10px', borderRadius: '6px', background: 'rgba(0,242,254,0.1)', color: '#00f2fe', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>

                    STAGE 4: EXECUTION & GUARDRAILS

                  </div>

                  <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

                    Cloud cTrader Execution & Guardrails

                  </h3>

                  <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.7, marginBottom: '16px' }}>

                    Orders route through private, sandboxed execution worker processes with hard-coded guardrails that prevent slippage, news spikes, and fat-finger position sizing.

                  </p>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Early Invalidation Guardrail: auto-kills positions showing zero structural traction.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Spread & Slippage Caps: rejects market fills if spread widens beyond tolerance.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Zero shared credentials: direct cTrader OpenAPI execution without desktop terminals running.

                    </li>

                  </ul>

                </div>

                <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 8px 24px rgba(0, 242, 254, 0.12)' }}>

                  <img src="/screenshots/execution.png" alt="PrimeEdge Cloud cTrader Execution Guardrails" style={{ width: '100%', display: 'block' }} />

                </div>

              </div>

            )}



            {activeWorkflowTab === 'learn' && (

              <div className="landing-workflow-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px', alignItems: 'center' }}>

                <div>

                  <div style={{ display: 'inline-flex', padding: '4px 10px', borderRadius: '6px', background: 'rgba(0,242,254,0.1)', color: '#00f2fe', fontSize: '12px', fontWeight: 800, marginBottom: '12px' }}>

                    STAGE 5: AUTO-JOURNAL & REPLAY

                  </div>

                  <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

                    Zero-Effort Telemetry & Deterministic Replay

                  </h3>

                  <p style={{ fontSize: '14px', color: '#94a3b8', lineHeight: 1.7, marginBottom: '16px' }}>

                    The moment a trade is executed, PrimeEdge logs the fill price, slippage, setup snapshot ID, and intra-trade MAE/MFE. Test new execution rules deterministically with full historical batch replay.

                  </p>

                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Complete execution autopsy: PnL (R-multiple), adverse pips, and holding time.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> Replay Engine: simulate alternative entry corridor rules across historical batches.

                    </li>

                    <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>

                      <CheckCircle size={15} color="#10b981" /> PDF & CSV audit export for trade review and decision analysis.

                    </li>

                  </ul>

                </div>

                <div style={{ borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 242, 254, 0.2)', boxShadow: '0 8px 24px rgba(0, 242, 254, 0.12)' }}>

                  <img src="/screenshots/chart.png" alt="PrimeEdge Auto Journal and Chart Analytics" style={{ width: '100%', display: 'block' }} />

                </div>

              </div>

            )}

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 4: WHAT MAKES PRIMEEDGE DIFFERENT (April Dunford Positioning) */}

        {/* ========================================================================= */}

        <section id="differentiation" style={{

          padding: '80px 24px',

          backgroundColor: '#0c0e14',

          borderTop: '1px solid rgba(255, 255, 255, 0.05)',

          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'

        }}>

          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            <div style={{ textAlign: 'center', marginBottom: '48px' }}>

              <span style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '1px' }}>

                Competitive Differentiation

              </span>

              <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

                What PrimeEdge Is  -  And What It Is Not

              </h2>

              <p style={{ fontSize: '15px', color: '#94a3b8', maxWidth: '680px', margin: '12px auto 0' }}>

                Most trading software attempts to replace the trader with a black-box or flood them with 50 indicators. PrimeEdge is trading decision infrastructure.

              </p>

            </div>



            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px' }}>

              {/* Not A Signal Group */}

              <div style={{ background: 'rgba(17, 24, 39, 0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '24px' }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>

                  <XCircle size={20} color="#ef4444" />

                  <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Not a Signal Group</span>

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Telegram channels give cryptic calls without invalidation logic or risk bounds. PrimeEdge gives structured setups with verified MAE/MFE sample sizes, dynamic entry corridors, and macro context.

                </p>

              </div>



              {/* Not An EA / Black-Box Bot */}

              <div style={{ background: 'rgba(17, 24, 39, 0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '24px' }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>

                  <XCircle size={20} color="#ef4444" />

                  <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Not a Black-Box EA</span>

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Automated EAs blindly execute until market conditions change and blow up the account. PrimeEdge puts you in the cockpit with human-governed execution, regime gates, and early invalidation protection.

                </p>

              </div>



              {/* Not A Charting Tool */}

              <div style={{ background: 'rgba(17, 24, 39, 0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '24px' }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>

                  <XCircle size={20} color="#ef4444" />

                  <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Not Just Charting</span>

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Charting platforms show price lines after they happen. PrimeEdge calculates point-in-time statistical distributions: expected adverse excursion, fill probability, and waiting cost tradeoffs.

                </p>

              </div>



              {/* Not An AI Chatbot */}

              <div style={{ background: 'rgba(17, 24, 39, 0.6)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '24px' }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>

                  <XCircle size={20} color="#ef4444" />

                  <span style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Not a Generative LLM Bot</span>

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  LLMs hallucinate trading advice. PrimeEdge's core quantitative engine is purely deterministic and statistical. The AI Assistant acts solely as an explanatory copilot grounded in mathematical tables.

                </p>

              </div>

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 5: SHOW THE PRODUCT (Interactive Feature Deep Dive) */}

        {/* ========================================================================= */}

        <section id="product" style={{ padding: '80px 24px', maxWidth: '1200px', margin: '0 auto' }}>

          <div style={{ textAlign: 'center', marginBottom: '40px' }}>

            <span style={{ fontSize: '12px', fontWeight: 700, color: '#00f2fe', textTransform: 'uppercase', letterSpacing: '1px' }}>

              Evidence Interface

            </span>

            <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

              Engineered for High-Conviction Intraday Execution

            </h2>

          </div>



          <div style={{

            display: 'flex',

            justifyContent: 'center',

            gap: '12px',

            flexWrap: 'wrap',

            marginBottom: '32px'

          }}>

            {[

              { id: 'radar', label: 'Opportunity Radar', icon: Compass },

              { id: 'planner', label: 'Trade Planner & Corridors', icon: Sliders },

              { id: 'journal', label: 'Integrated Auto-Journal', icon: BookOpen }

            ].map((tab) => {

              const Icon = tab.icon;

              const active = activeProductTab === tab.id;

              return (

                <button

                  key={tab.id}

                  onClick={() => setActiveProductTab(tab.id as any)}

                  style={{

                    padding: '10px 18px',

                    borderRadius: '8px',

                    border: active ? '1px solid #00f2fe' : '1px solid rgba(255,255,255,0.1)',

                    background: active ? 'rgba(0, 242, 254, 0.15)' : 'rgba(17, 24, 39, 0.5)',

                    color: active ? '#00f2fe' : '#94a3b8',

                    fontWeight: 700,

                    fontSize: '13px',

                    cursor: 'pointer',

                    display: 'flex',

                    alignItems: 'center',

                    gap: '8px',

                    transition: 'all 0.2s'

                  }}

                >

                  <Icon size={16} />

                  {tab.label}

                </button>

              );

            })}

          </div>



          {/* Feature Showcase Box */}

          <div style={{

            background: 'rgba(15, 23, 42, 0.85)',

            border: '1px solid rgba(255, 255, 255, 0.1)',

            borderRadius: '16px',

            padding: '32px',

            boxShadow: '0 20px 40px rgba(0,0,0,0.5)'

          }}>

            {activeProductTab === 'radar' && (

              <div>

                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>

                  Opportunity Radar: Session Opportunity Scanning

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px', maxWidth: '800px' }}>

                  Filters the noise by surfacing only setups that meet strict threshold criteria. Every card provides the exact quantitative thesis, DXY regime alignment, and session viability rating.

                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #00f2fe' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Market Signature Score (MSS)</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Composite score (0-100) combining structural alignment, macro regimes, and news buffer windows.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #10b981' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Status State Pipeline</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Transitions cleanly from WAIT (waiting for zone) to READY (actionable trigger) with zero ambiguity.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #818cf8' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Corridor Guidance</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Identifies whether current market price is inside the acceptable entry band or already extended.

                    </div>

                  </div>

                </div>

              </div>

            )}



            {activeProductTab === 'planner' && (

              <div>

                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>

                  Empirical Trade Planner & Waiting Cost Engine

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px', maxWidth: '800px' }}>

                  Before you risk a single dollar, know your exact numbers. The Trade Planner models Option A (aggressive entry) vs Option B (patient limit entry) with empirical historical fill rates.

                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #ef4444' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>P90 Invalidation Stop</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Place stop-loss where 90% of successful historical trades never ventured.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #10b981' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>P75 Feasible Target</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Exit targets set at realistic historical expansion zones, not unrealistic wishful targets.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #00f2fe' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Risk-Weighted Position Size</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Automatically calculates exact lot sizes based on your personal account equity and risk budget.

                    </div>

                  </div>

                </div>

              </div>

            )}



            {activeProductTab === 'journal' && (

              <div>

                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>

                  Automated Trade Journal & Performance Analytics

                </h3>

                <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px', maxWidth: '800px' }}>

                  Trading journals fail when they depend on manual entry. PrimeEdge automatically captures every fill, track continuous price evolution, and calculates real R-multiple payoffs without manual friction.

                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #00f2fe' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Direct cTrader Telemetry</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Tracks open tickets, fill timestamps, commission, swap, and slippage in real time.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #10b981' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Excursion Tracking</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Records maximum adverse excursion (MAE) and favorable excursion (MFE) for every trade.

                    </div>

                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '10px', borderLeft: '3px solid #f59e0b' }}>

                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>R-Multiple Win/Loss Curve</div>

                    <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>

                      Plots performance in pure risk units (R), freeing your psychology from arbitrary dollar swings.

                    </div>

                  </div>

                </div>

              </div>

            )}

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 6: EVIDENCE & METHODOLOGY */}

        {/* ========================================================================= */}

        <section style={{

          padding: '80px 24px',

          backgroundColor: '#0c0e14',

          borderTop: '1px solid rgba(255, 255, 255, 0.05)',

          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'

        }}>

          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            <div style={{ textAlign: 'center', marginBottom: '40px' }}>

              <span style={{ fontSize: '12px', fontWeight: 700, color: '#10b981', textTransform: 'uppercase', letterSpacing: '1px' }}>

                Statistical Integrity

              </span>

              <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

                How the Empirical Engine Works

              </h2>

              <p style={{ fontSize: '15px', color: '#94a3b8', maxWidth: '680px', margin: '12px auto 0' }}>

                PrimeEdge is grounded in quantitative finance principles: point-in-time data sampling, non-parametric distribution modeling, and rigorous sample size gating.

              </p>

            </div>



            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>

              <div style={{ background: 'rgba(17, 24, 39, 0.6)', borderRadius: '12px', padding: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>

                <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>

                  <Database size={18} color="#00f2fe" />

                  Point-in-Time Data Integrity

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  No look-ahead bias. When PrimeEdge generates a setup for the London open, it evaluates only data known prior to the session start timestamp. What you see is exactly what was mathematically available in that instant.

                </p>

              </div>



              <div style={{ background: 'rgba(17, 24, 39, 0.6)', borderRadius: '12px', padding: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>

                <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>

                  <LineChart size={18} color="#10b981" />

                  MAE / MFE Distributions

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  Instead of assuming normal bell curves, PrimeEdge records the actual Maximum Adverse Excursion (drawdown) and Maximum Favorable Excursion (run-up) across hundreds of matched signatures.

                </p>

              </div>



              <div style={{ background: 'rgba(17, 24, 39, 0.6)', borderRadius: '12px', padding: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>

                <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>

                  <Lock size={18} color="#f59e0b" />

                  Sample Size Confidence Penalty

                </div>

                <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                  If a regime has fewer than 30 historical matches, PrimeEdge automatically scales down the confidence score and warns the trader. We never extrapolate certainty from inadequate sample sets.

                </p>

              </div>

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 7: EXECUTION & GUARDRAILS */}

        {/* ========================================================================= */}

        <section style={{ padding: '80px 24px', maxWidth: '1100px', margin: '0 auto' }}>

          <div style={{ textAlign: 'center', marginBottom: '40px' }}>

            <span style={{ fontSize: '12px', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '1px' }}>

              Execution Protection

            </span>

            <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

              Decision Guardrails on Every Trade

            </h2>

            <p style={{ fontSize: '15px', color: '#94a3b8', maxWidth: '680px', margin: '12px auto 0' }}>

              Most losses occur not because the thesis was wrong, but because execution was sloppy. PrimeEdge deploys real-time runtime safety filters.

            </p>

          </div>



          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>

            <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '22px' }}>

              <div style={{ color: '#ef4444', fontWeight: 800, fontSize: '14px', marginBottom: '6px' }}>

                Early Invalidation Filter

              </div>

              <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                Monitors post-entry traction with a 45-second grace window. If a trade experiences immediate adverse momentum without structural absorption, it invalidates early at a fraction of a 1R loss.

              </p>

            </div>



            <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '22px' }}>

              <div style={{ color: '#f59e0b', fontWeight: 800, fontSize: '14px', marginBottom: '6px' }}>

                Spread & Volatility Hard-Caps

              </div>

              <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                If your broker widens spreads ahead of high-impact news releases, the execution bridge gates orders immediately, refusing to let you get filled into toxic liquidity.

              </p>

            </div>



            <div style={{ background: 'rgba(15, 23, 42, 0.8)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px', padding: '22px' }}>

              <div style={{ color: '#00f2fe', fontWeight: 800, fontSize: '14px', marginBottom: '6px' }}>

                3-Cycle Position De-bounce

              </div>

              <p style={{ fontSize: '13px', color: '#94a3b8', lineHeight: 1.6 }}>

                Protects against intermittent broker network drops. Orders are only verified after confirming 3 consecutive synchronized heartbeat cycles, preventing phantom duplicate tickets.

              </p>

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 8 & 9 & 10: WHO PRIMEEDGE IS FOR (AND NOT FOR) */}

        {/* ========================================================================= */}

        <section style={{

          padding: '80px 24px',

          backgroundColor: '#0c0e14',

          borderTop: '1px solid rgba(255, 255, 255, 0.05)',

          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'

        }}>

          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            <div style={{ textAlign: 'center', marginBottom: '48px' }}>

              <span style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '1px' }}>

                Trader Fit

              </span>

              <h2 style={{ fontSize: 'clamp(26px, 4vw, 38px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

                Is PrimeEdge Right for Your Trading?

              </h2>

            </div>



            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '32px' }}>

              {/* WHO IT IS FOR */}

              <div style={{

                background: 'rgba(16, 185, 129, 0.03)',

                border: '1px solid rgba(16, 185, 129, 0.3)',

                borderRadius: '16px',

                padding: '32px'

              }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>

                  <CheckCircle size={24} color="#10b981" />

                  <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#10b981' }}>Who PrimeEdge Is Built For</h3>

                </div>

                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px', color: '#cbd5e1' }}>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <CheckCircle size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Systematic Intraday Traders:</strong> Traders operating London and New York sessions who value empirical discipline over hunches.</span>

                  </li>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <CheckCircle size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Prop Firm & Account Scalers:</strong> Traders with strict daily drawdown limits who require verified P90 adverse excursion boundaries.</span>

                  </li>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <CheckCircle size={16} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Evidence-Driven Operators:</strong> Traders tired of discretionary second-guessing who want cold, hard probability tables and auto-journal telemetry.</span>

                  </li>

                </ul>

              </div>



              {/* WHO IT IS NOT FOR */}

              <div style={{

                background: 'rgba(239, 68, 68, 0.03)',

                border: '1px solid rgba(239, 68, 68, 0.3)',

                borderRadius: '16px',

                padding: '32px'

              }}>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>

                  <XCircle size={24} color="#ef4444" />

                  <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#ef4444' }}>Who PrimeEdge Is NOT For</h3>

                </div>

                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px', color: '#cbd5e1' }}>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <XCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Get-Rich-Quick Seekers:</strong> We do not offer 95% win-rate promises, automated passive riches, or magical compounding calculators.</span>

                  </li>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <XCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Passive Copy-Traders:</strong> If you want to click a button and walk away without understanding your risk parameters, PrimeEdge is not for you.</span>

                  </li>

                  <li style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>

                    <XCircle size={16} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />

                    <span><strong>Crypto Degens & Moonshot Traders:</strong> PrimeEdge focuses strictly on institutional FX majors and gold (XAUUSD) where liquidity and microstructure allow genuine statistical edge.</span>

                  </li>

                </ul>

              </div>

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 11: PRICING & TIERS */}

        {/* ========================================================================= */}

        <section id="pricing" style={{ padding: '80px 24px', maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>

          <div style={{

            background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 9, 13, 0.95) 100%)',

            border: '1px solid rgba(0, 242, 254, 0.3)',

            borderRadius: '20px',

            padding: '48px 32px',

            boxShadow: '0 20px 50px rgba(0, 242, 254, 0.15)',

            position: 'relative',

            overflow: 'hidden'

          }}>

            <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>

              Choose Your Trading Intelligence Tier

            </h2>

            <p style={{ fontSize: '15px', color: '#94a3b8', maxWidth: '620px', margin: '0 auto 28px' }}>

              Evidence-based decision support for every trader level. PrimeEdge identifies high-quality opportunities, explains the evidence behind them, and measures whether its intelligence improves your decision-making.

            </p>



            <button

              onClick={() => window.location.href = '/pricing'}

              style={{

                display: 'inline-flex',

                alignItems: 'center',

                gap: '8px',

                background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                color: '#08090d',

                padding: '14px 32px',

                borderRadius: '10px',

                fontSize: '16px',

                fontWeight: 800,

                textDecoration: 'none',

                cursor: 'pointer',

                transition: 'all 0.3s',

                boxShadow: '0 4px 20px rgba(0, 242, 254, 0.35)'

              }}

              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}

              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}

            >

              View Pricing Plans

              <ChevronRight className="w-5 h-5" />

            </button>



            <div style={{ marginTop: '32px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '24px', maxWidth: '1100px', margin: '32px auto 0' }}>

              {tiers.map((tier) => {

                const isPremium = tier.name === 'premium';

                const isPro = tier.name === 'pro';

                const isFree = tier.name === 'free';

                const Icon = isFree ? Zap : tier.name === 'starter' ? StarIcon : isPro ? Shield : Crown;



                return (

                  <div key={tier.tier_id} style={{

                    background: isPremium ? 'linear-gradient(135deg, rgba(0, 242, 254, 0.1), rgba(56, 189, 248, 0.05))' : isPro ? 'rgba(0, 242, 254, 0.05)' : 'rgba(0, 0, 0, 0.3)',

                    border: isPremium ? '1px solid rgba(0, 242, 254, 0.5)' : isPro ? '1px solid rgba(0, 242, 254, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',

                    borderRadius: '16px',

                    padding: '24px',

                    textAlign: 'left',

                    position: 'relative',

                    boxShadow: isPremium ? '0 0 30px rgba(0, 242, 254, 0.15)' : 'none'

                  }}>

                    {isPro && (

                      <div style={{ position: 'absolute', top: '-12px', left: '50%', transform: 'translateX(-50%)', background: '#00f2fe', color: '#08090d', padding: '4px 12px', borderRadius: '20px', fontSize: '11px', fontWeight: 800, textTransform: 'uppercase' }}>Most Popular</div>

                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>

                      <Icon className="w-6 h-6" style={{ color: isPremium || isPro ? '#00f2fe' : '#9ca3af' }} />

                      <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0 }}>{tier.display_name}</h3>

                    </div>

                    <div style={{ fontSize: '36px', fontWeight: 900, color: '#fff', marginBottom: '4px' }}>${tier.price_monthly === 0 ? '0' : tier.price_monthly}<span style={{ fontSize: '16px', color: '#64748b', fontWeight: 500 }}>{tier.price_monthly === 0 ? '/forever' : '/mo'}</span></div>

                    <p style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '16px' }}>{tier.description}</p>

                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, color: '#cbd5e1', fontSize: '13px', lineHeight: '1.8' }}>

                      {tier.features.map((feature: string, idx: number) => (

                        <li key={idx} style={{ marginBottom: '8px', display: 'flex', alignItems: 'center' }}>

                          <CheckCircle size={16} color="#10b981" style={{ marginRight: '8px' }} />

                          {feature}

                        </li>

                      ))}

                    </ul>

                    {tier.auto_execution_enabled && (

                      <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '6px', color: '#00f2fe', fontSize: '12px', fontWeight: 600 }}>

                        <Zap className="w-4 h-4" />

                        Auto-Execution Enabled

                      </div>

                    )}

                  </div>

                );

              })}

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* SECTION 12: FREQUENTLY ASKED QUESTIONS (Accordion) */}

        {/* ========================================================================= */}

        <section style={{

          padding: '80px 24px',

          backgroundColor: '#0c0e14',

          borderTop: '1px solid rgba(255, 255, 255, 0.05)',

          borderBottom: '1px solid rgba(255, 255, 255, 0.05)'

        }}>

          <div style={{ maxWidth: '840px', margin: '0 auto' }}>

            <div style={{ textAlign: 'center', marginBottom: '40px' }}>

              <span style={{ fontSize: '12px', fontWeight: 700, color: '#00f2fe', textTransform: 'uppercase', letterSpacing: '1px' }}>

                Got Questions?

              </span>

              <h2 style={{ fontSize: 'clamp(26px, 4vw, 36px)', fontWeight: 800, marginTop: '8px', color: '#fff' }}>

                Frequently Answered Questions

              </h2>

            </div>



            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>

              {[

                {

                  q: "How does PrimeEdge connect to my broker?",

                  a: "PrimeEdge connects to your broker via isolated, sandboxed execution controls. Your credentials are encrypted and stored securely on dedicated worker nodes. We do not hold client capital, pool deposits, or broker trades directly."

                },

                {

                  q: "Is PrimeEdge an automated black-box EA?",

                  a: "No. PrimeEdge is a trading decision system. It discovers high-probability session setups and computes exact mathematical invalidation stops. You review and authorize setups in the Trade Planner before they execute through the guarded cTrader bridge."

                },

                {

                  q: "What instruments does PrimeEdge support?",

                  a: "PrimeEdge currently specializes in major foreign exchange pairs (GBPUSD, EURUSD, USDJPY, AUDUSD, USDCAD) and Gold (XAUUSD). We deliberately focus on liquid markets where microstructure and volatility models remain statistically reliable."

                },

                {

                  q: "What is the Market Signature Score (MSS)?",

                  a: "The MSS is a 0 to 100 composite probability metric. It decomposes session liquidity sweeps, Dollar Index (DXY) alignment, Treasury yield trends, and multi-timeframe structural momentum. An MSS above 70 indicates high statistical convergence."

                },

                {

                  q: "Can I change my plan later?",

                  a: "Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately for upgrades and at the next billing cycle for downgrades."

                }

              ].map((faq, index) => {

                const isOpen = openFaq === index;

                return (

                  <div

                    key={index}

                    style={{

                      background: 'rgba(17, 24, 39, 0.7)',

                      border: '1px solid rgba(255,255,255,0.08)',

                      borderRadius: '10px',

                      overflow: 'hidden'

                    }}

                  >

                    <button

                      onClick={() => toggleFaq(index)}

                      style={{

                        width: '100%',

                        padding: '18px 20px',

                        background: 'none',

                        border: 'none',

                        display: 'flex',

                        justifyContent: 'space-between',

                        alignItems: 'center',

                        color: '#fff',

                        fontSize: '15px',

                        fontWeight: 700,

                        cursor: 'pointer',

                        textAlign: 'left'

                      }}

                    >

                      <span>{faq.q}</span>

                      {isOpen ? <ChevronUp size={18} color="#00f2fe" /> : <ChevronDown size={18} color="#94a3b8" />}

                    </button>

                    {isOpen && (

                      <div style={{

                        padding: '0 20px 20px',

                        fontSize: '14px',

                        color: '#94a3b8',

                        lineHeight: 1.7,

                        borderTop: '1px solid rgba(255,255,255,0.04)',

                        paddingTop: '14px'

                      }}>

                        {faq.a}

                      </div>

                    )}

                  </div>

                );

              })}

            </div>

          </div>

        </section>



        {/* ========================================================================= */}

        {/* FOOTER & REGULATORY DISCLOSURES */}

        {/* ========================================================================= */}

        <footer style={{

          padding: '60px 24px 40px',

          backgroundColor: '#08090d',

          borderTop: '1px solid rgba(255, 255, 255, 0.08)'

        }}>

          <div style={{ maxWidth: '1100px', margin: '0 auto' }}>

            <div style={{

              display: 'flex',

              justifyContent: 'space-between',

              alignItems: 'center',

              flexWrap: 'wrap',

              gap: '24px',

              paddingBottom: '32px',

              borderBottom: '1px solid rgba(255, 255, 255, 0.06)'

            }}>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

                <div style={{

                  width: '28px',

                  height: '28px',

                  background: 'linear-gradient(135deg, #00f2fe, #38bdf8)',

                  borderRadius: '6px',

                  display: 'flex',

                  alignItems: 'center',

                  justifyContent: 'center',

                  fontWeight: 900,

                  fontSize: '14px',

                  color: '#08090d'

                }}>

                  P

                </div>

                <span style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>PrimeEdge</span>

              </div>



              <div style={{ display: 'flex', gap: '16px 24px', fontSize: '13px', flexWrap: 'wrap' }}>

                <a href="/terms.html" style={{ color: '#94a3b8', textDecoration: 'none' }}>

                  Terms of Service & Risk Disclosure

                </a>

                <a href="/privacy.html" style={{ color: '#94a3b8', textDecoration: 'none' }}>

                  Privacy & Data Policy

                </a>

                <a href="/register" style={{ color: '#00f2fe', textDecoration: 'none', fontWeight: 600 }}>

                  Create Free Account

                </a>

              </div>

            </div>



            {/* Mandatory Regulatory Warning */}

            <div style={{ marginTop: '28px', fontSize: '11px', color: '#64748b', lineHeight: 1.6 }}>

              <p style={{ marginBottom: '10px' }}>

                <strong>REGULATORY & RISK DISCLOSURE:</strong> PrimeEdge provides trading decision support software and statistical analytical models. PrimeEdge is not a registered broker-dealer, commodity trading advisor (CTA), or financial advisory firm. All trading models, Market Signature Scores (MSS), and empirical distributions are provided strictly for educational and analytical purposes. Past performance and statistical analogies do not guarantee future results. Trading foreign exchange and leveraged financial contracts carries significant risk of capital loss and is not suitable for all investors.

              </p>

              <p>

                (c) {new Date().getFullYear()} PrimeEdge. All rights reserved. Encrypted institutional infrastructure.

              </p>

            </div>

          </div>

        </footer>

      </main>

    </div>

  );

}

