import React from 'react';
import { useGuideMode } from '../lib/guideMode';

const SIGNALS = [
  {
    key: 'growth_momentum',
    label: 'Growth Momentum',
    desc: 'Yield curve slope momentum',
    positiveLabel: 'Steepening',
    negativeLabel: 'Flattening',
    guide: 'Measures the rate of change in the 2s10s yield curve slope. Steepening = market pricing in stronger future growth.',
  },
  {
    key: 'inflation_momentum',
    label: 'Inflation Momentum',
    desc: '10Y yield rate-of-change',
    positiveLabel: 'Rising',
    negativeLabel: 'Falling',
    guide: '20-day momentum of the 10Y Treasury yield. Rising = inflation expectations re-accelerating, increasing rate risk.',
  },
  {
    key: 'liquidity',
    label: 'Liquidity Expansion',
    desc: 'Net Fed liquidity vs 2yr avg',
    positiveLabel: 'Expanding',
    negativeLabel: 'Contracting',
    guide: 'Fed reserves + RRP drawdown − TGA balance, z-scored vs 2-year history. Expanding = system awash with liquidity, risk-asset tailwind.',
  },
  {
    key: 'financial_stress',
    label: 'Financial Stress',
    desc: 'HY spreads + VIX (inverted)',
    positiveLabel: 'Calm',
    negativeLabel: 'Stressed',
    guide: 'Composite of HY credit spreads and VIX, inverted so positive = calm. Negative readings signal credit/vol stress.',
  },
  {
    key: 'dollar_strength',
    label: 'Dollar Strength',
    desc: 'DXY 20-day momentum',
    positiveLabel: 'Strengthening',
    negativeLabel: 'Weakening',
    guide: 'DXY 20-day rate-of-change, z-scored. Strong dollar is a headwind for commodities, EM assets, and risk appetite.',
  },
];

function signalColor(value) {
  if (value === null || value === undefined) return '#444';
  const abs = Math.abs(value);
  if (abs < 0.15) return 'rgba(255,255,255,0.3)';
  if (value > 0) return `rgba(34,197,94,${0.5 + abs * 0.5})`;
  return `rgba(239,68,68,${0.5 + abs * 0.5})`;
}

function signalGradient(value) {
  if (value === null || value === undefined) return '#333';
  const abs = Math.abs(value);
  if (abs < 0.15) return 'rgba(255,255,255,0.15)';
  const alpha1 = Math.min(0.9, 0.4 + abs * 0.6);
  const alpha2 = Math.min(0.5, 0.2 + abs * 0.4);
  if (value > 0) return `linear-gradient(90deg, rgba(34,197,94,${alpha2}), rgba(34,197,94,${alpha1}))`;
  return `linear-gradient(90deg, rgba(239,68,68,${alpha1}), rgba(239,68,68,${alpha2}))`;
}

function GaugeBar({ value }) {
  const v = value ?? 0;
  const isPositive = v >= 0;
  const abs = Math.abs(v);
  const pct = abs * 50; // max 50% of half-bar

  return (
    <div className="relative rounded-full overflow-hidden" style={{ height: 6, background: '#111' }}>
      {/* Track ticks */}
      <div className="absolute top-0 bottom-0 w-px" style={{ left: '25%', background: '#1a1a1a' }} />
      <div className="absolute top-0 bottom-0 w-px" style={{ left: '75%', background: '#1a1a1a' }} />
      {/* Center line */}
      <div
        className="absolute top-0 bottom-0"
        style={{ left: '50%', width: 1, background: '#2a2a2a', transform: 'translateX(-50%)', zIndex: 2 }}
      />
      {/* Fill with gradient */}
      <div
        className="absolute top-0 bottom-0 transition-all duration-700"
        style={{
          width: `${pct}%`,
          left: isPositive ? '50%' : `${50 - pct}%`,
          background: signalGradient(v),
          borderRadius: 3,
        }}
      />
      {/* Glow cap at the tip */}
      {abs > 0.15 && (
        <div
          className="absolute top-0 bottom-0 transition-all duration-700"
          style={{
            width: 3,
            left: isPositive ? `${50 + pct}%` : `${50 - pct}%`,
            background: signalColor(v),
            borderRadius: 2,
            filter: `blur(1px)`,
            transform: isPositive ? 'translateX(-100%)' : 'none',
          }}
        />
      )}
    </div>
  );
}

function SignalRow({ signal, value, rank }) {
  const v = value ?? null;
  const color = signalColor(v);
  const abs = v !== null ? Math.abs(v) : 0;
  const label =
    v === null ? '—'
    : abs < 0.15 ? 'Neutral'
    : v > 0 ? signal.positiveLabel
    : signal.negativeLabel;
  const guideMode = useGuideMode();

  return (
    <div className="py-2.5 border-b border-[#151515] last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Rank dot — brightest = strongest signal */}
          <div
            className="flex-shrink-0 rounded-sm"
            style={{
              width: 3,
              height: 3,
              background: v !== null && abs > 0.15 ? color : '#2a2a2a',
              opacity: v !== null ? 0.4 + abs * 0.6 : 0.2,
            }}
          />
          <span className="text-[11px] text-white/60 font-mono">{signal.label}</span>
          <span className="text-[10px] text-white/45 font-mono hidden sm:inline">{signal.desc}</span>
        </div>
        <div className="flex items-center gap-2.5">
          <span
            className="text-[10px] font-mono px-1.5 py-0.5 rounded"
            style={{
              color: v !== null && abs >= 0.15 ? color : 'rgba(255,255,255,0.45)',
              background: v !== null && abs >= 0.15 ? (v > 0 ? 'rgba(34,197,94,0.07)' : 'rgba(239,68,68,0.07)') : 'transparent',
            }}
          >
            {label}
          </span>
          <span
            className="font-mono text-[12px] font-semibold w-12 text-right tabular-nums"
            style={{ color }}
          >
            {v === null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(2)}
          </span>
        </div>
      </div>
      <GaugeBar value={v} />
      {guideMode && signal.guide && (
        <div style={{ fontSize: 9, color: 'rgba(59,130,246,0.6)', fontFamily: 'JetBrains Mono, monospace', marginTop: 5, lineHeight: 1.5 }}>
          {signal.guide}
        </div>
      )}
    </div>
  );
}

export default function SignalGauges({ data }) {
  const guideMode = useGuideMode();

  if (!data) {
    return (
      <div className="card flex h-40 items-center justify-center">
        <p className="text-[11px] text-white/45 font-mono">Loading signals…</p>
      </div>
    );
  }

  // Sort by absolute magnitude (strongest signal first)
  const sorted = [...SIGNALS].sort((a, b) => {
    const va = Math.abs(data[a.key] ?? 0);
    const vb = Math.abs(data[b.key] ?? 0);
    return vb - va;
  });

  // Composite signal: average of all values (positive = risk-on)
  const values = SIGNALS.map(s => data[s.key] ?? 0);
  const composite = values.reduce((a, b) => a + b, 0) / values.length;

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-1">
        <div className="label">Macro Signals</div>
        <div className="flex items-center gap-3">
          <span
            className="font-mono text-[11px] font-semibold"
            style={{ color: signalColor(composite) }}
          >
            {composite >= 0 ? '+' : ''}{composite.toFixed(2)} composite
          </span>
          <span className="text-[10px] text-white/45 font-mono">z-score · 252d</span>
        </div>
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 4, marginBottom: 8, lineHeight: 1.5 }}>
          Five macro factors, each normalized to ±1 via z-score over a 252-day rolling window. Sorted strongest → weakest. Green = risk-on, red = risk-off.
        </div>
      )}
      {!guideMode && (
        <div className="text-[10px] text-white/45 font-mono mb-3">
          sorted by signal strength · 20d momentum
        </div>
      )}
      <div>
        {sorted.map((s, i) => (
          <SignalRow key={s.key} signal={s} value={data[s.key]} rank={i} />
        ))}
      </div>

      {/* Scale labels */}
      <div className="flex justify-between mt-3 text-[10px] font-mono text-white/45">
        <span>← Bearish −1.0</span>
        <span>·</span>
        <span>Neutral</span>
        <span>·</span>
        <span>Bullish +1.0 →</span>
      </div>
    </div>
  );
}
