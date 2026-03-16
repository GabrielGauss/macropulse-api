import React from 'react';
import { REGIME_CONFIG } from '../lib/utils';

export default function Header({ connected, regime }) {
  const cfg = regime ? REGIME_CONFIG[regime.macro_regime] : null;
  const today = new Date().toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <header className="flex items-center justify-between border-b border-[#1f1f1f] px-5 py-3 bg-surface-0">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div
            className="h-2 w-2 rounded-full flex-shrink-0"
            style={{ background: '#22c55e', boxShadow: '0 0 6px #22c55e' }}
          />
          <span className="text-sm font-semibold tracking-tight">MacroPulse</span>
        </div>
        <div className="hidden sm:block h-4 w-px bg-[#1f1f1f]" />
        <span className="hidden sm:block text-[11px] text-white/25 font-mono">{today}</span>
      </div>

      {/* Right: regime + connection */}
      <div className="flex items-center gap-3">
        {cfg && (
          <div
            className="hidden sm:flex items-center gap-1.5 rounded px-2 py-1"
            style={{ background: cfg.bg, border: `1px solid ${cfg.color}33` }}
          >
            <div className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: cfg.color }} />
            <span
              className="text-[11px] font-medium font-mono uppercase tracking-wide"
              style={{ color: cfg.color }}
            >
              {cfg.label}
            </span>
          </div>
        )}

        <div className="flex items-center gap-1.5">
          <div
            className="live-dot"
            style={{ background: connected ? '#22c55e' : '#444' }}
          />
          <span className="text-[11px] text-white/30">
            {connected ? 'Live' : 'Polling'}
          </span>
        </div>
      </div>
    </header>
  );
}
