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
  expansion:  { text: 'Expansion is typically a dollar-negative environment: global growth is strong, risk appetite is high, and capital flows into emerging markets and risk assets. The DXY weakens as investors rotate out of safe-haven USD into higher-yielding currencies.' },
  recovery:   { text: 'Recovery sees the dollar stabilise or weaken as the global cycle re-synchronises. EM currencies recover, carry trades re-engage, and commodity currencies outperform. The Fed is still on hold — rate differential does not yet favour USD.' },
  tightening: { text: 'Tightening is the most dollar-positive regime. The Fed hikes faster than peers, widening rate differentials in favour of USD. DXY rallies as capital repatriates to the US. EM FX and commodity currencies suffer the most under a strong dollar.' },
  risk_off:   { text: 'Risk-Off triggers a classic safe-haven dollar surge. Capital floods into USD as investors unwind carry trades and seek liquidity. JPY and CHF also benefit. Risk currencies (AUD, NZD, EM) sell off sharply. Dollar strength may be short-lived once the Fed pivots.' },
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

export default function FXView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_dxy: r.d_dxy ?? 0,
      d_10y: r.d_10y ?? 0,
    }));
  }, [features.data]);

  const avg20 = (col) => {
    if (!features.data) return 0;
    return features.data.slice(0, 20).reduce((s, r) => s + (r[col] ?? 0), 0) / 20;
  };

  const dxyDir = avg20('d_dxy');
  const rateDir = avg20('d_10y');
  // Rate differential proxy: rising 10Y with strong DXY = USD bullish
  const differentialBias = dxyDir > 0 && rateDir > 0 ? 'Bullish USD' : dxyDir < 0 ? 'Bearish USD' : 'Neutral';
  const differentialColor = dxyDir > 0 && rateDir > 0 ? '#f59e0b' : dxyDir < 0 ? '#3b82f6' : '#94a3b8';

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">FX & Dollar</h2>
        <span className="text-[10px] text-white/25 font-mono">Dollar index · rate differential · risk sentiment</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="Dollar Trend"
          value={dxyDir > 0 ? 'Strengthening' : 'Weakening'}
          sub={`DXY 20d avg Δ: ${dxyDir > 0 ? '+' : ''}${(dxyDir * 100).toFixed(3)}%`}
          color={dxyDir > 0 ? '#f59e0b' : '#3b82f6'}
        />
        <StatCard
          label="Rate Pressure"
          value={rateDir > 0 ? 'Rising yields' : 'Falling yields'}
          sub={`10Y 20d avg Δ: ${rateDir > 0 ? '+' : ''}${(rateDir * 100).toFixed(3)}%`}
          color={rateDir > 0 ? '#f59e0b' : '#22c55e'}
        />
        <StatCard
          label="Rate Differential"
          value={differentialBias}
          sub="DXY vs 10Y momentum"
          color={differentialColor}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Dollar & Rate Dynamics (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_dxy" name="DXY Δ" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_10y" name="10Y Δ" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — FX context
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
