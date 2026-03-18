import React, { useCallback } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';
import { useGuideMode } from '../lib/guideMode';

// Signal → color mapping
function signalColor(signal) {
  if (!signal) return 'rgba(255,255,255,0.3)';
  const s = signal.toLowerCase();
  if (s === 'bullish' || s === 'risk_on') return '#22c55e';
  if (s === 'bearish' || s === 'risk_off') return '#ef4444';
  return '#f59e0b'; // neutral / unknown
}

function signalBg(signal) {
  const s = (signal || '').toLowerCase();
  if (s === 'bullish' || s === 'risk_on') return 'rgba(34,197,94,0.10)';
  if (s === 'bearish' || s === 'risk_off') return 'rgba(239,68,68,0.10)';
  return 'rgba(245,158,11,0.10)';
}

function signalBorder(signal) {
  const s = (signal || '').toLowerCase();
  if (s === 'bullish' || s === 'risk_on') return 'rgba(34,197,94,0.25)';
  if (s === 'bearish' || s === 'risk_off') return 'rgba(239,68,68,0.25)';
  return 'rgba(245,158,11,0.25)';
}

function scoreBarColor(score) {
  if (score > 30) return '#22c55e';
  if (score > 0)  return '#3b82f6';
  if (score > -30) return '#f59e0b';
  return '#ef4444';
}

function convictionColor(conviction) {
  if (!conviction) return 'rgba(255,255,255,0.3)';
  const c = conviction.toLowerCase();
  if (c === 'high')   return '#22c55e';
  if (c === 'medium') return '#f59e0b';
  return '#ef4444';
}

function SignalPill({ signal, size = 10 }) {
  return (
    <span
      style={{
        fontSize: size,
        fontFamily: 'JetBrains Mono, monospace',
        fontWeight: 600,
        color: signalColor(signal),
        background: signalBg(signal),
        border: `1px solid ${signalBorder(signal)}`,
        borderRadius: 4,
        padding: '1px 6px',
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}
    >
      {signal?.replace('_', ' ') || '—'}
    </span>
  );
}

// Composite score bar from -100 to +100, needle at score position
function CompositeScoreBar({ score }) {
  const clampedScore = Math.max(-100, Math.min(100, score ?? 0));
  // Map -100..+100 to 0..100% for needle position
  const needlePct = ((clampedScore + 100) / 200) * 100;
  const barColor = scoreBarColor(clampedScore);

  return (
    <div className="mt-3 mb-1">
      <div className="flex items-center justify-between mb-1">
        <span
          className="text-[10px] font-mono uppercase tracking-wide"
          style={{ color: 'rgba(255,255,255,0.45)' }}
        >
          Composite score
        </span>
        <span
          className="text-[10px] font-mono font-semibold"
          style={{ color: barColor }}
        >
          {clampedScore > 0 ? '+' : ''}{clampedScore.toFixed(1)}
        </span>
      </div>
      <div
        className="relative w-full overflow-hidden rounded-full"
        style={{ height: 6, background: 'rgba(255,255,255,0.06)' }}
      >
        {/* Gradient fill from center to needle */}
        <div
          className="absolute h-full"
          style={{
            left: clampedScore >= 0 ? '50%' : `${needlePct}%`,
            width: clampedScore >= 0
              ? `${needlePct - 50}%`
              : `${50 - needlePct}%`,
            background: barColor,
            opacity: 0.7,
          }}
        />
        {/* Center tick */}
        <div
          className="absolute top-0 bottom-0 w-px"
          style={{ left: '50%', background: 'rgba(255,255,255,0.15)' }}
        />
        {/* Needle */}
        <div
          className="absolute top-0 bottom-0 rounded-full"
          style={{
            left: `calc(${needlePct}% - 2px)`,
            width: 4,
            background: barColor,
          }}
        />
      </div>
      <div className="flex justify-between mt-0.5">
        <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>−100</span>
        <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>0</span>
        <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>+100</span>
      </div>
    </div>
  );
}

// 0-100 score bar for domain signals
function DomainScoreBar({ score }) {
  const clamped = Math.max(0, Math.min(100, score ?? 0));
  const color = scoreBarColor(clamped - 50); // treat 50 as neutral midpoint for coloring
  return (
    <div
      className="overflow-hidden rounded-full flex-shrink-0"
      style={{ height: 4, width: 60, background: 'rgba(255,255,255,0.06)' }}
    >
      <div
        className="h-full rounded-full"
        style={{ width: `${clamped}%`, background: color, opacity: 0.75 }}
      />
    </div>
  );
}

const DOMAIN_LABELS = {
  equity:    'Equity',
  rates:     'Rates',
  credit:    'Credit',
  liquidity: 'Liquidity',
};

function DomainRow({ domainKey, domain }) {
  if (!domain) return null;
  const label = DOMAIN_LABELS[domainKey] || domainKey;

  return (
    <div className="flex items-center gap-2 py-2 border-b border-[#1a1a1a] last:border-0">
      {/* Domain name */}
      <div
        className="flex-shrink-0 text-[10px] font-mono"
        style={{ width: 60, color: 'rgba(255,255,255,0.4)' }}
      >
        {label}
      </div>

      {/* Signal pill */}
      <div className="flex-shrink-0">
        <SignalPill signal={domain.signal} size={9} />
      </div>

      {/* Score bar */}
      <div className="flex-shrink-0">
        <DomainScoreBar score={domain.score} />
      </div>

      {/* Rationale — truncated, full text on hover */}
      <div
        className="flex-1 text-[10px] font-mono overflow-hidden text-ellipsis whitespace-nowrap min-w-0"
        style={{ color: 'rgba(255,255,255,0.45)' }}
        title={domain.rationale || ''}
      >
        {domain.rationale || '—'}
      </div>
    </div>
  );
}

export default function CompositeAnalysisCard() {
  const guideMode = useGuideMode();
  const fetchAnalysis = useCallback(() => api.getCompositeAnalysis(), []);
  const { data, loading, error } = useFetch(fetchAnalysis);

  return (
    <div className="card p-5 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="label">Composite Analysis</div>
        <span
          className="text-[10px] font-mono"
          style={{ color: 'rgba(255,255,255,0.50)' }}
        >
          rule-based · 4 domains
        </span>
      </div>

      {guideMode && (
        <div
          style={{
            fontSize: 10,
            color: 'rgba(59,130,246,0.7)',
            fontFamily: 'JetBrains Mono, monospace',
            marginBottom: 10,
            lineHeight: 1.6,
          }}
        >
          Four deterministic rule-based analysts (equity, rates, credit, liquidity) vote on macro disposition. High conviction = 3+ analysts agree. Regime alignment confirms HMM and rule-based approaches agree.
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-2 mt-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-8 rounded" style={{ background: 'rgba(255,255,255,0.04)' }} />
          ))}
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <p
          className="text-[11px] font-mono py-4 text-center"
          style={{ color: 'rgba(255,255,255,0.50)' }}
        >
          Analysis unavailable
        </p>
      )}

      {/* Content */}
      {!loading && !error && data && (
        <>
          {/* Top row: composite signal + conviction + alignment */}
          <div className="flex items-center gap-3 flex-wrap mt-2 mb-1">
            <SignalPill signal={data.composite_signal} size={10} />

            {/* Conviction badge */}
            <span
              style={{
                fontSize: 10,
                fontFamily: 'JetBrains Mono, monospace',
                color: convictionColor(data.conviction),
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid #2a2a2a',
                borderRadius: 4,
                padding: '1px 6px',
              }}
            >
              {data.conviction || '—'} conviction
            </span>

            {/* Regime alignment */}
            <span
              style={{
                fontSize: 10,
                fontFamily: 'JetBrains Mono, monospace',
                color: data.regime_alignment ? '#22c55e' : '#ef4444',
                background: data.regime_alignment ? 'rgba(34,197,94,0.07)' : 'rgba(239,68,68,0.07)',
                border: `1px solid ${data.regime_alignment ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                borderRadius: 4,
                padding: '1px 6px',
              }}
            >
              {data.regime_alignment ? '✓ aligned' : '✗ divergent'}
            </span>
          </div>

          {/* Composite score bar */}
          <CompositeScoreBar score={data.composite_score} />

          {/* Domain rows */}
          {data.domain_signals && (
            <div className="mt-2">
              <div className="text-[10px] font-mono uppercase tracking-wide mb-1" style={{ color: 'rgba(255,255,255,0.45)' }}>
                Domain breakdown
              </div>
              {Object.entries(data.domain_signals).map(([key, domain]) => (
                <DomainRow key={key} domainKey={key} domain={domain} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
