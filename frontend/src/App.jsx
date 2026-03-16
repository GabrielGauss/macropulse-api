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
import { useFetch } from './hooks/useFetch';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';

// Days per time filter label
const HISTORY_LIMITS = { '1M': 30, '3M': 90, '6M': 180, '1Y': 365 };

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

  // Re-fetch history when time window changes
  useEffect(() => { history.refetch(); }, [historyDays]);

  return (
    <div className="flex h-screen overflow-hidden bg-surface-0">
      {/* Sidebar */}
      <Sidebar
        regime={regime.data}
        activeSection={activeSection}
        onNavigate={setActiveSection}
      />

      {/* Main column */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header connected={connected} regime={regime.data} />

        <main className="flex-1 overflow-y-auto p-4 lg:p-5">
          {regime.error && (
            <div className="mb-4 rounded border border-[#2a2a2a] bg-surface-1 px-4 py-3 text-[11px] text-white/40 font-mono">
              API unavailable — check backend connection
            </div>
          )}

          <div className="mx-auto max-w-screen-xl space-y-4">
            {/* Hero row: regime + signal gauges + heatmap */}
            <div className="grid gap-4 lg:grid-cols-3">
              <RegimeCard regime={regime.data} />
              <SignalGauges data={scorecard.data} />
              <MacroHeatmap regime={regime.data} />
            </div>

            {/* Timeline with time filter */}
            <RegimeTimeline
              history={history.data}
              historyDays={historyDays}
              onHistoryDaysChange={setHistoryDays}
              historyLimits={HISTORY_LIMITS}
            />

            {/* Charts + model health */}
            <div className="grid gap-4 lg:grid-cols-3">
              <LiquidityChart data={liquidity.data} />
              <FactorsChart data={factors.data} />
              <DriftPanel data={drift.data} />
            </div>

            <footer className="pt-3 text-center text-[10px] text-white/15 font-mono border-t border-[#1f1f1f]">
              MacroPulse · Probabilistic macro regime intelligence
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
}
