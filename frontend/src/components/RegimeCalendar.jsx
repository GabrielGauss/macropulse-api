import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

const EXPOSURE = {
  expansion: '100%', recovery: '75%', tightening: '25%', risk_off: '0%',
};

const REGIME_DESC = {
  expansion:  'Growth accelerating, risk assets favored. 100% equity exposure.',
  recovery:   'Recovery phase, early-cycle. 75% equity exposure.',
  tightening: 'Fed tightening, growth slowing. 25% equity exposure.',
  risk_off:   'Risk-off: defensive posture. 0% equity exposure.',
};

export default function RegimeCalendar({ isFree = false }) {
  const maxDays = isFree ? 30 : 730;
  const fetchFull = useCallback(() => api.getRegimeHistory(maxDays), [maxDays]);
  const { data: raw, loading } = useFetch(fetchFull);
  const [tooltip, setTooltip] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const scrollRef = useRef(null);
  const guideMode = useGuideMode();

  // Must be before any early returns (Rules of Hooks)
  useEffect(() => {
    if (!raw || raw.length === 0 || !scrollRef.current) return;
    const CELL = 13, GAP = 2;
    const sorted2 = [...raw].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    const firstDate = new Date(sorted2[0].timestamp.slice(0, 10) + 'T00:00:00Z');
    const startDay = new Date(firstDate);
    const dow = startDay.getUTCDay();
    startDay.setUTCDate(startDay.getUTCDate() - (dow === 0 ? 6 : dow - 1));
    const today = new Date().toISOString().slice(0, 10);
    const todayDate = new Date(today + 'T00:00:00Z');
    const weeksUntilToday = Math.floor((todayDate - startDay) / (7 * 86400000));
    const pixelsPerWeek = CELL + GAP;
    scrollRef.current.scrollLeft = Math.max(0, weeksUntilToday * pixelsPerWeek - scrollRef.current.clientWidth + 80);
  }, [raw]);

  if (loading) {
    return (
      <div className="card p-5">
        <div className="label mb-4">Regime Calendar</div>
        <div className="h-32 flex items-center justify-center">
          <span className="text-[11px] text-white/45 font-mono">Loading…</span>
        </div>
      </div>
    );
  }

  if (!raw || raw.length === 0) {
    return (
      <div className="card p-5">
        <div className="label mb-4">Regime Calendar</div>
        <div className="h-32 flex items-center justify-center">
          <span className="text-[11px] text-white/45 font-mono">No data</span>
        </div>
      </div>
    );
  }

  const sorted = [...raw].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const regimeByDate = {};
  const scoreByDate = {};
  sorted.forEach(d => {
    const ds = d.timestamp.slice(0, 10);
    regimeByDate[ds] = d.macro_regime;
    scoreByDate[ds] = d.risk_score;
  });

  // First Monday on/before first data point
  const firstDate = new Date(sorted[0].timestamp.slice(0, 10) + 'T00:00:00Z');
  const startDay = new Date(firstDate);
  const dow = startDay.getUTCDay();
  startDay.setUTCDate(startDay.getUTCDate() - (dow === 0 ? 6 : dow - 1));

  // Sunday on/after last data point
  const lastDate = new Date(sorted[sorted.length - 1].timestamp.slice(0, 10) + 'T00:00:00Z');
  const endDay = new Date(lastDate);
  const edow = endDay.getUTCDay();
  if (edow !== 0) endDay.setUTCDate(endDay.getUTCDate() + (7 - edow));

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

  let lastMonth = -1;
  const monthLabels = weeks.map(week => {
    const m = new Date(week[0].date + 'T00:00:00Z').getUTCMonth();
    if (m !== lastMonth) {
      lastMonth = m;
      return new Date(week[0].date + 'T00:00:00Z').toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' });
    }
    return '';
  });

  const CELL = 13;
  const GAP = 2;
  const today = new Date().toISOString().slice(0, 10);


  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-1">
        <div className="label">Regime Calendar</div>
        <div className="flex items-center gap-3">
          {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
            <div key={key} className="flex items-center gap-1">
              <div className="rounded-sm flex-shrink-0" style={{ width: 8, height: 8, background: cfg.color }} />
              <span className="text-[10px] text-white/50 font-mono uppercase">{cfg.short}</span>
            </div>
          ))}
        </div>
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 10, lineHeight: 1.5 }}>
          Each cell = one trading day. Color = active macro regime. White ring = today. Hover for date, regime, risk score and equity allocation.
        </div>
      )}
      {!guideMode && <div className="mb-3" />}

      <div ref={scrollRef} style={{ overflowX: 'auto', paddingBottom: 4 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start', minWidth: 'max-content' }}>
          {/* Day labels */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: GAP, paddingTop: 18, flexShrink: 0 }}>
            {['M', '', 'W', '', 'F', '', 'S'].map((l, i) => (
              <div key={i} style={{ width: 10, height: CELL, lineHeight: `${CELL}px`, fontSize: 10, color: 'rgba(255,255,255,0.45)', fontFamily: 'JetBrains Mono, monospace', textAlign: 'right' }}>
                {l}
              </div>
            ))}
          </div>

          {/* Grid */}
          <div>
            <div style={{ display: 'flex', gap: GAP, marginBottom: 4 }}>
              {weeks.map((_, i) => (
                <div key={i} style={{ width: CELL, fontSize: 10, color: 'rgba(255,255,255,0.50)', fontFamily: 'JetBrains Mono, monospace', whiteSpace: 'nowrap', overflow: 'visible' }}>
                  {monthLabels[i]}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: GAP }}>
              {weeks.map((week, wi) => (
                <div key={wi} style={{ display: 'flex', flexDirection: 'column', gap: GAP }}>
                  {week.map((day, di) => {
                    const cfg = day.regime ? REGIME_CONFIG[day.regime] : null;
                    const isToday = day.date === today;
                    return (
                      <div
                        key={di}
                        style={{
                          width: CELL, height: CELL, borderRadius: 3,
                          background: cfg ? cfg.color + (isToday ? 'ff' : 'cc') : isToday ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)',
                          outline: isToday ? '2px solid rgba(255,255,255,0.7)' : 'none',
                          outlineOffset: isToday ? '-2px' : '0',
                          cursor: cfg ? 'default' : 'default',
                          transition: 'opacity 0.1s, transform 0.1s',
                          transform: 'scale(1)',
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.transform = 'scale(1.4)';
                          e.currentTarget.style.zIndex = '10';
                          const score = day.score;
                          setTooltip({
                            date: day.date,
                            label: cfg?.label ?? (isToday ? 'Today (no data)' : 'Weekend / No data'),
                            exposure: cfg ? EXPOSURE[day.regime] : null,
                            color: cfg?.color ?? 'rgba(255,255,255,0.3)',
                            regime: day.regime,
                            score,
                            isToday,
                          });
                          const TW = 200;
                          const x = e.clientX + TW + 24 > window.innerWidth ? e.clientX - TW - 8 : e.clientX + 16;
                          setTooltipPos({ x, y: e.clientY - 60 });
                        }}
                        onMouseMove={e => {
                          const TW = 200;
                          const x = e.clientX + TW + 24 > window.innerWidth ? e.clientX - TW - 8 : e.clientX + 16;
                          setTooltipPos({ x, y: e.clientY - 60 });
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

      {/* Hover tooltip — rendered via portal to escape animate-in stacking context */}
      {tooltip && ReactDOM.createPortal(
        <div style={{
          position: 'fixed', zIndex: 9999,
          left: tooltipPos.x, top: tooltipPos.y,
          background: '#0d0d0d',
          border: `1px solid ${tooltip.regime ? tooltip.color + '50' : '#222'}`,
          borderRadius: 8, padding: '9px 13px',
          fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
          pointerEvents: 'none', minWidth: 180,
          boxShadow: '0 8px 32px rgba(0,0,0,0.7)',
        }}>
          <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, marginBottom: 5 }}>
            {tooltip.date}{tooltip.isToday && <span style={{ color: 'rgba(255,255,255,0.5)', marginLeft: 6 }}>← today</span>}
          </div>
          {tooltip.regime ? (
            <>
              <div style={{ color: tooltip.color, fontWeight: 700, marginBottom: 4 }}>{tooltip.label}</div>
              {tooltip.score != null && (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>Risk score</span>
                  <span style={{ color: '#f0f0f0', fontWeight: 600 }}>
                    {tooltip.score > 0 ? '+' : ''}{tooltip.score.toFixed(1)}
                  </span>
                </div>
              )}
              {tooltip.exposure && (
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginTop: 3 }}>
                  <span style={{ color: 'rgba(255,255,255,0.3)' }}>Eq. exposure</span>
                  <span style={{ color: '#3b82f6', fontWeight: 600 }}>{tooltip.exposure}</span>
                </div>
              )}
              <div style={{ color: 'rgba(255,255,255,0.50)', fontSize: 10, marginTop: 5, lineHeight: 1.5 }}>
                {REGIME_DESC[tooltip.regime]}
              </div>
            </>
          ) : (
            <div style={{ color: 'rgba(255,255,255,0.50)', fontSize: 10 }}>{tooltip.label}</div>
          )}
        </div>,
        document.body
      )}

      {isFree && (
        <p className="text-[10px] text-white/45 font-mono mt-3">
          30-day window ·{' '}
          <a href="https://macropulse.live/#pricing" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'underline', color: 'inherit' }}>
            upgrade for 2Y history →
          </a>
        </p>
      )}
    </div>
  );
}
