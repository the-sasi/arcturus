"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Inline 30-day closing-price sparkline. Rendered as a bare SVG path —
 *  polarity is carried by the adjacent signed number, slope is shape-encoded. */
export function Sparkline({
  symbol,
  positive,
  width = 120,
  height = 28,
}: {
  symbol: string;
  positive: boolean | null;
  width?: number;
  height?: number;
}) {
  const { data } = useQuery({
    queryKey: ["candles", symbol, "1d"],
    queryFn: () => api.getCandles(symbol, "1d"),
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const closes = data?.candles.slice(-30).map((candle) => Number(candle.close)) ?? [];
  if (closes.length < 2) {
    return <div style={{ width, height }} />;
  }

  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;
  const step = width / (closes.length - 1);
  const points = closes.map((close, index) => {
    const x = index * step;
    const y = height - 2 - ((close - min) / span) * (height - 4);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const stroke = positive === null ? "#737373" : positive ? "#34d399" : "#f87171";

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      className="overflow-visible"
    >
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.9"
      />
    </svg>
  );
}
