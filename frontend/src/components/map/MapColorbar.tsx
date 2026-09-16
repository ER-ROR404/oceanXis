import { useMemo } from 'react';
import { fieldDomain, rgbString, uncertaintyColor, viridis } from './colorScales';
import type { LayerMode } from './OceanMap';

interface MapColorbarProps {
  layer: LayerMode;
  values: (number | null)[][];
  sigma: (number | null)[][];
}

/**
 * Reference-viewer style horizontal color scale (top-center over the map).
 * The domain always comes from the REAL loaded field; null land never
 * enters the scale. Testid stays `map-legend` for the readout contract.
 */
export function MapColorbar({ layer, values, sigma }: MapColorbarProps) {
  const { gradient, min, max, unit } = useMemo(() => {
    if (layer === 'uncertainty') {
      const domain = fieldDomain(sigma);
      const stops = [0, 0.25, 0.5, 0.75, 1].map((t) => rgbString(uncertaintyColor(t)));
      return {
        gradient: `linear-gradient(to right, ${stops.join(', ')})`,
        min: domain.min,
        max: domain.max,
        unit: '±1σ · °C',
      };
    }
    const domain = fieldDomain(values);
    const stops = [0, 0.25, 0.5, 0.75, 1].map((t) => rgbString(viridis(t)));
    return { gradient: `linear-gradient(to right, ${stops.join(', ')})`, min: domain.min, max: domain.max, unit: '°C' };
  }, [layer, values, sigma]);

  const mid = (min + max) / 2;
  return (
    <div
      data-testid="map-legend"
      aria-label={layer === 'temperature' ? 'Temperature color scale' : 'Uncertainty color scale'}
      className="pointer-events-none rounded-md border border-zinc-700/80 bg-zinc-950/85 px-3 py-1.5 backdrop-blur-sm"
    >
      <div className="h-1.5 w-56 rounded-sm sm:w-72" style={{ background: gradient }} aria-hidden="true" />
      <div className="mt-0.5 flex w-56 items-baseline justify-between font-mono-data text-[11px] text-zinc-300 sm:w-72">
        <span>{min.toFixed(1)}</span>
        <span className="text-zinc-500">{mid.toFixed(1)}</span>
        <span>{max.toFixed(1)}</span>
        <span className="ml-2 text-teal-300">{unit}</span>
      </div>
    </div>
  );
}
