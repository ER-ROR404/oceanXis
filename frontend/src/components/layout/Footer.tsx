
const HONEST_LINE = 'Modeled reconstruction; trained on data through 2023-12-31.';

/** Static honest footer on every screen (design spec §10). */
export function Footer() {
  return (
    <footer data-testid="footer" className="border-t border-zinc-800 bg-zinc-950 px-6 py-3 text-center text-xs text-zinc-500">
      <p>{HONEST_LINE}</p>
    </footer>
  );
}