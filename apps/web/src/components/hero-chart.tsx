"use client";

import { useQuery } from "@tanstack/react-query";
import { AreaSeries, ColorType, createChart, type IChartApi } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Candle } from "@/lib/types";

const INDICES = [
  { symbol: "INDEX:^NSEI", label: "NIFTY 50" },
  { symbol: "INDEX:^BSESN", label: "SENSEX" },
  { symbol: "INDEX:^GSPC", label: "S&P 500" },
  { symbol: "INDEX:^IXIC", label: "NASDAQ" },
];

const RANGES = [
  { key: "1D", interval: "5m", lastTradingDayOnly: true },
  { key: "1M", interval: "1h", lastTradingDayOnly: false },
  { key: "1Y", interval: "1d", lastTradingDayOnly: false },
] as const;

function toSeries(candles: Candle[], lastDayOnly: boolean) {
  let usable = candles;
  if (lastDayOnly && candles.length > 0) {
    const lastDate = candles[candles.length - 1].timestamp.slice(0, 10);
    usable = candles.filter((candle) => candle.timestamp.startsWith(lastDate));
  }
  return usable.map((candle) => ({
    time: (Date.parse(candle.timestamp) / 1000) as never,
    value: Number(candle.close),
  }));
}

export function HeroChart() {
  const [symbol, setSymbol] = useState(INDICES[0].symbol);
  const [range, setRange] = useState<(typeof RANGES)[number]>(RANGES[0]);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const { data, isPending } = useQuery({
    queryKey: ["candles", symbol, range.interval],
    queryFn: () => api.getCandles(symbol, range.interval),
    staleTime: 60_000,
  });

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !data) return;

    const points = toSeries(data.candles, range.lastTradingDayOnly);
    if (points.length === 0) return;

    const positive = points[points.length - 1].value >= points[0].value;
    const line = positive ? "#34d399" : "#f87171";

    const chart = createChart(container, {
      height: 260,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#737373",
        fontSize: 11,
        attributionLogo: true,
      },
      grid: {
        vertLines: { color: "#1f1f1f" },
        horzLines: { color: "#1f1f1f" },
      },
      rightPriceScale: { borderColor: "#262626" },
      timeScale: {
        borderColor: "#262626",
        timeVisible: range.key !== "1Y",
        // Clamp zoom/pan to the data: no drifting into empty whitespace
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
        minBarSpacing: 2,
      },
      crosshair: { horzLine: { labelBackgroundColor: "#404040" }, vertLine: { labelBackgroundColor: "#404040" } },
      autoSize: true,
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: line,
      lineWidth: 2,
      topColor: positive ? "rgba(52, 211, 153, 0.25)" : "rgba(248, 113, 113, 0.25)",
      bottomColor: "rgba(0,0,0,0)",
      priceLineVisible: false,
    });
    series.setData(points);
    chart.timeScale().fitContent();
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [data, range]);

  return (
    <section className="rounded-lg border border-neutral-800 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1">
          {INDICES.map((index) => (
            <button
              key={index.symbol}
              onClick={() => setSymbol(index.symbol)}
              className={`rounded-md px-2.5 py-1 text-xs ${
                symbol === index.symbol
                  ? "bg-neutral-100 font-medium text-neutral-900"
                  : "border border-neutral-800 text-neutral-400 hover:bg-neutral-900"
              }`}
            >
              {index.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {RANGES.map((option) => (
            <button
              key={option.key}
              onClick={() => setRange(option)}
              className={`rounded-md px-2.5 py-1 text-xs ${
                range.key === option.key
                  ? "bg-neutral-100 font-medium text-neutral-900"
                  : "border border-neutral-800 text-neutral-400 hover:bg-neutral-900"
              }`}
            >
              {option.key}
            </button>
          ))}
        </div>
      </div>
      <div className="relative mt-3 h-[260px]">
        {isPending && (
          <div className="absolute inset-0 animate-pulse rounded bg-neutral-900" />
        )}
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </section>
  );
}
