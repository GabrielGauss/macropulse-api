import React from 'react';
import { REGIME_CONFIG } from '../lib/utils';

export default function Header({ connected, regime }) {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });

  return (
    <header
      className="flex items-center justify-between border-b border-[#1f1f1f] bg-surface-0 flex-shrink-0"
      style={{ height: 48, paddingLeft: 16, paddingRight: 16 }}
    >
      {/* Date */}
      <span className="text-[11px] text-white/25 font-mono">{today}</span>

      {/* Right: connection status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div
            className="live-dot"
            style={{ background: connected ? '#22c55e' : '#444' }}
          />
          <span className="text-[11px] font-mono" style={{ color: connected ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.2)' }}>
            {connected ? 'Live' : 'Polling'}
          </span>
        </div>
      </div>
    </header>
  );
}
