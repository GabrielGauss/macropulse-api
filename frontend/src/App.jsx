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

export default function App() {
  const { connected, lastMessage } = useRegimeSocket();
  const [activeSection, setActiveSection] = useState('dashboard');
  const [historyDays, setHistoryDays] = useState(90);

  const fetchRegime    = useCallback(() => api.getCurrentRegime(), []);
  const fetchHistory   = useCallback(() => api.getRegimeHistory(historyDays), [historyDays]);
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
      />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header connected={connected} regime={regime.data} />

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
                  historyDays={historyDays}
                  onHistoryDaysChange={setHistoryDays}
                />
                <div className="grid gap-4 lg:grid-cols-3">
                  <LiquidityChart data={liquidity.data} />
                  <FactorsChart data={factors.data} />
                  <DriftPanel data={drift.data} />
                </div>
              </div>
            )}

            {/* ── Liquidity ── */}
            {activeSection === 'liquidity' && <LiquidityView />}

            {/* ── Signals ── */}
            {activeSection === 'signals' && <SignalsView />}

            {/* ── Backtests ── */}
            {activeSection === 'backtest' && <BacktestView />}

            <footer className="pt-4 mt-4 text-center text-[10px] text-white/10 font-mono border-t border-[#111]">
              MacroPulse · Probabilistic macro regime intelligence
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
