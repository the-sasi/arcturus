// API contract types — mirror services/api domain models.

export type SymbolRef = {
  exchange: string;
  ticker: string;
};

export type Quote = {
  symbol: SymbolRef;
  price: string;
  previous_close: string | null;
  change: string | null;
  change_percent: string | null;
  volume: number | null;
  currency: string | null;
  as_of: string;
};

export type Candle = {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
};

export type CandleSeries = {
  symbol: SymbolRef;
  interval: string;
  candles: Candle[];
};

export type WatchlistItem = {
  symbol: SymbolRef;
  added_at: string;
};

export type Watchlist = {
  id: string;
  name: string;
  created_at: string;
  items: WatchlistItem[];
};

export function formatSymbol(symbol: SymbolRef): string {
  return `${symbol.exchange}:${symbol.ticker}`;
}
