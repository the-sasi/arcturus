"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { StrategyVerdict } from "@/lib/types";

const STANCE_STYLE = {
  bullish: { label: "▲ Bullish", classes: "bg-emerald-500/15 text-emerald-400" },
  neutral: { label: "— Neutral", classes: "bg-neutral-500/15 text-neutral-400" },
  bearish: { label: "▼ Bearish", classes: "bg-red-500/15 text-red-400" },
} as const;

const REGIME_STYLE = {
  risk_on: { label: "Market: Risk-on ☀️", classes: "bg-emerald-500/15 text-emerald-400" },
  mixed: { label: "Market: Mixed ⛅", classes: "bg-amber-500/15 text-amber-400" },
  risk_off: { label: "Market: Risk-off ⛈️", classes: "bg-red-500/15 text-red-400" },
} as const;

function RegimeBadge({ symbol }: { symbol: string }) {
  const exchange = symbol.includes(":") ? symbol.split(":")[0] : "NSE";
  const { data } = useQuery({
    queryKey: ["regime", exchange],
    queryFn: () => api.getRegime(exchange),
    staleTime: 30 * 60_000,
    retry: 1,
  });
  if (!data) return null;
  const style = REGIME_STYLE[data.state];
  return (
    <span
      title={data.description}
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${style.classes}`}
    >
      {style.label}
    </span>
  );
}

function VerdictCard({ verdict }: { verdict: StrategyVerdict }) {
  const stance = STANCE_STYLE[verdict.stance];
  return (
    <div className="rounded-lg border border-neutral-800 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="text-sm font-medium text-neutral-200">{verdict.strategy.name}</span>
          <span className="ml-2 text-xs text-neutral-600">
            {verdict.strategy.style} · holds {verdict.strategy.typical_holding} · v
            {verdict.strategy.version}
          </span>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${stance.classes}`}>
          {stance.label}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-neutral-500">Confidence</span>
        <div className="h-1.5 w-40 overflow-hidden rounded bg-neutral-800">
          <div
            className={`h-full ${
              verdict.stance === "bullish"
                ? "bg-emerald-400"
                : verdict.stance === "bearish"
                  ? "bg-red-400"
                  : "bg-neutral-500"
            }`}
            style={{ width: `${verdict.confidence}%` }}
          />
        </div>
        <span className="text-xs tabular-nums text-neutral-400">{verdict.confidence}/100</span>
      </div>

      {(verdict.entry_zone || verdict.stop_loss) && (
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-neutral-400">
          {verdict.entry_zone && (
            <span>
              Entry zone:{" "}
              <span className="tabular-nums text-neutral-200">
                {Number(verdict.entry_zone.low).toFixed(2)} –{" "}
                {Number(verdict.entry_zone.high).toFixed(2)}
              </span>
            </span>
          )}
          {verdict.stop_loss && (
            <span>
              Stop-loss:{" "}
              <span className="tabular-nums text-neutral-200">
                {Number(verdict.stop_loss).toFixed(2)}
              </span>
            </span>
          )}
        </div>
      )}

      <ul className="mt-3 space-y-1">
        {verdict.reasons.map((reason, index) => (
          <li key={index} className="flex gap-2 text-xs leading-relaxed text-neutral-400">
            <span className="text-neutral-600">•</span>
            {reason}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function StrategyPanel({ symbol }: { symbol: string }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["strategies", symbol],
    queryFn: () => api.evaluateStrategies(symbol),
    staleTime: 5 * 60_000,
  });

  return (
    <section className="rounded-lg border border-neutral-800 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
            Strategy Analysis
          </h2>
          <RegimeBadge symbol={symbol} />
        </div>
        <span className="text-xs text-neutral-600">
          Rule-based signals with reasons — decision support, not financial advice.
        </span>
      </div>
      <div className="mt-3 space-y-3">
        {isPending ? (
          <div className="h-40 animate-pulse rounded bg-neutral-900" />
        ) : isError ? (
          <p className="text-sm text-red-400">
            {error instanceof ApiError ? error.message : "Strategy evaluation failed."}
          </p>
        ) : !data || data.length === 0 ? (
          <p className="text-sm text-neutral-500">
            Not enough price history to evaluate strategies for this symbol.
          </p>
        ) : (
          data.map((verdict) => <VerdictCard key={verdict.strategy.key} verdict={verdict} />)
        )}
      </div>
    </section>
  );
}
