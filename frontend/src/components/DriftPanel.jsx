import React from 'react';

const METRICS = [
  { key: 'pca_explained_variance', label: 'PCA Variance Drift', threshold: 0.10, fmt: 4 },
  { key: 'regime_persistence',     label: 'Regime Persistence',  threshold: 0.97, fmt: 3 },
  { key: 'feature_mean_shift',     label: 'Feature Mean Shift',  threshold: 1.5,  fmt: 3 },
  { key: 'feature_std_shift',      label: 'Feature Std Shift',   threshold: 1.5,  fmt: 3 },
];

function MetricRow({ label, value, threshold, fmt }) {
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
        <span
          className="font-mono text-[11px] font-medium"
          style={{ color: warn ? '#f59e0b' : '#22c55e' }}
        >
          {value.toFixed(fmt)}
        </span>
      </div>
      <div className="h-px bg-surface-3 overflow-hidden rounded-full">
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
    </div>
  );
}

export default function DriftPanel({ data }) {
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
            />
          );
        })}
      </div>
    </div>
  );
}
