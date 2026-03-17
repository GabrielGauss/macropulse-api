import React from 'react';
import { useGuideMode } from '../lib/guideMode';

const METRICS = [
  {
    key: 'pca_explained_variance', label: 'PCA Variance Drift', threshold: 0.10, fmt: 4,
    guide: 'How much the principal component loadings have shifted since calibration. Below 0.10 = factor structure stable — the model is reading the same macro signals.',
    warnText: 'Factor loadings shifted. Model may mis-classify regime; consider recalibration.',
  },
  {
    key: 'regime_persistence', label: 'Regime Persistence', threshold: 0.97, fmt: 3,
    guide: 'Fraction of rolling windows where the current regime would be re-confirmed. High (≥ 0.97) = stable, confident signal. Low = regime boundary / transition noise.',
    warnText: 'Low persistence: regime may be in transition. Signal confidence reduced.',
  },
  {
    key: 'feature_mean_shift', label: 'Feature Mean Shift', threshold: 1.5, fmt: 3,
    guide: 'Z-score of current feature means vs training-window distribution. Above 1.5 = macro environment is outside historical norms the model was trained on.',
    warnText: 'Distribution shift detected. Current macro conditions diverge from training history.',
  },
  {
    key: 'feature_std_shift', label: 'Feature Volatility Shift', threshold: 1.5, fmt: 3,
    guide: 'Z-score of current feature volatility vs training history. Above 1.5 = volatility regime change — signals are noisier than the model expects.',
    warnText: 'Volatility regime change. Feature noise elevated; signal-to-noise ratio lower.',
  },
];

function MetricRow({ label, value, threshold, fmt, guide, warnText, showGuide }) {
  const warn = value > threshold;
  const pct  = Math.min((value / (threshold * 1.5)) * 100, 100);
  return (
    <div className="py-3 border-b border-[#1f1f1f] last:border-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="h-1.5 w-1.5 rounded-full flex-shrink-0"
            style={{ background: warn ? '#f59e0b' : '#22c55e' }}
          />
          <span className="text-[11px] text-white/50">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          {warn && (
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: 'rgba(245,158,11,0.08)', color: '#f59e0b' }}>
              alert
            </span>
          )}
          <span
            className="font-mono text-[11px] font-medium"
            style={{ color: warn ? '#f59e0b' : '#22c55e' }}
          >
            {value.toFixed(fmt)}
          </span>
        </div>
      </div>
      <div className="h-1 bg-surface-3 overflow-hidden rounded-full">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: warn ? '#f59e0b' : '#22c55e',
            opacity: 0.7,
          }}
        />
      </div>
      <div className="flex justify-between mt-0.5 text-[9px] font-mono text-white/15">
        <span>0</span>
        <span>threshold {threshold}</span>
      </div>
      {showGuide && (
        <div style={{ fontSize: 9, color: warn ? 'rgba(245,158,11,0.6)' : 'rgba(59,130,246,0.6)', fontFamily: 'JetBrains Mono, monospace', marginTop: 5, lineHeight: 1.5 }}>
          {warn ? warnText : guide}
        </div>
      )}
    </div>
  );
}

export default function DriftPanel({ data }) {
  const guideMode = useGuideMode();

  if (!data?.data?.length) {
    return (
      <div className="card flex h-48 items-center justify-center">
        <p className="text-[11px] text-white/25 font-mono">No drift data</p>
      </div>
    );
  }

  const latest = data.data[0];
  const alerts = METRICS.filter(m => latest[m.key] != null && latest[m.key] > m.threshold);
  const allOk  = alerts.length === 0;

  return (
    <div className="card p-5 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="label">Model Health</div>
        <div
          className="flex items-center gap-1.5 rounded px-2 py-0.5"
          style={{
            background: allOk ? 'rgba(34,197,94,0.08)' : 'rgba(245,158,11,0.08)',
            border: `1px solid ${allOk ? '#22c55e33' : '#f59e0b33'}`,
          }}
        >
          <div
            className="h-1.5 w-1.5 rounded-full flex-shrink-0"
            style={{ background: allOk ? '#22c55e' : '#f59e0b' }}
          />
          <span
            className="text-[10px] font-medium font-mono uppercase tracking-wide"
            style={{ color: allOk ? '#22c55e' : '#f59e0b' }}
          >
            {allOk ? 'Nominal' : `${alerts.length} Alert${alerts.length > 1 ? 's' : ''}`}
          </span>
        </div>
      </div>

      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 8, lineHeight: 1.5 }}>
          Monitors model stability. Green = within calibration bounds. Amber alert = investigate before trading on signals.
        </div>
      )}

      {latest.model_version && (
        <div className="text-[10px] text-white/20 font-mono mb-3">{latest.model_version}</div>
      )}

      <div>
        {METRICS.map((m) => {
          const val = latest[m.key];
          if (val == null) return null;
          return (
            <MetricRow
              key={m.key}
              label={m.label}
              value={val}
              threshold={m.threshold}
              fmt={m.fmt}
              guide={m.guide}
              warnText={m.warnText}
              showGuide={guideMode}
            />
          );
        })}
      </div>
    </div>
  );
}
