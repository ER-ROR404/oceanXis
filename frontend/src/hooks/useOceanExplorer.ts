import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiClient, ApiError, ContractError } from '../api/client';
import type {
  AvailabilityResponse,
  Depth,
  MapPayload,
  PredictionEnvelope,
  PredictionStatus,
  ProfilePayload,
  Region,
  RegionAvailability,
} from '../types/contracts';

export interface SelectedCell {
  lat: number;
  lon: number;
}

export const REGION_LABELS: Record<Region, string> = {
  bay_of_bengal: 'Bay of Bengal',
  arabian_sea: 'Arabian Sea',
  north_indian_ocean: 'North Indian Ocean',
};

/** Map any thrown error to a human-readable honesty sentence (defensive last resort). */
export function descriptionOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof ContractError) {
    return 'The backend response did not match the OceanEmbed contract.';
  }
  return 'Unexpected error while contacting the OceanEmbed backend.';
}

export interface OceanExplorer {
  region: Region;
  date: string;
  depth: Depth;
  dates: string[];
  availability: AvailabilityResponse | null;
  availabilityState: 'loading' | 'ok' | 'error';
  latestAvailable: string | null;
  provenance: string | null;
  scope: RegionAvailability | null;
  mapEnvelope: PredictionEnvelope<MapPayload> | null;
  profileEnvelope: PredictionEnvelope<ProfilePayload> | null;
  selected: SelectedCell | null;
  status: PredictionStatus | null;
  bannerDetail: string | null;
  busyMap: boolean;
  busyProfile: boolean;
  setRegion: (region: Region) => void;
  setDate: (date: string) => void;
  setDepth: (depth: number) => void;
  selectCell: (lat: number, lon: number) => void;
  clearSelection: () => void;
}

/** Provenance sentence for a region entry; null when the region has no data. */
export function provenanceOf(entry: RegionAvailability | undefined): string | null {
  if (!entry || entry.status !== 'available' || !entry.checkpoint) return null;
  const c = entry.checkpoint;
  return `${entry.model_version} · ${c.file} · epoch ${c.epoch} · val_loss ${c.val_loss} · data through ${entry.date_end ?? ''}`;
}

/**
 * Owns every piece of explorer state and every /api/v1 fetch.
 *
 * The availability report (GET /availability) drives date availability per
 * region — the 31-date demo-cache limitation is gone; the live model service's
 * daily coverage (730 dates) is surfaced as-is, never invented (RULE 7).
 *
 * Race safety: a single monotonic sequence number gates every async result.
 * Any newer action invalidates older in-flight responses. Failures are honest:
 * status 'unavailable' plus a human-readable detail.
 */
export function useOceanExplorer(): OceanExplorer {
  const client = useMemo(
    () => new ApiClient(import.meta.env.VITE_API_BASE_URL ?? '/api/v1'),
    [],
  );

  const [region, setRegionState] = useState<Region>('bay_of_bengal');
  const [date, setDateState] = useState('');
  const [depth, setDepthState] = useState<Depth>(100);
  const [dates, setDates] = useState<string[]>([]);
  const [availability, setAvailability] = useState<AvailabilityResponse | null>(null);
  const [availabilityState, setAvailabilityState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [mapEnvelope, setMapEnvelope] = useState<PredictionEnvelope<MapPayload> | null>(null);
  const [profileEnvelope, setProfileEnvelope] = useState<PredictionEnvelope<ProfilePayload> | null>(null);
  const [selected, setSelected] = useState<SelectedCell | null>(null);
  const [status, setStatus] = useState<PredictionStatus | null>(null);
  const [bannerDetail, setBannerDetail] = useState<string | null>(null);
  const [busyMap, setBusyMap] = useState(false);
  const [busyProfile, setBusyProfile] = useState(false);
  const requestSeq = useRef(0);

  const setRegion = useCallback((next: Region) => {
    // Reset explorer state transactionally with the region change. The derive
    // effect re-fills dates from the availability report right after.
    setRegionState(next);
    setDateState('');
    setDates([]);
    setSelected(null);
    setMapEnvelope(null);
    setProfileEnvelope(null);
    setStatus(null);
    setBannerDetail(null);
    setBusyMap(false);
    setBusyProfile(false);
  }, []);
  const setDate = useCallback((next: string) => setDateState(next), []);
  const setDepth = useCallback((next: number) => setDepthState(next as Depth), []);
  const selectCell = useCallback((lat: number, lon: number) => {
    setSelected((current) => (current && current.lat === lat && current.lon === lon ? current : { lat, lon }));
  }, []);
  const clearSelection = useCallback(() => {
    setSelected(null);
  }, []);

  // Capability report: fetched once, trusted only through the contract guard.
  useEffect(() => {
    let cancelled = false;
    setAvailabilityState('loading');
    client
      .getAvailability()
      .then((avail) => {
        if (cancelled) return;
        setAvailability(avail);
        setAvailabilityState('ok');
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setAvailabilityState('error');
        setStatus('unavailable');
        setBannerDetail(descriptionOf(error));
      });
    return () => {
      cancelled = true;
    };
  }, [client]);

  // Derive dates (and an in-window default) for the selected region whenever
  // the report or the region changes.
  useEffect(() => {
    if (!availability) return;
    const entry = availability.regions.find((r) => r.region === region);
    const available = entry?.status === 'available' ? entry.dates : [];
    setDates(available);
    setDateState('');
    setMapEnvelope(null);
    setProfileEnvelope(null);
    setSelected(null);
    setStatus(null);
    setBannerDetail(null);
    setBusyMap(false);
    setBusyProfile(false);
    if (available.length === 0) {
      setStatus('unavailable');
      setBannerDetail(`No data is currently available for ${REGION_LABELS[region]}.`);
      return;
    }
    // Prefer a date inside the warm, strongly stratified late-summer window.
    const preferred = available.find((d) => d >= '2023-09-01');
    setDateState(preferred ?? available[available.length - 1] ?? available[0]);
  }, [availability, region]);

  // Gridded map field, per region/date/depth.
  useEffect(() => {
    if (!date) return;
    const seq = ++requestSeq.current;
    setBusyMap(true);
    client
      .getMap(region, date, depth)
      .then((env) => {
        if (seq !== requestSeq.current) return;
        setMapEnvelope(env);
        setStatus(env.status);
        setBannerDetail(null);
      })
      .catch((error: unknown) => {
        if (seq !== requestSeq.current) return;
        setMapEnvelope(null);
        setStatus('unavailable');
        setBannerDetail(descriptionOf(error));
      })
      .finally(() => {
        if (seq === requestSeq.current) setBusyMap(false);
      });
  }, [client, region, date, depth]);

  // Vertical profile, per region/date/selected cell (depth-independent).
  useEffect(() => {
    if (!date || !selected) {
      setProfileEnvelope(null);
      setBusyProfile(false);
      return;
    }
    const seq = ++requestSeq.current;
    setProfileEnvelope(null);
    setBusyProfile(true);
    client
      .getProfile(region, date, selected.lat, selected.lon)
      .then((env) => {
        if (seq !== requestSeq.current) return;
        setProfileEnvelope(env);
      })
      .catch(() => {
        // Honest miss: the profile panel explains the absence; the banner is
        // governed by the map status alone.
        if (seq !== requestSeq.current) return;
        setProfileEnvelope(null);
      })
      .finally(() => {
        if (seq === requestSeq.current) setBusyProfile(false);
      });
  }, [client, region, date, selected]);

  const entry = useMemo(
    () => (availability ? availability.regions.find((r) => r.region === region) : undefined),
    [availability, region],
  );

  return {
    region,
    date,
    depth,
    dates,
    availability,
    availabilityState,
    latestAvailable: entry?.status === 'available' ? entry.date_end : null,
    provenance: provenanceOf(entry),
    scope: availability?.regions.find((r) => r.status === 'available') ?? null,
    mapEnvelope,
    profileEnvelope,
    selected,
    status,
    bannerDetail,
    busyMap,
    busyProfile,
    setRegion,
    setDate,
    setDepth,
    selectCell,
    clearSelection,
  };
}