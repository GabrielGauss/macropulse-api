import React, { useEffect, useCallback } from 'react';
import Header from './components/Header';
import RegimeCard from './components/RegimeCard';
import RegimeTimeline from './components/RegimeTimeline';
import LiquidityChart from './components/LiquidityChart';
import FactorsChart from './components/FactorsChart';
import DriftPanel from './components/DriftPanel';
import { useFetch } from './hooks/useFetch';
import { useRegimeSocket } from './hooks/useRegimeSocket';
import { api } from './lib/api';

export default function App() {
  const { connected, lastMessage } = useRegimeSocket();

  const fetchRegime    = useCallback(() => api.getCurrentRegime(), []);
  const fetchHistory   = useCallback(() => api.getRegimeHistory(90), []);
  const fetchLiquidity = useCallback(() => api.getLiquidity(60), []);
  const fetchFactors   = useCallback(() => api.getFactors(60), []);
  const fetchDrift     = useCallback(() => api.getDrift(30), []);

  const regime    = useFetch(fetchRegime);
  const history   = useFetch(fetchHistory);
  const liquidity = useFetch(fetchLiquidity);
  const factors   = useFetch(fetchFactors);
  const drift     = useFetch(fetchDrift);

  useEffect(() => {
    if (lastMessage) {
      regime.refetch();
      history.refetch();
      liquidity.refetch();
      factors.refetch();
      drift.refetch();
    }
  }, [lastMessage]);

  return (
    <div className="flex min-h-screen flex-col bg-surface-0">
      <Header connected={connected} regime={regime.data} />

      <main className="flex-1 p-4 lg:p-6">
        {regime.error && (
          <div className="mb-4 rounded border border-[#2a2a2a] bg-surface-1 px-4 py-3 text-[11px] text-white/40 font-mono">
            API unavailable — check backend connection
          </div>
        )}

        <div className="mx-auto max-w-7xl space-y-4">
          {/* Top row: regime card + drift */}
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <RegimeCard regime={regime.data} />
            </div>
            <DriftPanel data={drift.data} />
          </div>

          {/* Timeline */}
          <RegimeTimeline history={history.data} />

          {/* Bottom charts */}
          <div className="grid gap-4 lg:grid-cols-2">
            <LiquidityChart data={liquidity.data} />
            <FactorsChart data={factors.data} />
          </div>

          <footer className="pt-3 text-center text-[10px] text-white/15 font-mono border-t border-[#1f1f1f]">
            MacroPulse · Probabilistic macro regime intelligence
          </footer>
        </div>
      </main>
    </div>
  );
}
