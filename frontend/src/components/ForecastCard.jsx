import React, { useCallback } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

function formatForecastDate(dateStr) {
  // dateStr is "2026-03-18" — parse as local to avoid UTC offset shifting the day
  const [year, month, day] = dateStr.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getDominantRegime(row) {
  const candidates = [
    { key: 'expansion',  prob: row.prob_expansion },
    { key: 'tightening', prob: row.prob_tightening },
    { key: 'risk_off',   prob: row.prob_risk_off },
    { key: 'recovery',   prob: row.prob_recovery },
  ];
  return candidates.reduce((best, c) => (c.prob > best.prob ? c : best), candidates[0]);
}

function riskScoreColor(score) {
  if (score > 20) return '#22c55e';
  if (score >= 0) return '#f59e0b';
  return '#ef4444';
}

const LEGEND_KEYS = ['expansion', 'recovery', 'tightening', 'risk_off'];

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-[#1a1a1a]">
      <div className="h-2.5 rounded" style={{ width: 44, background: 'rgba(255,255,255,0.06)' }} />
      <div className="flex-1 flex items-center gap-2">
        <div className="h-2 w-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }} />
        <div className="h-2.5 rounded" style={{ width: 56, background: 'rgba(255,255,255,0.06)' }} />
      </div>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }} />
      <div className="h-2.5 rounded" style={{ width: 32, background: 'rgba(255,255,255,0.06)' }} />
    </div>
  );
}

function ForecastRow({ row }) {
  const dominant = getDominantRegime(row);
  const cfg = REGIME_CONFIG[dominant.key] || {};
  const scoreColor = riskScoreColor(row.risk_score);

  // Stacked bar segments
  const segments = [
    { key: 'expansion',  prob: row.prob_expansion },
    { key: 'recovery',   prob: row.prob_recovery },
    { key: 'tightening', prob: row.prob_tightening },
    { key: 'risk_off',   prob: row.prob_risk_off },
  ];

  return (
    <div className="flex items-center gap-3 py-2 border-b border-[#1a1a1a] last:border-0">
      {/* Date */}
      <div
        className="flex-shrink-0 text-[10px] font-mono"
        style={{ width: 44, color: 'rgba(255,255,255,0.35)' }}
      >
        {formatForecastDate(row.date)}
      </div>

      {/* Dominant regime */}
      <div className="flex items-center gap-1.5 flex-shrink-0" style={{ width: 96 }}>
        <div
          className="h-1.5 w-1.5 rounded-full flex-shrink-0"
          style={{ background: cfg.color || '#555' }}
        />
        <span
          className="text-[10px] font-mono font-medium"
          style={{ color: cfg.color || 'rgba(255,255,255,0.4)' }}
        >
          {cfg.label || dominant.key}
        </span>
      </div>

      {/* Stacked mini-bar */}
      <div className="flex-1 overflow-hidden rounded-full" style={{ height: 6, minWidth: 0 }}>
        <div className="flex h-full w-full">
          {segments.map(seg => {
            const segCfg = REGIME_CONFIG[seg.key] || {};
            const widthPct = (seg.prob * 100).toFixed(2);
            return (
              <div
                key={seg.key}
                style={{
                  width: `${widthPct}%`,
                  background: segCfg.color || '#555',
                  flexShrink: 0,
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Risk score */}
      <div
        className="flex-shrink-0 text-[10px] font-mono font-medium text-right"
        style={{ width: 36, color: scoreColor }}
      >
        {row.risk_score.toFixed(1)}
      </div>
    </div>
  );
}

export default function ForecastCard() {
  const guideMode = useGuideMode();
  const fetchForecast = useCallback(() => api.getForecast(5), []);
  const { data, loading, error } = useFetch(fetchForecast);

  return (
    <div className="card p-5 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="label">5-Day Forecast</div>
        <span
          className="text-[10px] font-mono"
          style={{ color: 'rgba(255,255,255,0.50)' }}
        >
          ARIMA · 5d ahead
        </span>
      </div>

      {guideMode && (
        <div
          style={{
            fontSize: 10,
            color: 'rgba(59,130,246,0.7)',
            fontFamily: 'JetBrains Mono, monospace',
            marginBottom: 10,
            lineHeight: 1.6,
          }}
        >
          ARIMA(1,0,1) forward projection of HMM state probabilities. Dominant state = highest probability. Risk score trend indicates momentum direction.
        </div>
      )}

      {/* Column headers */}
      <div className="flex items-center gap-3 pb-1 mb-0.5">
        <div className="flex-shrink-0 text-[10px] font-mono uppercase tracking-wide" style={{ width: 44, color: 'rgba(255,255,255,0.45)' }}>Date</div>
        <div className="flex-shrink-0 text-[10px] font-mono uppercase tracking-wide" style={{ width: 96, color: 'rgba(255,255,255,0.45)' }}>Regime</div>
        <div className="flex-1 text-[10px] font-mono uppercase tracking-wide" style={{ color: 'rgba(255,255,255,0.45)' }}>Probability mix</div>
        <div className="flex-shrink-0 text-[10px] font-mono uppercase tracking-wide text-right" style={{ width: 36, color: 'rgba(255,255,255,0.45)' }}>Risk</div>
      </div>

      {/* Body */}
      {loading && (
        <div>
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      )}

      {error && !loading && (
        <p
          className="text-[11px] font-mono py-4 text-center"
          style={{ color: 'rgba(255,255,255,0.50)' }}
        >
          Forecast unavailable
        </p>
      )}

      {data?.forecast && !loading && (
        <div>
          {data.forecast.map((row) => (
            <ForecastRow key={row.date} row={row} />
          ))}
        </div>
      )}

      {/* Legend */}
      {!loading && !error && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 pt-2.5 border-t border-[#1a1a1a]">
          {LEGEND_KEYS.map(key => {
            const cfg = REGIME_CONFIG[key];
            return (
              <div key={key} className="flex items-center gap-1">
                <div className="h-1.5 w-1.5 rounded-full" style={{ background: cfg.color }} />
                <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.50)' }}>
                  {cfg.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
