import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Compass, 
  Sliders, 
  BookOpen, 
  MessageSquare, 
  AlertTriangle, 
  CheckCircle, 
  ShieldAlert, 
  Activity, 
  Zap, 
  ArrowRightLeft,
  Calendar,
  Send,
  Loader,
  Dna,
  History,
  Clock,
  Target,
  ChevronDown,
  ChevronUp,
  Layers
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TradePlanner } from './TradePlanner';
import MSDTradingViewChart from './MSDTradingViewChart';
import { EntryDistributionPanel } from './EntryDistributionPanel';
import type { EntryZoneData } from './EntryDistributionPanel';
import MethodologyTab from './MethodologyTab';
import HistoricalMatchModal from './HistoricalMatchModal';
import ExportReportButton from './ExportReportButton';
import { TakeSetupModal } from './TakeSetupModal';
import { AutoJournalTab } from './AutoJournalTab';
import { ReplayTab } from './ReplayTab';
import EvidenceAuditTab from './EvidenceAuditTab';
import { ExecutionTab } from './ExecutionTab';
import { Play } from 'lucide-react';
import { AuthProvider, useAuth } from './AuthContext';
import LoginPage from './LoginPage';


const API_BASE = (import.meta.env.VITE_API_URL ?? "") + "/api/v1";

interface MacroRegime {
  date: string;
  dxy_regime: string;
  yields_regime: string;
  risk_sentiment: string;
  no_trade_zones: { session: string; reason: string }[];
  macro_summary: string;
  overall_confidence_score: number;
}

interface MssDecomposition {
  base_probability: number;
  dxy_alignment: number;
  trend_alignment: number;
  session_suitability: number;
  news_buffer: number;
  sample_size_penalty: number;
}

interface WatchlistInstrument {
  instrument: string;
  direction?: string;
  status_state?: string;
  why_this_now?: string;
  evidence_strength?: string;
  mss_score: number;
  current_regime: string;
  continuation_probability: number;
  best_session: string;
  historical_sample_size: number;
  supporting_explanation: string;
  acceptable_corridor?: { p25_pips: number; p75_pips: number; p25_price: number; p75_price: number } | null;
  preferred_zone?: { p50_pips: number; p75_pips: number; p50_price: number; p75_price: number } | null;
  historical_adverse_boundary?: number | null;
  waiting_cost?: { fill_rate_pct: number; miss_rate_pct: number; narrative: string } | null;
  trade_thesis?: string | null;
  option_a_vs_b?: {
    option_a: { name: string; fill_rate_pct: number; target_rate_pct: number; sample_size: number; entry_price: number };
    option_b: { name: string; fill_rate_pct: number; target_rate_pct_if_filled: number; sample_size: number; entry_price: number };
    system_preference: string;
    waiting_cost: { fill_rate_pct: number; miss_rate_pct: number; narrative: string };
  } | null;
  mss_decomposition?: MssDecomposition | null;
}

interface InstrumentProfile {
  instrument: string;
  current_regime: string;
  similarity_score: number;
  continuation_probability: number;
  continuation_probability_raw?: number;
  direction?: string;
  status_state?: string;
  why_this_now?: string;
  setup_ref_price?: number;
  live_price?: number;
  edge_status?: string;
  required_payoff_gate?: number;
  reward_feasibility_ratio?: number;
  slippage_pips?: number;
  execution_delay_warning?: boolean;
  late_entry_recovery?: any;
  acceptable_corridor?: { p25_pips: number; p75_pips: number; p25_price: number; p75_price: number } | null;
  preferred_zone?: { p50_pips: number; p75_pips: number; p50_price: number; p75_price: number } | null;
  deep_retracement?: { p75_pips: number; p90_pips: number; p75_price: number; p90_price: number } | null;
  historical_adverse_boundary?: number | null;
  empirical_invalidation_pips?: number;
  empirical_invalidation_price?: number;
  empirical_target_pips?: number;
  empirical_target_price?: number;
  dual_trend_label?: string;
  expected_mae: number;
  expected_mfe: number;
  expected_holding_time: number;
  historical_sample_size: number;
  best_session: string;
  historical_failure_conditions: {
    volatility?: string;
    common_failure_session?: string;
    risk_sentiment?: string;
    news_event?: string;
    dxy_behavior?: string;
  };
  confidence_score: number;
  supporting_explanation: string;
  similarity_decomposition?: {
    trend: number;
    volatility: number;
    dxy: number;
    vix: number;
    yield: number;
    news: number;
  } | null;
  option_a_vs_b?: {
    option_a: {
      name: string;
      fill_rate_pct: number;
      target_rate_pct: number;
      sample_size: number;
      entry_price: number;
    };
    option_b: {
      name: string;
      fill_rate_pct: number;
      target_rate_pct_if_filled: number;
      sample_size: number;
      entry_price: number;
    };
    system_preference: string;
    waiting_cost: {
      fill_rate_pct: number;
      miss_rate_pct: number;
      narrative: string;
    };
  };
  waiting_cost?: {
    fill_rate_pct: number;
    miss_rate_pct: number;
    narrative: string;
  };
}

interface InstrumentDna {
  instrument: string;
  normal_mae_50: number;
  normal_mae_90: number;
  normal_mfe: number;
  best_session: string;
  worst_session: string;
  continuation_rate: number;
  best_dxy_state: string;
  worst_news_env: string;
  typical_holding_time: number;
  average_pullback: number;
  failure_signature: string;
}

interface SimilarDay {
  date: string;
  session: string;
  trend: string;
  dxy_state: string;
  outcome: string;
  matching_variables: string[];
  mae_pips: number;
  mfe_pips: number;
}

interface TimelineEvent {
  time: string;
  event: string;
  dxy: string;
  sentiment: string;
  narrative: string;
}

interface TradePlannerResponse {
  instrument: string;
  risk_pips: number;
  reward_pips: number;
  risk_reward_ratio: number;
  position_size_lots: number;
  risk_amount_usd: number;
  win_probability: number;
  expected_mae_pips: number;
  expected_mfe_pips: number;
  trade_quality_score: number;
  warnings: string[];
  mae_percentile?: number;
  survival_rate?: number;
}

interface JournalEntry {
  id?: number;
  instrument: string;
  date: string;
  session: string;
  market_regime: string;
  news_environment: string;
  mss_score: number;
  mae_actual: number;
  mfe_actual: number;
  execution_quality: string;
  risk_quality: string;
  outcome: string;
  lessons: string;
}

interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  citations?: { source: string; message: string }[];
  evidence?: { source: string; metric: string; value: string }[];
  intent?: string;
  suggestedFollowups?: string[];
}

interface RealtimeStatus {
  is_running: boolean;
  last_refresh_time: string | null;
  quotes: Record<string, { price: number; change: number; change_pct: number }>;
}

interface LiveIndicator {
  current: number;
  change: number;
  change_pct: number;
  trend: string;
  sma_5: number;
  sma_20: number;
  high_52w: number;
  low_52w: number;
}

interface LiveFundamentals {
  source: string;
  latency_note: string;
  fetched_at: string;
  indicators: Record<string, LiveIndicator>;
  derived: {
    risk_sentiment: string;
    yields_regime: string;
    dxy_trend: string;
  };
  economic_calendar: Array<{
    date: string;
    event: string;
    impact: string;
    no_trade_session: string;
  }>;
}

// SVG Arc Gauge for Survival Probability
function SurvivalGauge({ value, label }: { value: number; label: string }) {
  const percentage = Math.round(value * 100);
  const radius = 58;
  const strokeWidth = 10;
  const circumference = Math.PI * radius; // half-circle
  const filled = (percentage / 100) * circumference;
  const color = percentage >= 85 ? 'var(--accent-green)' : percentage >= 60 ? 'var(--accent-orange)' : 'var(--accent-red)';
  const bgColor = 'rgba(255,255,255,0.06)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="140" height="80" viewBox="0 0 140 80">
        {/* Background arc */}
        <path
          d={`M 12 72 A ${radius} ${radius} 0 0 1 128 72`}
          fill="none"
          stroke={bgColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d={`M 12 72 A ${radius} ${radius} 0 0 1 128 72`}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          style={{ transition: 'stroke-dasharray 0.8s ease-out, stroke 0.5s ease' }}
        />
        {/* Glow filter */}
        <defs>
          <filter id="gaugeGlow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {/* Glowing dot at tip */}
        <circle cx="70" cy="12" r="4" fill={color} filter="url(#gaugeGlow)" style={{ opacity: percentage > 0 ? 1 : 0 }}>
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="-90 70 72"
            to={`${-90 + (percentage / 100) * 180} 70 72`}
            dur="0.8s"
            fill="freeze"
          />
        </circle>
        {/* Percentage text */}
        <text x="70" y="62" textAnchor="middle" fontSize="26" fontWeight="800" fill={color} fontFamily="var(--font-sans)">
          {percentage}%
        </text>
      </svg>
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</span>
    </div>
  );
}

// Hoverable Info Tooltip with Decision Impact
function InfoTooltip({ title, explanation, decisionImpact }: { title: string; explanation: string; decisionImpact: string }) {
  const [show, setShow] = useState(false);

  return (
    <span 
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', marginLeft: '4px', cursor: 'pointer' }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onClick={(e) => { e.stopPropagation(); setShow(!show); }}
    >
      <span style={{ 
        display: 'inline-flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        width: '14px', 
        height: '14px', 
        borderRadius: '50%', 
        backgroundColor: 'rgba(0, 242, 254, 0.1)', 
        color: 'var(--accent-teal)', 
        fontSize: '10px', 
        fontWeight: 700,
        border: '1px solid rgba(0, 242, 254, 0.3)'
      }}>
        i
      </span>

      {show && (
        <div style={{
          position: 'absolute',
          bottom: '125%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '260px',
          backgroundColor: '#11141c',
          border: '1px solid var(--accent-teal)',
          borderRadius: '8px',
          padding: '12px',
          boxShadow: '0 10px 25px rgba(0,0,0,0.85)',
          zIndex: 9999,
          textAlign: 'left'
        }}>
          <div style={{ fontSize: '11px', fontWeight: 800, color: 'var(--accent-teal)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            {title}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-primary)', lineHeight: 1.4, marginBottom: '8px' }}>
            {explanation}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--accent-green)', fontWeight: 600, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '6px' }}>
            🎯 Decision Impact: {decisionImpact}
          </div>
        </div>
      )}
    </span>
  );
}

// Visual Horizon Tag (Intraday vs Macro)
function HorizonBadge({ type }: { type: 'intraday' | 'macro' }) {
  const isIntraday = type === 'intraday';
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '9px',
      fontWeight: 800,
      textTransform: 'uppercase',
      padding: '2px 6px',
      borderRadius: '4px',
      backgroundColor: isIntraday ? 'rgba(0, 242, 254, 0.12)' : 'rgba(168, 85, 247, 0.12)',
      color: isIntraday ? 'var(--accent-teal)' : '#c084fc',
      border: `1px solid ${isIntraday ? 'rgba(0, 242, 254, 0.3)' : 'rgba(168, 85, 247, 0.3)'}`,
      marginLeft: '6px'
    }}>
      {isIntraday ? '⚡ INTRADAY 1H' : '🌐 MACRO DAILY'}
    </span>
  );
}

function App() {
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<'find' | 'plan' | 'why' | 'journal' | 'chat' | 'replay' | 'execution'>('find');
  const [selectedInstrument, setSelectedInstrument] = useState<string>('GBPUSD');
  const [expandedMssSymbol, setExpandedMssSymbol] = useState<string | null>(null);
  const [selectedMatchForModal, setSelectedMatchForModal] = useState<any>(null);
  
  // State variables for backend data
  const [macroRegime, setMacroRegime] = useState<MacroRegime | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistInstrument[]>([]);
  const [instrumentProfile, setInstrumentProfile] = useState<InstrumentProfile | null>(null);
  const [instrumentDna, setInstrumentDna] = useState<InstrumentDna | null>(null);
  const [similarDays, setSimilarDays] = useState<SimilarDay[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  
  // Trade Planner Form State
  const [plannerInst, setPlannerInst] = useState<string>('GBPUSD');
  const [plannerEntry, setPlannerEntry] = useState<string>('1.2540');
  const [plannerStop, setPlannerStop] = useState<string>('1.2500');
  const [plannerTarget, setPlannerTarget] = useState<string>('1.2620');
  const [plannerRisk, setPlannerRisk] = useState<string>('1.0');
  const [plannerBalance, setPlannerBalance] = useState<string>('10000');
  const [plannerResult, setPlannerResult] = useState<TradePlannerResponse | null>(null);
  const [plannerLoading, setPlannerLoading] = useState<boolean>(false);
  const [plannerError, setPlannerError] = useState<string | null>(null);

  // Journal form state
  const [newJournalInst, setNewJournalInst] = useState<string>('GBPUSD');
  const [newJournalSess, setNewJournalSess] = useState<string>('LONDON');
  const [newJournalOutcome, setNewJournalOutcome] = useState<string>('WIN');
  const [newJournalMae, setNewJournalMae] = useState<string>('5.0');
  const [newJournalMfe, setNewJournalMfe] = useState<string>('25.0');
  const [newJournalLessons, setNewJournalLessons] = useState<string>('');

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { sender: 'ai', text: "Hello! I am your Market OS quantitative AI analyst. Ask me any question about GBPUSD, EURUSD, XAUUSD, AUDUSD, or USDJPY market regimes and signatures. I base all explanations on historical statistical MSD observations." }
  ]);
  const [chatInput, setChatInput] = useState<string>('');
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  // Auto Journal Take Setup Modal State
  const [takeSetupModalOpen, setTakeSetupModalOpen] = useState<boolean>(false);
  const [takeSetupSymbol, setTakeSetupSymbol] = useState<string>('GBPUSD');
  const [takeSetupSnapshotId, setTakeSetupSnapshotId] = useState<number | null>(null);
  const [takeSetupData, setTakeSetupData] = useState<any>({});

  const handleOpenTakeSetup = async (symbol: string) => {
    setTakeSetupSymbol(symbol);
    try {
      const res = await fetch(`${API_BASE}/journal/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: symbol, source: 'TAKE_SETUP_BUTTON' })
      });
      if (res.ok) {
        const snap = await res.json();
        setTakeSetupSnapshotId(snap.id);
        setTakeSetupData({
          status_state: snap.status_at_snapshot,
          direction: snap.direction,
          setup_ref_price: snap.setup_ref_price,
          corridor_p25_price: snap.corridor_p25_price,
          corridor_p75_price: snap.corridor_p75_price,
          p90_invalidation: snap.p90_invalidation,
          expected_mfe: snap.mfe_p50_pips,
          continuation_prob: snap.continuation_prob,
          trade_thesis: snap.setup_thesis
        });
        setTakeSetupModalOpen(true);
      }
    } catch (err) {
      console.error('Failed to create setup snapshot:', err);
    }
  };

  const handlePassSetup = async (symbol: string) => {
    try {
      const snapRes = await fetch(`${API_BASE}/journal/snapshot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instrument: symbol, source: 'PASS_BUTTON' })
      });
      if (snapRes.ok) {
        const snap = await snapRes.json();
        await fetch(`${API_BASE}/journal/pass`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ snapshot_id: snap.id, notes: 'Passed from Opportunity Radar' })
        });
        alert(`Setup for ${symbol} recorded as PASSED for post-session opportunity audit.`);
      }
    } catch (err) {
      console.error('Failed to record passed setup:', err);
    }
  };

  const handleConfirmTakeSetup = async (payload: any) => {
    if (!takeSetupSnapshotId) return;
    try {
      const res = await fetch(`${API_BASE}/journal/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          snapshot_id: takeSetupSnapshotId,
          ...payload
        })
      });
      if (res.ok) {
        setTakeSetupModalOpen(false);
        setActiveTab('journal');
      }
    } catch (err) {
      console.error('Failed to confirm take setup:', err);
    }
  };

  // Realtime Status & CSI State
  const [realtimeStatus, setRealtimeStatus] = useState<RealtimeStatus | null>(null);
  const [currencyStrength, setCurrencyStrength] = useState<Record<string, { strength: number; status: string; change_5d: number }> | null>(null);
  const [liveFundamentals, setLiveFundamentals] = useState<LiveFundamentals | null>(null);
  const [fundamentalsLoading, setFundamentalsLoading] = useState<boolean>(false);
  const [csiMode, setCsiMode] = useState<'macro' | 'intraday'>('intraday');

  // Load Dashboard Data
  // NOTE: csiMode is included in the currency-strength URL so this function
  // never overwrites the CSI state with stale mode-default data.
  const fetchDashboardData = async (mode: 'macro' | 'intraday' = csiMode) => {
    try {
      const [regimeRes, watchlistRes, timelineRes, statusRes, strengthRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard/regime`),
        fetch(`${API_BASE}/dashboard/watchlist`),
        fetch(`${API_BASE}/dashboard/timeline`),
        fetch(`${API_BASE}/realtime/status`),
        fetch(`${API_BASE}/dashboard/currency-strength?mode=${mode}`)
      ]);
      const regimeData = await regimeRes.json();
      const watchlistData = await watchlistRes.json();
      const timelineData = await timelineRes.json();
      const statusData = await statusRes.json();
      const strengthData = await strengthRes.json();
      
      setMacroRegime(regimeData);
      setWatchlist(watchlistData);
      setTimeline(timelineData);
      setRealtimeStatus(statusData);
      setCurrencyStrength(strengthData);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  // Load Live Fundamentals (separate fetch — slower due to yfinance latency)
  const fetchLiveFundamentals = async () => {
    setFundamentalsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/fundamentals/live`);
      if (res.ok) {
        const data = await res.json();
        setLiveFundamentals(data);
      }
    } catch (error) {
      console.error('Failed to fetch live fundamentals:', error);
    } finally {
      setFundamentalsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    fetchLiveFundamentals();
    // Auto-refresh fundamentals every 5 minutes
    const interval = setInterval(fetchLiveFundamentals, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Currency Strength Matrix on csiMode toggle — also re-fetch dashboard so they stay in sync
  useEffect(() => {
    fetch(`${API_BASE}/dashboard/currency-strength?mode=${csiMode}`)
      .then(res => res.json())
      .then(data => setCurrencyStrength(data))
      .catch(err => console.error("Error fetching currency strength matrix:", err));
  }, [csiMode]);

  // Chart data state — lifted so EntryDistributionPanel can consume entry_zone
  const [chartEntryZone, setChartEntryZone] = useState<EntryZoneData | null>(null);
  const [chartEntrySymbol, setChartEntrySymbol] = useState<string>(selectedInstrument);

  // When instrument changes, clear stale entry zone so panel disappears until new data loads
  useEffect(() => {
    setChartEntryZone(null);
    setChartEntrySymbol(selectedInstrument);
  }, [selectedInstrument]);

  // Load Instrument Profile
  useEffect(() => {
    fetch(`${API_BASE}/instruments/${selectedInstrument}/profile`)
      .then(res => res.json())
      .then(data => setInstrumentProfile(data))
      .catch(err => console.error("Error fetching instrument profile:", err));

    fetch(`${API_BASE}/instruments/${selectedInstrument}/dna`)
      .then(res => res.json())
      .then(data => setInstrumentDna(data))
      .catch(err => console.error("Error fetching instrument DNA:", err));

    fetch(`${API_BASE}/instruments/${selectedInstrument}/similar-days`)
      .then(res => res.json())
      .then(data => setSimilarDays(data))
      .catch(err => console.error("Error fetching similar days:", err));
  }, [selectedInstrument]);

  // Handle Trade Planner Evaluation
  const handleEvaluate = (e: React.FormEvent) => {
    e.preventDefault();
    setPlannerLoading(true);
    setPlannerError(null);
    setPlannerResult(null);

    const payload = {
      instrument: plannerInst,
      entry_price: parseFloat(plannerEntry),
      stop_loss: parseFloat(plannerStop),
      take_profit: parseFloat(plannerTarget),
      risk_pct: parseFloat(plannerRisk),
      account_balance: parseFloat(plannerBalance)
    };

    fetch(`${API_BASE}/trade-planner/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to evaluate setup.");
        return data;
      })
      .then(data => {
        setPlannerResult(data);
      })
      .catch(err => {
        setPlannerError(err.message);
      })
      .finally(() => {
        setPlannerLoading(false);
      });
  };

  // Handle Log completed trade to Journal
  const handleLogJournal = (e: React.FormEvent) => {
    e.preventDefault();
    const today = new Date().toISOString().split('T')[0];

    const payload = {
      instrument: newJournalInst,
      date: today,
      session: newJournalSess,
      market_regime: "Dynamic Regime from MSD",
      news_environment: "LOW_IMPACT",
      mss_score: 75.0,
      mae_actual: parseFloat(newJournalMae),
      mfe_actual: parseFloat(newJournalMfe),
      execution_quality: "EXCELLENT",
      risk_quality: "GOOD",
      outcome: newJournalOutcome,
      lessons: newJournalLessons
    };

    fetch(`${API_BASE}/journal/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(res => res.json())
      .then(data => {
        setJournal([data, ...journal]);
        setNewJournalLessons('');
      })
      .catch(err => console.error("Error logging journal:", err));
  };

  // Handle Chat message submit — routes to AI Analyst (tool-using reasoning layer)
  const handleSendMessage = (textToSend?: string) => {
    const text = textToSend || chatInput;
    if (!text.trim()) return;

    const userMsg: ChatMessage = { sender: 'user', text };
    const updatedMessages = [...chatMessages, userMsg];
    setChatMessages(updatedMessages);
    if (!textToSend) setChatInput('');
    setChatLoading(true);

    // Build conversation history for multi-turn memory (last 6 messages)
    const history = updatedMessages
      .slice(-6)
      .filter(m => m.sender === 'user' || m.sender === 'ai')
      .map(m => ({ role: m.sender === 'user' ? 'user' : 'model', content: m.text }));

    // Pass currently-selected instrument as symbol context hint
    const symbolHint = selectedInstrument || undefined;

    fetch(`${API_BASE}/analyst/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: text,
        symbol: symbolHint,
        conversation_history: history,
      })
    })
      .then(res => res.json())
      .then(data => {
        const aiMsg: ChatMessage = {
          sender: 'ai',
          text: data.answer,
          evidence: data.evidence,
          intent: data.intent,
          suggestedFollowups: data.suggested_followups,
        };
        setChatMessages(prev => [...prev, aiMsg]);
      })
      .catch(err => {
        console.error('Analyst error:', err);
        setChatMessages(prev => [...prev, {
          sender: 'ai',
          text: 'Market OS AI is temporarily unavailable. Please try again.',
        }]);
      })
      .finally(() => {
        setChatLoading(false);
      });
  };

  // Quick Chat questions helper
  const handleQuickQuestion = (q: string) => {
    handleSendMessage(q);
  };

  // Auth gate
  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading session...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="logo-container">
          <div className="logo-icon">M</div>
          <h1 className="logo-text">MARKET OS</h1>
        </div>

        <ul className="nav-links">
          <li>
            <div 
              className={`nav-item ${activeTab === 'find' ? 'active' : ''}`}
              onClick={() => setActiveTab('find')}
            >
              <Compass /> FIND (Radar)
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'plan' ? 'active' : ''}`}
              onClick={() => setActiveTab('plan')}
            >
              <Sliders /> PLAN (Cockpit)
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'execution' ? 'active' : ''}`}
              onClick={() => setActiveTab('execution')}
              style={{ color: activeTab === 'execution' ? 'var(--accent-green)' : undefined }}
            >
              <Zap /> EXECUTION (Bridge)
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'journal' ? 'active' : ''}`}
              onClick={() => setActiveTab('journal')}
            >
              <BookOpen /> Auto-Journal
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'why' ? 'active' : ''}`}
              onClick={() => setActiveTab('why')}
            >
              <TrendingUp /> WHY (Evidence)
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'replay' ? 'active' : ''}`}
              onClick={() => setActiveTab('replay')}
            >
              <Play /> REPLAY (Simulation)
            </div>
          </li>
          <li>
            <div 
              className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare /> AI Analyst
            </div>
          </li>
        </ul>


        <div className="user-profile">
          <div className="avatar" style={{ background: 'linear-gradient(135deg, var(--accent-teal), var(--accent-blue))' }}>
            {user?.full_name ? user.full_name.slice(0, 2).toUpperCase() : user?.email.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h4 style={{ fontSize: '13px', fontWeight: 600, margin: 0 }}>
              {user?.full_name || user?.email}
            </h4>
            <p style={{ fontSize: '10px', color: 'var(--text-secondary)', margin: '2px 0 0 0', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {user?.is_admin ? 'Admin' : user?.role || 'Trader'} · Market OS v2.1
            </p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '4px 8px',
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '0.3px',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={e => { (e.target as HTMLButtonElement).style.color = 'var(--accent-red)'; (e.target as HTMLButtonElement).style.borderColor = 'var(--accent-red)'; }}
            onMouseLeave={e => { (e.target as HTMLButtonElement).style.color = 'var(--text-secondary)'; (e.target as HTMLButtonElement).style.borderColor = 'var(--border-color)'; }}
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Panel Content */}
      <main className="main-content">
        
        {/* --- SCREEN 1: FIND (Opportunity Radar) --- */}
        {activeTab === 'find' && (
          <div className="animate-fade-in">
            <header className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 className="dashboard-title">FIND — Opportunity Radar</h2>
                <p className="dashboard-subtitle">What deserves my attention right now?</p>
              </div>
            </header>

            {/* Live Macro Fundamentals & CSI Matrix */}
            <div className="dashboard-grid" style={{ marginBottom: '20px' }}>
              <div className="col-12 glass-panel widget">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h3 className="widget-title" style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                    <Compass style={{ color: 'var(--accent-teal)', marginRight: '8px' }} /> Live Macro Fundamentals & CSI Matrix
                    <HorizonBadge type={csiMode === 'intraday' ? 'intraday' : 'macro'} />
                  </h3>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      onClick={() => setCsiMode('intraday')}
                      style={{
                        padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, border: '1px solid', cursor: 'pointer',
                        borderColor: csiMode === 'intraday' ? 'var(--accent-teal)' : 'rgba(255,255,255,0.08)',
                        backgroundColor: csiMode === 'intraday' ? 'rgba(0, 242, 254, 0.15)' : 'transparent',
                        color: csiMode === 'intraday' ? 'var(--accent-teal)' : '#64748b'
                      }}
                    >
                      ⚡ Intraday 1H CSI
                    </button>
                    <button
                      onClick={() => setCsiMode('macro')}
                      style={{
                        padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, border: '1px solid', cursor: 'pointer',
                        borderColor: csiMode === 'macro' ? '#a855f7' : 'rgba(255,255,255,0.08)',
                        backgroundColor: csiMode === 'macro' ? 'rgba(168, 85, 247, 0.15)' : 'transparent',
                        color: csiMode === 'macro' ? '#c084fc' : '#64748b'
                      }}
                    >
                      🌐 Daily Macro CSI
                    </button>
                  </div>
                </div>

                {currencyStrength && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '12px' }}>
                    {Object.entries(currencyStrength).map(([symbol, item]) => {
                      const isStrong = item.strength >= 55;
                      const isWeak = item.strength <= 45;
                      const color = isStrong ? 'var(--accent-green)' : isWeak ? 'var(--accent-red)' : 'var(--accent-orange)';
                      return (
                        <div key={symbol} style={{ backgroundColor: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 800, fontSize: '14px', color: '#fff' }}>{symbol}</span>
                            <span style={{ fontSize: '9px', fontWeight: 700, padding: '2px 5px', borderRadius: '4px', backgroundColor: `${color}22`, color }}>
                              {item.status}
                            </span>
                          </div>
                          <div style={{ fontSize: '18px', fontWeight: 800, color, marginTop: '6px' }}>{item.strength}</div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* First-Class NO HIGH-QUALITY SETUP Banner */}
            {watchlist.length > 0 && watchlist.every(w => w.status_state === 'NO SETUP' || w.status_state === 'NO EDGE') && (
              <div style={{ padding: '20px 24px', borderRadius: '12px', background: 'rgba(148, 163, 184, 0.1)', border: '1px solid rgba(148, 163, 184, 0.3)', color: '#cbd5e1', margin: '20px 0', display: 'flex', alignItems: 'center', gap: '16px' }}>
                <ShieldAlert size={24} style={{ color: '#94a3b8' }} />
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#f8fafc' }}>NO HIGH-QUALITY SETUP RIGHT NOW — Market OS Rewards Patience</div>
                  <div style={{ fontSize: '13px', color: '#94a3b8', marginTop: '3px' }}>No instrument currently meets the minimum historical conditions for an actionable setup.</div>
                </div>
              </div>
            )}

            {/* Opportunity Radar Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px', marginTop: '20px' }}>
              {watchlist.map((item) => {
                const isReady = item.status_state === 'READY';
                const isWait = item.status_state === 'WAIT';
                const badgeColor = isReady ? '#10b981' : isWait ? '#f59e0b' : '#94a3b8';
                const isLong = item.direction === 'LONG';
                const dirColor = isLong ? '#10b981' : item.direction === 'SHORT' ? '#ef4444' : '#94a3b8';

                return (
                  <div key={item.instrument} className="glass-panel" style={{ padding: '20px', borderRadius: '14px', border: `1px solid ${badgeColor}44`, borderTop: `4px solid ${badgeColor}`, background: 'rgba(17, 24, 39, 0.85)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <span style={{ fontSize: '22px', fontWeight: 800, color: '#fff' }}>{item.instrument}</span>
                        <span style={{ padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 800, backgroundColor: `${dirColor}22`, color: dirColor, border: `1px solid ${dirColor}44` }}>
                          {item.direction || 'LONG'}
                        </span>
                        {item.instrument === 'XAUUSD' ? (
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 800, backgroundColor: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)', border: '1px solid rgba(16,185,129,0.3)' }}>
                            VALIDATED EDGE
                          </span>
                        ) : (
                          <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 700, backgroundColor: 'rgba(148,163,184,0.12)', color: 'var(--text-muted)', border: '1px solid rgba(148,163,184,0.2)' }}>
                            MEAN REVERSION ONLY
                          </span>
                        )}
                      </div>
                      <span style={{ padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: 800, backgroundColor: `${badgeColor}22`, color: badgeColor, border: `1px solid ${badgeColor}55`, textTransform: 'uppercase' }}>
                        {item.status_state || 'WAIT'}
                      </span>
                    </div>

                    {/* WHY THIS NOW? Narrative Container */}
                    <div style={{ padding: '12px 14px', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '8px', borderLeft: `3px solid ${badgeColor}`, marginBottom: '14px' }}>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '3px' }}>Why This Now?</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.4 }}>{item.why_this_now || item.supporting_explanation}</div>
                    </div>

                    {/* Concise Evidence Sentence */}
                    <div style={{ fontSize: '12px', color: 'var(--accent-teal)', fontWeight: 700, marginBottom: '14px' }}>
                      🎯 {Math.round(item.continuation_probability * item.historical_sample_size)} of {item.historical_sample_size} similar setups reached target (N={item.historical_sample_size})
                    </div>

                    {/* Metrics Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', padding: '10px', backgroundColor: 'var(--bg-secondary)', borderRadius: '8px', marginBottom: '16px', fontSize: '11px' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Session</span>
                        <div style={{ fontWeight: 700, color: '#fff', marginTop: '2px' }}>{item.best_session}</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Evidence</span>
                        <div style={{ fontWeight: 700, color: item.evidence_strength === 'Strong' ? '#10b981' : '#f59e0b', marginTop: '2px' }}>{item.evidence_strength || 'Moderate'}</div>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Sample (N)</span>
                        <div style={{ fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{item.historical_sample_size}</div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        style={{
                          flex: 1,
                          padding: '9px',
                          borderRadius: '6px',
                          background: 'linear-gradient(135deg, var(--accent-teal), #00c6ff)',
                          border: 'none',
                          color: '#000',
                          fontWeight: 800,
                          fontSize: '11px',
                          cursor: 'pointer'
                        }}
                        onClick={() => handleOpenTakeSetup(item.instrument)}
                      >
                        ⚡ TAKE SETUP
                      </button>
                      <button
                        style={{
                          padding: '9px 12px',
                          borderRadius: '6px',
                          background: 'rgba(255,255,255,0.05)',
                          border: '1px solid var(--border-color)',
                          color: 'var(--text-secondary)',
                          fontWeight: 700,
                          fontSize: '11px',
                          cursor: 'pointer'
                        }}
                        onClick={() => handlePassSetup(item.instrument)}
                      >
                        PASS
                      </button>
                      <button
                        style={{
                          padding: '9px 12px',
                          borderRadius: '6px',
                          background: 'rgba(0,242,254,0.08)',
                          border: '1px solid var(--accent-teal)',
                          color: 'var(--accent-teal)',
                          fontWeight: 700,
                          fontSize: '11px',
                          cursor: 'pointer'
                        }}
                        onClick={() => {
                          setSelectedInstrument(item.instrument);
                          setActiveTab('plan');
                        }}
                      >
                        PLAN →
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* --- SCREEN 2: PLAN (Execution Cockpit) --- */}
        {activeTab === 'plan' && (
          <div className="animate-fade-in">
            <header className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 className="dashboard-title">PLAN — Execution Cockpit</h2>
                <p className="dashboard-subtitle">If I take this setup, exactly how should I execute it?</p>
              </div>

              <select className="form-input" style={{ width: '160px' }} value={selectedInstrument} onChange={(e) => setSelectedInstrument(e.target.value)}>
                <option value="GBPUSD">GBPUSD</option>
                <option value="EURUSD">EURUSD</option>
                <option value="XAUUSD">XAUUSD</option>
                <option value="AUDUSD">AUDUSD</option>
                <option value="USDJPY">USDJPY</option>
              </select>
            </header>

            {/* Execution Delay Warning Banner & Recovery Assistant */}
            {instrumentProfile?.execution_delay_warning && (
              <div style={{ padding: '16px 20px', borderRadius: '10px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-red)', fontSize: '13px', fontWeight: 800, marginBottom: '10px' }}>
                  <AlertTriangle size={18} />
                  <span>EXECUTION DEVIATION: Price slipped +{instrumentProfile.slippage_pips}p beyond open in direction of move</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                  Blind market chasing degrades expected value by <strong>-32.1%</strong>. Choose a validated mitigation strategy below:
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ padding: '12px', background: '#0a0d14', borderRadius: '6px', border: '1px solid var(--accent-teal)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--accent-teal)', fontWeight: 800, textTransform: 'uppercase' }}>
                      Option 1: Retest {instrumentProfile?.late_entry_recovery?.order_type || 'Limit'} at Open (Recommended)
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
                      Place {instrumentProfile?.late_entry_recovery?.order_type || 'Limit'} @ {instrumentProfile?.late_entry_recovery?.option_retest_limit?.entry_price ?? instrumentProfile?.setup_ref_price}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--accent-green)', marginTop: '2px', fontWeight: 700 }}>
                      Expected Value: +0.265R (100% EV Recovery)
                    </div>
                  </div>

                  <div style={{ padding: '12px', background: '#0a0d14', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--accent-orange)', fontWeight: 800, textTransform: 'uppercase' }}>
                      Option 2: Recalibrated Invalidation Stop
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
                      Market {instrumentProfile?.direction === 'LONG' ? 'Buy' : 'Sell'} @ {instrumentProfile?.live_price} · Shift SL
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Expected Value: +0.219R (82% EV Recovery)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Trade Thesis Banner */}
            {instrumentProfile?.supporting_explanation && (
              <div style={{ padding: '16px 20px', borderRadius: '12px', background: 'linear-gradient(135deg, rgba(0,242,254,0.1) 0%, rgba(16,185,129,0.1) 100%)', border: '1px solid rgba(0,242,254,0.3)', marginBottom: '20px' }}>
                <div style={{ fontSize: '11px', color: 'var(--accent-teal)', fontWeight: 800, textTransform: 'uppercase', marginBottom: '4px' }}>TRADE THESIS</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', lineHeight: 1.4 }}>
                  {selectedInstrument} continuation setup. Grounded in {instrumentProfile.historical_sample_size} matching historical sessions with {Math.round(instrumentProfile.continuation_probability * 100)}% historical success.
                </div>
              </div>
            )}

            {/* Option A vs Option B Cards with WAITING COST */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '20px' }}>
              {/* Option A */}
              <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>{instrumentProfile?.option_a_vs_b?.option_a?.name ? `OPTION A — ${instrumentProfile.option_a_vs_b.option_a.name}` : 'OPTION A — ENTER NOW (Market)'}</div>
                <div style={{ fontSize: '26px', fontWeight: 800, color: '#fff', marginTop: '6px' }}>
                  {instrumentProfile?.option_a_vs_b?.option_a?.target_rate_pct != null ? Math.round(instrumentProfile.option_a_vs_b.option_a.target_rate_pct) : Math.round((instrumentProfile?.continuation_probability || 0.58) * 100)}% <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Target Rate</span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--accent-teal)', marginTop: '4px' }}>
                  {instrumentProfile?.option_a_vs_b?.option_a?.fill_rate_pct ?? 100}% Fill Rate · N = {instrumentProfile?.option_a_vs_b?.option_a?.sample_size ?? instrumentProfile?.historical_sample_size ?? 100} comparable setups
                </div>
              </div>

              {/* Option B */}
              <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px', border: '1px solid var(--accent-teal)' }}>
                <div style={{ fontSize: '12px', color: 'var(--accent-teal)', fontWeight: 700, textTransform: 'uppercase' }}>{instrumentProfile?.option_a_vs_b?.option_b?.name ? `OPTION B — ${instrumentProfile.option_a_vs_b.option_b.name}` : 'OPTION B — WAIT FOR PULLBACK (Limit)'}</div>
                <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--accent-green)', marginTop: '6px' }}>
                  {instrumentProfile?.option_a_vs_b?.option_b?.target_rate_pct_if_filled != null ? Math.round(instrumentProfile.option_a_vs_b.option_b.target_rate_pct_if_filled) : Math.round(((instrumentProfile?.continuation_probability || 0.58) + 0.04) * 100)}% <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Target Rate If Filled</span>
                </div>
                <div style={{ fontSize: '12px', color: '#f59e0b', marginTop: '4px' }}>
                  {instrumentProfile?.option_a_vs_b?.option_b?.fill_rate_pct ?? 65.0}% Historical Fill Rate · N_filled = {instrumentProfile?.option_a_vs_b?.option_b?.sample_size ?? Math.round((instrumentProfile?.historical_sample_size || 100) * 0.65)}
                </div>
              </div>
            </div>

            {/* WAITING COST / MISS RISK Banner */}
            <div style={{ padding: '14px 18px', borderRadius: '10px', backgroundColor: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', color: '#f59e0b', marginBottom: '20px', fontSize: '13px', fontWeight: 600 }}>
              ⚠️ <strong>WAITING COST:</strong> {instrumentProfile?.waiting_cost?.narrative ?? instrumentProfile?.option_a_vs_b?.waiting_cost?.narrative ?? `Historically this pullback occurs in ${instrumentProfile?.waiting_cost?.fill_rate_pct ?? instrumentProfile?.option_a_vs_b?.waiting_cost?.fill_rate_pct ?? '...'} of 100 setups. You would miss approx ${instrumentProfile?.waiting_cost?.miss_rate_pct ?? instrumentProfile?.option_a_vs_b?.waiting_cost?.miss_rate_pct ?? '...'} of 100 opportunities by waiting.`}
            </div>

            {/* Clean 4-Line TradingView Chart */}
            <div className="glass-panel" style={{ marginBottom: '20px', borderRadius: '16px', border: '1px solid rgba(0,242,254,0.12)' }}>
              <MSDTradingViewChart symbol={selectedInstrument} onSymbolChange={(sym) => setSelectedInstrument(sym)} />
            </div>

            {/* Invalidation & Session Advice Row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px', marginBottom: '20px' }}>
              <div className="glass-panel" style={{ padding: '16px', borderRadius: '10px', borderLeft: '4px solid #ef4444' }}>
                <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 800, textTransform: 'uppercase' }}>INVALIDATION BOUNDARY (P90 MAE)</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
                  If price breaches adverse boundary ({instrumentProfile?.expected_mae || 15}p) before reaching target, setup is invalidated.
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '16px', borderRadius: '10px', borderLeft: '4px solid var(--accent-teal)' }}>
                <div style={{ fontSize: '11px', color: 'var(--accent-teal)', fontWeight: 800, textTransform: 'uppercase' }}>ACTIONABLE SESSION ADVICE</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
                  Preferred Session: {instrumentProfile?.best_session || 'LONDON'} corridor.
                </div>
              </div>
            </div>

            <button
              style={{ padding: '12px 24px', borderRadius: '8px', background: 'var(--accent-teal)', color: '#000', fontWeight: 800, fontSize: '13px', cursor: 'pointer', border: 'none' }}
              onClick={() => setActiveTab('why')}
            >
              AUDIT EVIDENCE (WHY) →
            </button>
          </div>
        )}

        {/* --- SCREEN 3: WHY (Evidence Audit Terminal) --- */}
        {activeTab === 'why' && (
          <EvidenceAuditTab
            selectedInstrument={selectedInstrument}
            setSelectedInstrument={setSelectedInstrument}
            instrumentProfile={instrumentProfile}
            instrumentDna={instrumentDna}
            similarDays={similarDays}
            macroRegime={macroRegime}
            chartEntryZone={chartEntryZone}
            onSelectMatchForModal={(match) => setSelectedMatchForModal(match)}
          />
        )}



        {/* --- 4. TRADING JOURNAL (Auto Journal) --- */}
        {activeTab === 'journal' && (
          <div className="animate-fade-in">
            <AutoJournalTab />
          </div>
        )}

        {/* --- 5. AI CHAT ASSISTANT --- */}
        {activeTab === 'chat' && (
          <div className="animate-fade-in">
            <header className="dashboard-header">
              <h2 className="dashboard-title">Conversational Research Assistant</h2>
              <p className="dashboard-subtitle">grounded exclusively in quantitative MSD historical signatures</p>
            </header>

            <div className="glass-panel" style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
              
              {/* Quick Questions buttons bar */}
              <div style={{ display: 'flex', gap: '8px', padding: '12px 16px', borderBottom: '1px solid var(--border-color)', overflowX: 'auto', flexShrink: 0 }}>
                <span style={{ fontSize: '11px', alignSelf: 'center', color: 'var(--text-muted)', textTransform: 'uppercase', marginRight: '8px', flexShrink: 0, letterSpacing: '0.5px' }}>Ask:</span>
                {[
                  { label: `What is ${selectedInstrument || 'GBPUSD'} doing?`, q: `What is ${selectedInstrument || 'GBPUSD'} doing right now?` },
                  { label: 'Compare all pairs', q: 'Compare GBPUSD vs EURUSD vs XAUUSD vs AUDUSD vs USDJPY' },
                  { label: 'What does READY mean?', q: 'What does READY mean in Market OS?' },
                  { label: 'What is P90?', q: 'What is P90 invalidation and why is it used?' },
                  { label: `Entry analysis ${selectedInstrument || 'GBPUSD'}`, q: `Where should I enter ${selectedInstrument || 'GBPUSD'}? Market or limit?` },
                  { label: `${selectedInstrument || 'GBPUSD'} drops 10 pips?`, q: `What if ${selectedInstrument || 'GBPUSD'} drops 10 pips from current price?` },
                ].map(({ label, q }) => (
                  <button
                    key={label}
                    className="btn"
                    style={{ padding: '5px 11px', fontSize: '11px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', whiteSpace: 'nowrap', flexShrink: 0 }}
                    onClick={() => handleQuickQuestion(q)}
                  >{label}</button>
                ))}
              </div>

              {/* Chat bubbles */}
              <div className="chat-messages">
                {chatMessages.map((msg, idx) => {
                  const isAI = msg.sender === 'ai';
                  return (
                    <div
                      key={idx}
                      className={`chat-bubble ${msg.sender === 'user' ? 'bubble-user' : 'bubble-ai'}`}
                    >
                      {/* Message text — render markdown-style bold */}
                      <div style={{ fontSize: '14px', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}
                        dangerouslySetInnerHTML={{
                          __html: msg.text
                            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                            .replace(/^#{1,3}\s+(.+)$/gm, '<span style="font-weight:700;color:var(--accent-teal);font-size:13px;text-transform:uppercase;letter-spacing:0.5px">$1</span>')
                        }}
                      />

                      {/* Structured Evidence Footer */}
                      {isAI && msg.evidence && msg.evidence.length > 0 && (
                        <div style={{
                          marginTop: '12px',
                          paddingTop: '10px',
                          borderTop: '1px solid rgba(0,242,254,0.12)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '4px',
                        }}>
                          <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.7px', color: 'var(--text-muted)', marginBottom: '4px' }}>Evidence Sources</span>
                          {msg.evidence.map((e, ei) => (
                            <div key={ei} style={{ display: 'flex', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--accent-teal)', flexShrink: 0 }}>▸</span>
                              <span><strong style={{ color: 'var(--text-primary)' }}>{e.metric}</strong>: {e.value}</span>
                              <span style={{ color: 'var(--text-muted)', marginLeft: 'auto', flexShrink: 0 }}>— {e.source}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Suggested Followups */}
                      {isAI && msg.suggestedFollowups && msg.suggestedFollowups.length > 0 && (
                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                          {msg.suggestedFollowups.map((f, fi) => (
                            <button
                              key={fi}
                              onClick={() => handleSendMessage(f)}
                              style={{
                                fontSize: '11px',
                                padding: '4px 10px',
                                background: 'rgba(0,242,254,0.06)',
                                border: '1px solid rgba(0,242,254,0.18)',
                                borderRadius: '20px',
                                color: 'var(--accent-teal)',
                                cursor: 'pointer',
                                lineHeight: 1.4,
                              }}
                            >{f}</button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
                {chatLoading && (
                  <div className="chat-bubble bubble-ai" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Loader className="animate-spin" style={{ color: 'var(--accent-teal)', width: '16px', height: '16px' }} />
                    <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Market OS AI is reasoning from quantitative data...</span>
                  </div>
                )}
              </div>

              {/* Input box */}
              <div className="chat-input-area">
                <input 
                  type="text" 
                  className="form-input" 
                  value={chatInput} 
                  onChange={(e) => setChatInput(e.target.value)} 
                  placeholder="Ask a quantitative question (e.g. 'Why is today's confidence only 62%?')..."
                  onKeyDown={(e) => { if (e.key === 'Enter') handleSendMessage(); }}
                  disabled={chatLoading}
                />
                <button className="btn" onClick={() => handleSendMessage()} disabled={chatLoading}>
                  <Send style={{ width: '16px', height: '16px' }} /> Send
                </button>
              </div>

            </div>
          </div>
        )}

        {/* --- 6. HISTORICAL REPLAY / SIMULATION --- */}
        {activeTab === 'replay' && (
          <div className="animate-fade-in">
            <ReplayTab />
          </div>
        )}

        {/* --- 7. LIVE EXECUTION GATEWAY & BRIDGE --- */}
        {activeTab === 'execution' && (
          <div className="animate-fade-in">
            <ExecutionTab />
          </div>
        )}



      </main>

      {/* Historical Signature Match Detail Modal */}
      <HistoricalMatchModal
        isOpen={!!selectedMatchForModal}
        onClose={() => setSelectedMatchForModal(null)}
        signature={selectedMatchForModal}
        instrument={selectedInstrument}
      />

      {/* Take Setup Execution Modal */}
      <TakeSetupModal
        isOpen={takeSetupModalOpen}
        onClose={() => setTakeSetupModalOpen(false)}
        instrument={takeSetupSymbol}
        setupData={takeSetupData}
        onConfirm={handleConfirmTakeSetup}
      />
    </div>
  );
}

function AppWithAuth() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

export default AppWithAuth;
