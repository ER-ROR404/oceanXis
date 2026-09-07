import { Waves } from 'lucide-react';

/** Top app bar: wordmark, product label, region context. */
export function Header() {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950 px-4 py-3 sm:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Waves className="h-5 w-5 text-teal-400" aria-hidden="true" />
        <span className="font-semibold text-base tracking-tight text-zinc-50">OCEANEMBED</span>
        <span className="hidden sm:inline-flex items-center rounded-full border border-zinc-700 bg-zinc-900 px-2.5 py-0.5 text-xs font-medium text-zinc-300">
          Subsurface Ocean Explorer
        </span>
      </div>
      <p className="text-xs text-zinc-500 font-mono-data">North Indian Ocean · 0.25°</p>
    </header>
  );
}