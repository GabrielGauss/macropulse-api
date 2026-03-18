import React, { useCallback, useState } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { useGuideMode } from '../lib/guideMode';
import { useCountdown } from '../hooks/useCountdown';

function RefreshIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 4v6h-6" />
      <path d="M1 20v-6h6" />
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function SkeletonBlock({ width = '100%', height = 10 }) {
  return (
    <div
      className="rounded"
      style={{
        width,
        height,
        background: 'rgba(255,255,255,0.06)',
        animation: 'pulse 1.5s ease-in-out infinite',
      }}
    />
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 mt-2">
      {/* Headline skeleton */}
      <SkeletonBlock width="85%" height={12} />
      {/* Paragraph blocks */}
      <div className="space-y-1.5 pt-1">
        <SkeletonBlock width="100%" height={8} />
        <SkeletonBlock width="92%" height={8} />
        <SkeletonBlock width="97%" height={8} />
      </div>
      <div className="space-y-1.5">
        <SkeletonBlock width="88%" height={8} />
        <SkeletonBlock width="100%" height={8} />
        <SkeletonBlock width="80%" height={8} />
      </div>
      <div className="space-y-1.5">
        <SkeletonBlock width="95%" height={8} />
        <SkeletonBlock width="73%" height={8} />
      </div>
    </div>
  );
}

function BlurredUpgradeOverlay() {
  return (
    <div
      className="absolute inset-0 flex flex-col items-center justify-center rounded-lg"
      style={{
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        background: 'rgba(13,13,13,0.55)',
        zIndex: 10,
      }}
    >
      <div
        className="mb-3 rounded-full flex items-center justify-center"
        style={{ width: 40, height: 40, background: 'rgba(255,255,255,0.04)', border: '1px solid #2a2a2a' }}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <div className="text-[12px] font-semibold text-white/60 mb-1">AI Macro Commentary</div>
      <div className="text-[10px] text-white/50 font-mono mb-4 text-center px-6">
        Available on Starter and Pro
      </div>
      <a
        href="https://macropulse.live/#pricing"
        target="_blank"
        rel="noopener noreferrer"
        className="rounded text-[11px] font-semibold px-4 py-1.5 transition-opacity hover:opacity-85"
        style={{ background: '#f0f0f0', color: '#0a0a0a', textDecoration: 'none' }}
      >
        View plans →
      </a>
    </div>
  );
}

function UnconfiguredPlaceholder() {
  const countdown = useCountdown();
  return (
    <div className="py-4 text-center">
      <div
        className="text-[10px] font-mono leading-relaxed px-2"
        style={{ color: 'rgba(255,255,255,0.3)' }}
      >
        AI commentary requires <span style={{ color: 'rgba(255,255,255,0.5)' }}>ANTHROPIC_API_KEY</span> in the server environment.
        Configure it in <span style={{ color: 'rgba(255,255,255,0.5)' }}>.env</span> to enable daily macro narratives.
      </div>
      {countdown && (
        <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.25)' }}>
          Next update in {countdown}
        </div>
      )}
    </div>
  );
}

function is503(error) {
  return error?.message?.includes('503');
}

export default function CommentaryCard({ tier }) {
  const guideMode = useGuideMode();
  const isFree = tier === 'free' || tier === null;

  const fetchCommentary = useCallback(() => api.getCommentary(), []);
  const { data, loading, error, refetch } = useFetch(fetchCommentary);

  return (
    <div className="card p-5 animate-in relative" style={{ overflow: 'hidden' }}>
      {/* Upgrade overlay — rendered over content */}
      {isFree && <BlurredUpgradeOverlay />}

      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="label">AI Macro Commentary</div>
        <div className="flex items-center gap-2">
          <span
            className="text-[10px] font-mono"
            style={{ color: 'rgba(255,255,255,0.50)' }}
          >
            claude-sonnet-4-6
          </span>
          <button
            onClick={refetch}
            disabled={loading}
            title="Refresh commentary"
            className="flex items-center justify-center rounded transition-opacity hover:opacity-70 disabled:opacity-30"
            style={{
              width: 22,
              height: 22,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid #2a2a2a',
              color: 'rgba(255,255,255,0.4)',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            <RefreshIcon />
          </button>
        </div>
      </div>

      {/* Loading state */}
      {loading && <LoadingSkeleton />}

      {/* 503 — API key not configured */}
      {!loading && error && is503(error) && <UnconfiguredPlaceholder />}

      {/* Generic error */}
      {!loading && error && !is503(error) && (
        <p
          className="text-[11px] font-mono py-4 text-center"
          style={{ color: 'rgba(255,255,255,0.50)' }}
        >
          Commentary unavailable
        </p>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <div className="mt-2 space-y-3">
          {/* Headline */}
          <p
            className="font-semibold leading-snug"
            style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}
          >
            {data.headline}
          </p>

          {/* Narrative paragraphs */}
          <div className="space-y-2">
            {(data.narrative || '').split('\n\n').filter(Boolean).map((para, i) => (
              <p
                key={i}
                style={{
                  fontSize: 11,
                  color: 'rgba(255,255,255,0.50)',
                  fontFamily: 'JetBrains Mono, monospace',
                  lineHeight: 1.7,
                  margin: 0,
                }}
              >
                {para}
              </p>
            ))}
          </div>

          {/* Key signals */}
          {data.key_signals?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {data.key_signals.map((signal, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: 9,
                    fontFamily: 'JetBrains Mono, monospace',
                    color: 'rgba(255,255,255,0.45)',
                    background: 'rgba(255,255,255,0.05)',
                    border: '1px solid #2a2a2a',
                    borderRadius: 4,
                    padding: '2px 6px',
                  }}
                >
                  {signal}
                </span>
              ))}
            </div>
          )}

          {/* Watch for */}
          {data.watch_for && (
            <div
              className="flex items-start gap-2 rounded-md px-3 py-2"
              style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}
            >
              <span
                className="flex-shrink-0 mt-0.5"
                style={{ color: 'rgba(245,158,11,0.7)' }}
              >
                <WarningIcon />
              </span>
              <p
                style={{
                  fontSize: 10,
                  fontFamily: 'JetBrains Mono, monospace',
                  color: 'rgba(245,158,11,0.7)',
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                {data.watch_for}
              </p>
            </div>
          )}

          {/* Timestamp */}
          {data.timestamp && (
            <div
              className="text-right"
              style={{ fontSize: 10, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.45)' }}
            >
              {data.timestamp}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
