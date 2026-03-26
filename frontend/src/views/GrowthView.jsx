import React, { useState, useCallback, useMemo } from 'react';
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';
import StatCard from '../components/StatCard';
import ChartTooltip from '../components/ChartTooltip';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };
const RANGE_OPTS = [{ l: '30d', v: 30 }, { l: '60d', v: 60 }, { l: '90d', v: 90 }, { l: '180d', v: 180 }];

const REGIME_CONTEXT = {
  expansion:  { text: 'Expansion is the strongest growth environment. Equities outperform, credit spreads compress, and the yield curve is positively sloped. Cyclicals and growth stocks lead. This is the regime where being fully invested is rewarded.' },
  recovery:   { text: 'Recovery signals a healing growth cycle. Equity momentum is positive but cautious — credit is normalising and liquidity is re-entering. Cyclical and value plays tend to outperform as the market reprices a soft-landing scenario.' },
  tightening: { text: 'Tightening constrains growth. Higher financing costs weigh on capex and consumption. Equity multiples compress as the discount rate rises. Defensives outperform cyclicals. Watch for yield curve inversion as a recession signal.' },
  risk_off:   { text: 'Risk-Off is a growth shock. Equities sell off sharply, credit spreads blow out, and growth expectations collapse. This is the regime where cash, Gold, and short-duration Treasuries preserve capital while equities and cyclicals suffer.' },
};

function RangePicker({ value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', borderRadius: 5, background: '#111', border: '1px solid #1a1a1a', padding: 2, gap: 2 }}>
      {RANGE_OPTS.map(({ l, v }) => {
        const active = value === v;
        return (
          <button key={v} onClick={() => onChange(v)}
            style={{ borderRadius: 4, padding: '2px 8px', fontFamily: 'JetBrains Mono', fontSize: 10, fontWeight: 500, cursor: 'pointer', border: 'none', background: active ? '#222' : 'transparent', color: active ? '#f0f0f0' : 'rgba(255,255,255,0.3)', transition: 'all 0.1s' }}>
            {l}
          </button>
        );
      })}
    </div>
  );
}

export default function GrowthView() {
  const [rangeDays, setRangeDays] = useState(90);
  const features = useFetch(useCallback(() => api.getFeatures(180), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    const slice = [...features.data].reverse().slice(-rangeDays);
    let logSP = 0, cCurve = 0;
    return slice.map(r => {
      logSP  += (r.d_sp500       ?? 0);
      cCurve += (r.d_yield_curve ?? 0);
      return {
        time:   new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        spIdx:  +(Math.exp(logSP) * 100).toFixed(2),
        cCurve: +(cCurve * 100).toFixed(2),
      };
    });
  }, [features.data, rangeDays]);

  const last = data[data.length - 1] ?? { spIdx: 100, cCurve: 0 };

  const avg20sp = useMemo(() => {
    if (!features.data) return 0;
    return features.data.slice(0, 20).reduce((s, r) => s + (r.d_sp500 ?? 0), 0) / 20;
  }, [features.data]);

  const growthSignal = avg20sp > 0.001 ? 'Accelerating' : avg20sp < -0.001 ? 'Decelerating' : 'Neutral';
  const growthColor = avg20sp > 0.001 ? '#22c55e' : avg20sp < -0.001 ? '#ef4444' : '#94a3b8';

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  if (features.loading) return (
    <div className="card p-5"><div className="animate-pulse space-y-3">
      {[1,2,3].map(i => <div key={i} style={{height: 60, background: 'rgba(255,255,255,0.03)', borderRadius: 6}} />)}
    </div></div>
  );
  if (features.error) return (
    <div className="card p-5 flex items-center justify-center" style={{height: 200}}>
      <span style={{fontSize: 11, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.2)'}}>Features unavailable — requires Starter or Pro plan</span>
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Growth Signals</h2>
        <span className="text-[10px] text-white/50 font-mono">Equity momentum · yield curve · liquidity support</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="S&P 500 Return"
          value={last.spIdx >= 100 ? 'Gaining' : 'Declining'}
          sub={`${last.spIdx >= 100 ? '+' : ''}${(last.spIdx - 100).toFixed(1)}% (${rangeDays}d)`}
          color={last.spIdx >= 100 ? '#22c55e' : '#ef4444'}
        />
        <StatCard
          label="Yield Curve"
          value={last.cCurve >= 0 ? 'Steepening' : 'Flattening'}
          sub={`${last.cCurve >= 0 ? '+' : ''}${last.cCurve.toFixed(0)}bps (${rangeDays}d)`}
          color={last.cCurve >= 0 ? '#3b82f6' : '#f59e0b'}
        />
        <StatCard
          label="Growth Signal"
          value={growthSignal}
          sub="20d momentum signal"
          color={growthColor}
        />
      </div>

      <div className="card p-5">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
          <div>
            <div className="label">Growth Indicators</div>
            <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>S&P 500 rebased to 100 · yield curve in bps</div>
          </div>
          <RangePicker value={rangeDays} onChange={setRangeDays} />
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <defs>
              <linearGradient id="spGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={v => `${v >= 100 ? '+' : ''}${(v - 100).toFixed(0)}%`} />
            <ReferenceLine y={100} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Area type="monotone" dataKey="spIdx" name="S&P 500" stroke="#22c55e" strokeWidth={1.5} fill="url(#spGradient)" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#22c55e', borderRadius: 1 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>S&P 500</span>
          </div>
        </div>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: regimeCfg?.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: regimeCfg?.color }}>
              {regimeCfg?.label} regime · growth context
            </span>
          </div>
          <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', lineHeight: 1.7, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{ctx.text}</p>
        </div>
      )}
    </div>
  );
}
