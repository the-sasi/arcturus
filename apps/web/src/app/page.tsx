import { QuoteCard } from "@/components/quote-card";

const MARKET_PULSE_SYMBOLS = [
  "NSE:RELIANCE",
  "NSE:TCS",
  "NSE:HDFCBANK",
  "NSE:INFY",
  "NASDAQ:AAPL",
  "NASDAQ:MSFT",
];

export default function DashboardPage() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
      <p className="mt-1 text-sm text-neutral-400">
        Live market pulse via the provider adapter layer.
      </p>
      <section className="mt-6">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-500">
          Market Pulse
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {MARKET_PULSE_SYMBOLS.map((symbol) => (
            <QuoteCard key={symbol} symbol={symbol} />
          ))}
        </div>
      </section>
    </div>
  );
}
