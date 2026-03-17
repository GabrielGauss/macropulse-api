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
  expansion:  { text: 'Expansion is crypto-positive: global liquidity is ample, risk appetite is high, and speculative capital flows into digital assets. BTC and ETH tend to outperform in late expansion as the risk-on trade extends. Altcoins outperform majors in this regime.' },
  recovery:   { text: 'Recovery marks the re-entry window for crypto. Liquidity is returning, the risk-off shock is unwinding, and BTC typically leads the rebound. This is historically the regime with the highest BTC forward returns as capital reprices the macro trajectory.' },
  tightening: { text: 'Tightening is the harshest regime for crypto. Rising real yields increase the opportunity cost of holding non-yielding digital assets. Liquidity drains from the system. BTC tends to de-rate alongside NASDAQ. Leverage is punished; spot holders survive.' },
  risk_off:   { text: 'Risk-Off creates intense crypto selling pressure. Digital assets are treated as high-beta risk assets, not as safe havens. BTC correlation with equities spikes. Liquidity evaporates. However, the regime tends to be short — the recovery phase that follows is powerful.' },
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

export default function CryptoView() {
  const features = useFetch(useCallback(() => api.getFeatures(120), []));
  const regime = useFetch(useCallback(() => api.getCurrentRegime(), []));

  const data = useMemo(() => {
    if (!features.data) return [];
    return [...features.data].reverse().map((r) => ({
      time: new Date(r.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      d_btc: r.d_btc ?? 0,
      d_eth: r.d_eth ?? 0,
    }));
  }, [features.data]);

  const avg20 = (col) => {
    if (!features.data) return 0;
    return features.data.slice(0, 20).reduce((s, r) => s + (r[col] ?? 0), 0) / 20;
  };

  const btcDir = avg20('d_btc');
  const ethDir = avg20('d_eth');
  const liquidityNet = features.data?.slice(0, 20).reduce((s, r) => s + (r.d_liquidity ?? 0), 0) ?? 0;

  const regimeCfg = regime.data ? REGIME_CONFIG[regime.data.macro_regime] : null;
  const ctx = regime.data ? REGIME_CONTEXT[regime.data.macro_regime] : null;

  // Check if crypto data is available (non-zero)
  const hasCryptoData = features.data?.some(r => r.d_btc !== 0 || r.d_eth !== 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Crypto</h2>
        <span className="text-[10px] text-white/25 font-mono">BTC · ETH · liquidity backdrop</span>
      </div>

      {!hasCryptoData && features.data && (
        <div className="card p-4" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
          <p className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.3)' }}>
            BTC/ETH data is being ingested. Charts will populate after the next daily pipeline run.
          </p>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <StatCard
          label="BTC Momentum"
          value={btcDir > 0 ? 'Positive' : btcDir < 0 ? 'Negative' : 'No data'}
          sub={hasCryptoData ? `20d avg Δ: ${btcDir > 0 ? '+' : ''}${(btcDir * 100).toFixed(3)}%` : 'Awaiting ingestion'}
          color={btcDir > 0 ? '#f59e0b' : btcDir < 0 ? '#ef4444' : '#94a3b8'}
        />
        <StatCard
          label="ETH Momentum"
          value={ethDir > 0 ? 'Positive' : ethDir < 0 ? 'Negative' : 'No data'}
          sub={hasCryptoData ? `20d avg Δ: ${ethDir > 0 ? '+' : ''}${(ethDir * 100).toFixed(3)}%` : 'Awaiting ingestion'}
          color={ethDir > 0 ? '#3b82f6' : ethDir < 0 ? '#ef4444' : '#94a3b8'}
        />
        <StatCard
          label="Liquidity Backdrop"
          value={liquidityNet > 0 ? 'Expanding' : 'Contracting'}
          sub={`20d net: ${liquidityNet > 0 ? '+' : ''}$${(liquidityNet / 1e6).toFixed(1)}T`}
          color={liquidityNet > 0 ? '#22c55e' : '#ef4444'}
        />
      </div>

      <div className="card p-5">
        <div className="label mb-4">Crypto Returns (120 days)</div>
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis dataKey="time" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(2)}%`} />
            <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="d_btc" name="BTC Δ" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="d_eth" name="ETH Δ" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {ctx && (
        <div className="card p-4" style={{ borderColor: `${regimeCfg?.color}22` }}>
          <div className="flex items-center gap-2 mb-2">
            <div className="h-1.5 w-1.5 rounded-full" style={{ background: regimeCfg?.color }} />
            <span className="text-[10px] font-mono uppercase tracking-wide" style={{ color: regimeCfg?.color }}>
              {regimeCfg?.label} regime — crypto context
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
