import React from 'react';
import { REGIME_CONFIG, formatDate, riskColor, confidenceBadge, EQUITY_EXPOSURE } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

export default function RegimeCard({ regime }) {
  if (!regime) {
    return (
      <div className="card p-6 animate-pulse">
        <div className="h-4 w-32 rounded bg-surface-3 mb-3" />
        <div className="h-8 w-48 rounded bg-surface-3 mb-6" />
        <div className="h-2 w-full rounded bg-surface-3" />
      </div>
    );
  }

  const cfg   = REGIME_CONFIG[regime.macro_regime] || REGIME_CONFIG.expansion;
  const score = regime.risk_score ?? 0;
  const conf  = confidenceBadge(regime.confidence ?? null);
  const guideMode = useGuideMode();

  // Conviction = dominant state probability (max of all 4 probs)
  const probs = regime.probabilities || {};
  const conviction = Object.values(probs).length
    ? Math.max(...Object.values(probs))
    : null;
  const convictionLabel = conviction == null ? null
    : conviction >= 0.80 ? 'high'
    : conviction >= 0.60 ? 'transitioning'
    : 'ambiguous';
  const convictionColor = conviction == null ? '#555'
    : conviction >= 0.80 ? '#22c55e'
    : conviction >= 0.60 ? '#f59e0b'
    : '#ef4444';

  // gauge: score from -100 to +100, bar starts at center (50%)
  const gaugeOffset = score < 0 ? (50 - Math.abs(score) / 2) : 50;
  const gaugeWidth  = Math.abs(score) / 2;

  return (
    <div className="card p-5 animate-in">
      {/* Top row: regime name + meta */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <div className="flex items-center gap-3">
          <div
            className="w-1 rounded-full self-stretch flex-shrink-0"
            style={{ background: cfg.color }}
          />
          <div>
            <div className="label mb-1">Current Macro Regime</div>
            <h2 className="text-2xl font-bold tracking-tight" style={{ color: cfg.color }}>
              {cfg.label}
            </h2>
            <div className="text-[11px] text-white/50 font-mono mt-0.5">
              <span className="text-white/45 mr-1">as of</span>{formatDate(new Date())}
            </div>
            {guideMode && (
              <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 5, maxWidth: 280, lineHeight: 1.5 }}>
                HMM outputs 4 regime states from daily PCA factors. "as of" = last pipeline run (daily, ~6 AM UTC). Score &gt; 0 = risk-on bias; &lt; 0 = risk-off.
              </div>
            )}
          </div>
        </div>

        {/* Confidence + model */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          {regime.confidence && (
            <div
              className="inline-flex items-center rounded px-2 py-0.5 text-[11px] font-medium font-mono uppercase tracking-wide"
              style={{ background: conf.bg, color: conf.color }}
            >
              {regime.confidence}
            </div>
          )}
          {regime.model_version && (
            <span className="text-[10px] text-white/45 font-mono">{regime.model_version}</span>
          )}
        </div>
      </div>

      {/* Risk score gauge */}
      <div className="mb-5">
        <div className="flex items-baseline justify-between mb-1.5">
          <span className="text-[11px] text-white/50 uppercase tracking-wider font-medium">Risk Score</span>
          <span className="font-mono text-xl font-semibold" style={{ color: riskColor(score) }}>
            {score > 0 ? '+' : ''}{score.toFixed(1)}
          </span>
        </div>
        <div className="relative h-1.5 rounded-full bg-surface-3 overflow-hidden">
          {/* Center reference */}
          <div className="absolute top-0 bottom-0 w-px bg-surface-4" style={{ left: '50%' }} />
          <div
            className="absolute top-0 h-full rounded-full transition-all duration-700"
            style={{
              left: `${gaugeOffset}%`,
              width: `${gaugeWidth}%`,
              background: riskColor(score),
            }}
          />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-white/45 font-mono">
          <span>−100</span>
          <span>0</span>
          <span>+100</span>
        </div>
      </div>

      {/* Probability bars — horizontal, compact */}
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(regime.probabilities || {}).map(([key, val]) => {
          const rc = REGIME_CONFIG[key];
          if (!rc) return null;
          const isActive = key === regime.macro_regime;
          return (
            <div
              key={key}
              className="rounded px-3 py-2.5"
              style={{
                background: isActive ? rc.bg : 'rgba(255,255,255,0.02)',
                border: `1px solid ${isActive ? rc.color + '33' : '#1f1f1f'}`,
              }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] text-white/40 font-medium">{rc.label}</span>
                <span className="font-mono text-xs font-semibold" style={{ color: rc.color }}>
                  {(val * 100).toFixed(0)}%
                </span>
              </div>
              <div className="h-0.5 rounded-full bg-surface-3">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${val * 100}%`, background: rc.color }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Equity Exposure */}
      {(() => {
        const exposure = EQUITY_EXPOSURE[regime.macro_regime];
        if (exposure === undefined) return null;
        const pct = Math.round(exposure * 100);
        const expColor = pct >= 75 ? '#22c55e' : pct >= 25 ? '#f59e0b' : '#ef4444';
        return (
          <div className="mt-3 pt-3 border-t border-[#1f1f1f]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] text-white/50 uppercase tracking-wider font-medium">Eq. Exposure</span>
              <span className="font-mono text-lg font-semibold" style={{ color: expColor }}>{pct}%</span>
            </div>
            <div className="relative h-1.5 rounded-full bg-surface-3 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, background: expColor }}
              />
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-white/45 font-mono">
              <span>0% Risk-Off</span>
              <span>100% Expansion</span>
            </div>
          </div>
        );
      })()}

      {/* Conviction */}
      {conviction != null && (
        <div className="mt-3 pt-3 border-t border-[#1f1f1f]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-white/50 uppercase tracking-wider font-medium">Signal Conviction</span>
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] font-mono uppercase tracking-wide px-1.5 py-0.5 rounded"
                style={{ color: convictionColor, border: `1px solid ${convictionColor}44`, background: `${convictionColor}10` }}
              >
                {convictionLabel}
              </span>
              <span className="font-mono text-base font-semibold" style={{ color: convictionColor }}>
                {(conviction * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <div className="relative h-1 rounded-full bg-surface-3 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${conviction * 100}%`, background: convictionColor }}
            />
          </div>
          {guideMode && (
            <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 4, lineHeight: 1.5 }}>
              Conviction = dominant state probability. &gt;80% = high confidence. 60–80% = transitioning. &lt;60% = treat as noise.
            </div>
          )}
        </div>
      )}

      {/* Persistence */}
      {regime.persistence_days != null && (
        <div className="mt-3 pt-3 border-t border-[#1f1f1f] flex gap-4 text-[11px]">
          <span className="text-white/50">
            Persistent for <span className="text-white/70 font-mono">{regime.persistence_days}d</span>
          </span>
          {regime.volatility_state && (
            <span className="text-white/50">
              Vol: <span className="text-white/70">{regime.volatility_state}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}
