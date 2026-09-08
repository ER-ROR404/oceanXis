import { MessageSquareQuote, Layers } from 'lucide-react';
import type { ExplainerInput } from '../../utils/explain';
import { buildExplanation } from '../../utils/explain';

interface ExplainLocationProps {
  input: ExplainerInput;
}

/** Deterministic "Explain this location" panel. No LLM involved. */
export function ExplainLocation({ input }: ExplainLocationProps) {
  const { sentences } = buildExplanation(input);
  return (
    <section
      data-testid="explain-location"
      aria-label="Explain this location"
      className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4"
    >
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-200">
        <MessageSquareQuote className="h-4 w-4 text-teal-400" aria-hidden="true" />
        Explain this location
      </h3>
      <ul className="space-y-1.5 text-sm text-zinc-400">
        {sentences.map((s, i) => (
          <li key={i} className="flex gap-2">
            <Layers className="mt-0.5 h-3.5 w-3.5 shrink-0 text-zinc-600" aria-hidden="true" />
            <span>{s}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-zinc-800 pt-2 text-xs text-zinc-500">
        Reconstruction from a statistical model, not an observation.
      </p>
    </section>
  );
}