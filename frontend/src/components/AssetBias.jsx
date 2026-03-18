import React from 'react';
import { REGIME_CONFIG } from '../lib/utils';

// Asset bias table: regime → asset class → bias
// bullish = +1, neutral = 0, bearish = -1
const BIAS_TABLE = {
  expansion:  { equities: 1,  bonds: -1, gold: 0,  commodities: 1,  crypto: 1  },
  recovery:   { equities: 1,  bonds: 1,  gold: 1,  commodities: 0,  crypto: 1  },
  tightening: { equities: -1, bonds: -1, gold: 0,  commodities: 1,  crypto: -1 },
  risk_off:   { equities: -1, bonds: 1,  gold: 1,  commodities: -1, crypto: -1 },
};

const ASSETS = [
  { key: 'equities',    label: 'Equities' },
  { key: 'bonds',       label: 'Bonds' },
  { key: 'gold',        label: 'Gold' },
  { key: 'commodities', label: 'Commodities' },
  { key: 'crypto',      label: 'Crypto' },
];

const BIAS_META = {
  1:  { label: 'Bullish',  color: '#22c55e', arrow: '↑' },
  0:  { label: 'Neutral',  color: 'rgba(255,255,255,0.3)', arrow: '→' },
  '-1': { label: 'Bearish', color: '#ef4444', arrow: '↓' },
};

function BiasCell({ bias, active }) {
  const meta = BIAS_META[String(bias)];
  return (
    <td className="text-center py-2 px-1">
      <span
        className="inline-flex items-center gap-0.5 font-mono text-[10px] font-semibold"
        style={{
          color: active ? meta.color : 'rgba(255,255,255,0.15)',
        }}
      >
        <span>{meta.arrow}</span>
      </span>
    </td>
  );
}

export default function AssetBias({ regime }) {
  const currentRegime = regime?.macro_regime;
  const regimes = ['expansion', 'recovery', 'tightening', 'risk_off'];

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-center justify-between mb-4">
        <div className="label">Asset Bias</div>
        {currentRegime && (
          <div
            className="text-[10px] font-mono font-medium px-2 py-0.5 rounded"
            style={{
              color: REGIME_CONFIG[currentRegime]?.color,
              background: REGIME_CONFIG[currentRegime]?.bg,
              border: `1px solid ${REGIME_CONFIG[currentRegime]?.color}33`,
            }}
          >
            {REGIME_CONFIG[currentRegime]?.label ?? currentRegime}
          </div>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[10px] font-mono border-collapse">
          <thead>
            <tr>
              <th className="text-left text-white/50 font-normal pb-2 pr-3">Asset</th>
              {regimes.map((r) => {
                const cfg = REGIME_CONFIG[r];
                const isActive = r === currentRegime;
                return (
                  <th
                    key={r}
                    className="text-center pb-2 px-1 font-medium"
                    style={{
                      color: isActive ? cfg.color : 'rgba(255,255,255,0.45)',
                    }}
                  >
                    {cfg.short}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {ASSETS.map((asset, i) => (
              <tr
                key={asset.key}
                className={i < ASSETS.length - 1 ? 'border-b border-[#1a1a1a]' : ''}
              >
                <td className="py-2 pr-3 text-white/40">{asset.label}</td>
                {regimes.map((r) => (
                  <BiasCell
                    key={r}
                    bias={BIAS_TABLE[r][asset.key]}
                    active={r === currentRegime}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-[#1a1a1a]">
        {Object.entries(BIAS_META).map(([b, meta]) => (
          <div key={b} className="flex items-center gap-1">
            <span className="font-mono text-[10px]" style={{ color: meta.color }}>
              {meta.arrow}
            </span>
            <span className="text-[10px] text-white/45 font-mono">{meta.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
