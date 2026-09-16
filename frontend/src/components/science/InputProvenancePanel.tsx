import { Layers } from 'lucide-react';

/**
 * The 7 LOCKED surface channels (problem statement / config/variables.yaml).
 * Wording mirrors the repo: "multi-source satellite-derived and ocean
 * observation products" — currents and winds are NOT pure satellite
 * measurements, so the UI must never claim they are.
 */
const CHANNELS = [
  { short: 'SST', label: 'Sea Surface Temperature' },
  { short: 'SSS', label: 'Sea Surface Salinity' },
  { short: 'SSH/SLA', label: 'Sea Surface Height / Sea Level Anomaly' },
  { short: 'Current U', label: 'Zonal surface current' },
  { short: 'Current V', label: 'Meridional surface current' },
  { short: 'Wind U', label: 'Zonal surface wind' },
  { short: 'Wind V', label: 'Meridional surface wind' },
];

/**
 * Demo spec Screen 5: what goes into OceanEmbed. Static, honest provenance —
 * no invented product names, no "7 satellite measurements" claim.
 */
export function InputProvenancePanel() {
  return (
    <section
      data-testid="input-provenance"
      aria-label="What goes into OceanEmbed?"
      className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4"
    >
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-zinc-400">
        <Layers className="h-4 w-4 text-teal-400" aria-hidden="true" />
        What goes into OceanEmbed?
      </h3>
      <p className="text-xs text-zinc-500">
        Multi-source satellite-derived and ocean observation products, harmonized onto a single
        0.25° reconstruction grid.
      </p>
      <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-7">
        {CHANNELS.map((c) => (
          <li
            key={c.short}
            className="rounded-md border border-zinc-800 bg-zinc-950/60 px-2 py-1.5 text-center"
          >
            <span className="block text-xs font-semibold text-zinc-100">{c.short}</span>
            <span className="block text-[10px] leading-tight text-zinc-500">{c.label}</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 border-t border-zinc-800 pt-2 text-[10px] uppercase tracking-wider text-zinc-600">
        Surface currents and winds combine satellite-observed and model-analysis products.
      </p>
    </section>
  );
}