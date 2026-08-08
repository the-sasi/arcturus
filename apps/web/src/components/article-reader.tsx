"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api, ApiError } from "@/lib/api";
import type { NewsArticle } from "@/lib/types";

/* eslint-disable @next/next/no-img-element -- remote news images from arbitrary
   hosts; next/image would require whitelisting every publisher domain */

export function ArticleReader({
  article,
  onClose,
}: {
  article: NewsArticle;
  onClose: () => void;
}) {
  const reader = useQuery({
    queryKey: ["article", article.url],
    queryFn: () => api.readArticle(article.url as string),
    enabled: article.url !== null,
    staleTime: 24 * 60 * 60_000,
    retry: false,
  });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const heroImage = reader.data?.image_url ?? article.image_url;
  const paragraphs =
    reader.data?.text?.split(/\n+/).filter((line) => line.trim().length > 0) ?? null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 sm:p-10"
      onClick={onClose}
    >
      <article
        className="w-full max-w-2xl rounded-xl border border-neutral-800 bg-neutral-950 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        {heroImage && (
          <img
            src={heroImage}
            alt=""
            className="h-56 w-full rounded-t-xl object-cover"
          />
        )}
        <div className="p-6">
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-xl font-semibold leading-snug">
              {reader.data?.title ?? article.title}
            </h2>
            <button
              onClick={onClose}
              className="rounded px-2 py-0.5 text-neutral-500 hover:bg-neutral-800 hover:text-neutral-200"
              title="Close (Esc)"
            >
              ✕
            </button>
          </div>
          <div className="mt-1 text-xs text-neutral-500">
            {reader.data?.site_name ?? article.publisher ?? "Unknown source"}
            {article.published_at
              ? ` · ${new Date(article.published_at).toLocaleString()}`
              : ""}
          </div>

          <div className="mt-4 space-y-3 text-sm leading-relaxed text-neutral-300">
            {article.url === null ? (
              <p className="text-neutral-500">No article link available.</p>
            ) : reader.isPending ? (
              <>
                <div className="h-4 w-full animate-pulse rounded bg-neutral-800" />
                <div className="h-4 w-11/12 animate-pulse rounded bg-neutral-800" />
                <div className="h-4 w-4/5 animate-pulse rounded bg-neutral-800" />
              </>
            ) : reader.isError || !paragraphs || paragraphs.length === 0 ? (
              <>
                {article.summary ? (
                  <p>{article.summary}</p>
                ) : (
                  <p className="text-neutral-500">
                    {reader.error instanceof ApiError
                      ? `Couldn't extract this article (${reader.error.message}).`
                      : "Couldn't extract this article."}
                  </p>
                )}
              </>
            ) : (
              paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)
            )}
          </div>

          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-5 inline-block text-sm text-neutral-400 underline hover:text-white"
            >
              Open original ↗
            </a>
          )}
        </div>
      </article>
    </div>
  );
}
