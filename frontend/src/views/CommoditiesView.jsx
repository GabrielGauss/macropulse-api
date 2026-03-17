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
  expansion:  { text: 'Expansion drives commodity demand: oil rallies on global growth, industrial metals outperform. Gold consolidates as risk appetite is high and real yields stabilise. The dollar tends to weaken in late expansion, providing a tailwind for dollar-denominated commodities.' },
  recovery:   { text: 'Recovery is early-cycle for commodities. Oil begins to price in growth normalisation. Gold benefits from dollar weakness and declining real yields. Commodity producers (energy, materials) outperform broader equities as capex cycles restart.' },
  tightening: { text: 'Tightening crushes commodity demand expectations. A stronger dollar acts as a direct headwind to commodity prices. Oil falls on demand destruction fears. Gold underperforms as real yields rise — the cost of holding non-yielding assets increases.' },
  risk_off:   { text: 'Risk-Off creates bifurcation: Gold surges as a safe haven while oil collapses on demand destruction fears. The dollar strengthens as a safe-haven currency, weighing on commodity prices. Only precious metals and agricultural staples hold value.' },
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

export default function CommoditiesView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_oil: r.d_oil ?? 0,
      d_gold: r.d_gold ?? 0,
      d_dxy: r.d_dxy ?? 0,
    }));
  }, [features.data]);

  const avg20 = (col) => {
    if (!features.data) return 0;
    return features.data.slice(0, 20).reduce((s, r) => s + (r[col] ?? 0), 0) / 20;
  };

  const oilDir = avg20('d_oil');
  const goldDir = avg20('d_gold');
  const dxyDir = avg20('d_dxy');

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Commodities</h2>
        <span className="text-[10px] text-white/25 font-mono">Oil · Gold · Dollar headwind</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="Oil Momentum"
          value={oilDir > 0 ? 'Rallying' : 'Declining'}
          sub={`20d avg Δ: ${oilDir > 0 ? '+' : ''}${(oilDir * 100).toFixed(3)}%`}
          color={oilDir > 0 ? '#22c55e' : '#ef4444'}
        />
        <StatCard
          label="Gold Momentum"
          value={goldDir > 0 ? 'Rallying' : 'Declining'}
          sub={`20d avg Δ: ${goldDir > 0 ? '+' : ''}${(goldDir * 100).toFixed(3)}%`}
          color={goldDir > 0 ? '#f59e0b' : '#ef4444'}
        />
        <StatCard
          label="Dollar Headwind"
          value={dxyDir > 0 ? 'Strengthening' : 'Weakening'}
          sub={`DXY 20d avg Δ: ${dxyDir > 0 ? '+' : ''}${(dxyDir * 100).toFixed(3)}%`}
          color={dxyDir > 0 ? '#ef4444' : '#22c55e'}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Commodity Dynamics (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_oil" name="Oil Δ" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_gold" name="Gold Δ" stroke="#eab308" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_dxy" name="DXY Δ" stroke="#94a3b8" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — commodities context
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
