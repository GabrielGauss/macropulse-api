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
  expansion:  { text: 'Expansion is crypto-positive: global liquidity is ample, risk appetite is high, and speculative capital flows into digital assets. BTC and ETH tend to outperform in late expansion as the risk-on trade extends. Altcoins outperform majors in this regime.' },
  recovery:   { text: 'Recovery marks the re-entry window for crypto. Liquidity is returning, the risk-off shock is unwinding, and BTC typically leads the rebound. This is historically the regime with the highest BTC forward returns as capital reprices the macro trajectory.' },
  tightening: { text: 'Tightening is the harshest regime for crypto. Rising real yields increase the opportunity cost of holding non-yielding digital assets. Liquidity drains from the system. BTC tends to de-rate alongside NASDAQ. Leverage is punished; spot holders survive.' },
  risk_off:   { text: 'Risk-Off creates intense crypto selling pressure. Digital assets are treated as high-beta risk assets, not as safe havens. BTC correlation with equities spikes. Liquidity evaporates. However, the regime tends to be short — the recovery phase that follows is powerful.' },
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

export default function CryptoView() {
  const [rangeDays, setRangeDays] = useState(90);
  const features = useFetch(useCallback(() => api.getFeatures(180), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const hasCryptoData = useMemo(() =>
    features.data?.some(r => Math.abs(r.d_btc ?? 0) > 1e-6 || Math.abs(r.d_eth ?? 0) > 1e-6),
    [features.data]
  );

  const data = useMemo(() => {
    if (!features.data) return [];
    const slice = [...features.data].reverse().slice(-rangeDays);
    let logBtc = 0, logEth = 0;
    return slice.map(r => {
      logBtc += (r.d_btc ?? 0);
      logEth += (r.d_eth ?? 0);
      return {
        time:   new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        btcIdx: +(Math.exp(logBtc) * 100).toFixed(2),
        ethIdx: +(Math.exp(logEth) * 100).toFixed(2),
      };
    });
  }, [features.data, rangeDays]);

  const last = data[data.length - 1] ?? { btcIdx: 100, ethIdx: 100 };

  const liquidityNet = useMemo(() =>
    features.data?.slice(0, 20).reduce((s, r) => s + (r.d_liquidity ?? 0), 0) ?? 0,
    [features.data]
  );

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
        <h2 className="text-[13px] font-semibold">Crypto</h2>
        <span className="text-[10px] text-white/50 font-mono">BTC · ETH · liquidity backdrop</span>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {hasCryptoData ? (
          <>
            <StatCard
              label="Bitcoin"
              value={last.btcIdx >= 100 ? 'Gaining' : 'Declining'}
              sub={`${last.btcIdx >= 100 ? '+' : ''}${(last.btcIdx - 100).toFixed(1)}% (${rangeDays}d)`}
              color={last.btcIdx >= 100 ? '#f59e0b' : '#ef4444'}
            />
            <StatCard
              label="Ethereum"
              value={last.ethIdx >= 100 ? 'Gaining' : 'Declining'}
              sub={`${last.ethIdx >= 100 ? '+' : ''}${(last.ethIdx - 100).toFixed(1)}% (${rangeDays}d)`}
              color={last.ethIdx >= 100 ? '#3b82f6' : '#ef4444'}
            />
            <StatCard
              label="Liquidity"
              value={liquidityNet > 0 ? 'Expanding' : 'Contracting'}
              sub={`20d net: ${liquidityNet > 0 ? '+' : ''}$${(liquidityNet / 1e6).toFixed(1)}T`}
              color={liquidityNet > 0 ? '#22c55e' : '#ef4444'}
            />
          </>
        ) : (
          <>
            <StatCard label="Bitcoin" value="No data" sub="BTC/ETH data pending — run pipeline to populate" color="#94a3b8" />
            <StatCard label="Ethereum" value="No data" sub="BTC/ETH data pending — run pipeline to populate" color="#94a3b8" />
            <StatCard
              label="Liquidity"
              value={liquidityNet > 0 ? 'Expanding' : 'Contracting'}
              sub={`20d net: ${liquidityNet > 0 ? '+' : ''}$${(liquidityNet / 1e6).toFixed(1)}T`}
              color={liquidityNet > 0 ? '#22c55e' : '#ef4444'}
            />
          </>
        )}
      </div>

      {hasCryptoData ? (
        <div className="card p-5">
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
            <div>
              <div className="label">Crypto Returns</div>
              <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>rebased to 100 at window start</div>
            </div>
            <RangePicker value={rangeDays} onChange={setRangeDays} />
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={v => `${v >= 100 ? '+' : ''}${(v - 100).toFixed(0)}%`} />
              <ReferenceLine y={100} stroke="rgba(255,255,255,0.08)" />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
              <Line type="monotone" dataKey="btcIdx" name="Bitcoin" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
              <Line type="monotone" dataKey="ethIdx" name="Ethereum" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 16, height: 2, background: '#f59e0b', borderRadius: 1 }} />
              <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>Bitcoin</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 16, height: 2, background: '#3b82f6', borderRadius: 1 }} />
              <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>Ethereum</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-5" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 8 }}>
            <div className="label">Crypto Returns</div>
            <RangePicker value={rangeDays} onChange={setRangeDays} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 140 }}>
            <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)', lineHeight: 1.7, textAlign: 'center', maxWidth: 420, margin: 0 }}>
              Crypto data is not yet available. The pipeline needs to run once after the BTC/ETH columns were added. It will auto-populate at 18:30 UTC.
            </p>
          </div>
        </div>
      )}

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: regimeCfg?.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: regimeCfg?.color }}>
              {regimeCfg?.label} regime · crypto context
            </span>
          </div>
          <p style={{ fontSize: 11, fontFamily: 'JetBrains Mono', lineHeight: 1.7, color: 'rgba(255,255,255,0.45)', margin: 0 }}>{ctx.text}</p>
        </div>
      )}
    </div>
  );
}
