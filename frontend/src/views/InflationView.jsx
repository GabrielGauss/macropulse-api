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
  expansion:  { text: 'Expansion regimes typically feature stable or falling long-end yields as liquidity is ample. Inflation expectations are moderate — the economy grows without overheating. Bonds and TIPS perform well in early expansion; Gold holds steady.', color: '#22c55e' },
  recovery:   { text: 'Recovery phases show rising inflation expectations as liquidity re-enters the system. The yield curve steepens as 10Y sells off faster than 2Y. Watch for breakeven inflation widening — the first sign of transition to tightening.', color: '#3b82f6' },
  tightening: { text: 'Tightening regimes are defined by rising yields and flattening or inverted curves as the Fed hikes rates to fight inflation. Real yields rise, pressuring Gold and long-duration bonds. Credit spreads widen as financing conditions deteriorate.', color: '#f59e0b' },
  risk_off:   { text: 'Risk-Off environments see a flight to safety: 10Y yields fall sharply as capital floods into Treasuries. The curve flattens or inverts. TIPS spreads widen briefly before collapsing. Gold surges as a safe haven.', color: '#ef4444' },
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

export default function InflationView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_10y: r.d_10y ?? 0,
      d_yield_curve: r.d_yield_curve ?? 0,
      d_hy_spread: r.d_hy_spread ?? 0,
    }));
  }, [features.data]);

  const latest = features.data?.[0] ?? {};
  const avg20 = (col) => {
    if (!features.data) return 0;
    const slice = features.data.slice(0, 20);
    return slice.reduce((s, r) => s + (r[col] ?? 0), 0) / slice.length;
  };

  const tenYDir = avg20('d_10y');
  const curveDir = avg20('d_yield_curve');
  const spreadDir = avg20('d_hy_spread');

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Inflation Dynamics</h2>
        <span className="text-[10px] text-white/25 font-mono">Rate pressure · yield curve · credit conditions</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="10Y Yield Pressure"
          value={tenYDir > 0 ? 'Rising' : 'Falling'}
          sub={`20d avg Δ: ${tenYDir > 0 ? '+' : ''}${(tenYDir * 100).toFixed(3)}%`}
          color={tenYDir > 0 ? '#f59e0b' : '#22c55e'}
        />
        <StatCard
          label="Curve Steepness"
          value={curveDir > 0 ? 'Steepening' : 'Flattening'}
          sub={`20d avg Δ: ${curveDir > 0 ? '+' : ''}${(curveDir * 100).toFixed(3)}%`}
          color={curveDir > 0 ? '#3b82f6' : '#ef4444'}
        />
        <StatCard
          label="Credit Conditions"
          value={spreadDir < 0 ? 'Tightening' : 'Widening'}
          sub={`HY spread 20d: ${spreadDir > 0 ? '+' : ''}${(spreadDir * 100).toFixed(3)}%`}
          color={spreadDir < 0 ? '#22c55e' : '#ef4444'}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Rate Momentum (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_10y" name="10Y Δ" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_yield_curve" name="Curve Δ" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — inflation context
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
