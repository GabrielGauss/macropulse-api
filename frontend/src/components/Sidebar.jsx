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
  account:     'M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-5 6a5 5 0 0 1 10 0',
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

// Items locked for free tier (need Starter+)
const STARTER_LOCKED = new Set(['liquidity', 'signals']);
// Items locked for Starter (need Pro)
const PRO_LOCKED = new Set(['backtest', 'inflation', 'growth', 'rates', 'commodities', 'fx', 'crypto', 'quant']);

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
  null, // divider
  { id: 'account',     label: 'Account',      icon: 'account',     available: true },
];

export default function Sidebar({ regime, activeSection = 'dashboard', onNavigate, tier }) {
  const isFree           = !tier || tier === 'free';
  const isStarterOrAbove = tier === 'starter' || tier === 'pro' || tier === 'owner';
  const isProOrAbove     = tier === 'pro' || tier === 'owner';
  const [collapsed, setCollapsed] = useState(false);
  const cfg = regime ? REGIME_CONFIG[regime.macro_regime] : null;

  return (
    <aside
      className="flex flex-col flex-shrink-0 border-r border-[#1a1a1a] bg-surface-0 transition-all duration-200"
      style={{ width: collapsed ? 56 : 200 }}
    >
      {/* Brand */}
      <div
        className="flex items-center border-b border-[#1a1a1a] px-3.5"
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

          const isLocked = (!isStarterOrAbove && STARTER_LOCKED.has(item.id)) ||
                           (!isProOrAbove    && PRO_LOCKED.has(item.id));
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
            className="px-2.5 py-2"
            style={{ background: '#0f0f0f', border: `1px solid #1c1c1c`, borderLeft: `2px solid ${cfg.color}` }}
          >
            <div className="text-[9px] uppercase tracking-[0.14em] font-medium mb-1"
              style={{ color: 'rgba(255,255,255,0.35)' }}>
              Live Regime
            </div>
            <div className="font-mono font-bold" style={{ fontSize: 14, color: cfg.color, lineHeight: 1, marginBottom: 2 }}>
              {cfg.label}
            </div>
            {regime.persistence_days != null && (
              <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.35)' }}>
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
          href="https://macropulse.live/api-docs.html"
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
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center justify-center border-t border-[#1a1a1a] transition-colors duration-100"
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
