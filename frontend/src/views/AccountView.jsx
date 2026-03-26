import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

const TIER_COLOR = { free: '#6b7280', starter: '#22c55e', pro: '#3b82f6', owner: '#f59e0b' };
const TIER_LIMIT = { free: 50, starter: 500, pro: -1, owner: -1 };

function UsageBar({ used, limit }) {
  if (limit <= 0) return (
    <div className="text-[11px] font-mono" style={{ color: '#22c55e' }}>Unlimited</div>
  );
  const pct = Math.min(100, (used / limit) * 100);
  const color = pct > 90 ? '#ef4444' : pct > 70 ? '#f59e0b' : '#22c55e';
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.60)' }}>
          {used} / {limit} today
        </span>
        <span className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.35)' }}>
          {Math.max(0, limit - used)} remaining
        </span>
      </div>
      <div className="h-1 bg-[#1a1a1a]">
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="border border-[#1a1a1a] bg-surface-1 mb-4">
      <div className="px-4 py-2.5 border-b border-[#1a1a1a]">
        <span className="text-[10px] font-mono uppercase tracking-widest"
          style={{ color: 'rgba(255,255,255,0.45)' }}>
          {title}
        </span>
      </div>
      <div className="px-4 py-4">{children}</div>
    </div>
  );
}

export default function AccountView({ meInfo, tier, onTierChange }) {
  const [usage, setUsage]         = useState(null);
  const [rotating, setRotating]   = useState(false);
  const [rotateConfirm, setRotateConfirm] = useState(false);
  const [newKey, setNewKey]       = useState('');
  const [keyCopied, setKeyCopied] = useState(false);
  const [loadingCheckout, setLoadingCheckout] = useState('');
  const [loadingPortal, setLoadingPortal]     = useState(false);
  const [error, setError]         = useState('');

  const t = tier || 'free';
  const color = TIER_COLOR[t] || TIER_COLOR.free;
  const isProOrAbove = t === 'pro' || t === 'owner';
  const isPaid = t === 'starter' || isProOrAbove;

  useEffect(() => {
    if (!api.hasKey()) return;
    api.getUsage()
      .then(setUsage)
      .catch(() => {});
  }, []);

  async function handleRotate() {
    if (!rotateConfirm) { setRotateConfirm(true); return; }
    setRotating(true);
    setError('');
    try {
      const res = await api.rotateKey();
      api.setKey(res.api_key);
      setNewKey(res.api_key);
      setRotateConfirm(false);
    } catch {
      setError('Key rotation failed. Try again.');
    } finally {
      setRotating(false);
    }
  }

  function copyNewKey() {
    navigator.clipboard.writeText(newKey).then(() => {
      setKeyCopied(true);
      setTimeout(() => setKeyCopied(false), 2000);
    });
  }

  async function handleUpgrade(upgradeTier) {
    setLoadingCheckout(upgradeTier);
    setError('');
    try {
      const res = await api.getCheckout(upgradeTier);
      window.open(res.checkout_url, '_blank');
    } catch {
      setError('Could not open checkout. Contact support@macropulse.live.');
    } finally {
      setLoadingCheckout('');
    }
  }

  async function handlePortal() {
    setLoadingPortal(true);
    setError('');
    try {
      const res = await api.getBillingPortal();
      window.open(res.portal_url, '_blank');
    } catch {
      setError('Could not open billing portal. Contact support@macropulse.live.');
    } finally {
      setLoadingPortal(false);
    }
  }

  return (
    <div className="max-w-lg">
      <div className="mb-5">
        <h2 className="text-[15px] font-semibold mb-0.5">Account</h2>
        <p className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.40)' }}>
          Manage your API key, tier, and billing.
        </p>
      </div>

      {error && (
        <div className="mb-4 border border-[#2a1a1a] bg-[#1a0a0a] px-4 py-3 text-[11px] font-mono"
          style={{ color: '#ef4444' }}>
          {error}
        </div>
      )}

      {/* Profile */}
      <Section title="Profile">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[12px] font-mono text-white/80">
              {meInfo?.email || '—'}
            </div>
            <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>
              {api.getKey()?.slice(0, 16)}…
            </div>
          </div>
          <span
            className="text-[10px] font-mono uppercase tracking-wide px-2 py-0.5"
            style={{ color, border: `1px solid ${color}40` }}
          >
            {t}
          </span>
        </div>
      </Section>

      {/* Usage */}
      {usage && (
        <Section title="Today's usage">
          <UsageBar used={usage.used_today} limit={usage.daily_limit} />
          <div className="mt-2 text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.30)' }}>
            Resets at midnight UTC
          </div>
        </Section>
      )}

      {/* Upgrade */}
      {!isPaid && (
        <Section title="Upgrade plan">
          <div className="space-y-3">
            <div className="flex items-center justify-between border border-[#1a1a1a] px-3 py-3">
              <div>
                <div className="text-[12px] font-semibold" style={{ color: '#22c55e' }}>Starter</div>
                <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.40)' }}>
                  500 req/day · Liquidity · Signals · 180d history
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-semibold text-white/70">$49<span className="text-[9px] text-white/35">/mo</span></div>
                <button
                  onClick={() => handleUpgrade('starter')}
                  disabled={!!loadingCheckout}
                  className="mt-1 text-[10px] font-mono px-3 py-1 transition-opacity disabled:opacity-40"
                  style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.25)' }}
                >
                  {loadingCheckout === 'starter' ? '...' : 'Upgrade →'}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between border border-[#1a1a1a] px-3 py-3">
              <div>
                <div className="text-[12px] font-semibold" style={{ color: '#3b82f6' }}>Pro</div>
                <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.40)' }}>
                  Unlimited · All domains · Backtests · Full history
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-semibold text-white/70">$199<span className="text-[9px] text-white/35">/mo</span></div>
                <button
                  onClick={() => handleUpgrade('pro')}
                  disabled={!!loadingCheckout}
                  className="mt-1 text-[10px] font-mono px-3 py-1 transition-opacity disabled:opacity-40"
                  style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.25)' }}
                >
                  {loadingCheckout === 'pro' ? '...' : 'Upgrade →'}
                </button>
              </div>
            </div>
          </div>
        </Section>
      )}

      {/* Starter → Pro upsell */}
      {t === 'starter' && (
        <Section title="Upgrade to Pro">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[12px] font-semibold" style={{ color: '#3b82f6' }}>Pro</div>
              <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.40)' }}>
                Unlimited requests · All domain views · Backtests
              </div>
            </div>
            <div className="text-right">
              <div className="text-[11px] font-semibold text-white/70">$199<span className="text-[9px] text-white/35">/mo</span></div>
              <button
                onClick={() => handleUpgrade('pro')}
                disabled={!!loadingCheckout}
                className="mt-1 text-[10px] font-mono px-3 py-1 transition-opacity disabled:opacity-40"
                style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.25)' }}
              >
                {loadingCheckout === 'pro' ? '...' : 'Upgrade →'}
              </button>
            </div>
          </div>
        </Section>
      )}

      {/* Billing portal (paid users) */}
      {isPaid && (
        <Section title="Billing">
          <div className="flex items-center justify-between">
            <div className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.50)' }}>
              Manage subscription, invoices, and payment method.
            </div>
            <button
              onClick={handlePortal}
              disabled={loadingPortal}
              className="flex-shrink-0 ml-4 text-[10px] font-mono px-3 py-1.5 transition-opacity disabled:opacity-40"
              style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.6)', border: '1px solid rgba(255,255,255,0.12)' }}
            >
              {loadingPortal ? '...' : 'Billing portal →'}
            </button>
          </div>
        </Section>
      )}

      {/* Key rotation */}
      <Section title="API key">
        {newKey ? (
          <div>
            <div className="text-[10px] font-mono mb-2" style={{ color: 'rgba(255,255,255,0.45)' }}>
              New key issued — shown once only
            </div>
            <div className="flex items-center gap-2 border border-[#252525] bg-[#080808] px-3 py-2.5 mb-3">
              <span className="font-mono text-[11px] truncate flex-1" style={{ color: '#22c55e' }}>
                {newKey}
              </span>
              <button
                onClick={copyNewKey}
                className="flex-shrink-0 text-[10px] font-mono px-2 py-1"
                style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.25)' }}
              >
                {keyCopied ? '✓ copied' : 'copy'}
              </button>
            </div>
            <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.30)' }}>
              Key saved in this browser. Previous key is now revoked.
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.60)' }}>
                {api.getKey()?.slice(0, 16)}…
              </div>
              <div className="text-[10px] font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>
                Revokes current key and issues a new one.
              </div>
            </div>
            <button
              onClick={handleRotate}
              disabled={rotating}
              className="flex-shrink-0 ml-4 text-[10px] font-mono px-3 py-1.5 transition-all disabled:opacity-40"
              style={{
                background: rotateConfirm ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.05)',
                color: rotateConfirm ? '#ef4444' : 'rgba(255,255,255,0.55)',
                border: `1px solid ${rotateConfirm ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.1)'}`,
              }}
            >
              {rotating ? '...' : rotateConfirm ? 'Confirm rotate' : 'Rotate key'}
            </button>
          </div>
        )}
      </Section>

      {/* Docs + support */}
      <div className="text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.30)' }}>
        Need help?{' '}
        <a href="https://macropulse.live/api-docs.html" target="_blank" rel="noopener noreferrer"
          style={{ color: 'rgba(255,255,255,0.50)', textDecoration: 'underline' }}>
          API docs
        </a>{' '}·{' '}
        <a href="mailto:support@macropulse.live"
          style={{ color: 'rgba(255,255,255,0.50)', textDecoration: 'underline' }}>
          support@macropulse.live
        </a>
      </div>
    </div>
  );
}
