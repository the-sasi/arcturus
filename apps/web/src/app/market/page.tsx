"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useWorkspaceStore } from "@/lib/store";
import { formatSymbol } from "@/lib/types";

const EXCHANGES = [
  { value: "", label: "All markets" },
  { value: "NSE", label: "India · NSE" },
  { value: "NASDAQ", label: "US · NASDAQ" },
  { value: "NYSE", label: "US · NYSE" },
  { value: "AMEX", label: "US · AMEX" },
];

const PAGE_SIZE = 25;

export default function MarketPage() {
  const router = useRouter();
  const setSelectedSymbol = useWorkspaceStore((state) => state.setSelectedSymbol);

  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [exchange, setExchange] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(query);
      setPage(0);
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["instruments", debounced, exchange, page],
    queryFn: () =>
      api.searchInstruments({
        query: debounced || undefined,
        exchange: exchange || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    staleTime: 60_000,
  });

  const open = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push("/workspace");
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Market Intelligence</h1>
      <p className="mt-1 max-w-2xl text-sm text-neutral-400">
        Every stock listed on the exchanges we track — search by company name or
        symbol, then click any row to research it in the Stock Workspace.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by company name or symbol… (e.g. tata, apple, INFY)"
          className="w-96 max-w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
        />
        <div className="flex gap-1">
          {EXCHANGES.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                setExchange(option.value);
                setPage(0);
              }}
              className={`rounded-md px-3 py-1.5 text-sm ${
                exchange === option.value
                  ? "bg-neutral-100 font-medium text-neutral-900"
                  : "border border-neutral-800 text-neutral-400 hover:bg-neutral-900"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5">
        {isPending ? (
          <div className="h-64 animate-pulse rounded-lg bg-neutral-900" />
        ) : isError ? (
          <p className="text-sm text-red-400">
            {error instanceof ApiError ? error.message : "Failed to load instruments"}
          </p>
        ) : data.total === 0 ? (
          <p className="text-sm text-neutral-500">
            No stocks found{debounced ? ` for "${debounced}"` : ""}. If the directory is
            empty, run a sync from Settings or ask the copilot to refresh listings.
          </p>
        ) : (
          <>
            <div className="text-xs text-neutral-500">
              {data.total.toLocaleString()} instruments
              {exchange ? ` on ${exchange}` : " across all tracked exchanges"}
            </div>
            <div className="mt-2 overflow-x-auto rounded-lg border border-neutral-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-800 text-left text-xs uppercase tracking-wide text-neutral-500">
                    <th className="px-4 py-2.5">Symbol</th>
                    <th className="px-4 py-2.5">Company</th>
                    <th className="px-4 py-2.5">Exchange</th>
                    <th className="px-4 py-2.5">Type</th>
                    <th className="px-4 py-2.5">Currency</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((instrument) => {
                    const symbol = formatSymbol(instrument.symbol);
                    return (
                      <tr
                        key={symbol}
                        onClick={() => open(symbol)}
                        className="cursor-pointer border-b border-neutral-900 last:border-0 hover:bg-neutral-900"
                      >
                        <td className="px-4 py-2 font-medium text-neutral-200">
                          {instrument.symbol.ticker}
                        </td>
                        <td className="px-4 py-2 text-neutral-300">{instrument.name}</td>
                        <td className="px-4 py-2 text-neutral-500">
                          {instrument.symbol.exchange}
                        </td>
                        <td className="px-4 py-2 text-neutral-500">{instrument.asset_class}</td>
                        <td className="px-4 py-2 text-neutral-500">{instrument.currency}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex items-center gap-3 text-sm">
              <button
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                disabled={page === 0}
                className="rounded-md border border-neutral-800 px-3 py-1 text-neutral-300 hover:bg-neutral-900 disabled:opacity-40"
              >
                ← Prev
              </button>
              <span className="text-neutral-500">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-neutral-800 px-3 py-1 text-neutral-300 hover:bg-neutral-900 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
