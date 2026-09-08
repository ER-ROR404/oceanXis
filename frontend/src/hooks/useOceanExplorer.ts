import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ApiClient, ApiError, ContractError } from '../api/client';
import type {
  Depth,
  MapPayload,
  PredictionEnvelope,
  PredictionStatus,
  ProfilePayload,
  Region,
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

/** Demo cache window (artifacts/demo_cache/manifest.json, weekly Jun-Dec 2023). */
export const DEMO_SCOPE = {
  earliest: '2023-06-01',
  latest: '2023-12-28',
  region: 'bay_of_bengal',
} as const;

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
  historyState: 'loading' | 'ok' | 'error';
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
}

/**
 * Owns every piece of explorer state and every /api/v1 fetch.
 *
 * Race safety: a single monotonic sequence number gates every async result
 * (history/map/profile). Any newer action invalidates older in-flight
 * responses, so switching region or depth can never be clobbered by a stale
 * response. Failures are honest: status 'unavailable' plus a human-readable
 * detail, never a fabricated field (RULE 1/D9 discipline).
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
  const [historyState, setHistoryState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [mapEnvelope, setMapEnvelope] = useState<PredictionEnvelope<MapPayload> | null>(null);
  const [profileEnvelope, setProfileEnvelope] = useState<PredictionEnvelope<ProfilePayload> | null>(null);
  const [selected, setSelected] = useState<SelectedCell | null>(null);
  const [status, setStatus] = useState<PredictionStatus | null>(null);
  const [bannerDetail, setBannerDetail] = useState<string | null>(null);
  const [busyMap, setBusyMap] = useState(false);
  const [busyProfile, setBusyProfile] = useState(false);
  const requestSeq = useRef(0);

  const setRegion = useCallback((next: Region) => {
    // Reset explorer state transactionally with the region change. Batching
    // date='' and dates=[] into the same commit keeps the map/profile effects
    // from firing with a date that belongs to the previous region (which would
    // win the sequence race and show stale fallback_demo for a region with no
    // data).
    setRegionState(next);
    setDateState('');
    setDates([]);
    setSelected(null);
    setMapEnvelope(null);
    setProfileEnvelope(null);
    setHistoryState('loading');
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

  // Available dates per region. An empty list is an honest no-data region.
  useEffect(() => {
    const seq = ++requestSeq.current;
    setDates([]);
    setDateState('');
    setMapEnvelope(null);
    setProfileEnvelope(null);
    setSelected(null);
    setHistoryState('loading');
    setStatus(null);
    setBannerDetail(null);
    setBusyMap(false);
    setBusyProfile(false);

    client
      .getHistory(region)
      .then((hist) => {
        if (seq !== requestSeq.current) return;
        const available = hist.dates;
        setHistoryState('ok');
        setDates(available);
        if (available.length === 0) {
          setStatus('unavailable');
          setBannerDetail(
            `No demo data for ${REGION_LABELS[region]} within the demo scope. The demo cache covers ${REGION_LABELS[DEMO_SCOPE.region]} from ${DEMO_SCOPE.earliest} to ${DEMO_SCOPE.latest}.`,
          );
          return;
        }
        // Prefer a date inside the warm, strongly stratified late-summer window.
        const preferred = available.find((d) => d >= '2023-09-01');
        setDateState(preferred ?? available[available.length - 1] ?? available[0]);
      })
      .catch((error: unknown) => {
        if (seq !== requestSeq.current) return;
        setHistoryState('error');
        setDates([]);
        setStatus('unavailable');
        setBannerDetail(descriptionOf(error));
      });
  }, [client, region]);

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

  return {
    region,
    date,
    depth,
    dates,
    historyState,
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
  };
}