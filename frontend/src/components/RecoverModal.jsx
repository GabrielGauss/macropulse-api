import React, { useState, useRef, useEffect } from 'react';
import { api } from '../lib/api';

/**
 * Two-step key recovery modal.
 * Step 1: enter email → POST /v1/auth/recover
 * Step 2: enter 6-digit code → POST /v1/auth/recover/verify → get new API key
 *
 * Props:
 *   onClose()          — called when modal is dismissed
 *   onRecovered(key)   — called with the new plaintext API key on success
 */
export default function RecoverModal({ onClose, onRecovered }) {
  const [step, setStep]       = useState(1); // 1 | 2 | 3 (success)
  const [email, setEmail]     = useState('');
  const [code, setCode]       = useState('');
  const [apiKey, setApiKey]   = useState('');
  const [copied, setCopied]   = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const emailRef = useRef(null);
  const codeRef  = useRef(null);

  useEffect(() => {
    if (step === 1) emailRef.current?.focus();
    if (step === 2) codeRef.current?.focus();
  }, [step]);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  async function handleRecover(e) {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError('');
    try {
      await api.recover(email.trim().toLowerCase());
      setStep(2);
    } catch (err) {
      setError(err?.detail || 'Could not send recovery email. Try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(e) {
    e.preventDefault();
    if (code.trim().length !== 6) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.recoverVerify(email.trim().toLowerCase(), code.trim());
      setApiKey(res.api_key);
      api.setKey(res.api_key);
      setStep(3);
      onRecovered?.(res.api_key);
    } catch (err) {
      setError(err?.detail || 'Invalid or expired code.');
    } finally {
      setLoading(false);
    }
  }

  function copyKey() {
    navigator.clipboard.writeText(apiKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.75)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        className="relative border border-[#252525] bg-[#0a0a0a]"
        style={{ width: 360, padding: '24px 24px 20px' }}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[14px] font-mono transition-colors"
          style={{ color: 'rgba(255,255,255,0.35)' }}
          onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.7)'}
          onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.35)'}
        >×</button>

        {/* Header */}
        <div className="mb-5">
          <div className="text-[11px] font-mono uppercase tracking-widest mb-1"
            style={{ color: '#f59e0b' }}>
            {step === 3 ? 'Key recovered' : 'Recover API key'}
          </div>
          <div className="text-[13px] font-semibold text-white/80">
            {step === 1 && 'Enter your email'}
            {step === 2 && 'Check your inbox'}
            {step === 3 && 'Your new API key'}
          </div>
        </div>

        {/* Step 1 — Email */}
        {step === 1 && (
          <form onSubmit={handleRecover}>
            <div className="mb-4 text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.45)' }}>
              We'll send a 6-digit code. Your old key will be revoked on verify.
            </div>
            <label className="block text-[10px] font-mono uppercase tracking-wide mb-1.5"
              style={{ color: 'rgba(255,255,255,0.45)' }}>
              Email address
            </label>
            <input
              ref={emailRef}
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full border border-[#252525] bg-[#080808] px-3 py-2 font-mono text-[12px] text-white/80 outline-none focus:border-[#333] placeholder:text-white/25 mb-4"
            />
            {error && (
              <div className="text-[11px] font-mono mb-3" style={{ color: '#ef4444' }}>{error}</div>
            )}
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full py-2 text-[12px] font-semibold transition-opacity disabled:opacity-40"
              style={{ background: '#f59e0b', color: '#000' }}
            >
              {loading ? 'Sending...' : 'Send recovery code'}
            </button>
          </form>
        )}

        {/* Step 2 — Code */}
        {step === 2 && (
          <form onSubmit={handleVerify}>
            <div className="mb-4 text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.50)' }}>
              Code sent to <span style={{ color: '#f59e0b' }}>{email}</span>
            </div>
            <label className="block text-[10px] font-mono uppercase tracking-wide mb-1.5"
              style={{ color: 'rgba(255,255,255,0.45)' }}>
              Recovery code
            </label>
            <input
              ref={codeRef}
              type="text"
              inputMode="numeric"
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="000000"
              maxLength={6}
              required
              className="w-full border border-[#252525] bg-[#080808] px-3 py-2 font-mono text-[16px] text-center tracking-[0.5em] text-white/80 outline-none focus:border-[#333] placeholder:text-white/25 mb-4"
            />
            {error && (
              <div className="text-[11px] font-mono mb-3" style={{ color: '#ef4444' }}>{error}</div>
            )}
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full py-2 text-[12px] font-semibold transition-opacity disabled:opacity-40"
              style={{ background: '#f59e0b', color: '#000' }}
            >
              {loading ? 'Verifying...' : 'Verify & recover key'}
            </button>
            <button
              type="button"
              onClick={() => { setStep(1); setCode(''); setError(''); }}
              className="w-full mt-2 py-1.5 text-[11px] font-mono transition-colors"
              style={{ color: 'rgba(255,255,255,0.35)' }}
              onMouseEnter={e => e.target.style.color = 'rgba(255,255,255,0.6)'}
              onMouseLeave={e => e.target.style.color = 'rgba(255,255,255,0.35)'}
            >
              ← Use a different email
            </button>
          </form>
        )}

        {/* Step 3 — Success */}
        {step === 3 && (
          <div>
            <div className="mb-3 text-[11px] font-mono" style={{ color: 'rgba(255,255,255,0.50)' }}>
              New key issued for <span style={{ color: '#f59e0b' }}>{email}</span>. Old key revoked.
            </div>
            <div className="text-[10px] font-mono uppercase tracking-wide mb-2"
              style={{ color: 'rgba(255,255,255,0.45)' }}>
              Your new API key — shown once only
            </div>
            <div
              className="flex items-center justify-between border border-[#252525] bg-[#080808] px-3 py-2.5 mb-4"
            >
              <span className="font-mono text-[11px] truncate mr-2" style={{ color: '#22c55e' }}>
                {apiKey}
              </span>
              <button
                onClick={copyKey}
                className="flex-shrink-0 text-[10px] font-mono px-2 py-1 transition-opacity"
                style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.25)' }}
              >
                {copied ? '✓ copied' : 'copy'}
              </button>
            </div>
            <div className="mb-5 text-[10px] font-mono" style={{ color: 'rgba(255,255,255,0.40)' }}>
              Key saved to this browser. Also sent to your email.
            </div>
            <button
              onClick={onClose}
              className="w-full py-2 text-[12px] font-semibold"
              style={{ background: '#22c55e', color: '#000' }}
            >
              Open dashboard →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
