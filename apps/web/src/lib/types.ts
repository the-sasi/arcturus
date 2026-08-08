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

export type MoversSnapshot = {
  gainers: Quote[];
  losers: Quote[];
  universe_size: number;
  quoted: number;
  advancing: number;
  declining: number;
};

export type StrategyMetadata = {
  key: string;
  name: string;
  version: string;
  style: string;
  description: string;
  typical_holding: string;
};

export type StrategyVerdict = {
  strategy: StrategyMetadata;
  symbol: SymbolRef;
  stance: "bullish" | "neutral" | "bearish";
  confidence: number;
  entry_zone: { low: string; high: string } | null;
  stop_loss: string | null;
  reasons: string[];
  as_of: string;
};

export type IndicatorSeries = {
  symbol: SymbolRef;
  interval: string;
  timestamps: string[];
  series: Record<string, (number | null)[]>;
};

export type Instrument = {
  symbol: SymbolRef;
  name: string;
  asset_class: string;
  currency: string;
};

export type InstrumentPage = {
  items: Instrument[];
  total: number;
  limit: number;
  offset: number;
};

export type CompanyProfile = {
  symbol: SymbolRef;
  name: string;
  sector: string | null;
  industry: string | null;
  country: string | null;
  website: string | null;
  employees: number | null;
  summary: string | null;
};

export type Fundamentals = {
  symbol: SymbolRef;
  currency: string | null;
  market_cap: number | null;
  trailing_pe: string | null;
  forward_pe: string | null;
  price_to_book: string | null;
  eps_trailing: string | null;
  dividend_yield: string | null;
  beta: string | null;
  fifty_two_week_high: string | null;
  fifty_two_week_low: string | null;
  average_volume: number | null;
  revenue: number | null;
  profit_margin: string | null;
  return_on_equity: string | null;
  debt_to_equity: string | null;
  as_of: string;
  extras: Record<string, unknown>;
};

export type NewsArticle = {
  title: string;
  publisher: string | null;
  url: string | null;
  published_at: string | null;
  summary: string | null;
  image_url: string | null;
};

export type ArticleContent = {
  url: string;
  title: string | null;
  text: string | null;
  site_name: string | null;
  image_url: string | null;
  published_at: string | null;
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
