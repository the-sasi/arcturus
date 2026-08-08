"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { formatSymbol } from "@/lib/types";

export function SymbolSearch({
  onSelect,
  placeholder = "Search company or symbol…",
}: {
  onSelect: (symbol: string) => void;
  placeholder?: string;
}) {
  const [text, setText] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(text), 200);
    return () => clearTimeout(timer);
  }, [text]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const suggestions = useQuery({
    queryKey: ["symbol-search", debounced],
    queryFn: () => api.searchInstruments({ query: debounced, limit: 8 }),
    enabled: debounced.trim().length >= 2,
    staleTime: 60_000,
  });

  const pick = (symbol: string) => {
    onSelect(symbol);
    setText("");
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="relative">
      <input
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const first = suggestions.data?.items[0];
            if (first) pick(formatSymbol(first.symbol));
            else if (text.includes(":")) pick(text.trim().toUpperCase());
          }
          if (event.key === "Escape") setOpen(false);
        }}
        placeholder={placeholder}
        className="w-72 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
      />
      {open && debounced.trim().length >= 2 && (
        <div className="absolute right-0 top-full z-40 mt-1 w-96 overflow-hidden rounded-md border border-neutral-700 bg-neutral-950 shadow-xl">
          {suggestions.isPending ? (
            <div className="px-3 py-2 text-sm text-neutral-500">Searching…</div>
          ) : !suggestions.data || suggestions.data.items.length === 0 ? (
            <div className="px-3 py-2 text-sm text-neutral-500">
              No matches. Try a company name (e.g. “tata”) or EXCHANGE:TICKER.
            </div>
          ) : (
            suggestions.data.items.map((instrument) => {
              const symbol = formatSymbol(instrument.symbol);
              return (
                <button
                  key={symbol}
                  onClick={() => pick(symbol)}
                  className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left hover:bg-neutral-900"
                >
                  <span className="truncate text-sm text-neutral-200">{instrument.name}</span>
                  <span className="shrink-0 text-xs text-neutral-500">{symbol}</span>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
