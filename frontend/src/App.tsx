export function App() {
  return (
    <div className="min-h-[100dvh] bg-zinc-950 text-zinc-50 flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-lg tracking-tight">OCEANEMBED</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-teal-950 text-teal-300 border border-teal-800">
            Subsurface Ocean Explorer
          </span>
        </div>
      </header>
      <main className="flex-1 p-6">
        <p className="text-zinc-400">Loading oceanographic intelligence...</p>
      </main>
      <footer className="border-t border-zinc-800 px-6 py-3 text-xs text-zinc-500 text-center">
        Modeled reconstruction; trained on data through 2023-12-31.
      </footer>
    </div>
  );
}

export default App;
