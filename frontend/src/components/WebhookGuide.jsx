import React, { useState } from 'react';

const STEP = { color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', fontSize: 10 };

export default function WebhookGuide({ tier }) {
  const [open, setOpen] = useState(true);
  const isPaid = tier === 'starter' || tier === 'pro' || tier === 'owner';

  return (
    <div
      className="card"
      style={{ padding: '14px 20px', borderColor: open ? '#2a2a2a' : '#1a1a1a' }}
    >
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8h1a4 4 0 0 1 0 8h-1"/><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="10" y1="1" x2="10" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/>
          </svg>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'rgba(255,255,255,0.7)', fontFamily: 'JetBrains Mono, monospace', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Webhook Delivery
          </span>
          {!isPaid && (
            <span style={{ fontSize: 9, color: '#f59e0b', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 3, padding: '1px 5px', fontFamily: 'JetBrains Mono, monospace' }}>
              Pro
            </span>
          )}
        </div>
        <svg
          width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}
        >
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </button>

      {open && (
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.65, margin: 0 }}>
            MacroPulse can POST a JSON payload to your endpoint every time the daily pipeline runs and detects a regime change. Available on the <strong style={{ color: 'rgba(255,255,255,0.7)' }}>Pro</strong> tier.
          </p>

          {/* Step 1 */}
          <div>
            <div style={{ ...STEP, marginBottom: 6 }}>01 — Register your webhook URL</div>
            <div style={{ background: '#0a0a0a', border: '1px solid #1f1f1f', borderRadius: 6, padding: '10px 14px', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.6)', lineHeight: 1.8 }}>
              <span style={{ color: '#888' }}>POST</span> <span style={{ color: '#3b82f6' }}>https://api.macropulse.live/v1/auth/webhook</span><br/>
              <span style={{ color: '#888' }}>Header:</span> X-MacroPulse-Key: <span style={{ color: '#22c55e' }}>mp_...</span><br/>
              <span style={{ color: '#888' }}>Body: </span>
              {'{'}"webhook_url": <span style={{ color: '#f59e0b' }}>"https://your.server/hook"</span>{'}'}
            </div>
          </div>

          {/* Step 2 */}
          <div>
            <div style={{ ...STEP, marginBottom: 6 }}>02 — Receive regime-change payloads</div>
            <div style={{ background: '#0a0a0a', border: '1px solid #1f1f1f', borderRadius: 6, padding: '10px 14px', fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: 'rgba(255,255,255,0.6)', lineHeight: 1.8 }}>
              <span style={{ color: '#888' }}>// POST to your URL when regime changes:</span><br/>
              {'{'}<br/>
              &nbsp;&nbsp;"event": <span style={{ color: '#f59e0b' }}>"regime_change"</span>,<br/>
              &nbsp;&nbsp;"prev_regime": <span style={{ color: '#f59e0b' }}>"tightening"</span>,<br/>
              &nbsp;&nbsp;"new_regime": &nbsp;<span style={{ color: '#22c55e' }}>"recovery"</span>,<br/>
              &nbsp;&nbsp;"risk_score": &nbsp;<span style={{ color: '#a78bfa' }}>31.1</span>,<br/>
              &nbsp;&nbsp;"date": &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style={{ color: '#f59e0b' }}>"2026-03-18"</span><br/>
              {'}'}
            </div>
          </div>

          {/* Step 3 */}
          <div>
            <div style={{ ...STEP, marginBottom: 6 }}>03 — Verify delivery (optional)</div>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', lineHeight: 1.65, margin: 0 }}>
              Your endpoint must respond with <code style={{ color: '#22c55e', background: 'rgba(34,197,94,0.08)', padding: '1px 5px', borderRadius: 3 }}>2xx</code> within 10 seconds.
              Failed deliveries are retried up to 3 times with exponential backoff.
              Check delivery status at <code style={{ color: '#3b82f6', background: 'rgba(59,130,246,0.08)', padding: '1px 5px', borderRadius: 3 }}>GET /v1/auth/webhook</code>.
            </p>
          </div>

          <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <a
              href="https://macropulse.live/api-docs.html#webhooks"
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 10, color: '#3b82f6', fontFamily: 'JetBrains Mono, monospace', textDecoration: 'none' }}
            >
              Full API docs →
            </a>
            {!isPaid && (
              <a
                href="https://macropulse.live/#pricing"
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: 10, color: '#f59e0b', fontFamily: 'JetBrains Mono, monospace', textDecoration: 'none' }}
              >
                Upgrade to Pro →
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
