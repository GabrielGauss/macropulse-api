import React, { useCallback, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { REGIME_CONFIG } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

// ── Heatmap cell colors ───────────────────────────────────────────────────────
function heatColor(value, min, max) {
  const t = max === min ? 0.5 : (value - min) / (max - min);
  if (t < 0.5) {
    const p = t * 2;
    return `rgba(239,68,68,${0.08 + p * 0.55})`;   // red (low / negative)
  } else {
    const p = (t - 0.5) * 2;
    return `rgba(34,197,94,${0.08 + p * 0.55})`;    // green (high / positive)
  }
}

// ── Transition Matrix ─────────────────────────────────────────────────────────
function TransitionMatrix({ data }) {
  const guideMode = useGuideMode();
  if (!data?.matrix) return null;

  const { regimes, matrix } = data;
  const cfgMap = (r) => REGIME_CONFIG[r] || { color: '#888', label: r };

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="label">HMM Transition Matrix</div>
        <span className="text-[10px] text-white/45 font-mono">daily P(from → to)</span>
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono', marginBottom: 8, lineHeight: 1.5 }}>
          Each cell = P(next regime | current regime). Diagonal = persistence. Rows sum to 1.0. Darker green = higher probability.
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 4 }}>
          <thead>
            <tr>
              <th style={{ width: 90, textAlign: 'left', fontSize: 10, color: 'rgba(255,255,255,0.45)', fontFamily: 'JetBrains Mono', fontWeight: 400, paddingBottom: 4 }}>from \ to</th>
              {regimes.map(r => (
                <th key={r} style={{ fontSize: 9, fontFamily: 'JetBrains Mono', fontWeight: 500, color: cfgMap(r).color, textAlign: 'center', paddingBottom: 4 }}>
                  {r.replace('_', '-')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={row.from}>
                <td style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: cfgMap(row.from).color, fontWeight: 500, paddingRight: 8 }}>
                  {row.from.replace('_', '-')}
                </td>
                {regimes.map(r => {
                  const v = row.to[r] ?? 0;
                  return (
                    <td
                      key={r}
                      title={`${row.from} → ${r}: ${(v * 100).toFixed(1)}%`}
                      style={{
                        background: heatColor(v, 0, 1),
                        borderRadius: 4,
                        textAlign: 'center',
                        fontSize: 10,
                        fontFamily: 'JetBrains Mono',
                        color: v > 0.3 ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.4)',
                        padding: '6px 4px',
                        minWidth: 56,
                      }}
                    >
                      {(v * 100).toFixed(1)}%
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── PCA Feature Loadings Heatmap ──────────────────────────────────────────────
function FeatureLoadings({ data }) {
  const guideMode = useGuideMode();
  if (!data?.factors) return null;

  const { factors, feature_names, total_variance_explained } = data;

  // Find global min/max for consistent color scale
  const allVals = factors.flatMap(f => Object.values(f.loadings));
  const minVal = Math.min(...allVals);
  const maxVal = Math.max(...allVals);

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="label">PCA Feature Loadings</div>
        <span className="text-[10px] text-white/45 font-mono">
          {(total_variance_explained * 100).toFixed(0)}% variance explained
        </span>
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono', marginBottom: 8, lineHeight: 1.5 }}>
          F1–F4 are latent macro factors. Large loadings = feature drives that factor. Green = positive contribution. Red = negative. F1 typically captures the liquidity/monetary axis.
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 3 }}>
          <thead>
            <tr>
              <th style={{ width: 40, textAlign: 'left', fontSize: 10, color: 'rgba(255,255,255,0.45)', fontFamily: 'JetBrains Mono', fontWeight: 400, paddingBottom: 4 }}>factor</th>
              {feature_names.map(f => (
                <th key={f} style={{ fontSize: 9, fontFamily: 'JetBrains Mono', fontWeight: 400, color: 'rgba(255,255,255,0.50)', textAlign: 'center', paddingBottom: 4, transform: 'none' }}>
                  {f.replace('d_', '')}
                </th>
              ))}
              <th style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)', fontFamily: 'JetBrains Mono', fontWeight: 400, paddingLeft: 8 }}>var%</th>
            </tr>
          </thead>
          <tbody>
            {factors.map(fac => (
              <tr key={fac.factor}>
                <td style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: '#3b82f6', fontWeight: 600, paddingRight: 6 }}>
                  {fac.factor}
                </td>
                {feature_names.map(fname => {
                  const v = fac.loadings[fname] ?? 0;
                  return (
                    <td
                      key={fname}
                      title={`${fac.factor} × ${fname}: ${v.toFixed(3)}`}
                      style={{
                        background: heatColor(v, minVal, maxVal),
                        borderRadius: 3,
                        textAlign: 'center',
                        fontSize: 9,
                        fontFamily: 'JetBrains Mono',
                        color: Math.abs(v) > 0.3 ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.3)',
                        padding: '5px 3px',
                        minWidth: 48,
                      }}
                    >
                      {v.toFixed(2)}
                    </td>
                  );
                })}
                <td style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: '#3b82f6', paddingLeft: 8, opacity: 0.7 }}>
                  {(fac.explained_variance * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Soft State Probabilities Timeline ────────────────────────────────────────
function ProbabilityTimeline({ data }) {
  const guideMode = useGuideMode();

  const series = useMemo(() => {
    if (!data?.series) return [];
    return data.series.slice(-180); // last 180 days
  }, [data]);

  if (!series.length) return null;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="label">Soft State Probabilities</div>
        <span className="text-[10px] text-white/45 font-mono">stacked · last 180d</span>
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono', marginBottom: 8, lineHeight: 1.5 }}>
          Unlike the binary regime timeline, this shows all 4 probability streams simultaneously. When the dominant band narrows, the model is less certain — regime change risk is elevated.
        </div>
      )}
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={series} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="date" tick={TICK} tickLine={false} interval="preserveStartEnd"
            tickFormatter={v => v?.slice(5)} />
          <YAxis tick={TICK} tickLine={false} domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div style={{ background: '#141414', border: '1px solid #2a2a2a', borderRadius: 6, padding: '8px 12px', fontSize: 11, fontFamily: 'JetBrains Mono' }}>
                  <div style={{ color: 'rgba(255,255,255,0.3)', marginBottom: 4 }}>{label}</div>
                  {payload.slice().reverse().map(p => (
                    <div key={p.dataKey} style={{ color: p.fill }}>
                      {p.name}: {(p.value * 100).toFixed(1)}%
                    </div>
                  ))}
                </div>
              );
            }}
          />
          <Area type="monotone" dataKey="prob_expansion"  stackId="1" stroke={REGIME_CONFIG.expansion.color}  fill={REGIME_CONFIG.expansion.bg}  fillOpacity={1} name="Expansion"  strokeWidth={1} />
          <Area type="monotone" dataKey="prob_recovery"   stackId="1" stroke={REGIME_CONFIG.recovery.color}   fill={REGIME_CONFIG.recovery.bg}   fillOpacity={1} name="Recovery"   strokeWidth={1} />
          <Area type="monotone" dataKey="prob_tightening" stackId="1" stroke={REGIME_CONFIG.tightening.color} fill={REGIME_CONFIG.tightening.bg} fillOpacity={1} name="Tightening" strokeWidth={1} />
          <Area type="monotone" dataKey="prob_risk_off"   stackId="1" stroke={REGIME_CONFIG.risk_off.color}   fill={REGIME_CONFIG.risk_off.bg}   fillOpacity={1} name="Risk-Off"   strokeWidth={1} />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2">
        {Object.entries(REGIME_CONFIG).map(([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div style={{ width: 8, height: 8, borderRadius: 2, background: cfg.color }} />
            <span style={{ fontSize: 10, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.50)' }}>{cfg.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main QuantView ────────────────────────────────────────────────────────────
export default function QuantView() {
  const fetchMatrix   = useCallback(() => api.getTransitionMatrix(), []);
  const fetchLoadings = useCallback(() => api.getFeatureLoadings(), []);
  const fetchProbs    = useCallback(() => api.getProbabilitySeries(365), []);

  const matrix   = useFetch(fetchMatrix);
  const loadings = useFetch(fetchLoadings);
  const probs    = useFetch(fetchProbs);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold">Quant HUD</h2>
        <span className="text-[10px] text-white/50 font-mono">model internals · HMM · PCA</span>
      </div>

      {matrix.loading || loadings.loading || probs.loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="card p-5 animate-pulse" style={{ height: 200 }} />
          ))}
        </div>
      ) : matrix.error ? (
        <div className="card p-6 text-center">
          <div className="text-[11px] text-white/30 font-mono">
            Model artifacts unavailable. Run the daily pipeline to generate them.
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <ProbabilityTimeline data={probs.data} />
          <TransitionMatrix data={matrix.data} />
          <FeatureLoadings data={loadings.data} />
        </div>
      )}
    </div>
  );
}
