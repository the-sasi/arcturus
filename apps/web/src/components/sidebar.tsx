"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Product modules from the blueprint. Modules ship incrementally; unshipped
// ones render as disabled so the information architecture is visible from day one.
const MODULES: { label: string; href: string; ready: boolean }[] = [
  { label: "Dashboard", href: "/", ready: true },
  { label: "AI Copilot", href: "/copilot", ready: false },
  { label: "Market Intelligence", href: "/market", ready: false },
  { label: "News Intelligence", href: "/news", ready: false },
  { label: "Decision Center", href: "/decisions", ready: false },
  { label: "Stock Workspace", href: "/workspace", ready: false },
  { label: "Watchlists", href: "/watchlists", ready: false },
  { label: "Research Lab", href: "/research", ready: false },
  { label: "Strategy Studio", href: "/strategies", ready: false },
  { label: "Automation Center", href: "/automation", ready: false },
  { label: "Portfolio Intelligence", href: "/portfolio", ready: false },
  { label: "Trade Journal", href: "/journal", ready: false },
  { label: "Psychology Lab", href: "/psychology", ready: false },
  { label: "Knowledge Hub", href: "/knowledge", ready: false },
  { label: "Analytics", href: "/analytics", ready: false },
  { label: "Settings", href: "/settings", ready: false },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-neutral-800 bg-neutral-950">
      <div className="px-5 py-5">
        <div className="text-lg font-semibold tracking-tight text-neutral-100">Arcturus</div>
        <div className="text-xs text-neutral-500">AI Trading OS</div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {MODULES.map((module) =>
          module.ready ? (
            <Link
              key={module.href}
              href={module.href}
              className={`block rounded-md px-3 py-1.5 text-sm transition-colors ${
                pathname === module.href
                  ? "bg-neutral-800 text-neutral-100"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
              }`}
            >
              {module.label}
            </Link>
          ) : (
            <span
              key={module.href}
              title="Coming soon"
              className="block cursor-not-allowed rounded-md px-3 py-1.5 text-sm text-neutral-700"
            >
              {module.label}
            </span>
          ),
        )}
      </nav>
    </aside>
  );
}
