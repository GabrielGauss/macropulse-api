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
  expansion:  { text: 'Expansion is typically a dollar-negative environment: global growth is strong, risk appetite is high, and capital flows into emerging markets and risk assets. The DXY weakens as investors rotate out of safe-haven USD into higher-yielding currencies.' },
  recovery:   { text: 'Recovery sees the dollar stabilise or weaken as the global cycle re-synchronises. EM currencies recover, carry trades re-engage, and commodity currencies outperform. The Fed is still on hold — rate differential does not yet favour USD.' },
  tightening: { text: 'Tightening is the most dollar-positive regime. The Fed hikes faster than peers, widening rate differentials in favour of USD. DXY rallies as capital repatriates to the US. EM FX and commodity currencies suffer the most under a strong dollar.' },
  risk_off:   { text: 'Risk-Off triggers a classic safe-haven dollar surge. Capital floods into USD as investors unwind carry trades and seek liquidity. JPY and CHF also benefit. Risk currencies (AUD, NZD, EM) sell off sharply. Dollar strength may be short-lived once the Fed pivots.' },
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

export default function FXView() {
  const [rangeDays, setRangeDays] = useState(90);
  const features = useFetch(useCallback(() => api.getFeatures(180), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    const slice = [...features.data].reverse().slice(-rangeDays);
    let cDxy = 0, c10y = 0;
    return slice.map(r => {
      cDxy += (r.d_dxy ?? 0);
      c10y += (r.d_10y ?? 0);
      return {
        time:  new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        cDxy:  +cDxy.toFixed(3),
        c10y:  +(c10y * 100).toFixed(2),
      };
    });
  }, [features.data, rangeDays]);

  const last = data[data.length - 1] ?? { cDxy: 0, c10y: 0 };

  const fxSignal = last.cDxy > 0 && last.c10y > 0
    ? 'USD Bullish'
    : last.cDxy < 0
      ? 'USD Bearish'
      : 'Neutral';
  const fxSignalColor = last.cDxy > 0 && last.c10y > 0
    ? '#f59e0b'
    : last.cDxy < 0
      ? '#3b82f6'
      : '#94a3b8';
  const fxSignalSub = regime.data?.macro_regime
    ? `${regime.data.macro_regime.replace('_', '-')} regime backdrop`
    : 'DXY + rate differential';

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
        <h2 className="text-[13px] font-semibold">FX & Dollar</h2>
        <span className="text-[10px] text-white/50 font-mono">Dollar index · rate differential · risk sentiment</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="US Dollar (DXY)"
          value={last.cDxy >= 0 ? 'Strengthening' : 'Weakening'}
          sub={`${last.cDxy >= 0 ? '+' : ''}${last.cDxy.toFixed(2)} pts (${rangeDays}d)`}
          color={last.cDxy > 0 ? '#f59e0b' : '#3b82f6'}
        />
        <StatCard
          label="Rate Differential"
          value={last.c10y >= 0 ? 'Supportive' : 'Headwind'}
          sub={`10Y ${last.c10y >= 0 ? '+' : ''}${last.c10y.toFixed(0)}bps`}
          color={last.c10y > 0 ? '#22c55e' : '#ef4444'}
        />
        <StatCard
          label="FX Signal"
          value={fxSignal}
          sub={fxSignalSub}
          color={fxSignalColor}
        />
      </div>

      <div className="card p-5">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
          <div>
            <div className="label">US Dollar Dynamics</div>
            <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>DXY cumulative change from window start</div>
          </div>
          <RangePicker value={rangeDays} onChange={setRangeDays} />
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="cDxy" name="DXY" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#f59e0b', borderRadius: 1 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>DXY</span>
          </div>
        </div>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: regimeCfg?.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: regimeCfg?.color }}>
              {regimeCfg?.label} regime · FX context
            </span>
          </div>
          <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', lineHeight: 1.7, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{ctx.text}</p>
        </div>
      )}
    </div>
  );
}
