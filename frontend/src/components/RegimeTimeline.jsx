import React from 'react';
import {
  ComposedChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, ReferenceArea,
} from 'recharts';
import { REGIME_CONFIG, formatDateShort } from '../lib/utils';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

function Tooltip_({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const cfg = REGIME_CONFIG[d.regime] || {};
  return (
    <div
      style={{
        background: '#141414',
        border: '1px solid #2a2a2a',
        borderRadius: 6,
        padding: '8px 12px',
        fontSize: 11,
        fontFamily: 'JetBrains Mono, monospace',
      }}
    >
      <div style={{ color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>
        {formatDateShort(d.timestamp)}
      </div>
      <div style={{ color: cfg.color || '#fff', fontWeight: 600 }}>
        {cfg.label || d.regime}
      </div>
      <div style={{ color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>
        Risk score: {d.risk_score > 0 ? '+' : ''}{d.risk_score?.toFixed(1)}
      </div>
    </div>
  );
}

function buildBands(data) {
  if (!data.length) return [];
  const bands = [];
  let start = data[0];
  let current = data[0].regime;

  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== current) {
      bands.push({ regime: current, x1: start.timestamp, x2: data[i - 1].timestamp });
      start = data[i];
      current = data[i].regime;
    }
  }
  bands.push({ regime: current, x1: start.timestamp, x2: data[data.length - 1].timestamp });
  return bands;
}

const TIME_OPTIONS = [
  { label: '1M', days: 30  },
  { label: '3M', days: 90  },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
];

export default function RegimeTimeline({
  history,
  historyDays = 90,
  onHistoryDaysChange,
  isFree = false,
}) {
  if (!history || history.length === 0) {
    return (
      <div className="card flex h-72 items-center justify-center">
        <p className="text-[11px] text-white/25 font-mono">No history data</p>
      </div>
    );
  }

  const data = [...history].reverse().map((r) => ({
    timestamp: r.timestamp,
    risk_score: r.risk_score,
    regime: r.macro_regime,
  }));

  const bands = buildBands(data);

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-4">
        <div className="label">Risk Score Timeline</div>

        <div className="flex items-center gap-2">
          {/* Regime legend */}
          <div className="hidden sm:flex items-center gap-3 mr-3">
            {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
              <div key={key} className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 rounded-sm flex-shrink-0" style={{ background: cfg.color }} />
                <span className="text-[9px] text-white/25 font-mono uppercase">{cfg.short}</span>
              </div>
            ))}
          </div>

          {/* Free tier — upgrade nudge instead of range picker */}
          {isFree && (
            <a
              href="https://macropulse.live/#pricing"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[9px] font-mono transition-colors"
              style={{ color: 'rgba(255,255,255,0.2)', textDecoration: 'none' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.2)'; }}
              title="Upgrade for full 2-year history"
            >
              30d · <span style={{ textDecoration: 'underline' }}>upgrade for 2Y →</span>
            </a>
          )}

          {/* Time filter pills (Starter / Pro only) */}
          {!isFree && <div
            className="flex items-center rounded"
            style={{ background: '#111', border: '1px solid #1f1f1f', padding: 2, gap: 2 }}
          >
            {TIME_OPTIONS.map(({ label, days }) => {
              const active = historyDays === days;
              return (
                <button
                  key={label}
                  onClick={() => onHistoryDaysChange?.(days)}
                  className="rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-colors duration-100"
                  style={{
                    background: active ? '#222' : 'transparent',
                    color: active ? '#f0f0f0' : 'rgba(255,255,255,0.3)',
                    cursor: 'pointer',
                    border: 'none',
                  }}
                  onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.6)'; }}
                  onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.3)'; }}
                >
                  {label}
                </button>
              );
            })}
          </div>}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
          <CartesianGrid
            stroke="rgba(255,255,255,0.03)"
            horizontal vertical={false}
          />

          {bands.map((b, i) => {
            const cfg = REGIME_CONFIG[b.regime];
            return (
              <ReferenceArea
                key={i}
                x1={b.x1}
                x2={b.x2}
                fill={cfg?.color || '#fff'}
                fillOpacity={0.05}
                stroke="none"
              />
            );
          })}

          <XAxis
            dataKey="timestamp"
            tick={TICK}
            tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[-100, 100]}
            tick={TICK}
            axisLine={false}
            tickLine={false}
            ticks={[-100, -50, 0, 50, 100]}
          />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
          <Tooltip
            content={<Tooltip_ />}
            cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }}
          />
          <Area
            type="monotone"
            dataKey="risk_score"
            stroke="rgba(255,255,255,0.6)"
            strokeWidth={1.5}
            fill="rgba(255,255,255,0.03)"
            dot={false}
            activeDot={{ r: 3, fill: '#fff', strokeWidth: 0 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
