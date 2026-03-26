import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';

const EXPOSURE = { expansion: '100%', recovery: '75%', tightening: '25%', risk_off: '0%' };
const CELL = 14;
const GAP  = 2;

// Compute streak of current regime at the end of the sorted data
function computeStreak(sorted) {
  if (!sorted.length) return null;
  const last = sorted[sorted.length - 1];
  const regime = last.macro_regime;
  let count = 0;
  for (let i = sorted.length - 1; i >= 0; i--) {
    if (sorted[i].macro_regime === regime) count++;
    else break;
  }
  return { regime, days: count };
}

// Stacked distribution bar
function DistBar({ sorted }) {
  const total = sorted.length;
  if (!total) return null;
  const counts = {};
  sorted.forEach(d => { counts[d.macro_regime] = (counts[d.macro_regime] || 0) + 1; });
  const entries = Object.entries(REGIME_CONFIG).map(([key, cfg]) => ({
    key, cfg, pct: ((counts[key] || 0) / total) * 100,
  })).filter(e => e.pct > 0);

  return (
    <div className="mb-4">
      <div className="flex h-1 w-full overflow-hidden mb-2">
        {entries.map(({ key, cfg, pct }) => (
          <div key={key} style={{ width: `${pct}%`, background: cfg.color, flexShrink: 0 }} />
        ))}
      </div>
      <div className="flex items-center gap-4 flex-wrap">
        {entries.map(({ key, cfg, pct }) => (
          <div key={key} className="flex items-center gap-1.5">
            <div style={{ width: 6, height: 6, background: cfg.color, flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: cfg.color }}>
              {cfg.short}
            </span>
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.35)' }}>
              {pct.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RegimeCalendar({ isFree = false, tier }) {
  const maxDays = isFree ? 30 : 730;
  const fetchFull = useCallback(() => api.getRegimeHistory(maxDays), [maxDays]);
  const { data: raw, loading } = useFetch(fetchFull);
  const [tooltip, setTooltip]     = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const scrollRef = useRef(null);

  // Auto-scroll to today
  useEffect(() => {
    if (!raw || !raw.length || !scrollRef.current) return;
    const sorted2 = [...raw].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const firstDate = new Date(sorted2[0].timestamp.slice(0, 10) + 'T00:00:00Z');
    const startDay  = new Date(firstDate);
    const dow = startDay.getUTCDay();
    startDay.setUTCDate(startDay.getUTCDate() - (dow === 0 ? 6 : dow - 1));
    const todayDate = new Date(new Date().toISOString().slice(0, 10) + 'T00:00:00Z');
    const weeksToToday = Math.floor((todayDate - startDay) / (7 * 86400000));
    scrollRef.current.scrollLeft = Math.max(0, weeksToToday * (CELL + GAP) - scrollRef.current.clientWidth + 80);
  }, [raw]);

  if (loading || tier === null) {
    return (
      <div className="card p-5">
        <div className="label mb-4">Regime Calendar</div>
        <div className="h-32 flex items-center justify-center">
          <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.3)' }}>
            Loading…
          </span>
        </div>
      </div>
    );
  }

  if (!raw || !raw.length) {
    return (
      <div className="card p-5">
        <div className="label mb-4">Regime Calendar</div>
        <div className="h-32 flex items-center justify-center">
          <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.3)' }}>
            No data
          </span>
        </div>
      </div>
    );
  }

  const sorted = [...raw].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const regimeByDate = {};
  const scoreByDate  = {};
  sorted.forEach(d => {
    const ds = d.timestamp.slice(0, 10);
    regimeByDate[ds] = d.macro_regime;
    scoreByDate[ds]  = d.risk_score;
  });

  // Grid bounds
  const firstDate = new Date(sorted[0].timestamp.slice(0, 10) + 'T00:00:00Z');
  const startDay  = new Date(firstDate);
  const dow = startDay.getUTCDay();
  startDay.setUTCDate(startDay.getUTCDate() - (dow === 0 ? 6 : dow - 1));

  const lastDate = new Date(sorted[sorted.length - 1].timestamp.slice(0, 10) + 'T00:00:00Z');
  const endDay   = new Date(lastDate);
  const edow = endDay.getUTCDay();
  if (edow !== 0) endDay.setUTCDate(endDay.getUTCDate() + (7 - edow));

  // Build weeks
  const weeks = [];
  const cur = new Date(startDay);
  while (cur <= endDay) {
    const week = [];
    for (let d = 0; d < 7; d++) {
      const ds = cur.toISOString().slice(0, 10);
      week.push({ date: ds, regime: regimeByDate[ds] || null, score: scoreByDate[ds] ?? null });
      cur.setUTCDate(cur.getUTCDate() + 1);
    }
    weeks.push(week);
  }

  // Month labels — show label only on first week of each month
  let lastMonth = -1;
  const monthLabels = weeks.map(week => {
    const m = new Date(week[0].date + 'T00:00:00Z').getUTCMonth();
    if (m !== lastMonth) {
      lastMonth = m;
      return new Date(week[0].date + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' });
    }
    return '';
  });

  // Month change indicator (for vertical separators)
  const isMonthStart = weeks.map(week =>
    new Date(week[0].date + 'T00:00:00Z').getUTCDate() <= 7
  );

  const today  = new Date().toISOString().slice(0, 10);
  const streak = computeStreak(sorted);
  const firstLabel = sorted[0].timestamp.slice(0, 7);
  const lastLabel  = sorted[sorted.length - 1].timestamp.slice(0, 7);

  async function handleExport() {
    const resp = await api.exportRegimeCsv(isFree ? 30 : 730);
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'macropulse_regimes.csv'; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="card p-5 animate-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="label mb-1">Regime Calendar</div>
          <div style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.30)' }}>
            {firstLabel} → {lastLabel} · {sorted.length}d
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Current streak badge */}
          {streak && (
            <div
              className="flex items-center gap-1.5 px-2 py-1"
              style={{ border: `1px solid ${REGIME_CONFIG[streak.regime]?.color}44`, background: `${REGIME_CONFIG[streak.regime]?.color}08` }}
            >
              <div style={{ width: 5, height: 5, background: REGIME_CONFIG[streak.regime]?.color }} />
              <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: REGIME_CONFIG[streak.regime]?.color }}>
                {streak.days}d streak
              </span>
            </div>
          )}
          <button
            onClick={handleExport}
            style={{
              background: 'transparent', border: '1px solid #2a2a2a',
              padding: '4px 10px', cursor: 'pointer',
              color: 'rgba(255,255,255,0.40)', fontSize: 10,
              fontFamily: 'JetBrains Mono, monospace',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; e.currentTarget.style.borderColor = '#3a3a3a'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'rgba(255,255,255,0.40)'; e.currentTarget.style.borderColor = '#2a2a2a'; }}
          >
            ↓ CSV
          </button>
        </div>
      </div>

      {/* Distribution bar */}
      <DistBar sorted={sorted} />

      {/* Calendar grid */}
      <div ref={scrollRef} style={{ overflowX: 'auto', paddingBottom: 4 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start', minWidth: 'max-content' }}>
          {/* Day labels (Mon–Sun) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: GAP, paddingTop: 18, flexShrink: 0 }}>
            {['M', '', 'W', '', 'F', '', ''].map((l, i) => (
              <div key={i} style={{
                width: 10, height: CELL, lineHeight: `${CELL}px`,
                fontSize: 9, color: 'rgba(255,255,255,0.30)',
                fontFamily: 'JetBrains Mono, monospace', textAlign: 'right',
              }}>
                {l}
              </div>
            ))}
          </div>

          {/* Weeks */}
          <div>
            {/* Month labels row */}
            <div style={{ display: 'flex', gap: GAP, marginBottom: 4 }}>
              {weeks.map((_, i) => (
                <div key={i} style={{
                  width: CELL, fontSize: 9, color: monthLabels[i] ? 'rgba(255,255,255,0.45)' : 'transparent',
                  fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap', overflow: 'visible',
                  fontWeight: monthLabels[i] ? 600 : 400,
                }}>
                  {monthLabels[i]}
                </div>
              ))}
            </div>

            {/* Cell grid */}
            <div style={{ display: 'flex', gap: GAP }}>
              {weeks.map((week, wi) => (
                <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: GAP }}>
                  {week.map((day, di) => {
                    const cfg     = day.regime ? REGIME_CONFIG[day.regime] : null;
                    const isToday = day.date === today;
                    const isWknd  = di >= 5; // Sat/Sun
                    return (
                      <div
                        key={di}
                        style={{
                          width: CELL, height: CELL,
                          background: cfg
                            ? cfg.color + (isToday ? 'ff' : 'bb')
                            : isToday
                            ? 'rgba(255,255,255,0.10)'
                            : isWknd
                            ? 'rgba(255,255,255,0.02)'
                            : 'rgba(255,255,255,0.04)',
                          outline: isToday ? '2px solid rgba(255,255,255,0.75)' : 'none',
                          outlineOffset: isToday ? '-2px' : 0,
                          borderLeft: isMonthStart[wi] && di === 0 ? '1px solid #2a2a2a' : 'none',
                          cursor: cfg ? 'default' : 'default',
                          transition: 'transform 0.1s',
                          transform: 'scale(1)',
                          position: 'relative',
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.transform = 'scale(1.5)';
                          e.currentTarget.style.zIndex = '10';
                          setTooltip({
                            date: day.date, regime: day.regime,
                            label: cfg?.label ?? (isToday ? 'Today · no data' : isWknd ? 'Weekend' : 'No data'),
                            exposure: cfg ? EXPOSURE[day.regime] : null,
                            color: cfg?.color ?? 'rgba(255,255,255,0.2)',
                            score: day.score, isToday,
                          });
                          const TW = 190;
                          setTooltipPos({
                            x: e.clientX + TW + 24 > window.innerWidth ? e.clientX - TW - 8 : e.clientX + 16,
                            y: e.clientY - 64,
                          });
                        }}
                        onMouseMove={e => {
                          const TW = 190;
                          setTooltipPos({
                            x: e.clientX + TW + 24 > window.innerWidth ? e.clientX - TW - 8 : e.clientX + 16,
                            y: e.clientY - 64,
                          });
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.transform = 'scale(1)';
                          e.currentTarget.style.zIndex = '';
                          setTooltip(null);
                        }}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Free tier note */}
      {isFree && (
        <div className="mt-3 pt-3 border-t border-[#1a1a1a] flex items-center justify-between">
          <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.35)' }}>
            30-day window on Free
          </span>
          <a
            href="https://macropulse.live/pricing"
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: '#22c55e', textDecoration: 'none' }}
            onMouseEnter={e => e.target.style.textDecoration = 'underline'}
            onMouseLeave={e => e.target.style.textDecoration = 'none'}
          >
            Upgrade for 2Y history →
          </a>
        </div>
      )}

      {/* Tooltip portal */}
      {tooltip && ReactDOM.createPortal(
        <div style={{
          position: 'fixed', zIndex: 9999,
          left: tooltipPos.x, top: tooltipPos.y,
          background: '#0d0d0d',
          border: `1px solid ${tooltip.regime ? tooltip.color + '50' : '#222'}`,
          padding: '10px 14px',
          fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
          pointerEvents: 'none', minWidth: 180,
          boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
        }}>
          <div style={{ color: 'rgba(255,255,255,0.30)', fontSize: 10, marginBottom: 5 }}>
            {tooltip.date}
            {tooltip.isToday && <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 8 }}>today</span>}
          </div>
          {tooltip.regime ? (
            <>
              <div style={{ color: tooltip.color, fontWeight: 700, marginBottom: 5 }}>{tooltip.label}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {tooltip.score != null && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20 }}>
                    <span style={{ color: 'rgba(255,255,255,0.35)' }}>Risk score</span>
                    <span style={{ color: '#f0f0f0', fontWeight: 600 }}>
                      {tooltip.score > 0 ? '+' : ''}{tooltip.score.toFixed(1)}
                    </span>
                  </div>
                )}
                {tooltip.exposure && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20 }}>
                    <span style={{ color: 'rgba(255,255,255,0.35)' }}>Eq. exposure</span>
                    <span style={{ color: '#3b82f6', fontWeight: 600 }}>{tooltip.exposure}</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ color: 'rgba(255,255,255,0.40)', fontSize: 10 }}>{tooltip.label}</div>
          )}
        </div>,
        document.body
      )}
    </div>
  );
}
