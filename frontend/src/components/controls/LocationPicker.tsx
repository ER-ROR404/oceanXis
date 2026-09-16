import { useState } from 'react';
import type { Coordinates } from '../../types/contracts';
import { nearestIndex } from '../map/colorScales';

interface LocationPickerProps {
  /** Live field coordinates; null until the map payload loads (never guessed). */
  coordinates: Coordinates | null;
  onPick: (lat: number, lon: number) => void;
}

const inputClass =
  'w-28 rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 font-mono-data text-sm text-zinc-100 ' +
  'focus:outline-none focus:ring-2 focus:ring-teal-600/40 focus:ring-offset-2 focus:ring-offset-zinc-950';

/**
 * Keyboard/accessibility route to a reconstruction cell (§39): type
 * latitude/longitude, get snapped to the REAL loaded grid, inspect.
 * Without a loaded field the form stays disabled — it never invents a grid.
 */
export function LocationPicker({ coordinates, onPick }: LocationPickerProps) {
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const ready = coordinates !== null;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!coordinates) return;
    const latNum = Number(lat);
    const lonNum = Number(lon);
    if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) return;
    onPick(
      coordinates.latitude[nearestIndex(coordinates.latitude, latNum)],
      coordinates.longitude[nearestIndex(coordinates.longitude, lonNum)],
    );
  };

  return (
    <form
      data-testid="location-picker"
      aria-label="Inspect location by coordinates"
      onSubmit={submit}
      className="flex flex-wrap items-end gap-2 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
    >
      <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
        Latitude
        <input
          aria-label="Latitude"
          className={inputClass}
          inputMode="decimal"
          placeholder="15.25"
          value={lat}
          disabled={!ready}
          onChange={(e) => setLat(e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
        Longitude
        <input
          aria-label="Longitude"
          className={inputClass}
          inputMode="decimal"
          placeholder="87.50"
          value={lon}
          disabled={!ready}
          onChange={(e) => setLon(e.target.value)}
        />
      </label>
      <button
        type="submit"
        aria-label="Inspect location"
        disabled={!ready}
        className="rounded-md bg-teal-400 px-3 py-1.5 text-xs font-medium text-zinc-950 disabled:opacity-50 disabled:pointer-events-none"
      >
        Inspect
      </button>
      {!ready && (
        <p className="w-full text-[11px] text-zinc-600">Load a temperature field first; coordinates snap to its grid.</p>
      )}
    </form>
  );
}
