const BASE = '';

function getKey() {
  return localStorage.getItem('mp_api_key') || '';
}

async function apiFetch(path, options = {}) {
  const key = getKey();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (key) headers['X-MacroPulse-Key'] = key;
  const res = await fetch(`${BASE}${path}`, { headers, ...options });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
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
  getHealth:         () => apiFetch('/health'),
  setKey:            (key) => { if (key) localStorage.setItem('mp_api_key', key.trim()); else localStorage.removeItem('mp_api_key'); },
  getKey,
  hasKey:            () => !!getKey(),
};
