import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts';
import { formatDateShort, formatNumber } from '../lib/utils';
import { useGuideMode } from '../lib/guideMode';

const TICK = { fill: 'rgba(255,255,255,0.2)', fontSize: 10, fontFamily: 'JetBrains Mono' };
const LIQ_COLOR = '#3b82f6';

function LiqTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  const delta = d.d_liquidity;
  const isPos = delta >= 0;
  return (
    <div style={{
      background: '#141414', border: '1px solid #2a2a2a',
      borderRadius: 6, padding: '8px 12px',
      fontSize: 11, fontFamily: 'JetBrains Mono, monospace',
    }}>
      <div style={{ color: 'rgba(255,255,255,0.3)', marginBottom: 4 }}>
        {formatDateShort(d.time)}
      </div>
      <div style={{ color: '#f0f0f0' }}>
        {formatNumber(d.net_liquidity)}
      </div>
      {delta != null && (
        <div style={{ color: isPos ? '#22c55e' : '#ef4444', marginTop: 2 }}>
          {isPos ? '+' : ''}{formatNumber(delta)} 4w
        </div>
      )}
      {d.zscore != null && (
        <div style={{ color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>
          z: {d.zscore.toFixed(2)}
        </div>
      )}
    </div>
  );
}

export default function LiquidityChart({ data }) {
  if (!data?.data?.length) {
    return (
      <div className="card flex h-64 items-center justify-center">
        <p className="text-[11px] text-white/25 font-mono">No liquidity data</p>
      </div>
    );
  }

  const rows = [...data.data].reverse();
  const latest = rows[rows.length - 1];
  const zscore = latest?.zscore;
  const guideMode = useGuideMode();

  // Trend: compare last 5 points
  const trendDelta = rows.length >= 5
    ? rows[rows.length - 1].net_liquidity - rows[rows.length - 5].net_liquidity
    : null;
  const trendUp = trendDelta != null && trendDelta > 0;

  return (
    <div className="card p-5 animate-in">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="label mb-1">Net Liquidity Proxy</div>
          {latest && (
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-lg font-semibold text-white/80">
                {formatNumber(latest.net_liquidity)}
              </span>
              {trendDelta != null && (
                <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono', color: trendUp ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                  {trendUp ? '▲' : '▼'} {formatNumber(Math.abs(trendDelta))}
                </span>
              )}
            </div>
          )}
          {guideMode && (
            <div style={{ fontSize: 10, color: 'rgba(59,130,246,0.7)', fontFamily: 'JetBrains Mono, monospace', marginTop: 3, lineHeight: 1.5 }}>
              Fed reserves + RRP drawdown − TGA build. Positive = system flush with liquidity.
            </div>
          )}
        </div>
        {zscore != null && (
          <div className="text-right">
            <div className="label mb-1">Z-Score</div>
            <div
              className="font-mono text-base font-semibold"
              style={{ color: zscore > 1 ? '#22c55e' : zscore < -1 ? '#ef4444' : '#f59e0b' }}
            >
              {zscore > 0 ? '+' : ''}{zscore.toFixed(2)}
            </div>
            <div style={{ fontSize: 9, fontFamily: 'JetBrains Mono', color: 'rgba(255,255,255,0.2)', marginTop: 2 }}>
              {Math.abs(zscore) > 1 ? (zscore > 0 ? 'elevated' : 'depressed') : 'normal range'}
            </div>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={rows} margin={{ top: 2, right: 2, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="liqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={LIQ_COLOR} stopOpacity={0.15} />
              <stop offset="100%" stopColor={LIQ_COLOR} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="rgba(255,255,255,0.03)" horizontal vertical={false} />
          <XAxis
            dataKey="time"
            tick={TICK}
            tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={TICK}
            tickFormatter={(v) => formatNumber(v, 0)}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<LiqTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="net_liquidity"
            stroke={LIQ_COLOR}
            strokeWidth={1.5}
            fill="url(#liqGrad)"
            dot={false}
            activeDot={{ r: 3, fill: LIQ_COLOR, strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
