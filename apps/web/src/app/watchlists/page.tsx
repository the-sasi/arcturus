"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { QuoteCard } from "@/components/quote-card";
import { api, ApiError } from "@/lib/api";
import { formatSymbol, type Watchlist } from "@/lib/types";

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong";
}

function CreateWatchlistForm() {
  const [name, setName] = useState("");
  const queryClient = useQueryClient();
  const create = useMutation({
    mutationFn: api.createWatchlist,
    onSuccess: () => {
      setName("");
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
    },
  });

  return (
    <form
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (name.trim()) create.mutate(name.trim());
      }}
    >
      <input
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="New watchlist name"
        className="w-48 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={create.isPending || !name.trim()}
        className="rounded-md bg-neutral-100 px-3 py-1.5 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-40"
      >
        Create
      </button>
      {create.isError && (
        <span className="self-center text-sm text-red-400">{errorMessage(create.error)}</span>
      )}
    </form>
  );
}

function WatchlistPanel({ watchlist }: { watchlist: Watchlist }) {
  const [symbol, setSymbol] = useState("");
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["watchlists"] });

  const addItem = useMutation({
    mutationFn: (value: string) => api.addWatchlistItem(watchlist.id, value),
    onSuccess: () => {
      setSymbol("");
      invalidate();
    },
  });
  const removeItem = useMutation({
    mutationFn: (value: string) => api.removeWatchlistItem(watchlist.id, value),
    onSuccess: invalidate,
  });
  const removeList = useMutation({
    mutationFn: () => api.deleteWatchlist(watchlist.id),
    onSuccess: invalidate,
  });

  return (
    <section className="rounded-lg border border-neutral-800 p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">{watchlist.name}</h2>
        <button
          onClick={() => removeList.mutate()}
          className="text-sm text-neutral-500 hover:text-red-400"
        >
          Delete list
        </button>
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (symbol.trim()) addItem.mutate(symbol.trim().toUpperCase());
        }}
      >
        <input
          value={symbol}
          onChange={(event) => setSymbol(event.target.value)}
          placeholder="Add symbol, e.g. NSE:RELIANCE"
          className="w-64 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-sm placeholder:text-neutral-600 focus:border-neutral-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={addItem.isPending || !symbol.trim()}
          className="rounded-md border border-neutral-700 px-3 py-1.5 text-sm hover:bg-neutral-900 disabled:opacity-40"
        >
          Add
        </button>
        {addItem.isError && (
          <span className="self-center text-sm text-red-400">{errorMessage(addItem.error)}</span>
        )}
      </form>

      {watchlist.items.length === 0 ? (
        <p className="mt-4 text-sm text-neutral-500">No symbols yet.</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {watchlist.items.map((item) => {
            const value = formatSymbol(item.symbol);
            return (
              <div key={value} className="relative">
                <QuoteCard symbol={value} />
                <button
                  onClick={() => removeItem.mutate(value)}
                  title="Remove"
                  className="absolute right-2 top-2 rounded px-1.5 text-neutral-600 hover:bg-neutral-800 hover:text-red-400"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function WatchlistsPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["watchlists"],
    queryFn: api.listWatchlists,
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Watchlists</h1>
          <p className="mt-1 text-sm text-neutral-400">
            Persisted in TimescaleDB via the watchlist repository.
          </p>
        </div>
        <CreateWatchlistForm />
      </div>

      <div className="mt-6 space-y-6">
        {isPending ? (
          <div className="h-32 animate-pulse rounded-lg bg-neutral-900" />
        ) : isError ? (
          <p className="text-sm text-red-400">{errorMessage(error)}</p>
        ) : data.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No watchlists yet — create one to get started.
          </p>
        ) : (
          data.map((watchlist) => <WatchlistPanel key={watchlist.id} watchlist={watchlist} />)
        )}
      </div>
    </div>
  );
}
