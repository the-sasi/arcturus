import type { CandleSeries, Quote } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8600";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = ((await response.json()) as { detail?: string }).detail ?? detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  getQuote: (symbol: string) =>
    request<Quote>(`/api/v1/market/quote/${encodeURIComponent(symbol)}`),
  getCandles: (symbol: string, interval = "1d") =>
    request<CandleSeries>(
      `/api/v1/market/candles/${encodeURIComponent(symbol)}?interval=${interval}`,
    ),
};
