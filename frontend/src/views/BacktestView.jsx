import React, { useState, useCallback } from 'react';
import {
  ComposedChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceArea, ReferenceLine,
} from 'recharts';
import { REGIME_CONFIG, EQUITY_EXPOSURE } from '../lib/utils';
import { api } from '../lib/api';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

const PRESETS = [
  { label: '2022 Bear',  start: '2022-01-01', end: '2022-12-31' },
  { label: '2023 Bull',  start: '2023-01-01', end: '2023-12-31' },
  { label: '2024',       start: '2024-01-01', end: '2024-12-31' },
  { label: 'Last 12M',   start: new Date(Date.now() - 365*86400000).toISOString().slice(0,10), end: new Date().toISOString().slice(0,10) },
];

function RichTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const cfg = REGIME_CONFIG[d.regime] || {};
  const EQ = EQUITY_EXPOSURE;
  return (
    <div style={{
      background: '#0d0d0d',
      border: `1px solid ${cfg.color}40`,
      borderRadius: 10, padding: '12px 16px',
      fontSize: 11, fontFamily: 'JetBrains Mono, monospace', minWidth: 185,
      boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px ${cfg.color}18`,
    }}>
      <div style={{ color: 'rgba(255,255,255,0.28)', marginBottom: 8, fontSize: 10 }}>{d.date}</div>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: `${cfg.color}18`, border: `1px solid ${cfg.color}35`,
        borderRadius: 5, padding: '3px 8px', marginBottom: 10,
      }}>
        <div style={{ width: 7, height: 7, borderRadius: 2, background: cfg.color }} />
        <span style={{ color: cfg.color, fontWeight: 700, fontSize: 11 }}>{cfg.label || d.regime}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>Risk score</span>
          <span style={{ color: '#f0f0f0', fontWeight: 600 }}>
            {d.risk_score > 0 ? '+' : ''}{d.risk_score?.toFixed(1)}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>Eq. exposure</span>
          <span style={{ color: '#3b82f6', fontWeight: 600 }}>
            {EQ[d.regime] != null ? `${(EQ[d.regime] * 100).toFixed(0)}%` : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}

function TransitionLabel({ viewBox, regime }) {
  const cfg = REGIME_CONFIG[regime] || {};
  const x = viewBox?.x ?? 0;
  const y = (viewBox?.y ?? 0) - 2;
  return (
    <g>
      <rect x={x - 14} y={y} width={28} height={14} rx={3}
        fill={cfg.color || '#fff'} fillOpacity={0.15}
        stroke={cfg.color || '#fff'} strokeOpacity={0.35} strokeWidth={0.5}
      />
      <text x={x} y={y + 9.5} textAnchor="middle"
        fontSize={7.5} fontFamily="JetBrains Mono, monospace"
        fill={cfg.color || '#fff'} fontWeight={700}
      >
        {cfg.short || regime?.slice(0, 3).toUpperCase()}
      </text>
    </g>
  );
}

function buildBands(data) {
  if (!data.length) return [];
  const bands = [];
  let start = data[0], current = data[0].regime;
  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== current) {
      bands.push({ regime: current, x1: start.date, x2: data[i - 1].date });
      start = data[i]; current = data[i].regime;
    }
  }
  bands.push({ regime: current, x1: start.date, x2: data[data.length - 1].date });
  return bands;
}

function StatBox({ label, value, color }) {
  return (
    <div className="card p-4">
      <div className="label mb-1">{label}</div>
      <div className="font-mono text-lg font-semibold" style={{ color: color || '#f0f0f0' }}>{value}</div>
    </div>
  );
}

export default function BacktestView() {
  const [start, setStart]   = useState('2024-01-01');
  const [end, setEnd]       = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState('');

  async function run() {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await fetch('/v1/backtest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-MacroPulse-Key': api.getKey(),
        },
        body: JSON.stringify({ start, end }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Error ${res.status}`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const summary = result?.summary;
  const timeline = result?.timeline ?? [];
  const bands = buildBands(timeline);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold tracking-tight">Backtest</h2>
        <span className="text-[10px] text-white/25 font-mono">Historical regime replay</span>
      </div>

      {/* How it works */}
      <div className="card p-5">
        <div className="label mb-3">How Backtests Work</div>
        <p style={{fontSize:11, fontFamily:'JetBrains Mono', color:'rgba(255,255,255,0.4)', lineHeight:1.7, marginBottom:12}}>
          The backtest engine replays the MacroPulse regime signal over any historical window.
          For each day, it applies the regime-weighted equity allocation to the S&P 500 and records
          the resulting risk score and regime classification.
        </p>
        <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
          {[['Expansion','100%','#22c55e'],['Recovery','75%','#3b82f6'],['Tightening','25%','#f59e0b'],['Risk-Off','0%','#ef4444']].map(([r,eq,c]) => (
            <div key={r} style={{padding:'6px 12px', borderRadius:6, background:'rgba(255,255,255,0.03)', border:`1px solid ${c}22`, fontFamily:'JetBrains Mono', fontSize:10}}>
              <span style={{color:c, fontWeight:600}}>{r}</span>
              <span style={{color:'rgba(255,255,255,0.3)', marginLeft:6}}>{eq} equity</span>
            </div>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="card p-5">
        <div className="label mb-4">Parameters</div>

        {/* Preset buttons */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
          {PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => { setStart(p.start); setEnd(p.end); }}
              style={{
                padding: '3px 10px', borderRadius: 4, fontFamily: 'JetBrains Mono', fontSize: 10,
                fontWeight: 500, cursor: 'pointer', border: '1px solid #2a2a2a',
                background: '#111', color: 'rgba(255,255,255,0.4)', transition: 'all 0.1s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = '#f0f0f0'; e.currentTarget.style.borderColor = '#3a3a3a'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.4)'; e.currentTarget.style.borderColor = '#2a2a2a'; }}
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-3 items-end">
          <div>
            <label className="text-[10px] text-white/30 font-mono uppercase tracking-wide block mb-1.5">Start Date</label>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="w-full rounded px-3 py-2 text-[12px] font-mono outline-none"
              style={{
                background: '#111', border: '1px solid #2a2a2a',
                color: '#f0f0f0', colorScheme: 'dark',
              }}
              onFocus={(e) => { e.target.style.borderColor = '#3a3a3a'; }}
              onBlur={(e) => { e.target.style.borderColor = '#2a2a2a'; }}
            />
          </div>
          <div>
            <label className="text-[10px] text-white/30 font-mono uppercase tracking-wide block mb-1.5">End Date</label>
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="w-full rounded px-3 py-2 text-[12px] font-mono outline-none"
              style={{
                background: '#111', border: '1px solid #2a2a2a',
                color: '#f0f0f0', colorScheme: 'dark',
              }}
              onFocus={(e) => { e.target.style.borderColor = '#3a3a3a'; }}
              onBlur={(e) => { e.target.style.borderColor = '#2a2a2a'; }}
            />
          </div>
          <div>
            <button
              onClick={run}
              disabled={loading || !api.hasKey()}
              className="w-full py-2 rounded font-mono text-[12px] font-semibold transition-opacity duration-150"
              style={{
                background: api.hasKey() ? '#f0f0f0' : '#222',
                color: api.hasKey() ? '#0a0a0a' : '#444',
                cursor: api.hasKey() ? 'pointer' : 'not-allowed',
                border: 'none',
              }}
            >
              {loading ? 'Running…' : 'Run Backtest →'}
            </button>
          </div>
        </div>

        {!api.hasKey() && (
          <div className="mt-3 text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
            Enter your API key in the header to use the backtest engine.
          </div>
        )}

        {error && (
          <div className="mt-3 text-[11px] font-mono text-red-400 border border-red-400/20 rounded px-3 py-2 bg-red-400/5">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {summary && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatBox label="Total Days" value={summary.total_days} />
            <StatBox label="Regime Transitions" value={summary.transitions} />
            <StatBox label="Avg Persistence" value={`${summary.avg_persistence_days?.toFixed(1)}d`} />
            <StatBox
              label="Mean Risk Score"
              value={(summary.mean_risk_score >= 0 ? '+' : '') + summary.mean_risk_score?.toFixed(1)}
              color={summary.mean_risk_score > 0 ? '#22c55e' : '#ef4444'}
            />
          </div>

          {/* Interpretation */}
          <div className="card p-4" style={{borderColor:'rgba(255,255,255,0.06)'}}>
            <div className="label mb-2">Interpreting Results</div>
            <p style={{fontSize:10, fontFamily:'JetBrains Mono', color:'rgba(255,255,255,0.3)', lineHeight:1.7, margin:0}}>
              {summary.transitions} regime transitions over {summary.total_days} days · avg persistence {summary.avg_persistence_days?.toFixed(1)}d per regime.
              {summary.mean_risk_score > 20
                ? ' Risk score strongly positive — model was predominantly bullish.'
                : summary.mean_risk_score > 0
                  ? ' Risk score mildly positive — mixed regime environment.'
                  : ' Risk score negative — model was predominantly defensive.'}
            </p>
          </div>

          {/* Regime distribution */}
          <div className="card p-5">
            <div className="label mb-3">Regime Distribution</div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(summary.regime_distribution || {}).map(([regime, pct]) => {
                const cfg = REGIME_CONFIG[regime] || {};
                return (
                  <div key={regime} className="p-3 rounded" style={{ background: cfg.bg || '#111', border: `1px solid ${cfg.color || '#1f1f1f'}22` }}>
                    <div className="text-[10px] text-white/30 font-mono uppercase tracking-wide mb-1">{cfg.label || regime}</div>
                    <div className="font-mono text-base font-semibold" style={{ color: cfg.color || '#f0f0f0' }}>
                      {(pct * 100).toFixed(1)}%
                    </div>
                    <div className="h-0.5 rounded-full mt-2" style={{ background: '#1a1a1a' }}>
                      <div className="h-full rounded-full" style={{ width: `${pct * 100}%`, background: cfg.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Timeline chart */}
          {timeline.length > 0 && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="label">Risk Score Timeline</div>
                <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.25)' }}>
                  {summary.transitions} regime transitions
                </div>
              </div>
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart data={timeline} margin={{ top: 20, right: 4, bottom: 0, left: -18 }}>
                  <defs>
                    <linearGradient id="btGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="rgba(255,255,255,0.07)" />
                      <stop offset="100%" stopColor="rgba(255,255,255,0)" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />
                  {bands.map((b, i) => {
                    const cfg = REGIME_CONFIG[b.regime];
                    return <ReferenceArea key={i} x1={b.x1} x2={b.x2} fill={cfg?.color || '#fff'} fillOpacity={0.04} stroke="none" />;
                  })}
                  {/* Transition annotation lines */}
                  {timeline.map((d, i) => {
                    if (i === 0 || d.regime === timeline[i-1].regime) return null;
                    const cfg = REGIME_CONFIG[d.regime];
                    return (
                      <ReferenceLine
                        key={`t-${i}`}
                        x={d.date}
                        stroke={cfg?.color || '#fff'} strokeOpacity={0.25}
                        strokeDasharray="3 3" strokeWidth={1}
                        label={(props) => <TransitionLabel {...props} regime={d.regime} />}
                      />
                    );
                  })}
                  <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="2 4" />
                  <XAxis dataKey="date" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[-100, 100]} tick={TICK} axisLine={false} tickLine={false} ticks={[-100, -50, 0, 50, 100]} />
                  <Tooltip
                    content={<RichTooltip />}
                    cursor={{ stroke: 'rgba(255,255,255,0.12)', strokeWidth: 1, strokeDasharray: '3 3' }}
                  />
                  <Area type="monotone" dataKey="risk_score" stroke="rgba(255,255,255,0.55)" strokeWidth={1.5} fill="url(#btGradient)" dot={false} activeDot={{ r: 4, fill: '#fff', strokeWidth: 0 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!summary && !loading && (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <div className="text-[11px] text-white/20 font-mono mb-2">No results yet</div>
          <div className="text-[10px] text-white/10 font-mono">Select a date range above and run the backtest</div>
        </div>
      )}
    </div>
  );
}
