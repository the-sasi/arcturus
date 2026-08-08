"use client";

import { useQueries } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BacktestResult } from "@/lib/types";

const STRATEGY_KEYS = ["ema_crossover", "rsi_mean_reversion", "range_breakout"];

function pct(value: number | null, signed = true): string {
  if (value === null) return "—";
  const sign = signed && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

function tone(value: number | null): string {
  if (value === null) return "text-neutral-500";
  return value >= 0 ? "text-emerald-400" : "text-red-400";
}

function Row({ result }: { result: BacktestResult }) {
  const beat = result.total_return_pct - result.buy_hold_return_pct;
  return (
    <tr className="border-b border-neutral-900 last:border-0">
      <td className="px-3 py-2 text-neutral-200">{result.strategy.name}</td>
      <td className="px-3 py-2 tabular-nums text-neutral-400">{result.trades.length}</td>
      <td className="px-3 py-2 tabular-nums text-neutral-400">
        {result.win_rate_pct === null ? "—" : `${result.win_rate_pct.toFixed(0)}%`}
      </td>
      <td className={`px-3 py-2 tabular-nums ${tone(result.total_return_pct)}`}>
        {pct(result.total_return_pct)}
      </td>
      <td className="px-3 py-2 tabular-nums text-neutral-400">
        {pct(result.buy_hold_return_pct)}
      </td>
      <td className={`px-3 py-2 tabular-nums ${tone(beat)}`}>{pct(beat)}</td>
      <td className="px-3 py-2 tabular-nums text-red-400">
        {result.max_drawdown_pct.toFixed(1)}%
      </td>
      <td className="px-3 py-2 tabular-nums text-neutral-400">
        {result.annualized_sharpe === null ? "—" : result.annualized_sharpe.toFixed(2)}
      </td>
      <td className="px-3 py-2 tabular-nums text-neutral-500">
        {result.exposure_pct.toFixed(0)}%
      </td>
    </tr>
  );
}

export function BacktestPanel({ symbol }: { symbol: string }) {
  const queries = useQueries({
    queries: STRATEGY_KEYS.map((key) => ({
      queryKey: ["backtest", symbol, key],
      queryFn: () => api.backtestStrategy(symbol, key),
      staleTime: 60 * 60_000,
      retry: 1,
    })),
  });

  const loading = queries.some((query) => query.isPending);
  const results = queries
    .map((query) => query.data)
    .filter((data): data is BacktestResult => data !== undefined);

  return (
    <section className="rounded-lg border border-neutral-800 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
          Backtests · last 3 years
        </h2>
        <span className="text-xs text-neutral-600">
          Simulated with 0.2%/side costs, next-open fills, ATR stops. Past
          performance ≠ future results.
        </span>
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="h-28 animate-pulse rounded bg-neutral-900" />
        ) : results.length === 0 ? (
          <p className="text-sm text-neutral-500">
            Backtests unavailable for this symbol (insufficient history).
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-800 text-left uppercase tracking-wide text-neutral-600">
                  <th className="px-3 py-2">Strategy</th>
                  <th className="px-3 py-2">Trades</th>
                  <th className="px-3 py-2">Win rate</th>
                  <th className="px-3 py-2">Return</th>
                  <th className="px-3 py-2">Buy & hold</th>
                  <th className="px-3 py-2">Edge</th>
                  <th className="px-3 py-2">Max DD</th>
                  <th className="px-3 py-2">Sharpe</th>
                  <th className="px-3 py-2">Exposure</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result) => (
                  <Row key={result.strategy.key} result={result} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
