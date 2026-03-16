import React, { useState, useCallback } from 'react';
import {
  ComposedChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceArea,
} from 'recharts';
import { REGIME_CONFIG } from '../lib/utils';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

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
  const [apiKey, setApiKey] = useState('');
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
          'X-MacroPulse-Key': apiKey,
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

      {/* Controls */}
      <div className="card p-5">
        <div className="label mb-4">Parameters</div>
        <div className="grid gap-4 lg:grid-cols-4 items-end">
          <div>
            <label className="text-[10px] text-white/30 font-mono uppercase tracking-wide block mb-1.5">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="mp_..."
              className="w-full rounded px-3 py-2 text-[12px] font-mono outline-none"
              style={{
                background: '#111', border: '1px solid #2a2a2a',
                color: '#f0f0f0',
              }}
              onFocus={(e) => { e.target.style.borderColor = '#3a3a3a'; }}
              onBlur={(e) => { e.target.style.borderColor = '#2a2a2a'; }}
            />
          </div>
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
              disabled={loading || !apiKey}
              className="w-full py-2 rounded font-mono text-[12px] font-semibold transition-opacity duration-150"
              style={{
                background: apiKey ? '#f0f0f0' : '#222',
                color: apiKey ? '#0a0a0a' : '#444',
                cursor: apiKey ? 'pointer' : 'not-allowed',
                border: 'none',
              }}
            >
              {loading ? 'Running…' : 'Run Backtest →'}
            </button>
          </div>
        </div>

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
              <div className="label mb-4">Risk Score Timeline</div>
              <ResponsiveContainer width="100%" height={220}>
                <ComposedChart data={timeline} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />
                  {bands.map((b, i) => {
                    const cfg = REGIME_CONFIG[b.regime];
                    return <ReferenceArea key={i} x1={b.x1} x2={b.x2} fill={cfg?.color || '#fff'} fillOpacity={0.05} stroke="none" />;
                  })}
                  <XAxis dataKey="date" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis domain={[-100, 100]} tick={TICK} axisLine={false} tickLine={false} ticks={[-100, -50, 0, 50, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#141414', border: '1px solid #2a2a2a', borderRadius: 6, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}
                    labelStyle={{ color: 'rgba(255,255,255,0.35)' }}
                  />
                  <Area type="monotone" dataKey="risk_score" stroke="rgba(255,255,255,0.6)" strokeWidth={1.5} fill="rgba(255,255,255,0.03)" dot={false} />
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
          <div className="text-[10px] text-white/10 font-mono">Enter your API key and date range above, then run</div>
        </div>
      )}
    </div>
  );
}
