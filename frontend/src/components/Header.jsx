import React, { useState, useRef, useEffect } from 'react';
import { REGIME_CONFIG } from '../lib/utils';
import { api } from '../lib/api';

export default function Header({ connected, regime }) {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  });

  const [showKeyInput, setShowKeyInput] = useState(false);
  const [keyDraft, setKeyDraft] = useState('');
  const [hasKey, setHasKey] = useState(api.hasKey());
  const inputRef = useRef(null);
  const popoverRef = useRef(null);

  useEffect(() => {
    if (showKeyInput) setTimeout(() => inputRef.current?.focus(), 50);
  }, [showKeyInput]);

  // Close popover when clicking outside
  useEffect(() => {
    if (!showKeyInput) return;
    function handleClickOutside(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setShowKeyInput(false);
        setKeyDraft('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showKeyInput]);

  function saveKey() {
    if (!keyDraft.trim()) return;
    api.setKey(keyDraft.trim());
    setHasKey(true);
    setShowKeyInput(false);
    setKeyDraft('');
    window.location.reload();
  }

  function clearKey() {
    api.setKey(null);
    setHasKey(false);
    window.location.reload();
  }

  const storedKey = api.getKey();
  const keyPrefix = storedKey ? storedKey.slice(0, 16) + '…' : null;

  return (
    <header
      className="flex items-center justify-between border-b border-[#1f1f1f] bg-surface-0 flex-shrink-0 relative"
      style={{ height: 48, paddingLeft: 16, paddingRight: 16 }}
    >
      {/* Date */}
      <span className="text-[11px] text-white/25 font-mono">{today}</span>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* API key indicator */}
        <div className="relative" ref={popoverRef}>
          {hasKey ? (
            <div className="flex items-center gap-2">
              <span
                className="text-[10px] font-mono"
                style={{ color: 'rgba(34,197,94,0.5)' }}
              >
                {keyPrefix}
              </span>
              <button
                onClick={clearKey}
                className="text-[10px] font-mono transition-colors"
                style={{ color: 'rgba(255,255,255,0.15)' }}
                onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
                onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.15)'}
                title="Clear API key"
              >
                ×
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowKeyInput(v => !v)}
              className="text-[10px] font-mono transition-colors"
              style={{ color: 'rgba(255,255,255,0.2)' }}
              onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.5)'}
              onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.2)'}
            >
              + Enter API key
            </button>
          )}

          {/* Key entry popover */}
          {showKeyInput && (
            <div
              className="absolute right-0 top-8 z-50 rounded-lg border border-[#2a2a2a] bg-[#111] shadow-2xl"
              style={{ width: 320, padding: '14px 16px' }}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-semibold text-white/60">API Key</span>
                <button
                  onClick={() => { setShowKeyInput(false); setKeyDraft(''); }}
                  className="text-[12px] font-mono text-white/20 hover:text-white/50 transition-colors"
                >×</button>
              </div>
              <input
                ref={inputRef}
                type="text"
                value={keyDraft}
                onChange={e => setKeyDraft(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') saveKey(); if (e.key === 'Escape') { setShowKeyInput(false); setKeyDraft(''); } }}
                placeholder="mp_xxxxxxxxxxxx..."
                className="w-full rounded-md border border-[#2a2a2a] bg-[#0a0a0a] px-3 py-2 font-mono text-[11px] text-green-400 outline-none focus:border-[#3a3a3a] placeholder:text-white/15"
              />
              <div className="flex items-center justify-between mt-3">
                <span className="text-[10px] text-white/20">Stored in browser only</span>
                <button
                  onClick={saveKey}
                  disabled={!keyDraft.trim()}
                  className="rounded px-3 py-1.5 text-[11px] font-semibold transition-opacity disabled:opacity-30"
                  style={{ background: '#f0f0f0', color: '#000' }}
                >
                  Save key
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Connection status */}
        <div className="flex items-center gap-1.5">
          <div
            className="live-dot"
            style={{ background: connected ? '#22c55e' : '#444' }}
          />
          <span
            className="text-[11px] font-mono"
            style={{ color: connected ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.2)' }}
          >
            {connected ? 'Live' : 'Polling'}
          </span>
        </div>
      </div>
    </header>
  );
}
