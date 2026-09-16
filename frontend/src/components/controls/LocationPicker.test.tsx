import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LocationPicker } from './LocationPicker';

const COORDS = { latitude: [15.0, 15.25, 15.5], longitude: [87.0, 87.5, 88.0] };

describe('LocationPicker (keyboard route to a grid cell)', () => {
  it('snaps typed coordinates to the real grid and reports the cell center', () => {
    const onPick = vi.fn();
    render(<LocationPicker coordinates={COORDS} onPick={onPick} />);
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '15.3' } });
    fireEvent.change(screen.getByLabelText(/longitude/i), { target: { value: '87.4' } });
    fireEvent.click(screen.getByRole('button', { name: /inspect location/i }));
    expect(onPick).toHaveBeenCalledWith(15.25, 87.5);
  });

  it('stays disabled without a loaded field instead of inventing a grid', () => {
    const onPick = vi.fn();
    render(<LocationPicker coordinates={null} onPick={onPick} />);
    expect(screen.getByRole('button', { name: /inspect location/i }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByTestId('location-picker').textContent).toMatch(/field/i);
    expect(onPick).not.toHaveBeenCalled();
  });
});
