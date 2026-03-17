import React, { useState, useRef, useEffect, useCallback } from 'react';
import { REGIME_CONFIG } from '../lib/utils';
import { api } from '../lib/api';
import { useFetch } from '../hooks/useFetch';

const TIER_COLOR = {
  free:    'rgba(255,255,255,0.2)',
  starter: '#3b82f6',
  pro:     '#f59e0b',
  owner:   '#22c55e',
};

export default function Header({ connected, regime, meInfo, guideMode, onToggleGuide }) {
  const dataDate = regime?.time
    ? new Date(regime.time).toLocaleString('en-US', {
        weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZone: 'UTC', timeZoneName: 'short',
      })
    : '—';

  const fetchPipelineStatus = useCallback(() => api.getPipelineStatus(), []);
  const pipelineStatus = useFetch(fetchPipelineStatus);
  const ps = pipelineStatus.data;

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

  const [copied, setCopied] = useState(false);
  function copyKey() {
    if (!storedKey) return;
    navigator.clipboard.writeText(storedKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <header
      className="flex items-center justify-between border-b border-[#1f1f1f] bg-surface-0 flex-shrink-0 relative"
      style={{ height: 48, paddingLeft: 16, paddingRight: 16 }}
    >
      {/* Data timestamp + pipeline freshness */}
      <div className="flex items-center gap-3">
        <span className="text-[11px] text-white/25 font-mono">
          <span className="text-white/15 mr-1">data</span>{dataDate}
        </span>
        {ps && (
          <span
            className="text-[9px] font-mono px-1.5 py-0.5 rounded"
            style={{
              color: ps.status === 'success' && !ps.data_lag ? '#22c55e' : ps.data_lag ? '#f59e0b' : '#ef4444',
              border: `1px solid ${ps.status === 'success' && !ps.data_lag ? 'rgba(34,197,94,0.3)' : ps.data_lag ? 'rgba(245,158,11,0.3)' : 'rgba(239,68,68,0.3)'}`,
              background: 'transparent',
            }}
            title={ps.last_run_at ? `Pipeline: ${ps.status} · ${new Date(ps.last_run_at).toLocaleString('en-US', { timeZone: 'UTC' })} UTC` : 'No pipeline runs recorded'}
          >
            {ps.data_lag ? 'data lag' : ps.status === 'success' ? 'fresh' : ps.status}
          </span>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* API key indicator */}
        <div className="relative" ref={popoverRef}>
          {hasKey ? (
            <div className="flex items-center gap-2">
              <button
                onClick={copyKey}
                className="flex items-center gap-1.5 transition-opacity"
                style={{ opacity: 0.5 }}
                onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                onMouseLeave={e => e.currentTarget.style.opacity = '0.5'}
                title="Copy API key"
              >
                <span className="text-[10px] font-mono" style={{ color: '#22c55e' }}>
                  {keyPrefix}
                </span>
                {copied ? (
                  <span className="text-[9px] font-mono" style={{ color: '#22c55e' }}>✓</span>
                ) : (
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                )}
              </button>
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

        {/* Email + tier */}
        {meInfo && (
          <div className="hidden sm:flex items-center gap-2">
            <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
              {meInfo.email}
            </span>
            <span
              className="text-[9px] font-mono uppercase tracking-wide px-1.5 py-0.5 rounded"
              style={{
                color: TIER_COLOR[meInfo.tier] || TIER_COLOR.free,
                border: `1px solid ${TIER_COLOR[meInfo.tier] || TIER_COLOR.free}`,
                opacity: 0.85,
              }}
            >
              {meInfo.tier}
            </span>
          </div>
        )}

        {/* Guide mode toggle */}
        <button
          onClick={onToggleGuide}
          title={guideMode ? 'Guide mode on — click to hide annotations' : 'Guide mode off — click to show chart annotations'}
          style={{
            fontSize: 9, fontFamily: 'JetBrains Mono, monospace',
            padding: '3px 8px', borderRadius: 4,
            border: `1px solid ${guideMode ? 'rgba(59,130,246,0.4)' : '#2a2a2a'}`,
            background: guideMode ? 'rgba(59,130,246,0.08)' : 'transparent',
            color: guideMode ? '#3b82f6' : 'rgba(255,255,255,0.2)',
            cursor: 'pointer', transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', gap: 5,
          }}
          onMouseEnter={e => { if (!guideMode) { e.currentTarget.style.borderColor = '#3a3a3a'; e.currentTarget.style.color = 'rgba(255,255,255,0.45)'; } }}
          onMouseLeave={e => { if (!guideMode) { e.currentTarget.style.borderColor = '#2a2a2a'; e.currentTarget.style.color = 'rgba(255,255,255,0.2)'; } }}
        >
          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
          </svg>
          guide
        </button>

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
