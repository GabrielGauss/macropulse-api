import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, Brush,
} from 'recharts';
import { formatDateShort } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };

const FACTORS = [
  {
    key: 'factor_1', color: '#22c55e', short: 'F1',
    label: 'F1 — Rates / Liquidity',
    guide: 'Primary axis: captures Fed balance sheet + yield curve dynamics. Positive = system flush with liquidity.',
  },
  {
    key: 'factor_2', color: '#3b82f6', short: 'F2',
    label: 'F2 — Risk Appetite',
    guide: 'Secondary axis: equity momentum vs credit stress. Positive = risk-on; negative = flight to safety.',
  },
  {
    key: 'factor_3', color: '#f59e0b', short: 'F3',
    label: 'F3 — Growth / Inflation',
    guide: 'Tertiary axis: growth-inflation differential. Positive = growth dominant; negative = stagflation signal.',
  },
  {
    key: 'factor_4', color: '#ef4444', short: 'F4',
    label: 'F4 — Dollar / Stress',
    guide: 'Quaternary: DXY strength + HY spread residual. Rising = dollar strength & credit stress.',
  },
];

function FactorTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: '#0d0d0d', border: '1px solid #2a2a2a',
      borderRadius: 8, padding: '10px 14px',
      fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
      boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
    }}>
      <div style={{ color: 'rgba(255,255,255,0.3)', marginBottom: 7, fontSize: 10 }}>
        {formatDateShort(d?.time)}
      </div>
      {payload.map((p, i) => {
        const f = FACTORS.find(f => f.key === p.dataKey);
        return (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 20, marginTop: 3 }}>
            <span style={{ color: p.color, opacity: 0.8 }}>{f?.short ?? p.name}</span>
            <span style={{ color: p.color, fontWeight: 700 }}>
              {p.value >= 0 ? '+' : ''}{p.value?.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function FactorsChart({ data }) {
  const guideMode = useGuideMode();

  if (!data?.data?.length) {
    return (
      <div className="card flex h-64 items-center justify-center">
        <p className="text-[11px] text-white/45 font-mono">No factor data</p>
      </div>
    );
  }

  const rows = [...data.data].reverse();

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-start justify-between mb-1">
        <div className="label">PCA Latent Factors</div>
        <div className="flex gap-3 flex-wrap justify-end">
          {FACTORS.map((f) => (
            <div key={f.key} className="flex items-center gap-1.5">
              <div className="h-2 w-3 rounded-sm flex-shrink-0" style={{ background: f.color, opacity: 0.8 }} />
              <span className="text-[10px] text-white/50 font-mono">{f.short}</span>
            </div>
          ))}
        </div>
      </div>

      {guideMode ? (
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', lineHeight: 1.5, marginBottom: 6 }}>
            PCA reduces 8 raw macro features to 4 orthogonal latent dimensions. F1 explains the most variance. Cross-zero moves = directional regime pressure. Drag the brush to zoom.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {FACTORS.map(f => (
              <div key={f.key} style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: f.color, fontWeight: 700, flexShrink: 0 }}>{f.short}</span>
                <span style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(59,130,246,0.55)', lineHeight: 1.5 }}>{f.guide}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-[10px] text-white/45 font-mono mb-3">
          4 orthogonal axes from PCA · cross-zero = directional shift
        </div>
      )}

      <ResponsiveContainer width="100%" height={260}>
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
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.07)" strokeDasharray="2 4" />
          <Tooltip content={<FactorTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
          {FACTORS.map((f) => (
            <Line
              key={f.key}
              type="monotone"
              dataKey={f.key}
              name={f.short}
              stroke={f.color}
              strokeWidth={1.5}
              dot={false}
              opacity={0.8}
              activeDot={{ r: 3, fill: f.color, strokeWidth: 0 }}
            />
          ))}
          <Brush
            dataKey="time"
            height={20}
            stroke="#1f1f1f"
            fill="#0d0d0d"
            travellerWidth={6}
            tickFormatter={() => ''}
            startIndex={Math.max(0, rows.length - 90)}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
