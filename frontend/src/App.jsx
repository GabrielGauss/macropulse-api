import React, { useState, useEffect, useCallback } from 'react';
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
const ForecastCard          = React.lazy(() => import('./components/ForecastCard'));
const CommentaryCard        = React.lazy(() => import('./components/CommentaryCard'));
const CompositeAnalysisCard = React.lazy(() => import('./components/CompositeAnalysisCard'));
const AlertSettings         = React.lazy(() => import('./components/AlertSettings'));
const WebhookGuide          = React.lazy(() => import('./components/WebhookGuide'));
import { useFetch } from './hooks/useFetch';
import { GuideModeContext, useGuideModeState } from './lib/guideMode';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';

function UpgradeGate({ feature, plan = 'Starter' }) {
  const isPro = plan === 'Pro';
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div
        className="mb-6 flex items-center justify-center"
        style={{ width: 48, height: 48, background: 'rgba(255,255,255,0.03)', border: '1px solid #222' }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <div className="text-[13px] font-semibold text-white/60 mb-1">{feature}</div>
      <div className="text-[11px] text-white/40 font-mono mb-5">
        Requires <span style={{ color: isPro ? '#3b82f6' : '#22c55e' }}>{plan}</span> plan
      </div>
      <a
        href="https://macropulse.live/pricing.html"
        target="_blank"
        rel="noopener noreferrer"
        className="text-[11px] font-mono px-4 py-2 transition-opacity hover:opacity-80"
        style={{
          background: isPro ? 'rgba(59,130,246,0.1)' : 'rgba(34,197,94,0.1)',
          color: isPro ? '#3b82f6' : '#22c55e',
          border: `1px solid ${isPro ? 'rgba(59,130,246,0.25)' : 'rgba(34,197,94,0.25)'}`,
          textDecoration: 'none',
        }}
      >
        Upgrade to {plan} →
      </a>
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

  // Derive capabilities from tier
  const isFree            = tier === 'free' || tier === null;
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
              !isStarterOrAbove ? <UpgradeGate feature="Liquidity Analysis" plan="Starter" /> : <LiquidityView />
            )}

            {/* ── Signals ── */}
            {activeSection === 'signals' && (
              !isStarterOrAbove ? <UpgradeGate feature="Signal Deep-Dive" plan="Starter" /> : <SignalsView />
            )}

            {/* ── Performance ── */}
            {activeSection === 'performance' && (
              <PerformanceView />
            )}

            {/* ── Backtests ── */}
            {activeSection === 'backtest' && (
              !isProOrAbove ? <UpgradeGate feature="Backtest Engine" plan="Pro" /> : <BacktestView />
            )}

            {/* ── Domain Views ── */}
            {activeSection === 'inflation'   && (!isProOrAbove ? <UpgradeGate feature="Inflation Analysis"   plan="Pro" /> : <InflationView />)}
            {activeSection === 'growth'      && (!isProOrAbove ? <UpgradeGate feature="Growth Analysis"      plan="Pro" /> : <GrowthView />)}
            {activeSection === 'rates'       && (!isProOrAbove ? <UpgradeGate feature="Rates Analysis"       plan="Pro" /> : <RatesView />)}
            {activeSection === 'commodities' && (!isProOrAbove ? <UpgradeGate feature="Commodities Analysis" plan="Pro" /> : <CommoditiesView />)}
            {activeSection === 'fx'          && (!isProOrAbove ? <UpgradeGate feature="FX Analysis"          plan="Pro" /> : <FXView />)}
            {activeSection === 'crypto'      && (!isProOrAbove ? <UpgradeGate feature="Crypto Analysis"      plan="Pro" /> : <CryptoView />)}
            {activeSection === 'quant'       && (!isProOrAbove ? <UpgradeGate feature="Quant HUD"            plan="Pro" /> : <QuantView />)}

            </React.Suspense>
            <footer className="pt-4 mt-4 text-center text-[10px] text-white/35 font-mono border-t border-[#111]">
              MacroPulse · Probabilistic macro regime intelligence
            </footer>
          </div>
        </main>
      </div>
    </div>
    </GuideModeContext.Provider>
  );
}
