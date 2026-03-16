import React from 'react';

const SIGNALS = [
  {
    key: 'growth_momentum',
    label: 'Growth Momentum',
    desc: 'Yield curve slope momentum',
    positiveLabel: 'Steepening',
    negativeLabel: 'Flattening',
  },
  {
    key: 'inflation_momentum',
    label: 'Inflation Momentum',
    desc: '10Y yield rate-of-change',
    positiveLabel: 'Rising',
    negativeLabel: 'Falling',
  },
  {
    key: 'liquidity',
    label: 'Liquidity Expansion',
    desc: 'Net Fed liquidity vs 2yr avg',
    positiveLabel: 'Expanding',
    negativeLabel: 'Contracting',
  },
  {
    key: 'financial_stress',
    label: 'Financial Stress',
    desc: 'HY spreads + VIX (inverted)',
    positiveLabel: 'Calm',
    negativeLabel: 'Stressed',
  },
  {
    key: 'dollar_strength',
    label: 'Dollar Strength',
    desc: 'DXY 20-day momentum',
    positiveLabel: 'Strengthening',
    negativeLabel: 'Weakening',
  },
];

function signalColor(value) {
  if (value === null || value === undefined) return '#444';
  const abs = Math.abs(value);
  if (abs < 0.15) return 'rgba(255,255,255,0.3)';
  if (value > 0) return `rgba(34,197,94,${0.5 + abs * 0.5})`;
  return `rgba(239,68,68,${0.5 + abs * 0.5})`;
}

function GaugeBar({ value }) {
  // value is [-1, 1]
  const v = value ?? 0;
  const isPositive = v >= 0;
  const pct = Math.abs(v) * 50; // max 50% of half-bar

  return (
    <div className="relative h-1.5 rounded-full overflow-hidden" style={{ background: '#1a1a1a' }}>
      {/* Center line */}
      <div
        className="absolute top-0 bottom-0 w-px"
        style={{ left: '50%', background: '#333', transform: 'translateX(-50%)' }}
      />
      {/* Fill */}
      <div
        className="absolute top-0 bottom-0 transition-all duration-700"
        style={{
          width: `${pct}%`,
          left: isPositive ? '50%' : `${50 - pct}%`,
          background: signalColor(v),
          borderRadius: 2,
        }}
      />
    </div>
  );
}

function SignalRow({ signal, value }) {
  const v = value ?? null;
  const color = signalColor(v);
  const label =
    v === null ? '—'
    : Math.abs(v) < 0.15 ? 'Neutral'
    : v > 0 ? signal.positiveLabel
    : signal.negativeLabel;

  return (
    <div className="py-2.5 border-b border-[#1a1a1a] last:border-0">
      <div className="flex items-center justify-between mb-1.5">
        <div>
          <span className="text-[11px] text-white/60 font-mono">{signal.label}</span>
          <span className="ml-2 text-[9px] text-white/20 font-mono hidden sm:inline">{signal.desc}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
            {label}
          </span>
          <span
            className="font-mono text-[11px] font-semibold w-12 text-right"
            style={{ color }}
          >
            {v === null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2)}
          </span>
        </div>
      </div>
      <GaugeBar value={v} />
    </div>
  );
}

export default function SignalGauges({ data }) {
  if (!data) {
    return (
      <div className="card flex h-40 items-center justify-center">
        <p className="text-[11px] text-white/25 font-mono">Loading signals…</p>
      </div>
    );
  }

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-1">
        <div className="label">Macro Signals</div>
        <span className="text-[9px] text-white/15 font-mono">z-score · 252d window</span>
      </div>
      <div className="text-[9px] text-white/20 font-mono mb-3">
        20-day momentum normalized to ±1
      </div>
      <div>
        {SIGNALS.map((s) => (
          <SignalRow key={s.key} signal={s} value={data[s.key]} />
        ))}
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-2 text-[8px] font-mono text-white/15">
        <span>← −1.0 Bearish</span>
        <span>0</span>
        <span>Bullish +1.0 →</span>
      </div>
    </div>
  );
}
