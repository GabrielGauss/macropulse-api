import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import RegimeCard from './components/RegimeCard';
import RegimeTimeline from './components/RegimeTimeline';
import LiquidityChart from './components/LiquidityChart';
import FactorsChart from './components/FactorsChart';
import DriftPanel from './components/DriftPanel';
import SignalGauges from './components/SignalGauges';
import MacroHeatmap from './components/MacroHeatmap';
import RegimeCalendar from './components/RegimeCalendar';
const InflationView         = React.lazy(() => import('./views/InflationView'));
const GrowthView            = React.lazy(() => import('./views/GrowthView'));
const RatesView             = React.lazy(() => import('./views/RatesView'));
const CommoditiesView       = React.lazy(() => import('./views/CommoditiesView'));
const FXView                = React.lazy(() => import('./views/FXView'));
const CryptoView            = React.lazy(() => import('./views/CryptoView'));
const QuantView             = React.lazy(() => import('./views/QuantView'));
const LiquidityView         = React.lazy(() => import('./views/LiquidityView'));
const SignalsView           = React.lazy(() => import('./views/SignalsView'));
const BacktestView          = React.lazy(() => import('./views/BacktestView'));
const PerformanceView       = React.lazy(() => import('./views/PerformanceView'));
const AccountView           = React.lazy(() => import('./views/AccountView'));
const ForecastCard          = React.lazy(() => import('./components/ForecastCard'));
const CommentaryCard        = React.lazy(() => import('./components/CommentaryCard'));
const CompositeAnalysisCard = React.lazy(() => import('./components/CompositeAnalysisCard'));
const AlertSettings         = React.lazy(() => import('./components/AlertSettings'));
const WebhookGuide          = React.lazy(() => import('./components/WebhookGuide'));
import { useFetch } from './hooks/useFetch';
import { GuideModeContext, useGuideModeState } from './lib/guideMode';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';
import RegisterModal from './components/RegisterModal';
import RecoverModal from './components/RecoverModal';

const GATE_COPY = {
  'Liquidity Analysis': {
    tagline: 'The hidden driver behind every regime shift.',
    bullets: [
      'Fed balance sheet decomposition — net liquidity in real time',
      'Repo markets, RRP facility & TGA drain — all in one view',
      'Liquidity-adjusted equity risk premium signal',
    ],
  },
  'Signal Deep-Dive': {
    tagline: 'Every indicator behind the regime, laid bare.',
    bullets: [
      'Yield curve shape, credit spreads & VIX term structure',
      'Live indicator table with regime-relative z-scores',
      'See exactly which signals are driving the current classification',
    ],
  },
  'Backtest Engine': {
    tagline: 'Validate your strategy against two years of regime history.',
    bullets: [
      'Regime-conditioned P&L — Sharpe, drawdown, win rate by state',
      'Compare Long / Short / Cash across all four regimes',
      'Export results as CSV for further analysis',
    ],
  },
  'Inflation Analysis': {
    tagline: 'CPI, PPI and breakevens in regime context.',
    bullets: [
      'Inflation trend vs. regime alignment — bullish or headwind?',
      'Breakeven rates, TIPS real yield & PCE decomposition',
      'Forward-looking inflation pressure score',
    ],
  },
  'Growth Analysis': {
    tagline: 'ISM, PMI and leading indicators decoded.',
    bullets: [
      'Manufacturing vs. services divergence signal',
      'Leading indicator composite with regime overlay',
      'Growth momentum score — where are we in the cycle?',
    ],
  },
  'Rates Analysis': {
    tagline: 'The full yield curve — not just 10Y.',
    bullets: [
      '2s10s, 3m10Y, real rates & Fed funds path',
      'Curve shape regime — steepening, flattening, inverted',
      'Duration risk score relative to current macro state',
    ],
  },
  'Commodities Analysis': {
    tagline: 'Oil, gold and copper as macro indicators.',
    bullets: [
      'Commodity regime signal — risk-on or inflation hedge?',
      'Gold vs. real rates divergence alert',
      'Energy and metals momentum with regime context',
    ],
  },
  'FX Analysis': {
    tagline: 'Dollar strength and EM stress in one view.',
    bullets: [
      'DXY trend, EM FX stress index & carry signal',
      'G10 relative strength vs. macro regime',
      'Dollar liquidity proxy for global risk appetite',
    ],
  },
  'Crypto Analysis': {
    tagline: 'BTC and ETH as risk-appetite gauges.',
    bullets: [
      'Crypto risk score mapped to macro regime phase',
      'BTC/ETH correlation to liquidity and risk-off signals',
      'Regime-adjusted position sizing framework',
    ],
  },
  'Quant HUD': {
    tagline: 'Raw model internals for quantitative research.',
    bullets: [
      'PCA factor scores — what\'s actually driving regimes',
      'HMM transition matrix — regime persistence probabilities',
      'Model drift metrics — when to trust the signal less',
    ],
  },
};

function UpgradeGate({ feature, plan = 'Starter' }) {
  const isPro  = plan === 'Pro';
  const color  = isPro ? '#3b82f6' : '#22c55e';
  const copy   = GATE_COPY[feature] || { tagline: '', bullets: [] };

  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <div style={{ maxWidth: 420, width: '100%' }}>
        {/* Lock + plan badge */}
        <div className="flex items-center gap-3 mb-5">
          <div
            className="flex items-center justify-center flex-shrink-0"
            style={{ width: 36, height: 36, background: 'rgba(255,255,255,0.03)', border: '1px solid #222' }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white/70">{feature}</div>
            <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Requires <span style={{ color }}>{plan}</span> plan
            </div>
          </div>
        </div>

        {/* Tagline */}
        {copy.tagline && (
          <div className="text-[12px] text-white/50 mb-4 font-mono">{copy.tagline}</div>
        )}

        {/* What you get */}
        {copy.bullets.length > 0 && (
          <div
            className="mb-6 p-4"
            style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #1a1a1a' }}
          >
            <div className="text-[9px] font-mono uppercase tracking-widest mb-3" style={{ color: 'rgba(255,255,255,0.30)' }}>
              What's included
            </div>
            <div className="flex flex-col gap-2">
              {copy.bullets.map((b, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-[10px] mt-px flex-shrink-0" style={{ color }}>—</span>
                  <span className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.50)' }}>{b}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <a
          href="https://macropulse.live/pricing.html"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[11px] font-mono px-5 py-2.5 transition-opacity hover:opacity-80"
          style={{
            background: isPro ? 'rgba(59,130,246,0.1)' : 'rgba(34,197,94,0.1)',
            color,
            border: `1px solid ${isPro ? 'rgba(59,130,246,0.25)' : 'rgba(34,197,94,0.25)'}`,
            textDecoration: 'none',
          }}
        >
          Upgrade to {plan} →
        </a>
        <div className="mt-3 text-[9px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
          14-day money-back guarantee · Cancel anytime
        </div>
      </div>
    </div>
  );
}

function NoKeyBanner({ onGetKey, onRecover }) {
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem('mp_banner_dismissed') === '1'
  );
  if (dismissed) return null;

  function dismiss() {
    sessionStorage.setItem('mp_banner_dismissed', '1');
    setDismissed(true);
  }

  return (
    <div
      className="mb-4 flex items-start gap-4 px-4 py-3"
      style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #1f1f1f', position: 'relative' }}
    >
      {/* Dismiss */}
      <button
        onClick={dismiss}
        className="absolute top-2.5 right-3 text-[12px] font-mono transition-colors"
        style={{ color: 'rgba(255,255,255,0.25)' }}
        onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.55)'}
        onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.25)'}
        title="Dismiss"
      >×</button>

      {/* Indicator */}
      <div
        className="flex-shrink-0 flex items-center justify-center mt-0.5"
        style={{ width: 28, height: 28, border: '1px solid #222', background: 'rgba(34,197,94,0.05)' }}
      >
        <div style={{ width: 6, height: 6, background: '#22c55e', borderRadius: '50%' }} />
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold text-white/60 mb-0.5">
          You're viewing live macro signals — no API key set.
        </div>
        <div className="text-[10px] font-mono text-white/35 leading-relaxed">
          MacroPulse tracks the global macro regime using a Hidden Markov Model across 14 indicators.
          Unlock deeper views — liquidity, signals, forecasts — with a free API key.
        </div>
        <div className="flex items-center gap-3 mt-2.5">
          <button
            onClick={onGetKey}
            className="text-[10px] font-mono px-3 py-1.5 transition-opacity hover:opacity-80"
            style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.25)' }}
          >
            Get free API key →
          </button>
          <button
            onClick={onRecover}
            className="text-[10px] font-mono transition-colors"
            style={{ color: 'rgba(255,255,255,0.35)' }}
            onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
            onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.35)'}
          >
            Already registered? Recover key →
          </button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const { connected, lastMessage } = useRegimeSocket();
  const [activeSection, setActiveSection] = useState('dashboard');
  const [guideMode, toggleGuideMode] = useGuideModeState();
  const [historyDays, setHistoryDays] = useState(365);
  const [tier, setTier] = useState(null); // null = loading, 'free'|'starter'|'pro'|'owner'
  const [meInfo, setMeInfo] = useState(null); // { email, tier }
  const [showRegister, setShowRegister] = useState(false);
  const [showRecover, setShowRecover] = useState(false);

  // Derive capabilities from tier (null = still loading — don't gate anything yet)
  const tierLoading       = tier === null;
  const isFree            = tier === 'free';
  const isStarterOrAbove  = tier === 'starter' || tier === 'pro' || tier === 'owner';
  const isProOrAbove      = tier === 'pro' || tier === 'owner';
  const FREE_HISTORY_LIMIT    = 30;
  const STARTER_HISTORY_LIMIT = 180;

  useEffect(() => {
    if (!api.hasKey()) { setTier('free'); return; }
    api.getMe()
      .then(me => {
        setTier(me.tier || 'free');
        setMeInfo({ email: me.email, tier: me.tier || 'free' });
      })
      .catch(() => setTier('free'));
  }, []);

  const fetchRegime    = useCallback(() => api.getCurrentRegime(), []);
  const fetchHistory   = useCallback(() => {
    const limit = isFree ? FREE_HISTORY_LIMIT : isStarterOrAbove && !isProOrAbove ? STARTER_HISTORY_LIMIT : historyDays;
    return api.getRegimeHistory(limit);
  }, [historyDays, isFree, isStarterOrAbove, isProOrAbove]);
  const fetchLiquidity = useCallback(() => api.getLiquidity(60), []);
  const fetchFactors   = useCallback(() => api.getFactors(60), []);
  const fetchDrift     = useCallback(() => api.getDrift(30), []);
  const fetchScorecard = useCallback(() => api.getScorecard(), []);

  const regime    = useFetch(fetchRegime);
  const history   = useFetch(fetchHistory);
  const liquidity = useFetch(fetchLiquidity);
  const factors   = useFetch(fetchFactors);
  const drift     = useFetch(fetchDrift);
  const scorecard = useFetch(fetchScorecard);

  useEffect(() => {
    if (lastMessage) {
      regime.refetch();
      history.refetch();
      liquidity.refetch();
      factors.refetch();
      drift.refetch();
      scorecard.refetch();
    }
  }, [lastMessage]);

  useEffect(() => { history.refetch(); }, [historyDays]);

  return (
    <GuideModeContext.Provider value={guideMode}>
    <div className="flex h-screen overflow-hidden bg-surface-0">
      <Sidebar
        regime={regime.data}
        activeSection={activeSection}
        onNavigate={setActiveSection}
        tier={tier}
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header connected={connected} regime={regime.data} meInfo={meInfo} guideMode={guideMode} onToggleGuide={toggleGuideMode} />

        <main className="flex-1 overflow-y-auto p-4 lg:p-5">
          {regime.error && (
            <div className="mb-4 rounded border border-[#2a2a2a] bg-surface-1 px-4 py-3 text-[11px] text-white/40 font-mono">
              API unavailable — check backend connection
            </div>
          )}

          <div className="mx-auto max-w-screen-xl">
            <React.Suspense fallback={<div className="flex items-center justify-center h-full"><span className="text-[11px] text-white/30 font-mono">Loading…</span></div>}>

            {/* ── Dashboard ── */}
            {activeSection === 'dashboard' && (
              <div className="space-y-4">
                {!api.hasKey() && (
                  <NoKeyBanner
                    onGetKey={() => setShowRegister(true)}
                    onRecover={() => setShowRecover(true)}
                  />
                )}
                <div className="grid gap-4 lg:grid-cols-3">
                  <RegimeCard regime={regime.data} />
                  <SignalGauges data={scorecard.data} />
                  <MacroHeatmap regime={regime.data} />
                </div>
                <RegimeTimeline
                  history={history.data}
                  historyDays={isFree ? FREE_HISTORY_LIMIT : isStarterOrAbove && !isProOrAbove ? STARTER_HISTORY_LIMIT : historyDays}
                  onHistoryDaysChange={isProOrAbove ? setHistoryDays : undefined}
                  isFree={isFree}
                />
                <RegimeCalendar isFree={isFree} tier={tier} />
                <div className="grid gap-4 lg:grid-cols-3">
                  <LiquidityChart data={liquidity.data} />
                  <FactorsChart data={factors.data} />
                  <DriftPanel data={drift.data} />
                </div>
                <CompositeAnalysisCard />
                <ForecastCard />
                <CommentaryCard tier={tier} />
                <AlertSettings tier={tier} />
                <WebhookGuide tier={tier} />
              </div>
            )}

            {/* ── Liquidity ── */}
            {activeSection === 'liquidity' && (
              tierLoading ? null : !isStarterOrAbove ? <UpgradeGate feature="Liquidity Analysis" plan="Starter" /> : <LiquidityView />
            )}

            {/* ── Signals ── */}
            {activeSection === 'signals' && (
              tierLoading ? null : !isStarterOrAbove ? <UpgradeGate feature="Signal Deep-Dive" plan="Starter" /> : <SignalsView />
            )}

            {/* ── Performance ── */}
            {activeSection === 'performance' && (
              <PerformanceView />
            )}

            {/* ── Backtests ── */}
            {activeSection === 'backtest' && (
              tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Backtest Engine" plan="Pro" /> : <BacktestView />
            )}

            {/* ── Domain Views ── */}
            {activeSection === 'inflation'   && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Inflation Analysis"   plan="Pro" /> : <InflationView />)}
            {activeSection === 'growth'      && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Growth Analysis"      plan="Pro" /> : <GrowthView />)}
            {activeSection === 'rates'       && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Rates Analysis"       plan="Pro" /> : <RatesView />)}
            {activeSection === 'commodities' && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Commodities Analysis" plan="Pro" /> : <CommoditiesView />)}
            {activeSection === 'fx'          && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="FX Analysis"          plan="Pro" /> : <FXView />)}
            {activeSection === 'crypto'      && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Crypto Analysis"      plan="Pro" /> : <CryptoView />)}
            {activeSection === 'quant'       && (tierLoading ? null : !isProOrAbove ? <UpgradeGate feature="Quant HUD"            plan="Pro" /> : <QuantView />)}

            {activeSection === 'account' && (
              <AccountView
                meInfo={meInfo}
                tier={tier}
                onTierChange={setTier}
              />
            )}

            </React.Suspense>
            <footer className="pt-4 mt-4 text-center text-[10px] text-white/35 font-mono border-t border-[#111]">
              MacroPulse · Probabilistic macro regime intelligence
            </footer>
          </div>
        </main>
      </div>
    </div>

    {showRegister && (
      <RegisterModal
        onClose={() => setShowRegister(false)}
        onRegistered={() => { setShowRegister(false); window.location.reload(); }}
        onSwitchToRecover={() => { setShowRegister(false); setShowRecover(true); }}
      />
    )}
    {showRecover && (
      <RecoverModal
        onClose={() => setShowRecover(false)}
        onRecovered={() => { setShowRecover(false); window.location.reload(); }}
      />
    )}
    </GuideModeContext.Provider>
  );
}
