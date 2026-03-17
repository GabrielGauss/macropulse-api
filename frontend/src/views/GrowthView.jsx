import React, { useCallback, useMemo } from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

const REGIME_CONTEXT = {
  expansion:  { text: 'Expansion is the strongest growth environment. Equities outperform, credit spreads compress, and the yield curve is positively sloped. Cyclicals and growth stocks lead. This is the regime where being fully invested is rewarded.' },
  recovery:   { text: 'Recovery signals a healing growth cycle. Equity momentum is positive but cautious — credit is normalising and liquidity is re-entering. Cyclical and value plays tend to outperform as the market reprices a soft-landing scenario.' },
  tightening: { text: 'Tightening constrains growth. Higher financing costs weigh on capex and consumption. Equity multiples compress as the discount rate rises. Defensives outperform cyclicals. Watch for yield curve inversion as a recession signal.' },
  risk_off:   { text: 'Risk-Off is a growth shock. Equities sell off sharply, credit spreads blow out, and growth expectations collapse. This is the regime where cash, Gold, and short-duration Treasuries preserve capital while equities and cyclicals suffer.' },
};

function StatCard({ label, value, sub, color }) {
  return (
    <div className="card p-4">
      <div className="text-[10px] font-mono uppercase tracking-wide mb-2" style={{ color: 'rgba(255,255,255,0.25)' }}>{label}</div>
      <div className="text-[22px] font-semibold font-mono leading-none mb-1" style={{ color: color || '#f0f0f0' }}>{value}</div>
      {sub && <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>{sub}</div>}
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#141414', border: '1px solid #2a2a2a', borderRadius: 6, padding: '8px 12px', fontSize: 11, fontFamily: 'JetBrains Mono' }}>
      <div style={{ color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value > 0 ? '+' : ''}{(p.value * 100).toFixed(3)}%
        </div>
      ))}
    </div>
  );
}

export default function GrowthView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_sp500: r.d_sp500 ?? 0,
      d_yield_curve: r.d_yield_curve ?? 0,
      d_liquidity: (r.d_liquidity ?? 0) / 1e6, // scale to comparable range
    }));
  }, [features.data]);

  const avg20 = (col, transform) => {
    if (!features.data) return 0;
    const slice = features.data.slice(0, 20);
    return slice.reduce((s, r) => s + (transform ? transform(r[col] ?? 0) : (r[col] ?? 0)), 0) / slice.length;
  };

  const equityDir = avg20('d_sp500');
  const curveDir = avg20('d_yield_curve');
  const liquidity20 = features.data?.slice(0, 20).reduce((s, r) => s + (r.d_liquidity ?? 0), 0) ?? 0;

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Growth Signals</h2>
        <span className="text-[10px] text-white/25 font-mono">Equity momentum · yield curve · liquidity support</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="Equity Momentum"
          value={equityDir > 0 ? 'Positive' : 'Negative'}
          sub={`S&P 500 20d avg: ${equityDir > 0 ? '+' : ''}${(equityDir * 100).toFixed(3)}%`}
          color={equityDir > 0 ? '#22c55e' : '#ef4444'}
        />
        <StatCard
          label="Yield Curve"
          value={curveDir > 0 ? 'Steepening' : 'Flattening'}
          sub={`Growth signal: ${curveDir > 0 ? 'positive' : 'negative'}`}
          color={curveDir > 0 ? '#22c55e' : '#f59e0b'}
        />
        <StatCard
          label="Liquidity Flow"
          value={liquidity20 > 0 ? 'Expanding' : 'Contracting'}
          sub={`20d net: ${liquidity20 > 0 ? '+' : ''}$${(liquidity20 / 1e6).toFixed(1)}T`}
          color={liquidity20 > 0 ? '#22c55e' : '#ef4444'}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Growth Indicators (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_sp500" name="S&P500 Δ" stroke="#22c55e" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_yield_curve" name="Curve Δ" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — growth context
            </span>
          </div>
          <p className="text-[11px] font-mono leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>
            {ctx.text}
          </p>
        </div>
      )}
    </div>
  );
}
