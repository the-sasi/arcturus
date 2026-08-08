"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ArticleReader } from "@/components/article-reader";
import { QuoteCard } from "@/components/quote-card";
import { api, ApiError } from "@/lib/api";
import { useWorkspaceStore } from "@/lib/store";
import type { Fundamentals, NewsArticle } from "@/lib/types";

/* eslint-disable @next/next/no-img-element -- publisher thumbnails come from
   arbitrary hosts; next/image would need per-domain config */

function humanize(value: number | null): string {
  if (value === null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  return value.toLocaleString();
}

function num(value: string | null, digits = 2): string {
  return value === null ? "—" : Number(value).toFixed(digits);
}

function pct(value: string | null): string {
  return value === null ? "—" : `${(Number(value) * 100).toFixed(2)}%`;
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="mt-0.5 text-sm font-medium tabular-nums">{value}</div>
    </div>
  );
}

function FundamentalsGrid({ data }: { data: Fundamentals }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      <Metric label="Market Cap" value={humanize(data.market_cap)} />
      <Metric label="P/E (trailing)" value={num(data.trailing_pe)} />
      <Metric label="P/E (forward)" value={num(data.forward_pe)} />
      <Metric label="Price / Book" value={num(data.price_to_book)} />
      <Metric label="EPS (trailing)" value={num(data.eps_trailing)} />
      {/* Yahoo already reports dividendYield in percent units */}
      <Metric
        label="Dividend Yield"
        value={data.dividend_yield === null ? "—" : `${num(data.dividend_yield)}%`}
      />
      <Metric label="Beta" value={num(data.beta)} />
      <Metric label="52w High" value={num(data.fifty_two_week_high)} />
      <Metric label="52w Low" value={num(data.fifty_two_week_low)} />
      <Metric label="Avg Volume" value={humanize(data.average_volume)} />
      <Metric label="Revenue" value={humanize(data.revenue)} />
      <Metric label="Profit Margin" value={pct(data.profit_margin)} />
      <Metric label="ROE" value={pct(data.return_on_equity)} />
      <Metric label="Debt / Equity" value={num(data.debt_to_equity)} />
      <Metric
        label="Analyst View"
        value={String(data.extras["recommendationKey"] ?? "—").replace("_", " ")}
      />
    </div>
  );
}

function Panel({
  title,
  isPending,
  error,
  children,
}: {
  title: string;
  isPending: boolean;
  error: unknown;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-neutral-800 p-5">
      <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">{title}</h2>
      <div className="mt-3">
        {isPending ? (
          <div className="h-20 animate-pulse rounded bg-neutral-900" />
        ) : error ? (
          <p className="text-sm text-red-400">
            {error instanceof ApiError ? error.message : "Failed to load"}
          </p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}

export default function WorkspacePage() {
  const selectedSymbol = useWorkspaceStore((state) => state.selectedSymbol);
  const setSelectedSymbol = useWorkspaceStore((state) => state.setSelectedSymbol);
  const [input, setInput] = useState(selectedSymbol);
  const [openArticle, setOpenArticle] = useState<NewsArticle | null>(null);

  const profile = useQuery({
    queryKey: ["profile", selectedSymbol],
    queryFn: () => api.getProfile(selectedSymbol),
    staleTime: 5 * 60_000,
  });
  const fundamentals = useQuery({
    queryKey: ["fundamentals", selectedSymbol],
    queryFn: () => api.getFundamentals(selectedSymbol),
    staleTime: 5 * 60_000,
  });
  const news = useQuery({
    queryKey: ["news", selectedSymbol],
    queryFn: () => api.getNews(selectedSymbol, 8),
    staleTime: 5 * 60_000,
  });

  return (
    <div className="p-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Stock Workspace</h1>
          <p className="mt-1 text-sm text-neutral-400">
            {profile.data ? profile.data.name : selectedSymbol}
            {profile.data?.sector ? ` · ${profile.data.sector}` : ""}
            {profile.data?.industry ? ` · ${profile.data.industry}` : ""}
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (input.trim()) setSelectedSymbol(input.trim().toUpperCase());
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="EXCHANGE:TICKER"
            className="w-56 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-md bg-neutral-100 px-3 py-1.5 text-sm font-medium text-neutral-900 hover:bg-white"
          >
            Load
          </button>
        </form>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Panel
            title="Fundamentals"
            isPending={fundamentals.isPending}
            error={fundamentals.error}
          >
            {fundamentals.data && <FundamentalsGrid data={fundamentals.data} />}
          </Panel>

          <Panel title="About" isPending={profile.isPending} error={profile.error}>
            {profile.data && (
              <div className="space-y-2 text-sm text-neutral-300">
                {profile.data.summary ? (
                  <p className="leading-relaxed">{profile.data.summary}</p>
                ) : (
                  <p className="text-neutral-500">No description available.</p>
                )}
                <div className="flex flex-wrap gap-x-6 gap-y-1 pt-2 text-neutral-400">
                  {profile.data.country && <span>Country: {profile.data.country}</span>}
                  {profile.data.employees !== null && (
                    <span>Employees: {profile.data.employees.toLocaleString()}</span>
                  )}
                  {profile.data.website && (
                    <a
                      href={profile.data.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-neutral-300 underline hover:text-white"
                    >
                      Website
                    </a>
                  )}
                </div>
              </div>
            )}
          </Panel>
        </div>

        <div className="space-y-6">
          <QuoteCard symbol={selectedSymbol} />
          <Panel title="News" isPending={news.isPending} error={news.error}>
            {news.data && news.data.length === 0 ? (
              <p className="text-sm text-neutral-500">No recent news.</p>
            ) : (
              <ul className="space-y-3">
                {news.data?.map((article, index) => (
                  <li key={index}>
                    <button
                      onClick={() => setOpenArticle(article)}
                      className="flex w-full gap-3 rounded-md p-1.5 text-left hover:bg-neutral-900"
                    >
                      {article.image_url && (
                        <img
                          src={article.image_url}
                          alt=""
                          className="h-14 w-20 shrink-0 rounded object-cover"
                          loading="lazy"
                        />
                      )}
                      <span className="min-w-0">
                        <span className="block text-sm text-neutral-200">{article.title}</span>
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
          </Panel>
        </div>
      </div>

      {openArticle && (
        <ArticleReader article={openArticle} onClose={() => setOpenArticle(null)} />
      )}
    </div>
  );
}
