"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ModalityScorePoint } from "@/lib/charts/series";

type ModalityScoresChartProps = {
  points: ModalityScorePoint[];
};

export function ModalityScoresChart({ points }: ModalityScoresChartProps) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Sem contribuições de modalidade para plotar.
      </p>
    );
  }

  return (
    <div
      className="h-56 w-full"
      role="img"
      aria-label="Scores parciais por modalidade"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis dataKey="modality" tick={{ fontSize: 12 }} />
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
          <Bar
            dataKey="score"
            name="Score parcial"
            fill="var(--foreground)"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
