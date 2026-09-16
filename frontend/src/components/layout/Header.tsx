import { Waves } from 'lucide-react';

export type ExplorerRoute = 'explorer' | 'validation';

interface HeaderProps {
  route?: ExplorerRoute;
  onNavigate?: (route: ExplorerRoute) => void;
}

/** Top product bar: wordmark, minimal scientific nav, region context. */
export function Header({ route = 'explorer', onNavigate = () => {} }: HeaderProps) {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950 px-4 py-3 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Waves className="h-5 w-5 text-teal-400" aria-hidden="true" />
          <span className="text-base font-semibold tracking-tight text-zinc-50">OCEANEMBED</span>
          <span className="hidden items-center rounded-full border border-zinc-700 bg-zinc-900 px-2.5 py-0.5 text-xs font-medium text-zinc-300 sm:inline-flex">
            Subsurface Ocean Explorer
          </span>
          <span className="hidden items-center rounded-md border border-amber-800/60 bg-amber-950/30 px-2.5 py-0.5 text-xs font-medium text-amber-300 sm:inline-flex">
            Research prototype · Historical reconstruction
          </span>
          <nav aria-label="Primary" className="ml-2 flex items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/60 p-0.5">
            <button
              type="button"
              onClick={() => onNavigate('explorer')}
              aria-current={route === 'explorer' ? 'page' : undefined}
              className={route === 'explorer' ? 'rounded bg-teal-400 px-3 py-1 text-xs font-medium text-zinc-950' : 'rounded px-3 py-1 text-xs text-zinc-400 hover:text-zinc-100'}
            >
              Ocean Explorer
            </button>
            <button
              type="button"
              onClick={() => onNavigate('validation')}
              aria-current={route === 'validation' ? 'page' : undefined}
              className={route === 'validation' ? 'rounded bg-teal-400 px-3 py-1 text-xs font-medium text-zinc-950' : 'rounded px-3 py-1 text-xs text-zinc-400 hover:text-zinc-100'}
            >
              Validation &amp; Model
            </button>
          </nav>
        </div>
        <p className="font-mono-data text-xs text-zinc-500">Bay of Bengal · 0.25°</p>
      </div>
      <p data-testid="hero-tagline" className="mt-1.5 text-xs text-zinc-400">
        Satellite-derived Surface Observations → Subsurface Temperature Reconstruction
      </p>
    </header>
  );
}
