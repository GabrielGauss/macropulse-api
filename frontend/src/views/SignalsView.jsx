import React, { useCallback } from 'react';
import SignalGauges from '../components/SignalGauges';
import MacroHeatmap from '../components/MacroHeatmap';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';

const SIGNAL_DOCS = [
  {
    key: 'growth_momentum',
    label: 'Growth Momentum',
    formula: 'zscore(20d sum of Δyield curve)',
    interpretation: 'Positive = curve steepening → growth expectations rising. Negative = flattening or inversion → growth concerns.',
    bullish: 'Equities, Cyclicals, Commodities',
    bearish: 'Long bonds, Defensives',
  },
  {
    key: 'inflation_momentum',
    label: 'Inflation Momentum',
    formula: 'zscore(20d sum of Δ10Y yield)',
    interpretation: 'Positive = rising rate-of-change in 10Y yield → inflation expectations building. Negative = disinflationary.',
    bullish: 'TIPS, Gold, Commodities, Real Assets',
    bearish: 'Long duration bonds, Growth stocks',
  },
  {
    key: 'liquidity',
    label: 'Liquidity Expansion',
    formula: 'zscore(net liquidity level · 504d window)',
    interpretation: 'Positive = Fed balance sheet above 2-year average → abundant dollar liquidity. The single most important macro driver.',
    bullish: 'Risk assets broadly — equities, crypto, EM',
    bearish: 'Cash, short-term T-bills when deeply negative',
  },
  {
    key: 'financial_stress',
    label: 'Financial Stress',
    formula: '−zscore(20d sum of (ΔBAML HY spread + ΔVIX) / 2)',
    interpretation: 'Positive = spreads and volatility falling → calm, risk-on. Negative = spreads widening, vol rising → stress building.',
    bullish: 'Equities, High Yield, EM debt',
    bearish: 'Treasuries, Gold, Volatility (when negative)',
  },
  {
    key: 'dollar_strength',
    label: 'Dollar Strength',
    formula: 'zscore(20d sum of ΔDXY)',
    interpretation: 'Positive = DXY momentum upward → strong dollar. Often a headwind for EM, commodities, and crypto.',
    bullish: 'USD cash, short EM',
    bearish: 'Gold, Commodities, EM equities, Crypto',
  },
];

function SignalDocRow({ doc, value }) {
  const color = value == null ? '#555'
    : value > 0.2 ? '#22c55e'
    : value < -0.2 ? '#ef4444'
    : 'rgba(255,255,255,0.3)';

  return (
    <div className="card p-4 animate-in">
      <div className="flex items-start justify-between mb-2">
        <div className="text-[12px] font-semibold text-white/80">{doc.label}</div>
        <span
          className="font-mono text-[13px] font-bold ml-4 flex-shrink-0"
          style={{ color }}
        >
          {value == null ? '—' : (value >= 0 ? '+' : '') + value.toFixed(2)}
        </span>
      </div>
      <div className="text-[10px] font-mono text-white/25 mb-2">{doc.formula}</div>
      <p className="text-[11px] text-white/40 leading-relaxed mb-2">{doc.interpretation}</p>
      <div className="flex gap-4 text-[10px] font-mono">
        <span><span style={{ color: '#22c55e' }}>↑ </span><span className="text-white/25">{doc.bullish}</span></span>
        <span><span style={{ color: '#ef4444' }}>↓ </span><span className="text-white/25">{doc.bearish}</span></span>
      </div>
    </div>
  );
}

export default function SignalsView() {
  const fetchScorecard = useCallback(() => api.getScorecard(), []);
  const fetchRegime    = useCallback(() => api.getCurrentRegime(), []);
  const scorecard = useFetch(fetchScorecard);
  const regime    = useFetch(fetchRegime);
  const sc = scorecard.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] font-semibold tracking-tight">Macro Signals</h2>
        <span className="text-[10px] text-white/25 font-mono">z-score · 252d normalization</span>
      </div>

      {/* Top: gauges + heatmap */}
      <div className="grid gap-4 lg:grid-cols-2">
        <SignalGauges data={sc} />
        <MacroHeatmap regime={regime.data} />
      </div>

      {/* Signal detail cards */}
      <div className="label pt-2">Signal Methodology</div>
      <div className="grid gap-3 lg:grid-cols-2">
        {SIGNAL_DOCS.map((doc) => (
          <SignalDocRow key={doc.key} doc={doc} value={sc?.[doc.key]} />
        ))}
      </div>
    </div>
  );
}
