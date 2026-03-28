import { useState } from 'react';

export function ApiKeyManager({ apiKey, tier, onRotate }) {
  const [visible, setVisible]   = useState(false);
  const [rotating, setRotating] = useState(false);
  const [copied, setCopied]     = useState(false);

  const display = apiKey
    ? (visible ? apiKey : `${apiKey.slice(0, 8)}${'•'.repeat(20)}${apiKey.slice(-4)}`)
    : '•'.repeat(32);

  const copy = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const rotate = async () => {
    if (!confirm('Rotate API key? Your current key stops working immediately.')) return;
    setRotating(true);
    try { await onRotate?.(); } finally { setRotating(false); }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-700">API Key</p>
        <span className="text-xs text-gray-400">Plan: {tier ?? 'free'}</span>
      </div>

      <div className="flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-sm">
        <span className="flex-1 truncate text-gray-700">{display}</span>
        <button onClick={() => setVisible(v => !v)} className="shrink-0 text-xs text-gray-400 hover:text-gray-600">
          {visible ? 'Hide' : 'Show'}
        </button>
        <button onClick={copy} className="shrink-0 text-xs text-gray-400 hover:text-gray-600">
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <p className="text-xs text-gray-400">
        Send as <code className="rounded bg-gray-100 px-1">X-MacroPulse-Key: {'{your-key}'}</code> on every request.
      </p>

      <button
        onClick={rotate}
        disabled={rotating}
        className="w-full rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
      >
        {rotating ? 'Rotating\u2026' : 'Rotate Key'}
      </button>
    </div>
  );
}
