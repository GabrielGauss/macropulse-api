import React, { useState, useCallback } from 'react';
import { useFetch } from '../hooks/useFetch';
import { api } from '../lib/api';

export default function AlertSettings({ tier }) {
  const isPro = tier === 'pro' || tier === 'owner';
  const isStarter = tier === 'starter' || isPro;

  const fetchInfo = useCallback(() => isPro ? api.getWebhookInfo() : Promise.resolve(null), [isPro]);
  const { data: webhookInfo, refetch } = useFetch(fetchInfo);

  const [webhookUrl, setWebhookUrl] = useState('');
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [msg, setMsg] = useState(null);

  async function saveWebhook() {
    setSaving(true); setMsg(null);
    try {
      await api.setWebhook(webhookUrl || null);
      setMsg({ type: 'ok', text: 'Webhook saved.' });
      refetch();
    } catch (e) {
      setMsg({ type: 'err', text: e.message || 'Failed to save.' });
    } finally { setSaving(false); }
  }

  async function testWebhook() {
    setTesting(true); setMsg(null);
    try {
      const r = await api.testWebhook();
      setMsg({ type: 'ok', text: `Test delivered (HTTP ${r.http_status}).` });
    } catch (e) {
      setMsg({ type: 'err', text: 'Delivery failed — check your endpoint.' });
    } finally { setTesting(false); }
  }

  return (
    <div className="card p-5 animate-in">
      <div className="label mb-4">Regime Change Alerts</div>

      {/* Email alerts */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[13px] font-semibold text-white/80">Email alerts</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded"
            style={{ background: isStarter ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.05)',
                     color: isStarter ? '#22c55e' : 'rgba(255,255,255,0.3)',
                     border: `1px solid ${isStarter ? 'rgba(34,197,94,0.2)' : '#222'}` }}>
            {isStarter ? 'active' : 'starter+'}
          </span>
        </div>
        <p className="text-[12px] text-white/50 font-mono">
          {isStarter
            ? 'You will receive an email when the macro regime changes — immediately after the daily pipeline runs at 18:30 UTC.'
            : 'Upgrade to Starter to receive email alerts on every regime change.'}
        </p>
      </div>

      {/* Webhook */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-[13px] font-semibold text-white/80">Webhook delivery</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded"
            style={{ background: isPro ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.05)',
                     color: isPro ? '#3b82f6' : 'rgba(255,255,255,0.3)',
                     border: `1px solid ${isPro ? 'rgba(59,130,246,0.2)' : '#222'}` }}>
            {isPro ? (webhookInfo?.configured ? 'configured' : 'not set') : 'pro only'}
          </span>
        </div>
        {isPro ? (
          <>
            <p className="text-[12px] text-white/50 font-mono mb-3">
              POST regime change payload to your endpoint on every transition.
            </p>
            {webhookInfo?.webhook_url && (
              <div className="text-[11px] font-mono text-white/40 mb-2">
                Current: {webhookInfo.webhook_url}
              </div>
            )}
            <div className="flex gap-2">
              <input
                type="url"
                value={webhookUrl}
                onChange={e => setWebhookUrl(e.target.value)}
                placeholder="https://your-endpoint.com/hook"
                className="flex-1 rounded px-3 py-2 text-[12px] font-mono"
                style={{ background: '#111', border: '1px solid #2a2a2a', color: '#f0f0f0', outline: 'none' }}
              />
              <button
                onClick={saveWebhook}
                disabled={saving}
                className="px-4 py-2 rounded text-[12px] font-semibold transition-opacity hover:opacity-80"
                style={{ background: '#f0f0f0', color: '#0a0a0a' }}
              >
                {saving ? '…' : 'Save'}
              </button>
              {webhookInfo?.configured && (
                <button
                  onClick={testWebhook}
                  disabled={testing}
                  className="px-4 py-2 rounded text-[12px] font-semibold transition-opacity hover:opacity-80"
                  style={{ background: 'transparent', border: '1px solid #2a2a2a', color: 'rgba(255,255,255,0.6)' }}
                >
                  {testing ? '…' : 'Test'}
                </button>
              )}
            </div>
            {msg && (
              <div className="mt-2 text-[11px] font-mono" style={{ color: msg.type === 'ok' ? '#22c55e' : '#ef4444' }}>
                {msg.text}
              </div>
            )}
          </>
        ) : (
          <p className="text-[12px] text-white/50 font-mono">
            <a href="https://macropulse.live/#pricing" target="_blank" rel="noopener noreferrer"
               style={{ color: '#3b82f6', textDecoration: 'none' }}>
              Upgrade to Pro
            </a> to configure a webhook endpoint for automated regime change delivery.
          </p>
        )}
      </div>
    </div>
  );
}
