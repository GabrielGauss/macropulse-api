import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts';
import { formatDateShort } from '../lib/utils';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

// Subdued but distinct — not neon
const FACTOR_COLORS = [
  { line: '#22c55e', label: 'F1 — Liquidity' },
  { line: '#3b82f6', label: 'F2 — Risk Appetite' },
  { line: '#f59e0b', label: 'F3 — Growth' },
  { line: '#ef4444', label: 'F4 — Stress' },
];

function FactorTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: '#141414', border: '1px solid #2a2a2a',
      borderRadius: 6, padding: '8px 12px',
      fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
    }}>
      <div style={{ color: 'rgba(255,255,255,0.3)', marginBottom: 6 }}>
        {formatDateShort(d?.time)}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginTop: 2 }}>
          {p.name}: <span style={{ fontWeight: 600 }}>{p.value?.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}

export default function FactorsChart({ data }) {
  if (!data?.data?.length) {
    return (
      <div className="card flex h-64 items-center justify-center">
        <p className="text-[11px] text-white/25 font-mono">No factor data</p>
      </div>
    );
  }

  const rows = [...data.data].reverse();

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-start justify-between mb-4">
        <div className="label">PCA Latent Factors</div>
        <div className="flex gap-3 flex-wrap justify-end">
          {FACTOR_COLORS.map((f, i) => (
            <div key={i} className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-sm flex-shrink-0" style={{ background: f.line }} />
              <span className="text-[9px] text-white/25 font-mono">F{i + 1}</span>
            </div>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={rows} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />
          <XAxis
            dataKey="time"
            tick={TICK}
            tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis tick={TICK} axisLine={false} tickLine={false} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" />
          <Tooltip content={<FactorTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
          {FACTOR_COLORS.map((f, i) => (
            <Line
              key={i}
              type="monotone"
              dataKey={`factor_${i + 1}`}
              name={`F${i + 1}`}
              stroke={f.line}
              strokeWidth={1.5}
              dot={false}
              opacity={0.75}
              activeDot={{ r: 3, fill: f.line, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
