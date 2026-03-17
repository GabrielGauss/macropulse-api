import React, { useState, useCallback, useMemo } from 'react';
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip,
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
  expansion:  { text: 'Expansion regimes typically feature stable or falling long-end yields as liquidity is ample. Inflation expectations are moderate — the economy grows without overheating. Bonds and TIPS perform well in early expansion; Gold holds steady.' },
  recovery:   { text: 'Recovery phases show rising inflation expectations as liquidity re-enters the system. The yield curve steepens as 10Y sells off faster than 2Y. Watch for breakeven inflation widening — the first sign of transition to tightening.' },
  tightening: { text: 'Tightening regimes are defined by rising yields and flattening or inverted curves as the Fed hikes rates to fight inflation. Real yields rise, pressuring Gold and long-duration bonds. Credit spreads widen as financing conditions deteriorate.' },
  risk_off:   { text: 'Risk-Off environments see a flight to safety: 10Y yields fall sharply as capital floods into Treasuries. The curve flattens or inverts. TIPS spreads widen briefly before collapsing. Gold surges as a safe haven.' },
};

function RangePicker({ value, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', borderRadius: 5, background: '#111', border: '1px solid #1f1f1f', padding: 2, gap: 2 }}>
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

export default function InflationView() {
  const [rangeDays, setRangeDays] = useState(90);
  const features = useFetch(useCallback(() => api.getFeatures(180), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    const slice = [...features.data].reverse().slice(-rangeDays);
    let c10y = 0, cCurve = 0, cHY = 0;
    return slice.map(r => {
      c10y   += (r.d_10y        ?? 0);
      cCurve += (r.d_yield_curve ?? 0);
      cHY    += (r.d_hy_spread   ?? 0);
      return {
        time:   new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        c10y:   +(c10y   * 100).toFixed(2),
        cCurve: +(cCurve * 100).toFixed(2),
        cHY:    +(cHY    * 100).toFixed(2),
      };
    });
  }, [features.data, rangeDays]);

  const last = data[data.length - 1] ?? { c10y: 0, cCurve: 0, cHY: 0 };

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
        <h2 className="text-[13px] font-semibold">Inflation Dynamics</h2>
        <span className="text-[10px] text-white/25 font-mono">Rate pressure · yield curve · credit conditions</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="10Y Yield"
          value={last.c10y >= 0 ? 'Rising' : 'Falling'}
          sub={`${last.c10y >= 0 ? '+' : ''}${last.c10y.toFixed(0)}bps (${rangeDays}d)`}
          color={last.c10y > 0 ? '#f59e0b' : '#22c55e'}
        />
        <StatCard
          label="Yield Curve"
          value={last.cCurve >= 0 ? 'Steepening' : 'Flattening'}
          sub={`${last.cCurve >= 0 ? '+' : ''}${last.cCurve.toFixed(0)}bps (${rangeDays}d)`}
          color={last.cCurve > 0 ? '#3b82f6' : '#ef4444'}
        />
        <StatCard
          label="HY Spreads"
          value={last.cHY > 0 ? 'Widening' : 'Tightening'}
          sub={`${last.cHY >= 0 ? '+' : ''}${last.cHY.toFixed(0)}bps (${rangeDays}d)`}
          color={last.cHY > 0 ? '#ef4444' : '#22c55e'}
        />
      </div>

      <div className="card p-5">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
          <div>
            <div className="label">Rate Dynamics</div>
            <div style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.2)', marginTop: 2 }}>cumulative change from window start · basis points</div>
          </div>
          <RangePicker value={rangeDays} onChange={setRangeDays} />
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={v => `${v >= 0 ? '+' : ''}${v.toFixed(0)}bps`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="c10y" name="10Y Yield" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="cCurve" name="Yield Curve" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#f59e0b', borderRadius: 1 }} />
            <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.3)' }}>10Y Yield</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#3b82f6', borderRadius: 1 }} />
            <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.3)' }}>Yield Curve</span>
          </div>
        </div>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: regimeCfg?.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: regimeCfg?.color }}>
              {regimeCfg?.label} regime · inflation context
            </span>
          </div>
          <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', lineHeight: 1.7, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{ctx.text}</p>
        </div>
      )}
    </div>
  );
}
