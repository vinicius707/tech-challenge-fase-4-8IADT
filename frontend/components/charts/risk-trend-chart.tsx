"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RiskTrendPoint } from "@/lib/charts/series";

type RiskTrendChartProps = {
  points: RiskTrendPoint[];
};

export function RiskTrendChart({ points }: RiskTrendChartProps) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Sem histórico de Risco para plotar ainda.
      </p>
    );
  }

  return (
    <div className="h-56 w-full" role="img" aria-label="Tendência de Risco">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} width={36} />
          <Tooltip
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(2) : String(value)
            }
            labelFormatter={(label, payload) => {
              const level = payload?.[0]?.payload?.level;
              return level ? `${label} · ${level}` : String(label);
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            name="Risco"
            stroke="var(--foreground)"
            strokeWidth={2}
            dot={{ r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
