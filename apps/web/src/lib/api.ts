import type {
  CandleSeries,
  CompanyProfile,
  Fundamentals,
  NewsArticle,
  Quote,
  Watchlist,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8600";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

const jsonPost = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  getQuote: (symbol: string) =>
    request<Quote>(`/api/v1/market/quote/${encodeURIComponent(symbol)}`),
  getCandles: (symbol: string, interval = "1d") =>
    request<CandleSeries>(
      `/api/v1/market/candles/${encodeURIComponent(symbol)}?interval=${interval}`,
    ),

  getProfile: (symbol: string) =>
    request<CompanyProfile>(`/api/v1/market/profile/${encodeURIComponent(symbol)}`),
  getFundamentals: (symbol: string) =>
    request<Fundamentals>(`/api/v1/market/fundamentals/${encodeURIComponent(symbol)}`),
  getNews: (symbol: string, limit = 10) =>
    request<NewsArticle[]>(
      `/api/v1/market/news/${encodeURIComponent(symbol)}?limit=${limit}`,
    ),

  listWatchlists: () => request<Watchlist[]>("/api/v1/watchlists"),
  createWatchlist: (name: string) =>
    request<Watchlist>("/api/v1/watchlists", jsonPost({ name })),
  deleteWatchlist: (id: string) =>
    request<void>(`/api/v1/watchlists/${id}`, { method: "DELETE" }),
  addWatchlistItem: (id: string, symbol: string) =>
    request<Watchlist>(`/api/v1/watchlists/${id}/items`, jsonPost({ symbol })),
  removeWatchlistItem: (id: string, symbol: string) =>
    request<Watchlist>(
      `/api/v1/watchlists/${id}/items/${encodeURIComponent(symbol)}`,
      { method: "DELETE" },
    ),
};
