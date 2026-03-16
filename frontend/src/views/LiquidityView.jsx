import React, { useCallback } from 'react';
import LiquidityChart from '../components/LiquidityChart';
import SignalGauges from '../components/SignalGauges';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';

function StatCard({ label, value, sub, color }) {
  return (
    <div className="card p-4">
      <div className="label mb-2">{label}</div>
      <div className="font-mono text-xl font-semibold" style={{ color: color || '#f0f0f0' }}>
        {value}
      </div>
      {sub && <div className="text-[10px] text-white/25 font-mono mt-1">{sub}</div>}
    </div>
  );
}

export default function LiquidityView() {
  const fetchLiquidity  = useCallback(() => api.getLiquidity(365), []);
  const fetchScorecard  = useCallback(() => api.getScorecard(), []);
  const liquidity = useFetch(fetchLiquidity);
  const scorecard = useFetch(fetchScorecard);

  const latest = liquidity.data?.data?.[0];
  const sc = scorecard.data;

  const trendColor = sc?.liquidity > 0.2 ? '#22c55e' : sc?.liquidity < -0.2 ? '#ef4444' : '#f59e0b';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold tracking-tight">Liquidity</h2>
        <span className="text-[10px] text-white/25 font-mono">Fed balance sheet proxy</span>
      </div>

      {/* Stat row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Net Liquidity"
          value={latest?.net_liquidity != null ? `${(latest.net_liquidity / 1000).toFixed(1)}T` : '—'}
          sub="WALCL − RRP − TGA"
        />
        <StatCard
          label="4-Week Change"
          value={
            latest?.d_liquidity != null
              ? `${latest.d_liquidity > 0 ? '+' : ''}${(latest.d_liquidity / 1000).toFixed(2)}T`
              : '—'
          }
          color={latest?.d_liquidity > 0 ? '#22c55e' : latest?.d_liquidity < 0 ? '#ef4444' : '#f0f0f0'}
          sub="trailing 20-day"
        />
        <StatCard
          label="Liquidity Signal"
          value={sc?.liquidity != null ? (sc.liquidity >= 0 ? '+' : '') + sc.liquidity.toFixed(2) : '—'}
          color={trendColor}
          sub="z-score · 2yr window"
        />
        <StatCard
          label="Stress Signal"
          value={sc?.financial_stress != null ? (sc.financial_stress >= 0 ? '+' : '') + sc.financial_stress.toFixed(2) : '—'}
          color={sc?.financial_stress > 0.2 ? '#22c55e' : sc?.financial_stress < -0.2 ? '#ef4444' : '#f59e0b'}
          sub="HY spread + VIX (inv)"
        />
      </div>

      {/* Full chart */}
      <LiquidityChart data={liquidity.data} />

      {/* Signal gauges — liquidity context */}
      <div className="grid gap-4 lg:grid-cols-2">
        <SignalGauges data={sc} />
        <div className="card p-5">
          <div className="label mb-3">About This View</div>
          <div className="space-y-3 text-[11px] text-white/40 font-mono leading-relaxed">
            <p>Net Liquidity = Fed Total Assets (WALCL) minus Reverse Repo (RRPONTSYD) minus Treasury General Account (WTREGEN).</p>
            <p>When net liquidity expands, risk assets typically benefit — more dollars are available to flow into markets.</p>
            <p>The 2-year z-score normalizes the current level against historical context. Values above +1 indicate historically elevated liquidity.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
