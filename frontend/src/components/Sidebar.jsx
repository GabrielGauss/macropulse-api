import React, { useState } from 'react';
import { REGIME_CONFIG } from '../lib/utils';

// Inline SVG icons — no icon library dependency
const Icon = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const ICONS = {
  dashboard:   'M2 2h5v5H2V2zm7 0h5v5H9V2zm-7 7h5v5H2V9zm7 0h5v5H9V9z',
  liquidity:   'M8 1c0 0-5 4.5-5 8a5 5 0 0010 0c0-3.5-5-8-5-8z',
  signals:     'M1 8l3-3 3 3 3-4 3 3 2-2',
  backtest:    'M2 14V6l4-4 4 4V2l3 3M2 14h12M6 14v-4h4v4',
  inflation:   'M8 2l1.5 3.5L13 6l-2.5 2.5.5 3.5L8 10.5 5 12l.5-3.5L3 6l3.5-.5L8 2z',
  growth:      'M1 12l4-5 3 3 4-6 3 3',
  rates:       'M5 11V5m3 6V2m3 9V7M1 14h14',
  fx:          'M3 5h10M3 8h10M3 11h10M8 2v12',
  commodities: 'M8 2L2 14h12L8 2zM8 9v3',
  crypto:      'M5 7h4c1 0 2 .5 2 1.5S10 10 9 10H5V7zm0 3h4.5c1 0 2 .5 2 1.5S10.5 13 9.5 13H5v-3zM5 4h3',
  collapse:    'M10 4L6 8l4 4',
  expand:      'M6 4l4 4-4 4',
};

const NAV_ITEMS = [
  { id: 'dashboard',   label: 'Dashboard',    icon: 'dashboard',   available: true  },
  { id: 'liquidity',   label: 'Liquidity',    icon: 'liquidity',   available: true  },
  { id: 'signals',     label: 'Signals',      icon: 'signals',     available: true  },
  { id: 'backtest',    label: 'Backtests',    icon: 'backtest',    available: true  },
  null, // divider
  { id: 'inflation',   label: 'Inflation',    icon: 'inflation',   available: false },
  { id: 'growth',      label: 'Growth',       icon: 'growth',      available: false },
  { id: 'rates',       label: 'Rates',        icon: 'rates',       available: false },
  { id: 'commodities', label: 'Commodities',  icon: 'commodities', available: false },
  { id: 'fx',          label: 'FX',           icon: 'fx',          available: false },
  { id: 'crypto',      label: 'Crypto',       icon: 'crypto',      available: false },
];

export default function Sidebar({ regime, activeSection = 'dashboard', onNavigate }) {
  const [collapsed, setCollapsed] = useState(false);
  const cfg = regime ? REGIME_CONFIG[regime.macro_regime] : null;

  return (
    <aside
      className="flex flex-col flex-shrink-0 border-r border-[#1f1f1f] bg-surface-0 transition-all duration-200"
      style={{ width: collapsed ? 56 : 200 }}
    >
      {/* Brand */}
      <div
        className="flex items-center border-b border-[#1f1f1f] px-3.5"
        style={{ height: 48, minHeight: 48 }}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className="h-2 w-2 rounded-full flex-shrink-0"
            style={{ background: '#22c55e', boxShadow: '0 0 6px rgba(34,197,94,0.6)' }}
          />
          {!collapsed && (
            <span className="text-[13px] font-semibold tracking-tight truncate">MacroPulse</span>
          )}
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map((item, i) => {
          if (!item) {
            return (
              <div
                key={`div-${i}`}
                className="my-2 border-t border-[#1a1a1a]"
              />
            );
          }

          const isActive = item.id === activeSection && item.available;

          return (
            <button
              key={item.id}
              title={collapsed ? item.label : undefined}
              onClick={() => item.available && onNavigate?.(item.id)}
              disabled={!item.available}
              className="w-full flex items-center rounded-md transition-colors duration-100"
              style={{
                gap: 10,
                padding: collapsed ? '7px 12px' : '7px 10px',
                background: isActive ? 'rgba(255,255,255,0.06)' : 'transparent',
                color: isActive
                  ? '#f0f0f0'
                  : item.available
                  ? 'rgba(255,255,255,0.35)'
                  : 'rgba(255,255,255,0.15)',
                cursor: item.available ? 'pointer' : 'default',
                justifyContent: collapsed ? 'center' : 'flex-start',
              }}
              onMouseEnter={(e) => {
                if (item.available && !isActive) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                  e.currentTarget.style.color = 'rgba(255,255,255,0.6)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = item.available
                    ? 'rgba(255,255,255,0.35)'
                    : 'rgba(255,255,255,0.15)';
                }
              }}
            >
              <Icon d={ICONS[item.icon]} size={15} />
              {!collapsed && (
                <span className="text-[12px] font-medium truncate">{item.label}</span>
              )}
              {!collapsed && !item.available && (
                <span
                  className="ml-auto text-[8px] font-mono uppercase tracking-wide"
                  style={{ color: 'rgba(255,255,255,0.15)' }}
                >
                  soon
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Regime status (expanded only) */}
      {!collapsed && cfg && (
        <div className="px-3 pb-3">
          <div
            className="rounded px-2.5 py-2"
            style={{ background: cfg.bg, border: `1px solid ${cfg.color}22` }}
          >
            <div className="text-[9px] uppercase tracking-widest font-medium mb-0.5"
              style={{ color: 'rgba(255,255,255,0.25)' }}>
              Regime
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} />
              <span className="text-[11px] font-semibold font-mono" style={{ color: cfg.color }}>
                {cfg.label}
              </span>
            </div>
            {regime.persistence_days != null && (
              <div className="text-[9px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.2)' }}>
                {regime.persistence_days}d persistent
              </div>
            )}
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center border-t border-[#1f1f1f] transition-colors duration-100"
        style={{
          height: 40,
          color: 'rgba(255,255,255,0.2)',
          background: 'transparent',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.2)'; }}
        title={collapsed ? 'Expand' : 'Collapse'}
      >
        <Icon d={collapsed ? ICONS.expand : ICONS.collapse} size={14} />
      </button>
    </aside>
  );
}
