"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

function formatPrice(value: string, currency: string | null): string {
  const number = Number(value);
  const formatted = number.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const prefix = currency === "INR" ? "₹" : currency === "USD" ? "$" : "";
  return `${prefix}${formatted}`;
}

export function QuoteCard({ symbol }: { symbol: string }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.getQuote(symbol),
    refetchInterval: 60_000,
  });

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
      <div className="text-sm font-medium text-neutral-400">{symbol}</div>
      {isPending ? (
        <div className="mt-2 h-7 w-24 animate-pulse rounded bg-neutral-800" />
      ) : isError ? (
        <div className="mt-2 text-sm text-red-400">{error.message}</div>
      ) : (
        <>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {formatPrice(data.price, data.currency)}
          </div>
          {data.change !== null && data.change_percent !== null && (
            <div
              className={`mt-0.5 text-sm tabular-nums ${
                Number(data.change) >= 0 ? "text-emerald-400" : "text-red-400"
              }`}
            >
              {Number(data.change) >= 0 ? "+" : ""}
              {Number(data.change).toFixed(2)} ({data.change_percent}%)
            </div>
          )}
        </>
      )}
    </div>
  );
}
