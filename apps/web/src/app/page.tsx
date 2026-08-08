"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArticleReader } from "@/components/article-reader";
import { QuoteCard } from "@/components/quote-card";
import { api } from "@/lib/api";
import { useWorkspaceStore } from "@/lib/store";
import { formatSymbol, type NewsArticle, type Quote } from "@/lib/types";

/* eslint-disable @next/next/no-img-element -- publisher thumbnails from arbitrary hosts */

const INDICES = [
  { symbol: "INDEX:^NSEI", label: "NIFTY 50" },
  { symbol: "INDEX:^BSESN", label: "SENSEX" },
  { symbol: "INDEX:^GSPC", label: "S&P 500" },
  { symbol: "INDEX:^IXIC", label: "NASDAQ" },
];

const FALLBACK_PULSE = [
  "NSE:RELIANCE",
  "NSE:TCS",
  "NSE:HDFCBANK",
  "NSE:INFY",
  "NASDAQ:AAPL",
  "NASDAQ:MSFT",
];

function IndexCard({ symbol, label }: { symbol: string; label: string }) {
  const { data, isPending } = useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.getQuote(symbol),
    refetchInterval: 60_000,
  });
  const change = data?.change_percent !== null ? Number(data?.change_percent) : null;
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-3">
      <div className="text-xs font-medium text-neutral-500">{label}</div>
      {isPending || !data ? (
        <div className="mt-1.5 h-5 w-20 animate-pulse rounded bg-neutral-800" />
      ) : (
        <div className="mt-0.5 flex items-baseline gap-2">
          <span className="text-lg font-semibold tabular-nums">
            {Number(data.price).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
          {change !== null && (
            <span
              className={`text-xs tabular-nums ${change >= 0 ? "text-emerald-400" : "text-red-400"}`}
            >
              {change >= 0 ? "▲" : "▼"} {Math.abs(change).toFixed(2)}%
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function MoverRow({ quote, onOpen }: { quote: Quote; onOpen: (symbol: string) => void }) {
  const change = Number(quote.change_percent ?? 0);
  const symbol = formatSymbol(quote.symbol);
  return (
    <button
      onClick={() => onOpen(symbol)}
      className="flex w-full items-center justify-between rounded px-2 py-1.5 text-sm hover:bg-neutral-900"
    >
      <span className="font-medium text-neutral-200">{quote.symbol.ticker}</span>
      <span className="flex items-baseline gap-3 tabular-nums">
        <span className="text-neutral-400">
          {quote.currency === "INR" ? "₹" : quote.currency === "USD" ? "$" : ""}
          {Number(quote.price).toLocaleString(undefined, { maximumFractionDigits: 2 })}
        </span>
        <span className={change >= 0 ? "text-emerald-400" : "text-red-400"}>
          {change >= 0 ? "+" : ""}
          {change.toFixed(2)}%
        </span>
      </span>
    </button>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const setSelectedSymbol = useWorkspaceStore((state) => state.setSelectedSymbol);
  const [openArticle, setOpenArticle] = useState<NewsArticle | null>(null);

  const openInWorkspace = (symbol: string) => {
    setSelectedSymbol(symbol);
    router.push("/workspace");
  };

  const watchlists = useQuery({ queryKey: ["watchlists"], queryFn: api.listWatchlists });
  const movers = useQuery({
    queryKey: ["movers"],
    queryFn: api.getMovers,
    refetchInterval: 120_000,
  });
  const news = useQuery({
    queryKey: ["dashboard-news"],
    queryFn: async () => {
      const [india, us] = await Promise.allSettled([
        api.getNews("INDEX:^NSEI", 6),
        api.getNews("INDEX:^GSPC", 6),
      ]);
      const merged = [
        ...(india.status === "fulfilled" ? india.value : []),
        ...(us.status === "fulfilled" ? us.value : []),
      ];
      return merged
        .sort((a, b) =>
          (b.published_at ?? "").localeCompare(a.published_at ?? ""),
        )
        .slice(0, 8);
    },
    staleTime: 5 * 60_000,
  });

  const firstListWithItems = watchlists.data?.find((list) => list.items.length > 0);
  const pulseSymbols = firstListWithItems
    ? firstListWithItems.items.map((item) => formatSymbol(item.symbol)).slice(0, 6)
    : FALLBACK_PULSE;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      <p className="mt-1 text-sm text-neutral-400">Your morning briefing.</p>

      <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {INDICES.map((index) => (
          <IndexCard key={index.symbol} symbol={index.symbol} label={index.label} />
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section>
            <div className="flex items-baseline justify-between">
              <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
                {firstListWithItems ? `Watchlist · ${firstListWithItems.name}` : "Market Pulse"}
              </h2>
              <Link href="/watchlists" className="text-xs text-neutral-500 hover:text-neutral-300">
                {firstListWithItems ? "Manage watchlists →" : "Create a watchlist →"}
              </Link>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pulseSymbols.map((symbol) => (
                <button key={symbol} onClick={() => openInWorkspace(symbol)} className="text-left">
                  <QuoteCard symbol={symbol} />
                </button>
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-neutral-800 p-4">
              <h3 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
                Top Gainers
              </h3>
              <div className="mt-2 space-y-0.5">
                {movers.isPending ? (
                  <div className="h-32 animate-pulse rounded bg-neutral-900" />
                ) : movers.isError || !movers.data ? (
                  <p className="text-sm text-neutral-500">Unavailable right now.</p>
                ) : movers.data.gainers.length === 0 ? (
                  <p className="text-sm text-neutral-500">No gainers in the tracked set.</p>
                ) : (
                  movers.data.gainers.map((quote) => (
                    <MoverRow
                      key={formatSymbol(quote.symbol)}
                      quote={quote}
                      onOpen={openInWorkspace}
                    />
                  ))
                )}
              </div>
            </div>
            <div className="rounded-lg border border-neutral-800 p-4">
              <h3 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
                Top Losers
              </h3>
              <div className="mt-2 space-y-0.5">
                {movers.isPending ? (
                  <div className="h-32 animate-pulse rounded bg-neutral-900" />
                ) : movers.isError || !movers.data ? (
                  <p className="text-sm text-neutral-500">Unavailable right now.</p>
                ) : movers.data.losers.length === 0 ? (
                  <p className="text-sm text-neutral-500">No losers in the tracked set.</p>
                ) : (
                  movers.data.losers.map((quote) => (
                    <MoverRow
                      key={formatSymbol(quote.symbol)}
                      quote={quote}
                      onOpen={openInWorkspace}
                    />
                  ))
                )}
              </div>
            </div>
          </section>
          {movers.data && (
            <p className="text-xs text-neutral-600">
              Movers tracked across {movers.data.universe_size} major stocks (NIFTY-50 + US
              majors) — full-market movers arrive with Phase 2.
            </p>
          )}
        </div>

        <section className="rounded-lg border border-neutral-800 p-5">
          <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
            Market Headlines
          </h2>
          <div className="mt-3">
            {news.isPending ? (
              <div className="h-64 animate-pulse rounded bg-neutral-900" />
            ) : !news.data || news.data.length === 0 ? (
              <p className="text-sm text-neutral-500">No headlines right now.</p>
            ) : (
              <ul className="space-y-3">
                {news.data.map((article, position) => (
                  <li key={position}>
                    <button
                      onClick={() => setOpenArticle(article)}
                      className="flex w-full gap-3 rounded-md p-1.5 text-left hover:bg-neutral-900"
                    >
                      {article.image_url && (
                        <img
                          src={article.image_url}
                          alt=""
                          className="h-12 w-16 shrink-0 rounded object-cover"
                          loading="lazy"
                        />
                      )}
                      <span className="min-w-0">
                        <span className="block text-sm leading-snug text-neutral-200">
                          {article.title}
                        </span>
                        <span className="mt-0.5 block text-xs text-neutral-500">
                          {article.publisher ?? "Unknown"}
                          {article.published_at
                            ? ` · ${new Date(article.published_at).toLocaleDateString()}`
                            : ""}
                        </span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>

      {openArticle && (
        <ArticleReader article={openArticle} onClose={() => setOpenArticle(null)} />
      )}
    </div>
  );
}
