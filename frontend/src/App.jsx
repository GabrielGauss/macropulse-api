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
import LiquidityView from './views/LiquidityView';
import SignalsView from './views/SignalsView';
import BacktestView from './views/BacktestView';
import { useFetch } from './hooks/useFetch';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';

function UpgradeGate({ feature }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div
        className="mb-6 rounded-full flex items-center justify-center"
        style={{ width: 48, height: 48, background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a' }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <div className="text-[13px] font-semibold text-white/60 mb-1">{feature}</div>
      <div className="text-[11px] text-white/25 font-mono mb-5">Available on Starter and Pro plans</div>
      <a
        href="https://macropulse.live/#pricing"
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-md text-[12px] font-semibold px-5 py-2 transition-opacity hover:opacity-85"
        style={{ background: '#f0f0f0', color: '#0a0a0a', textDecoration: 'none' }}
      >
        View plans →
      </a>
    </div>
  );
}

export default function App() {
  const { connected, lastMessage } = useRegimeSocket();
  const [activeSection, setActiveSection] = useState('dashboard');
  const [historyDays, setHistoryDays] = useState(90);
  const [tier, setTier] = useState(null); // null = loading, 'free'|'starter'|'pro'|'owner'
  const [meInfo, setMeInfo] = useState(null); // { email, tier }

  // Derive capabilities from tier
  const isFree = tier === 'free' || tier === null;
  const FREE_HISTORY_LIMIT = 30;

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
  const fetchHistory   = useCallback(() => api.getRegimeHistory(isFree ? FREE_HISTORY_LIMIT : historyDays), [historyDays, isFree]);
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
    <div className="flex h-screen overflow-hidden bg-surface-0">
      <Sidebar
        regime={regime.data}
        activeSection={activeSection}
        onNavigate={setActiveSection}
        tier={tier}
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header connected={connected} regime={regime.data} meInfo={meInfo} />

        <main className="flex-1 overflow-y-auto p-4 lg:p-5">
          {regime.error && (
            <div className="mb-4 rounded border border-[#2a2a2a] bg-surface-1 px-4 py-3 text-[11px] text-white/40 font-mono">
              API unavailable — check backend connection
            </div>
          )}

          <div className="mx-auto max-w-screen-xl">

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
                  historyDays={isFree ? FREE_HISTORY_LIMIT : historyDays}
                  onHistoryDaysChange={isFree ? undefined : setHistoryDays}
                  isFree={isFree}
                />
                <div className="grid gap-4 lg:grid-cols-3">
                  <LiquidityChart data={liquidity.data} />
                  <FactorsChart data={factors.data} />
                  <DriftPanel data={drift.data} />
                </div>
              </div>
            )}

            {/* ── Liquidity ── */}
            {activeSection === 'liquidity' && (
              isFree ? <UpgradeGate feature="Liquidity Analysis" /> : <LiquidityView />
            )}

            {/* ── Signals ── */}
            {activeSection === 'signals' && (
              isFree ? <UpgradeGate feature="Signal Deep-Dive" /> : <SignalsView />
            )}

            {/* ── Backtests ── */}
            {activeSection === 'backtest' && (
              isFree ? <UpgradeGate feature="Backtest Engine" /> : <BacktestView />
            )}

            <footer className="pt-4 mt-4 text-center text-[10px] text-white/10 font-mono border-t border-[#111]">
              MacroPulse · Probabilistic macro regime intelligence
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
