import { describe, it, expect } from 'vitest';
import { formatLatLon } from './latlon';

describe('formatLatLon', () => {
  it('formats north/east positive coordinates with two decimals', () => {
    expect(formatLatLon(15.25, 87.5)).toBe('15.25°N, 87.50°E');
  });

  it('labels southern and western coordinates correctly', () => {
    expect(formatLatLon(-12.345, -38.5)).toBe('12.35°S, 38.50°W');
  });

  it('treats zero as positive (equator/prime meridian)', () => {
    expect(formatLatLon(0, 0)).toBe('0.00°N, 0.00°E');
  });
});