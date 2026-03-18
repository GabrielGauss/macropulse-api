import React, { useState } from 'react';
import { REGIME_CONFIG } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

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

// Per-cell explanations for tooltip
const RATIONALE = {
  Equities: {
    expansion: 'Growth + loose policy = earnings up, multiples expand.',
    recovery: 'Recession behind us; early-cycle momentum favors equities.',
    tightening: 'Rising rates compress P/E multiples and slow growth.',
    risk_off: 'Flight to safety. Equity risk premium collapses.',
  },
  'Long Bonds': {
    expansion: 'Strong growth keeps rates elevated, pressuring duration.',
    recovery: 'Rates falling as Fed pivots. Duration performs well.',
    tightening: 'Fed hiking = bond prices fall hardest at long end.',
    risk_off: 'Safe-haven bid drives yields down, prices up.',
  },
  'Short Bonds': {
    expansion: 'Neutral — front end anchored by Fed, minimal duration risk.',
    recovery: 'Mild tailwind as curve steepens from the front.',
    tightening: 'Short end rises with hikes, but less duration damage.',
    risk_off: 'Mild safe-haven bid. Less upside than long bonds.',
  },
  Gold: {
    expansion: 'Real rates rising = opportunity cost of gold high. Neutral.',
    recovery: 'Inflation hedge + weak dollar = mild tailwind.',
    tightening: 'Inflation concern supports gold even with rate headwind.',
    risk_off: 'Classic safe haven. Dollar demand can cap upside.',
  },
  Oil: {
    expansion: 'Peak demand cycle. Global growth drives commodity prices.',
    recovery: 'Early-cycle demand recovery, supply adjusting.',
    tightening: 'Demand still ok but growth headwinds building.',
    risk_off: 'Demand destruction fears. Price drops on growth concerns.',
  },
  Dollar: {
    expansion: 'Growth differential may support dollar, but risk-on = outflows.',
    recovery: 'Weak dollar = carry trade out, EM and commodities win.',
    tightening: 'Rate differential strongly bullish dollar. Fed hikes vs peers.',
    risk_off: 'Flight to dollar as reserve currency. DXY spikes.',
  },
  Bitcoin: {
    expansion: 'Risk-on + liquidity = BTC outperforms. High beta to equities.',
    recovery: 'Early-cycle liquidity surge. BTC leads risk assets.',
    tightening: 'Tighter liquidity kills high-beta assets. BTC hit hardest.',
    risk_off: 'Correlation to equities increases in selloffs. No safe haven.',
  },
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
  const guideMode = useGuideMode();
  const [hoverCell, setHoverCell] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-1">
        <div className="label">Asset × Regime Heatmap</div>
        {currentRegime && (
          <span
            className="text-[10px] font-mono uppercase tracking-wide"
            style={{ color: REGIME_CONFIG[currentRegime]?.color }}
          >
            Active: {REGIME_CONFIG[currentRegime]?.label}
          </span>
        )}
      </div>
      {guideMode && (
        <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginBottom: 10, lineHeight: 1.5 }}>
          Historical asset-regime bias matrix. Active regime column is highlighted. ++ = strong tailwind, −− = strong headwind. Hover any cell for rationale. These are macro tendencies, not trade signals.
        </div>
      )}
      {!guideMode && <div className="mb-3" />}

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
                      color: isActive ? cfg.color : 'rgba(255,255,255,0.45)',
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
                  const isHovered = hoverCell?.asset === asset && hoverCell?.regime === r;
                  return (
                    <td
                      key={r}
                      className="py-1.5 text-center"
                      style={{
                        fontSize: 10,
                        fontFamily: 'JetBrains Mono, monospace',
                        fontWeight: 600,
                        background: biasColor(val, isActive),
                        color: textColor(val, isActive),
                        borderLeft: isActive ? `1px solid ${REGIME_CONFIG[r]?.color}18` : 'none',
                        borderRight: isActive ? `1px solid ${REGIME_CONFIG[r]?.color}18` : 'none',
                        borderBottom: ai < assets.length - 1 ? '1px solid #111' : 'none',
                        cursor: 'default',
                        outline: isHovered ? `1px solid rgba(255,255,255,0.12)` : 'none',
                        transition: 'outline 0.1s',
                      }}
                      onMouseEnter={(e) => {
                        setHoverCell({ asset, regime: r, val, meta, rationale: RATIONALE[asset]?.[r] });
                        setTooltipPos({ x: e.clientX + 14, y: e.clientY - 56 });
                      }}
                      onMouseMove={(e) => setTooltipPos({ x: e.clientX + 14, y: e.clientY - 56 })}
                      onMouseLeave={() => setHoverCell(null)}
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
            <span className="font-mono text-[10px] font-semibold" style={{ color: l.color }}>
              {l.label.split(' ')[0]}
            </span>
            <span className="text-[10px] text-white/45 font-mono">{l.label.split(' ').slice(1).join(' ')}</span>
          </div>
        ))}
      </div>

      {/* Hover tooltip */}
      {hoverCell && (
        <div style={{
          position: 'fixed', zIndex: 999,
          left: tooltipPos.x, top: tooltipPos.y,
          background: '#0d0d0d',
          border: `1px solid ${hoverCell.val > 0 ? 'rgba(34,197,94,0.3)' : hoverCell.val < 0 ? 'rgba(239,68,68,0.3)' : '#2a2a2a'}`,
          borderRadius: 8, padding: '10px 14px',
          fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
          pointerEvents: 'none', maxWidth: 240,
          boxShadow: '0 8px 32px rgba(0,0,0,0.7)',
        }}>
          <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 10, marginBottom: 4 }}>
            {hoverCell.asset} · {REGIME_CONFIG[hoverCell.regime]?.label}
          </div>
          <div style={{
            color: hoverCell.val === 2 ? '#22c55e' : hoverCell.val === 1 ? '#4ade80'
              : hoverCell.val === 0 ? 'rgba(255,255,255,0.4)'
              : hoverCell.val === -1 ? '#f87171' : '#ef4444',
            fontWeight: 700, marginBottom: 6,
          }}>
            {hoverCell.meta?.title}
          </div>
          {hoverCell.rationale && (
            <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 10, lineHeight: 1.55 }}>
              {hoverCell.rationale}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
