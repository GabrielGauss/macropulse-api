/**
 * Shared dark-theme Recharts tooltip for all domain views.
 *
 * Props forwarded from Recharts <Tooltip content={<ChartTooltip />} />:
 *   active, payload, label
 *
 * Optional:
 *   formatValue  — (value, dataKey) => string   default: shows raw number with +/- sign
 */
export default function ChartTooltip({ active, payload, label, formatValue }) {
  if (!active || !payload?.length) return null;

  const fmt = formatValue || ((v) => {
    const n = Number(v);
    if (isNaN(n)) return String(v);
    return (n > 0 ? '+' : '') + (n * 100).toFixed(3) + '%';
  });

  return (
    <div style={{
      background: '#141414',
      border: '1px solid #2a2a2a',
      borderRadius: 6,
      padding: '8px 12px',
      fontSize: 11,
      fontFamily: 'JetBrains Mono, monospace',
      minWidth: 140,
    }}>
      <div style={{ color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ color: p.color, lineHeight: '1.6' }}>
          {p.name}: {fmt(p.value, p.dataKey)}
        </div>
      ))}
    </div>
  );
}
