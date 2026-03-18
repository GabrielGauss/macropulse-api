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
  performance: 'M2 13l4-4 3 3 4-7 3 3',
  liquidity:   'M8 1c0 0-5 4.5-5 8a5 5 0 0010 0c0-3.5-5-8-5-8z',
  signals:     'M1 8l3-3 3 3 3-4 3 3 2-2',
  backtest:    'M2 14V6l4-4 4 4V2l3 3M2 14h12M6 14v-4h4v4',
  inflation:   'M8 2l1.5 3.5L13 6l-2.5 2.5.5 3.5L8 10.5 5 12l.5-3.5L3 6l3.5-.5L8 2z',
  growth:      'M1 12l4-5 3 3 4-6 3 3',
  rates:       'M5 11V5m3 6V2m3 9V7M1 14h14',
  fx:          'M3 5h10M3 8h10M3 11h10M8 2v12',
  commodities: 'M8 2L2 14h12L8 2zM8 9v3',
  crypto:      'M5 7h4c1 0 2 .5 2 1.5S10 10 9 10H5V7zm0 3h4.5c1 0 2 .5 2 1.5S10.5 13 9.5 13H5v-3zM5 4h3',
  quant:       'M2 14L5 9l3 2 2-4 2 3 2-6',
  collapse:    'M10 4L6 8l4 4',
  expand:      'M6 4l4 4-4 4',
};

const FREE_LOCKED = new Set(['liquidity', 'signals', 'backtest', 'inflation', 'growth', 'rates', 'commodities', 'fx', 'crypto', 'quant']);

const NAV_ITEMS = [
  { id: 'dashboard',   label: 'Dashboard',    icon: 'dashboard',   available: true  },
  { id: 'performance', label: 'Performance',  icon: 'performance', available: true  },
  { id: 'liquidity',   label: 'Liquidity',    icon: 'liquidity',   available: true  },
  { id: 'signals',     label: 'Signals',      icon: 'signals',     available: true  },
  { id: 'backtest',    label: 'Backtests',    icon: 'backtest',    available: true  },
  null, // divider
  { id: 'inflation',   label: 'Inflation',    icon: 'inflation',   available: true },
  { id: 'growth',      label: 'Growth',       icon: 'growth',      available: true },
  { id: 'rates',       label: 'Rates',        icon: 'rates',       available: true },
  { id: 'commodities', label: 'Commodities',  icon: 'commodities', available: true },
  { id: 'fx',          label: 'FX',           icon: 'fx',          available: true },
  { id: 'crypto',      label: 'Crypto',       icon: 'crypto',      available: true },
  null, // divider
  { id: 'quant',       label: 'Quant HUD',    icon: 'quant',       available: true },
];

export default function Sidebar({ regime, activeSection = 'dashboard', onNavigate, tier }) {
  const isFree = !tier || tier === 'free';
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
          <svg
            width="16" height="16" viewBox="0 0 16 16" fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="flex-shrink-0"
            style={{ filter: 'drop-shadow(0 0 4px rgba(34,197,94,0.5))' }}
          >
            <circle cx="8" cy="8" r="6" stroke="#22c55e" strokeWidth="1.2" />
            <ellipse cx="8" cy="8" rx="2.5" ry="6" stroke="#22c55e" strokeWidth="1" />
            <line x1="2" y1="8" x2="14" y2="8" stroke="#22c55e" strokeWidth="1" />
            <path d="M2.8 5.5Q8 6.8 13.2 5.5" stroke="#22c55e" strokeWidth="0.8" opacity="0.6" />
            <path d="M2.8 10.5Q8 9.2 13.2 10.5" stroke="#22c55e" strokeWidth="0.8" opacity="0.6" />
          </svg>
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

          const isLocked = isFree && FREE_LOCKED.has(item.id);
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
                  : 'rgba(255,255,255,0.35)',
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
                    : 'rgba(255,255,255,0.25)';
                }
              }}
            >
              <Icon d={ICONS[item.icon]} size={15} />
              {!collapsed && (
                <span className="text-[12px] font-medium truncate">{item.label}</span>
              )}
              {!collapsed && isLocked && (
                <svg className="ml-auto flex-shrink-0" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
              )}
              {!collapsed && !item.available && !isLocked && (
                <span
                  className="ml-auto text-[10px] font-mono uppercase tracking-wide"
                  style={{ color: 'rgba(255,255,255,0.35)' }}
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
            <div className="text-[10px] uppercase tracking-widest font-medium mb-0.5"
              style={{ color: 'rgba(255,255,255,0.50)' }}>
              Regime
            </div>
            <div className="flex items-center gap-1.5">
              <div className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} />
              <span className="text-[11px] font-semibold font-mono" style={{ color: cfg.color }}>
                {cfg.label}
              </span>
            </div>
            {regime.persistence_days != null && (
              <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.45)' }}>
                {regime.persistence_days}d persistent
              </div>
            )}
          </div>
        </div>
      )}

      {/* External links */}
      <div className="border-t border-[#1a1a1a] px-2 py-2 space-y-0.5">
        <a
          href="https://macropulse.live"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center rounded-md transition-colors duration-100"
          style={{
            gap: 10,
            padding: collapsed ? '6px 12px' : '6px 10px',
            color: 'rgba(255,255,255,0.45)',
            justifyContent: collapsed ? 'center' : 'flex-start',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
          title="macropulse.live"
        >
          <svg width={15} height={15} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="6" />
            <path d="M8 2c0 0-2.5 2.5-2.5 6S8 14 8 14M8 2c0 0 2.5 2.5 2.5 6S8 14 8 14M2 8h12" />
          </svg>
          {!collapsed && (
            <span className="text-[11px] font-medium">macropulse.live</span>
          )}
        </a>
        <a
          href="https://github.com/GabrielGauss/macropulse-api"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center rounded-md transition-colors duration-100"
          style={{
            gap: 10,
            padding: collapsed ? '6px 12px' : '6px 10px',
            color: 'rgba(255,255,255,0.45)',
            justifyContent: collapsed ? 'center' : 'flex-start',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
          title="API Docs"
        >
          <svg width={15} height={15} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 2h6l3 3v9H4V2zM10 2v3h3M6 7h5M6 9.5h5M6 12h3" />
          </svg>
          {!collapsed && (
            <span className="text-[11px] font-medium">API Docs</span>
          )}
        </a>
        <a
          href="https://discord.gg/YxTH5hPaeN"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center rounded-md transition-colors duration-100"
          style={{
            gap: 10,
            padding: collapsed ? '6px 12px' : '6px 10px',
            color: 'rgba(255,255,255,0.45)',
            justifyContent: collapsed ? 'center' : 'flex-start',
            textDecoration: 'none',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
          title="Join Discord"
        >
          <svg width={15} height={15} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.015.043.032.054a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
          </svg>
          {!collapsed && (
            <span className="text-[11px] font-medium">Discord</span>
          )}
        </a>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center border-t border-[#1f1f1f] transition-colors duration-100"
        style={{
          height: 40,
          color: 'rgba(255,255,255,0.45)',
          background: 'transparent',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.7)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; }}
        title={collapsed ? 'Expand' : 'Collapse'}
      >
        <Icon d={collapsed ? ICONS.expand : ICONS.collapse} size={14} />
      </button>
    </aside>
  );
}
