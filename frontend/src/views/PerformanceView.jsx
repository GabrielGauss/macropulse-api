import React, { useState, useEffect } from 'react';
import {
  ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceArea, ReferenceLine, Brush,
} from 'recharts';
import { REGIME_CONFIG, EQUITY_EXPOSURE } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };
const EQ   = EQUITY_EXPOSURE;

// ── Tooltip ───────────────────────────────────────────────────────────────────
function PerfTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const cfg = REGIME_CONFIG[d.regime] || {};
  const strat = d.stratRebased;
  const bh    = d.bhRebased;
  const delta = strat != null && bh != null ? (strat - bh).toFixed(1) : null;
  return (
    <div style={{
      background: '#0d0d0d', border: `1px solid ${cfg.color}40`,
      borderRadius: 10, padding: '12px 16px', fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace', minWidth: 210,
      boxShadow: `0 8px 32px rgba(0,0,0,0.65), 0 0 0 1px ${cfg.color}18`,
    }}>
      <div style={{ color: 'rgba(255,255,255,0.28)', marginBottom: 8, fontSize: 10 }}>{d.date}</div>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: `${cfg.color}18`, border: `1px solid ${cfg.color}35`,
        borderRadius: 5, padding: '3px 8px', marginBottom: 10,
      }}>
        <div style={{ width: 7, height: 7, borderRadius: 2, background: cfg.color }} />
        <span style={{ color: cfg.color, fontWeight: 700 }}>{cfg.label || d.regime}</span>
        <span style={{ color: `${cfg.color}88`, fontSize: 10 }}>· {(EQ[d.regime] * 100).toFixed(0)}% equity</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20 }}>
          <span style={{ color: '#3b82f6' }}>Strategy</span>
          <span style={{ color: '#f0f0f0', fontWeight: 600 }}>
            {strat != null ? `${strat >= 100 ? '+' : ''}${(strat - 100).toFixed(1)}%` : '—'}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20 }}>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Buy &amp; Hold</span>
          <span style={{ color: 'rgba(255,255,255,0.55)', fontWeight: 600 }}>
            {bh != null ? `${bh >= 100 ? '+' : ''}${(bh - 100).toFixed(1)}%` : '—'}
          </span>
        </div>
        {delta != null && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', gap: 20,
            borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 5, marginTop: 2,
          }}>
            <span style={{ color: 'rgba(255,255,255,0.3)' }}>Outperformance</span>
            <span style={{ color: parseFloat(delta) >= 0 ? '#22c55e' : '#ef4444', fontWeight: 700 }}>
              {parseFloat(delta) >= 0 ? '+' : ''}{delta}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Regime transition label pill ──────────────────────────────────────────────
function TransitionLabel({ viewBox, regime }) {
  const cfg = REGIME_CONFIG[regime] || {};
  const x = viewBox?.x ?? 0;
  const y = (viewBox?.y ?? 0) - 2;
  return (
    <g>
      <rect x={x - 14} y={y} width={28} height={14} rx={3}
        fill={cfg.color || '#fff'} fillOpacity={0.15}
        stroke={cfg.color || '#fff'} strokeOpacity={0.35} strokeWidth={0.5} />
      <text x={x} y={y + 9.5} textAnchor="middle"
        fontSize={7.5} fontFamily="JetBrains Mono, monospace"
        fill={cfg.color || '#fff'} fontWeight={700} letterSpacing="0.04em">
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

function buildTransitions(data) {
  const t = [];
  for (let i = 1; i < data.length; i++) {
    if (data[i].regime !== data[i - 1].regime)
      t.push({ date: data[i].date, regime: data[i].regime });
  }
  return t;
}

// ── Stat pill ─────────────────────────────────────────────────────────────────
function StatPill({ label, value, color, sub }) {
  return (
    <div style={{
      padding: '10px 16px', background: '#0f0f0f',
      border: '1px solid #1f1f1f', borderRadius: 8, flex: '1 1 100px',
    }}>
      <div style={{ fontSize: 9, fontFamily: 'JetBrains Mono', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.25)', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'JetBrains Mono', color: color || '#f0f0f0', lineHeight: 1.2 }}>{value}</div>
      {sub && <div style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.2)', marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

// ── Copy snippet button ───────────────────────────────────────────────────────
function CopySnippet() {
  const [copied, setCopied] = useState(false);
  const snippet = `import requests\n\ndata = requests.get("https://api.macropulse.live/v1/public/chart-data").json()\nseries = data["series"]  # [{date, regime, risk_score, sp500, gold, strategy}, ...]`;
  function copy() {
    navigator.clipboard.writeText(snippet).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    });
  }
  return (
    <button onClick={copy} style={{
      fontSize: 9, fontFamily: 'JetBrains Mono', padding: '3px 9px',
      borderRadius: 4, border: '1px solid #2a2a2a', cursor: 'pointer',
      background: copied ? 'rgba(34,197,94,0.08)' : 'transparent',
      color: copied ? '#22c55e' : 'rgba(255,255,255,0.25)',
      transition: 'all 0.2s', display: 'inline-flex', alignItems: 'center', gap: 5,
    }}>
      {copied ? (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
      ) : (
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2"/>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
      )}
      {copied ? 'copied!' : 'copy snippet'}
    </button>
  );
}

const RANGE_OPTIONS = [
  { label: '3M', days: 90  },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: '2Y', days: 730 },
];

// ── Main component ────────────────────────────────────────────────────────────
export default function PerformanceView() {
  const [allData,          setAllData]          = useState(null);
  const [loading,          setLoading]          = useState(true);
  const [error,            setError]            = useState('');
  const [rangeDays,        setRangeDays]        = useState(365);
  const [showBands,        setShowBands]        = useState(true);
  const [showTransitions,  setShowTransitions]  = useState(true);
  const guideMode = useGuideMode();

  useEffect(() => {
    fetch('https://api.macropulse.live/v1/public/chart-data')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => { setAllData(d); setLoading(false); })
      .catch(e => { setError(`Failed to load chart data (${e})`); setLoading(false); });
  }, []);

  if (loading) return (
    <div className="flex h-64 items-center justify-center">
      <div className="text-[11px] text-white/20 font-mono animate-pulse">Loading performance data…</div>
    </div>
  );
  if (error) return (
    <div className="card flex h-64 items-center justify-center">
      <div className="text-[11px] text-red-400/60 font-mono">{error}</div>
    </div>
  );

  // Slice to selected window
  const rawSlice = (allData?.series ?? []).slice(-rangeDays);
  if (!rawSlice.length) return null;

  // Rebase both series to 100 at window start
  const bhBase    = rawSlice[0].sp500;
  const stratBase = rawSlice[0].strategy;
  const data = rawSlice.map(d => ({
    date:        d.date,
    regime:      d.regime,
    bhRebased:    bhBase    ? Math.round((d.sp500    / bhBase)    * 1000) / 10 : null,
    stratRebased: stratBase ? Math.round((d.strategy / stratBase) * 1000) / 10 : null,
  }));

  const bands      = buildBands(data);
  const transitions = buildTransitions(data);

  // Window stats
  const last       = data[data.length - 1];
  const stratRet   = last.stratRebased != null ? (last.stratRebased - 100).toFixed(1) : '—';
  const bhRet      = last.bhRebased    != null ? (last.bhRebased    - 100).toFixed(1) : '—';
  const outperf    = last.stratRebased != null && last.bhRebased != null
    ? (last.stratRebased - last.bhRebased).toFixed(1) : '—';

  // Regime distribution
  const dist  = {};
  data.forEach(d => { dist[d.regime] = (dist[d.regime] || 0) + 1; });
  const total = data.length || 1;

  const rangeLabel = RANGE_OPTIONS.find(o => o.days === rangeDays)?.label ?? '';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold tracking-tight">Strategy Performance</h2>
        <span className="text-[10px] text-white/25 font-mono">Regime-weighted equity allocation vs buy &amp; hold</span>
      </div>

      {/* ── Stats row ── */}
      <div className="flex gap-3 flex-wrap">
        <StatPill
          label="Strategy return"
          value={`${parseFloat(stratRet) >= 0 ? '+' : ''}${stratRet}%`}
          color={parseFloat(stratRet) >= 0 ? '#22c55e' : '#ef4444'}
          sub={`${rangeLabel} window`}
        />
        <StatPill
          label="Buy &amp; Hold SPX"
          value={`${parseFloat(bhRet) >= 0 ? '+' : ''}${bhRet}%`}
          color="rgba(255,255,255,0.45)"
          sub="S&P 500"
        />
        <StatPill
          label="Outperformance"
          value={`${parseFloat(outperf) >= 0 ? '+' : ''}${outperf}%`}
          color={parseFloat(outperf) >= 0 ? '#22c55e' : '#ef4444'}
          sub={parseFloat(outperf) < 0 ? 'expected in bull runs ↓' : 'vs buy & hold'}
        />
        <StatPill label="Sharpe · 2yr"   value={allData?.stats?.sharpe_proxy != null ? allData.stats.sharpe_proxy : '—'}  color="#3b82f6"  sub="annualised" />
        <StatPill label="Max drawdown"   value={allData?.stats?.max_drawdown != null ? `${allData.stats.max_drawdown}%` : '—'} color="#ef4444" sub="strategy · 2yr" />
      </div>

      {/* ── Main chart ── */}
      <div className="card p-5">
        {/* Chart header */}
        <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
          <div>
            <div className="label mb-1">Strategy vs Buy &amp; Hold</div>
            <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.25)' }}>
              Rebased to 100 at window start · {transitions.length} transitions · {rangeLabel} window
            </div>
            {guideMode && (
              <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 4, maxWidth: 400, lineHeight: 1.5 }}>
                Blue = MacroPulse strategy (regime-weighted equity: 100% → 75% → 25% → 0%). Dashed = passive S&P 500 buy &amp; hold. Both rebased to 100 at window start. Drag brush to zoom.
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={() => setShowBands(b => !b)} style={{
              fontSize: 9, fontFamily: 'JetBrains Mono', padding: '2px 7px',
              borderRadius: 4, border: '1px solid #2a2a2a', cursor: 'pointer',
              background: showBands ? '#1f1f1f' : 'transparent',
              color: showBands ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.2)',
              transition: 'all 0.15s',
            }}>regimes</button>
            <button onClick={() => setShowTransitions(t => !t)} style={{
              fontSize: 9, fontFamily: 'JetBrains Mono', padding: '2px 7px',
              borderRadius: 4, border: '1px solid #2a2a2a', cursor: 'pointer',
              background: showTransitions ? '#1f1f1f' : 'transparent',
              color: showTransitions ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.2)',
              transition: 'all 0.15s',
            }}>transitions</button>
            <CopySnippet />
            {/* Range picker */}
            <div className="flex items-center rounded" style={{ background: '#111', border: '1px solid #1f1f1f', padding: 2, gap: 2 }}>
              {RANGE_OPTIONS.map(({ label, days }) => {
                const active = rangeDays === days;
                return (
                  <button key={label} onClick={() => setRangeDays(days)}
                    className="rounded px-2 py-0.5 font-mono text-[10px] font-medium transition-colors duration-100"
                    style={{ background: active ? '#222' : 'transparent', color: active ? '#f0f0f0' : 'rgba(255,255,255,0.3)', cursor: 'pointer', border: 'none' }}
                    onMouseEnter={e => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.6)'; }}
                    onMouseLeave={e => { if (!active) e.currentTarget.style.color = 'rgba(255,255,255,0.3)'; }}>
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={data} margin={{ top: 20, right: 4, bottom: 0, left: -8 }}>
            <defs>
              <linearGradient id="stratGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="rgba(59,130,246,0.22)" />
                <stop offset="100%" stopColor="rgba(59,130,246,0)" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />
            {showBands && bands.map((b, i) => {
              const cfg = REGIME_CONFIG[b.regime];
              return <ReferenceArea key={i} x1={b.x1} x2={b.x2} fill={cfg?.color || '#fff'} fillOpacity={0.04} stroke="none" />;
            })}
            {showTransitions && transitions.map((t, i) => {
              const cfg = REGIME_CONFIG[t.regime];
              return (
                <ReferenceLine key={i} x={t.date}
                  stroke={cfg?.color || '#fff'} strokeOpacity={0.25}
                  strokeDasharray="3 3" strokeWidth={1}
                  label={props => <TransitionLabel {...props} regime={t.regime} />} />
              );
            })}
            <ReferenceLine y={100} stroke="rgba(255,255,255,0.06)" strokeDasharray="2 4" />
            <XAxis dataKey="date" tick={TICK} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={TICK} axisLine={false} tickLine={false}
              tickFormatter={v => `${v >= 100 ? '+' : ''}${(v - 100).toFixed(0)}%`} />
            <Tooltip content={<PerfTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.12)', strokeWidth: 1, strokeDasharray: '3 3' }} />
            <Area type="monotone" dataKey="stratRebased" name="MacroPulse Strategy"
              stroke="#3b82f6" strokeWidth={1.5} fill="url(#stratGrad)"
              dot={false} activeDot={{ r: 4, fill: '#3b82f6', strokeWidth: 0 }} />
            <Line type="monotone" dataKey="bhRebased" name="Buy &amp; Hold SPX"
              stroke="rgba(255,255,255,0.3)" strokeWidth={1} strokeDasharray="4 3"
              dot={false} activeDot={{ r: 3, fill: '#fff', strokeWidth: 0 }} />
            <Brush
              dataKey="date"
              height={22}
              stroke="#1f1f1f"
              fill="#0d0d0d"
              travellerWidth={6}
              tickFormatter={() => ''}
              startIndex={Math.max(0, data.length - Math.min(data.length, 90))}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#1a1a1a] flex-wrap gap-2">
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-2">
              <div style={{ width: 24, height: 2, background: '#3b82f6', borderRadius: 1 }} />
              <span className="text-[10px] font-mono text-white/35">MacroPulse Strategy</span>
            </div>
            <div className="flex items-center gap-2">
              <svg width="24" height="8" viewBox="0 0 24 8">
                <line x1="0" y1="4" x2="24" y2="4" stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="4 3"/>
              </svg>
              <span className="text-[10px] font-mono text-white/35">Buy &amp; Hold SPX</span>
            </div>
          </div>
          <span className="text-[9px] font-mono text-white/15">
            EXP 100% · REC 75% · TGT 25% · RFO 0%
          </span>
        </div>
      </div>

      {/* ── Regime distribution ── */}
      <div className="card p-5">
        <div className="label mb-3">Regime Distribution · {rangeLabel} Window</div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {['expansion', 'recovery', 'tightening', 'risk_off'].map(r => {
            const cfg = REGIME_CONFIG[r];
            const pct = ((dist[r] || 0) / total) * 100;
            return (
              <div key={r} className="p-3 rounded" style={{ background: cfg.bg, border: `1px solid ${cfg.color}22` }}>
                <div className="text-[9px] text-white/30 font-mono uppercase tracking-wide mb-1">{cfg.label}</div>
                <div className="font-mono text-base font-semibold" style={{ color: cfg.color }}>{pct.toFixed(1)}%</div>
                <div className="text-[9px] font-mono mt-1" style={{ color: 'rgba(255,255,255,0.2)' }}>
                  {EQ[r] * 100}% equity · {dist[r] || 0}d
                </div>
                <div className="h-0.5 rounded-full mt-2" style={{ background: '#1a1a1a' }}>
                  <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: cfg.color }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
