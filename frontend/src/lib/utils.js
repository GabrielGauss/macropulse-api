// Semantically correct regime colors:
//   expansion  = green  (ample liquidity, risk-on)
//   recovery   = blue   (healing, cautious risk-on)
//   tightening = amber  (Fed draining, defensive)
//   risk_off   = red    (crisis, flat)
export const REGIME_CONFIG = {
  expansion:  { color: '#22c55e', bg: 'rgba(34,197,94,0.10)',  label: 'Expansion',  short: 'EXP' },
  recovery:   { color: '#3b82f6', bg: 'rgba(59,130,246,0.10)', label: 'Recovery',   short: 'REC' },
  tightening: { color: '#f59e0b', bg: 'rgba(245,158,11,0.10)', label: 'Tightening', short: 'TGT' },
  risk_off:   { color: '#ef4444', bg: 'rgba(239,68,68,0.10)',  label: 'Risk-Off',   short: 'RFO' },
};

export function formatDate(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateShort(ts) {
  if (!ts) return '—';
  const d = new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function formatNumber(n, decimals = 1) {
  if (n == null) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e12) return (n / 1e12).toFixed(decimals) + 'T';
  if (abs >= 1e9)  return (n / 1e9).toFixed(decimals) + 'B';
  if (abs >= 1e6)  return (n / 1e6).toFixed(decimals) + 'M';
  return n.toFixed(decimals);
}

export function riskColor(score) {
  if (score >= 30)  return '#22c55e';
  if (score >= 0)   return '#3b82f6';
  if (score >= -30) return '#f59e0b';
  return '#ef4444';
}

export function confidenceBadge(conf) {
  if (!conf) return { color: '#555', bg: 'rgba(85,85,85,0.15)' };
  if (conf === 'HIGH')     return { color: '#22c55e', bg: 'rgba(34,197,94,0.1)' };
  if (conf === 'MODERATE') return { color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' };
  return { color: '#ef4444', bg: 'rgba(239,68,68,0.1)' };
}
