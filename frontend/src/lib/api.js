const BASE = '';

function getKey() {
  return localStorage.getItem('mp_api_key') || '';
}

async function apiFetch(path, options = {}) {
  const key = getKey();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (key) headers['X-MacroPulse-Key'] = key;
  const res = await fetch(`${BASE}${path}`, { headers, ...options });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return Promise.reject(data);
  }
  return res.json();
}

// Unauthenticated helper for auth endpoints (no key header needed)
async function publicFetch(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return Promise.reject(data);
  return data;
}

export const api = {
  getCurrentRegime:  () => apiFetch('/v1/regime/current'),
  getRegimeHistory:  (limit = 90) => apiFetch(`/v1/regime/history?limit=${limit}`),
  getLiquidity:      (limit = 60) => apiFetch(`/v1/liquidity?limit=${limit}`),
  getFactors:        (limit = 60) => apiFetch(`/v1/factors?limit=${limit}`),
  getDrift:          (limit = 30) => apiFetch(`/v1/drift?limit=${limit}`),
  getScorecard:      () => apiFetch('/v1/scorecard'),
  getFeatures:       (limit = 90) => apiFetch(`/v1/features?limit=${limit}`),
  getSignals:        () => apiFetch('/v1/signals/latest'),
  runBacktest:       (params) => apiFetch('/v1/backtest', { method: 'POST', body: JSON.stringify(params) }),
  getMe:             () => apiFetch('/v1/auth/me'),
  exportRegimeCsv: (limit = 730) => {
    const key = getKey();
    const url = `${BASE}/v1/regime/export?limit=${limit}`;
    return fetch(url, { headers: key ? { 'X-MacroPulse-Key': key } : {} });
  },
  getHealth:         () => apiFetch('/health'),
  getPipelineStatus:       () => apiFetch('/v1/pipeline/status'),
  getTransitionMatrix:     () => apiFetch('/v1/model/transition-matrix'),
  getFeatureLoadings:      () => apiFetch('/v1/model/feature-loadings'),
  getProbabilitySeries:    (limit = 365) => apiFetch(`/v1/model/probabilities?limit=${limit}`),
  getCommentary:        () => apiFetch('/v1/regime/commentary'),
  getForecast:          (horizon = 5) => apiFetch(`/v1/forecast?horizon=${horizon}`),
  getCompositeAnalysis: () => apiFetch('/v1/analysis/composite'),
  getWebhookInfo:    () => apiFetch('/v1/webhook/info'),
  setWebhook:        (url) => apiFetch('/v1/webhook/set', { method: 'POST', body: JSON.stringify({ url }) }),
  testWebhook:       () => apiFetch('/v1/webhook/test'),
  // Auth — registration flow (no key required)
  register:          (email) => publicFetch('/v1/auth/register', { email }),
  verify:            (email, code) => publicFetch('/v1/auth/verify', { email, code }),
  // Auth — key recovery flow (no key required)
  recover:           (email) => publicFetch('/v1/auth/recover', { email }),
  recoverVerify:     (email, code) => publicFetch('/v1/auth/recover/verify', { email, code }),
  // Auth — key management (key required)
  rotateKey:         () => apiFetch('/v1/auth/rotate', { method: 'POST' }),
  getUsage:          () => apiFetch('/v1/auth/usage'),
  // Billing — Stripe
  getCheckout:       (tier) => apiFetch('/v1/billing/stripe/checkout', { method: 'POST', body: JSON.stringify({ tier }) }),
  getBillingPortal:  () => apiFetch('/v1/billing/stripe/portal'),

  setKey:            (key) => { if (key) localStorage.setItem('mp_api_key', key.trim()); else localStorage.removeItem('mp_api_key'); },
  getKey,
  hasKey:            () => !!getKey(),
};
