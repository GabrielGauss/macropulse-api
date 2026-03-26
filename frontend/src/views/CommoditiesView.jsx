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
  expansion:  { text: 'Expansion drives commodity demand: oil rallies on global growth, industrial metals outperform. Gold consolidates as risk appetite is high and real yields stabilise. The dollar tends to weaken in late expansion, providing a tailwind for dollar-denominated commodities.' },
  recovery:   { text: 'Recovery is early-cycle for commodities. Oil begins to price in growth normalisation. Gold benefits from dollar weakness and declining real yields. Commodity producers (energy, materials) outperform broader equities as capex cycles restart.' },
  tightening: { text: 'Tightening crushes commodity demand expectations. A stronger dollar acts as a direct headwind to commodity prices. Oil falls on demand destruction fears. Gold underperforms as real yields rise — the cost of holding non-yielding assets increases.' },
  risk_off:   { text: 'Risk-Off creates bifurcation: Gold surges as a safe haven while oil collapses on demand destruction fears. The dollar strengthens as a safe-haven currency, weighing on commodity prices. Only precious metals and agricultural staples hold value.' },
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

export default function CommoditiesView() {
  const [rangeDays, setRangeDays] = useState(90);
  const features = useFetch(useCallback(() => api.getFeatures(180), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    const slice = [...features.data].reverse().slice(-rangeDays);
    let logOil = 0, logGold = 0;
    return slice.map(r => {
      logOil  += (r.d_oil  ?? 0);
      logGold += (r.d_gold ?? 0);
      return {
        time:    new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        oilIdx:  +(Math.exp(logOil)  * 100).toFixed(2),
        goldIdx: +(Math.exp(logGold) * 100).toFixed(2),
      };
    });
  }, [features.data, rangeDays]);

  const cDxy = useMemo(() => {
    if (!features.data) return 0;
    return [...features.data].reverse().slice(-rangeDays).reduce((s, r) => s + (r.d_dxy ?? 0), 0);
  }, [features.data, rangeDays]);

  const last = data[data.length - 1] ?? { oilIdx: 100, goldIdx: 100 };

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
        <h2 className="text-[13px] font-semibold">Commodities</h2>
        <span className="text-[10px] text-white/50 font-mono">Oil · Gold · Dollar headwind</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="Gold"
          value={last.goldIdx >= 100 ? 'Gaining' : 'Declining'}
          sub={`${last.goldIdx >= 100 ? '+' : ''}${(last.goldIdx - 100).toFixed(1)}% (${rangeDays}d)`}
          color={last.goldIdx >= 100 ? '#f59e0b' : '#ef4444'}
        />
        <StatCard
          label="Oil"
          value={last.oilIdx >= 100 ? 'Gaining' : 'Declining'}
          sub={`${last.oilIdx >= 100 ? '+' : ''}${(last.oilIdx - 100).toFixed(1)}% (${rangeDays}d)`}
          color={last.oilIdx >= 100 ? '#22c55e' : '#ef4444'}
        />
        <StatCard
          label="USD Headwind"
          value={cDxy > 0 ? 'Strengthening' : 'Weakening'}
          sub={`DXY ${cDxy >= 0 ? '+' : ''}${cDxy.toFixed(1)} pts (${rangeDays}d)`}
          color={cDxy > 0 ? '#f59e0b' : '#22c55e'}
        />
      </div>

      <div className="card p-5">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
          <div>
            <div className="label">Commodities</div>
            <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>rebased to 100 at window start</div>
          </div>
          <RangePicker value={rangeDays} onChange={setRangeDays} />
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <defs>
              <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={v => `${v >= 100 ? '+' : ''}${(v - 100).toFixed(0)}%`} />
            <ReferenceLine y={100} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Area type="monotone" dataKey="goldIdx" name="Gold" stroke="#f59e0b" strokeWidth={1.5} fill="url(#goldGradient)" dot={false} />
            <Line type="monotone" dataKey="oilIdx" name="Oil" stroke="#22c55e" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#f59e0b', borderRadius: 1 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>Gold</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 16, height: 2, background: '#22c55e', borderRadius: 1 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>Oil</span>
          </div>
        </div>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: regimeCfg?.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: regimeCfg?.color }}>
              {regimeCfg?.label} regime · commodities context
            </span>
          </div>
          <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', lineHeight: 1.7, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{ctx.text}</p>
        </div>
      )}
    </div>
  );
}
