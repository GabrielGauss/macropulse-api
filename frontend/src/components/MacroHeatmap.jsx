import React from 'react';
import { REGIME_CONFIG } from '../lib/utils';

// Historical bias matrix: asset × regime
// +2 = strong bullish, +1 = mild bullish, 0 = neutral, -1 = mild bearish, -2 = strong bearish
const BIAS = {
  //                    expansion  recovery  tightening  risk_off
  Equities:     {       expansion: 2,  recovery: 1,  tightening: -2, risk_off: -2 },
  'Long Bonds': {       expansion: -1, recovery: 2,  tightening: -2, risk_off: 2  },
  'Short Bonds':  {     expansion: 0,  recovery: 1,  tightening: 0,  risk_off: 1  },
  Gold:         {       expansion: 0,  recovery: 1,  tightening: 1,  risk_off: 2  },
  Oil:          {       expansion: 2,  recovery: 1,  tightening: 1,  risk_off: -1 },
  Dollar:       {       expansion: -1, recovery: -1, tightening: 2,  risk_off: 1  },
  Bitcoin:      {       expansion: 2,  recovery: 2,  tightening: -2, risk_off: -2 },
};

const REGIMES = ['expansion', 'recovery', 'tightening', 'risk_off'];

const LABELS = {
  2:  { text: '++', title: 'Strong Bullish' },
  1:  { text: '+',  title: 'Mild Bullish'   },
  0:  { text: '—',  title: 'Neutral'        },
  '-1': { text: '−',  title: 'Mild Bearish' },
  '-2': { text: '−−', title: 'Strong Bearish'},
};

function biasColor(value, active) {
  const opacity = active ? 1 : 0.45;
  if (value === 2)  return `rgba(34,197,94,${active ? 0.18 : 0.06})`;
  if (value === 1)  return `rgba(34,197,94,${active ? 0.09 : 0.03})`;
  if (value === 0)  return 'transparent';
  if (value === -1) return `rgba(239,68,68,${active ? 0.09 : 0.03})`;
  if (value === -2) return `rgba(239,68,68,${active ? 0.18 : 0.06})`;
  return 'transparent';
}

function textColor(value, active) {
  if (!active) {
    if (value > 0) return 'rgba(34,197,94,0.25)';
    if (value < 0) return 'rgba(239,68,68,0.25)';
    return 'rgba(255,255,255,0.1)';
  }
  if (value === 2)  return '#22c55e';
  if (value === 1)  return '#4ade80';
  if (value === 0)  return 'rgba(255,255,255,0.2)';
  if (value === -1) return '#f87171';
  if (value === -2) return '#ef4444';
  return 'rgba(255,255,255,0.2)';
}

export default function MacroHeatmap({ regime }) {
  const currentRegime = regime?.macro_regime;
  const assets = Object.keys(BIAS);

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-4">
        <div className="label">Asset × Regime Heatmap</div>
        {currentRegime && (
          <span
            className="text-[9px] font-mono uppercase tracking-wide"
            style={{ color: REGIME_CONFIG[currentRegime]?.color }}
          >
            Active: {REGIME_CONFIG[currentRegime]?.label}
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse" style={{ tableLayout: 'fixed' }}>
          <colgroup>
            <col style={{ width: '32%' }} />
            {REGIMES.map((r) => <col key={r} style={{ width: '17%' }} />)}
          </colgroup>
          <thead>
            <tr>
              <th />
              {REGIMES.map((r) => {
                const cfg = REGIME_CONFIG[r];
                const isActive = r === currentRegime;
                return (
                  <th
                    key={r}
                    className="pb-2 text-center"
                    style={{
                      fontSize: 9,
                      fontFamily: 'JetBrains Mono, monospace',
                      fontWeight: 600,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: isActive ? cfg.color : 'rgba(255,255,255,0.2)',
                      borderBottom: isActive
                        ? `1px solid ${cfg.color}55`
                        : '1px solid transparent',
                    }}
                  >
                    {cfg.short}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {assets.map((asset, ai) => (
              <tr key={asset}>
                <td
                  className="py-1.5 pr-2"
                  style={{
                    fontSize: 10,
                    fontFamily: 'JetBrains Mono, monospace',
                    color: 'rgba(255,255,255,0.4)',
                    borderBottom: ai < assets.length - 1 ? '1px solid #111' : 'none',
                  }}
                >
                  {asset}
                </td>
                {REGIMES.map((r) => {
                  const val = BIAS[asset][r];
                  const isActive = r === currentRegime;
                  const meta = LABELS[String(val)];
                  return (
                    <td
                      key={r}
                      className="py-1.5 text-center"
                      title={meta?.title}
                      style={{
                        fontSize: 10,
                        fontFamily: 'JetBrains Mono, monospace',
                        fontWeight: 600,
                        background: biasColor(val, isActive),
                        color: textColor(val, isActive),
                        borderLeft: isActive ? `1px solid ${REGIME_CONFIG[r]?.color}18` : 'none',
                        borderRight: isActive ? `1px solid ${REGIME_CONFIG[r]?.color}18` : 'none',
                        borderBottom: ai < assets.length - 1 ? '1px solid #111' : 'none',
                      }}
                    >
                      {meta?.text}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-[#1a1a1a] flex-wrap">
        {[
          { label: '++ Strong Bull', color: '#22c55e' },
          { label: '+ Mild Bull',    color: '#4ade80' },
          { label: '— Neutral',      color: 'rgba(255,255,255,0.2)' },
          { label: '− Mild Bear',    color: '#f87171' },
          { label: '−− Strong Bear', color: '#ef4444' },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1">
            <span className="font-mono text-[9px] font-semibold" style={{ color: l.color }}>
              {l.label.split(' ')[0]}
            </span>
            <span className="text-[8px] text-white/15 font-mono">{l.label.split(' ').slice(1).join(' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
