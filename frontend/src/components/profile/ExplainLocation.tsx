import type { ExplainerInput } from '../../utils/explain';
import { buildExplanation } from '../../utils/explain';

interface ExplainLocationProps {
  input: ExplainerInput;
}

/** Deterministic "Explain this location" summary. No LLM involved. */
export function ExplainLocation({ input }: ExplainLocationProps) {
  const { sentences } = buildExplanation(input);
  return (
    <section
      data-testid="explain-location"
      aria-label="Explain this location"
      className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2"
    >
      <h3 className="mb-1 text-xs font-semibold text-zinc-300">Explain this location</h3>
      <ul className="space-y-1 text-xs leading-snug text-zinc-400">
        {sentences.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
      <p className="mt-1.5 border-t border-zinc-800 pt-1.5 text-[11px] text-zinc-500">
        Reconstruction from a statistical model, not an observation.
      </p>
    </section>
  );
}