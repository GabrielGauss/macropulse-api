import React, { useState } from 'react';
import {
  ComposedChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, ReferenceArea, Brush,
} from 'recharts';
import { useGuideMode } from '../lib/guideMode';
import { REGIME_CONFIG, formatDateShort, EQUITY_EXPOSURE } from '../lib/utils';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

// ── Rich hover tooltip ────────────────────────────────────────────────────────
function RichTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const cfg = REGIME_CONFIG[d.regime] || {};
  const exposure = EQUITY_EXPOSURE[d.regime];
  const score = d.risk_score;
  const trend = d.scoreDelta;

  return (
    <div style={{
      background: '#0d0d0d',
      border: `1px solid ${cfg.color}40`,
      borderRadius: 10,
      padding: '12px 16px',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
      minWidth: 190,
      boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px ${cfg.color}18`,
    }}>
      {/* Date */}
      <div style={{ color: 'rgba(255,255,255,0.28)', marginBottom: 8, fontSize: 10 }}>
        {formatDateShort(d.timestamp)}
      </div>

      {/* Regime badge */}
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: `${cfg.color}18`, border: `1px solid ${cfg.color}35`,
        borderRadius: 5, padding: '3px 8px', marginBottom: 10,
      }}>
        <div style={{ width: 7, height: 7, borderRadius: 2, background: cfg.color, flexShrink: 0 }} />
        <span style={{ color: cfg.color, fontWeight: 700, fontSize: 11, letterSpacing: '0.02em' }}>
          {cfg.label || d.regime}
        </span>
      </div>

      {/* Metrics grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>Risk score</span>
          <span style={{ color: '#f0f0f0', fontWeight: 600 }}>
            {score > 0 ? '+' : ''}{score?.toFixed(1)}
            {trend != null && (
              <span style={{ marginLeft: 5, fontSize: 9, color: trend >= 0 ? '#22c55e' : '#ef4444' }}>
                {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}
              </span>
            )}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>Eq. exposure</span>
          <span style={{ color: '#3b82f6', fontWeight: 600 }}>
            {exposure != null ? `${(exposure * 100).toFixed(0)}%` : '—'}
          </span>
        </div>
        {d.daysInRegime > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <span style={{ color: 'rgba(255,255,255,0.3)' }}>Days in regime</span>
            <span style={{ color: 'rgba(255,255,255,0.55)', fontWeight: 500 }}>{d.daysInRegime}d</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Transition label pill at top of each change line ──────────────────────────
function TransitionLabel({ viewBox, regime }) {
  const cfg = REGIME_CONFIG[regime] || {};
  const x = viewBox?.x ?? 0;
  const y = (viewBox?.y ?? 0) - 2;
  const w = 28; const h = 14;
  return (
    <g>
      <rect x={x - w / 2} y={y} width={w} height={h} rx={3}
        fill={cfg.color || '#fff'} fillOpacity={0.15}
        stroke={cfg.color || '#fff'} strokeOpacity={0.35} strokeWidth={0.5}
      />
      <text x={x} y={y + 9.5} textAnchor="middle"
        fontSize={7.5} fontFamily="JetBrains Mono, monospace"
        fill={cfg.color || '#fff'} fontWeight={700} letterSpacing="0.04em"
      >
        {cfg.short || regime?.slice(0, 3).toUpperCase()}
      </text>
    </g>
  );
}

// ── Build regime background bands ─────────────────────────────────────────────
function buildBands(data) {
  if (!data.length) return [];
  const bands = [];
  let start = data[0], current = data[0].regime;
  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== current) {
      bands.push({ regime: current, x1: start.timestamp, x2: data[i - 1].timestamp });
      start = data[i]; current = data[i].regime;
    }
  }
  bands.push({ regime: current, x1: start.timestamp, x2: data[data.length - 1].timestamp });
  return bands;
}

// ── Build transition annotation points ────────────────────────────────────────
function buildTransitions(data) {
  const transitions = [];
  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== data[i - 1].regime) {
      transitions.push({ timestamp: data[i].timestamp, regime: data[i].regime });
    }
  }
  return transitions;
}

const TIME_OPTIONS = [
  { label: '1M', days: 30  },
  { label: '3M', days: 90  },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: '2Y', days: 730 },
];

export default function RegimeTimeline({
  history,
  historyDays = 90,
  onHistoryDaysChange,
  isFree = false,
}) {
  const [showTransitions, setShowTransitions] = useState(true);
  const guideMode = useGuideMode();

  if (!history || history.length === 0) {
    return (
      <div className="card flex h-72 items-center justify-center">
        <p className="text-[11px] text-white/45 font-mono">No history data</p>
      </div>
    );
  }

  const raw = [...history].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const data = raw.map((r, i, arr) => {
    // Days in current regime streak
    let startIdx = i;
    while (startIdx > 0 && arr[startIdx - 1].macro_regime === r.macro_regime) startIdx--;
    const daysInRegime = Math.round(
      (new Date(r.timestamp) - new Date(arr[startIdx].timestamp)) / 86400000
    );
    // Score delta vs previous point
    const scoreDelta = i > 0 ? r.risk_score - arr[i - 1].risk_score : null;
    return {
      timestamp: r.timestamp,
      risk_score: r.risk_score,
      regime: r.macro_regime,
      daysInRegime,
      scoreDelta,
    };
  });

  const bands = buildBands(data);
  const transitions = buildTransitions(data);

  // Current streak info for header badge
  const last = data[data.length - 1];
  const currentRegimeCfg = REGIME_CONFIG[last?.regime] || {};
  const streakDays = last?.daysInRegime ?? 0;

  return (
    <div className="card p-5 animate-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
        <div>
          <div className="label mb-1">Risk Score Timeline</div>
          {guideMode && (
            <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 2, maxWidth: 340, lineHeight: 1.5 }}>
              Composite HMM output: positive = risk-on, negative = risk-off. Colored bands = active regime. Drag the brush below to zoom.
            </div>
          )}
          {last && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 10, fontFamily: 'JetBrains Mono, monospace' }}>
              <div style={{ width: 6, height: 6, borderRadius: 2, background: currentRegimeCfg.color, flexShrink: 0 }} />
              <span style={{ color: currentRegimeCfg.color }}>In {currentRegimeCfg.label || last.regime}</span>
              <span style={{ color: 'rgba(255,255,255,0.45)' }}>·</span>
              <span style={{ color: 'rgba(255,255,255,0.50)' }}>{streakDays}d streak</span>
              <span style={{ color: 'rgba(255,255,255,0.45)' }}>·</span>
              <span style={{ color: 'rgba(255,255,255,0.50)' }}>{transitions.length} transitions</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Regime legend */}
          <div className="hidden sm:flex items-center gap-3">
            {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
              <div key={key} className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 rounded-sm flex-shrink-0" style={{ background: cfg.color }} />
                <span className="text-[10px] text-white/50 font-mono uppercase">{cfg.short}</span>
              </div>
            ))}
          </div>

          {/* Transition toggle */}
          {!isFree && transitions.length > 0 && (
            <button
              onClick={() => setShowTransitions(t => !t)}
              style={{
                fontSize: 9, fontFamily: 'JetBrains Mono, monospace', padding: '2px 7px',
                borderRadius: 4, border: '1px solid #2a2a2a', cursor: 'pointer',
                background: showTransitions ? '#1f1f1f' : 'transparent',
                color: showTransitions ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.45)',
                transition: 'all 0.15s',
              }}
            >
              transitions
            </button>
          )}

          {/* Free tier nudge */}
          {isFree ? (
            <a
              href="https://macropulse.live/#pricing"
              target="_blank" rel="noopener noreferrer"
              className="text-[10px] font-mono transition-colors"
              style={{ color: 'rgba(255,255,255,0.45)', textDecoration: 'none' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
              title="Upgrade for full 2-year history"
            >
              30d · <span style={{ textDecoration: 'underline' }}>upgrade for 2Y →</span>
            </a>
          ) : (
            /* Time range pills */
            <div
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
                      color: active ? '#f0f0f0' : 'rgba(255,255,255,0.45)',
                      cursor: 'pointer', border: 'none',
                    }}
                    onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
                    onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data} margin={{ top: 20, right: 4, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />

          {/* Regime background bands */}
          {bands.map((b, i) => {
            const cfg = REGIME_CONFIG[b.regime];
            return (
              <ReferenceArea
                key={i}
                x1={b.x1} x2={b.x2}
                fill={cfg?.color || '#fff'} fillOpacity={0.04}
                stroke="none"
              />
            );
          })}

          {/* Regime transition annotation lines */}
          {showTransitions && transitions.map((t, i) => {
            const cfg = REGIME_CONFIG[t.regime];
            return (
              <ReferenceLine
                key={i}
                x={t.timestamp}
                stroke={cfg?.color || '#fff'}
                strokeOpacity={0.25}
                strokeDasharray="3 3"
                strokeWidth={1}
                label={(props) => <TransitionLabel {...props} regime={t.regime} />}
              />
            );
          })}

          {/* Zero baseline */}
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="2 4" />

          <XAxis
            dataKey="timestamp"
            tick={TICK}
            tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            axisLine={false} tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[-100, 100]}
            tick={TICK}
            axisLine={false} tickLine={false}
            ticks={[-100, -50, 0, 50, 100]}
          />
          <Tooltip
            content={<RichTooltip />}
            cursor={{ stroke: 'rgba(255,255,255,0.12)', strokeWidth: 1, strokeDasharray: '3 3' }}
          />
          <Area
            type="monotone"
            dataKey="risk_score"
            stroke="rgba(255,255,255,0.55)"
            strokeWidth={1.5}
            fill="url(#riskGradient)"
            dot={false}
            activeDot={{ r: 4, fill: '#fff', strokeWidth: 0 }}
          />
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(255,255,255,0.08)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0)" />
            </linearGradient>
          </defs>
          <Brush
            dataKey="timestamp"
            height={22}
            stroke="#1f1f1f"
            fill="#0d0d0d"
            travellerWidth={6}
            tickFormatter={() => ''}
            startIndex={Math.max(0, data.length - Math.min(data.length, 90))}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
