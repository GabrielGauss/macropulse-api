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
  expansion:  { text: 'In Expansion, the short end is anchored by a patient Fed and the long end reflects stable growth expectations. HY spreads are tight and credit is accessible. Duration risk is moderate — yields can drift higher, but real rates remain supportive.' },
  recovery:   { text: 'Recovery features a bear-steepening yield curve: the long end sells off as growth and inflation expectations rise, while the Fed holds short rates low. This is a window of opportunity before the hiking cycle begins.' },
  tightening: { text: 'Tightening is the bear-flattening regime. The Fed aggressively hikes the short end while long-end yields lag — the curve inverts. HY spreads widen as leveraged companies face higher refinancing costs. Avoid duration and credit risk here.' },
  risk_off:   { text: 'Risk-Off causes a flight-to-quality bull rally in Treasuries. Both 2Y and 10Y yields fall, but the long end falls faster — curve steepens from the bottom. HY spreads blow out. This is the regime where Treasuries finally deliver on their hedge promise.' },
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

export default function RatesView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_10y: r.d_10y ?? 0,
      d_2y: r.d_2y ?? 0,
      d_hy_spread: r.d_hy_spread ?? 0,
    }));
  }, [features.data]);

  const avg20 = (col) => {
    if (!features.data) return 0;
    return features.data.slice(0, 20).reduce((s, r) => s + (r[col] ?? 0), 0) / 20;
  };

  const tenY = avg20('d_10y');
  const twoY = avg20('d_2y');
  const hy = avg20('d_hy_spread');
  const curveDir = tenY - twoY; // bear steepen = 10Y rises more than 2Y

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Rates & Credit</h2>
        <span className="text-[10px] text-white/25 font-mono">Treasury yields · yield curve · HY spreads</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <StatCard
          label="10Y Pressure"
          value={tenY > 0 ? 'Selling off' : 'Rallying'}
          sub={`20d avg Δ: ${tenY > 0 ? '+' : ''}${(tenY * 100).toFixed(3)}%`}
          color={tenY > 0 ? '#f59e0b' : '#22c55e'}
        />
        <StatCard
          label="2Y Pressure"
          value={twoY > 0 ? 'Selling off' : 'Rallying'}
          sub={`20d avg Δ: ${twoY > 0 ? '+' : ''}${(twoY * 100).toFixed(3)}%`}
          color={twoY > 0 ? '#f59e0b' : '#22c55e'}
        />
        <StatCard
          label="Curve Dynamic"
          value={curveDir > 0 ? 'Bear steep.' : curveDir < 0 ? 'Flattening' : 'Neutral'}
          sub="10Y vs 2Y momentum"
          color={curveDir > 0 ? '#3b82f6' : '#ef4444'}
        />
        <StatCard
          label="HY Spreads"
          value={hy > 0 ? 'Widening' : 'Tightening'}
          sub={`20d avg Δ: ${hy > 0 ? '+' : ''}${(hy * 100).toFixed(3)}%`}
          color={hy > 0 ? '#ef4444' : '#22c55e'}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Rate Dynamics (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_10y" name="10Y Δ" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_2y" name="2Y Δ" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_hy_spread" name="HY Spread Δ" stroke="#ef4444" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — rates context
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
