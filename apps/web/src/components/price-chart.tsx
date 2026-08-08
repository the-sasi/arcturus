"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Candle } from "@/lib/types";

const RANGES = [
  { key: "1D", interval: "5m", lastDayOnly: true, indicators: false },
  { key: "6M", interval: "1d", lastDayOnly: false, indicators: true, slice: 126 },
  { key: "1Y", interval: "1d", lastDayOnly: false, indicators: true },
  { key: "3Y", interval: "1wk", lastDayOnly: false, indicators: true },
] as const;

const EMA_FAST = { key: "ema_20", label: "EMA 20", color: "#60a5fa" };
const EMA_SLOW = { key: "ema_50", label: "EMA 50", color: "#f59e0b" };
const RSI = { key: "rsi_14", label: "RSI 14", color: "#a78bfa" };

function usableCandles(candles: Candle[], range: (typeof RANGES)[number]): Candle[] {
  let out = candles;
  if (range.lastDayOnly && candles.length > 0) {
    const lastDate = candles[candles.length - 1].timestamp.slice(0, 10);
    out = candles.filter((candle) => candle.timestamp.startsWith(lastDate));
  }
  if ("slice" in range && range.slice) {
    out = out.slice(-range.slice);
  }
  return out;
}

const toTime = (iso: string) => (Date.parse(iso) / 1000) as never;

export function PriceChart({ symbol }: { symbol: string }) {
  const [range, setRange] = useState<(typeof RANGES)[number]>(RANGES[2]);
  const containerRef = useRef<HTMLDivElement>(null);

  const candlesQuery = useQuery({
    queryKey: ["candles", symbol, range.interval],
    queryFn: () => api.getCandles(symbol, range.interval),
    staleTime: 60_000,
  });
  const indicatorsQuery = useQuery({
    queryKey: ["indicators", symbol, range.interval],
    queryFn: () => api.getIndicators(symbol, range.interval, "ema:20,ema:50,rsi:14"),
    enabled: range.indicators,
    staleTime: 60_000,
  });

  useEffect(() => {
    const container = containerRef.current;
    const data = candlesQuery.data;
    if (!container || !data) return;

    const candles = usableCandles(data.candles, range);
    if (candles.length === 0) return;

    const chart = createChart(container, {
      height: 430,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#737373",
        fontSize: 11,
        attributionLogo: true,
      },
      grid: { vertLines: { color: "#1f1f1f" }, horzLines: { color: "#1f1f1f" } },
      rightPriceScale: { borderColor: "#262626" },
      timeScale: {
        borderColor: "#262626",
        timeVisible: range.key === "1D",
        // Clamp zoom/pan to the data: no drifting into empty whitespace
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
        minBarSpacing: 2,
      },
      crosshair: {
        horzLine: { labelBackgroundColor: "#404040" },
        vertLine: { labelBackgroundColor: "#404040" },
      },
      autoSize: true,
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#f87171",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#f87171",
    });
    candleSeries.setData(
      candles.map((candle) => ({
        time: toTime(candle.timestamp),
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
      })),
    );

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      color: "#404040",
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    volumeSeries.setData(
      candles.map((candle) => ({
        time: toTime(candle.timestamp),
        value: candle.volume,
        color: Number(candle.close) >= Number(candle.open) ? "#34d39933" : "#f8717133",
      })),
    );

    const indicators = indicatorsQuery.data;
    if (range.indicators && indicators) {
      const byTimestamp = new Map(indicators.timestamps.map((ts, index) => [ts, index]));
      const overlay = (key: string, color: string, paneIndex = 0) => {
        const points = candles.flatMap((candle) => {
          const index = byTimestamp.get(candle.timestamp);
          const value = index === undefined ? null : indicators.series[key]?.[index];
          return value === null || value === undefined
            ? []
            : [{ time: toTime(candle.timestamp), value }];
        });
        if (points.length === 0) return null;
        const series = chart.addSeries(
          LineSeries,
          { color, lineWidth: 2, priceLineVisible: false, lastValueVisible: false },
          paneIndex,
        );
        series.setData(points);
        return series;
      };

      overlay(EMA_FAST.key, EMA_FAST.color);
      overlay(EMA_SLOW.key, EMA_SLOW.color);
      const rsiSeries = overlay(RSI.key, RSI.color, 1);
      if (rsiSeries) {
        for (const level of [30, 70]) {
          rsiSeries.createPriceLine({
            price: level,
            color: "#525252",
            lineWidth: 1,
            lineStyle: 3,
            axisLabelVisible: false,
            title: "",
          });
        }
        try {
          chart.panes()[1]?.setHeight(96);
        } catch {
          // pane sizing is cosmetic; ignore if unavailable
        }
      }
    }

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candlesQuery.data, indicatorsQuery.data, range]);

  return (
    <section className="rounded-lg border border-neutral-800 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3 text-xs text-neutral-400">
          <span className="font-medium uppercase tracking-wide text-neutral-500">
            Price Chart
          </span>
          {range.indicators && (
            <span className="flex items-center gap-3">
              {[EMA_FAST, EMA_SLOW, RSI].map((item) => (
                <span key={item.key} className="flex items-center gap-1">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  {item.label}
                </span>
              ))}
            </span>
          )}
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
      <div className="relative mt-3 h-[430px]">
        {candlesQuery.isPending && (
          <div className="absolute inset-0 animate-pulse rounded bg-neutral-900" />
        )}
        {candlesQuery.isError && (
          <p className="p-4 text-sm text-red-400">Chart unavailable for this symbol.</p>
        )}
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </section>
  );
}
