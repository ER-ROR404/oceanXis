import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ControlPanel } from './ControlPanel';

describe('ControlPanel', () => {
  it('switches layers, regions and resets the view', () => {
    const onLayerChange = vi.fn();
    const onRegionChange = vi.fn();
    const onResetView = vi.fn();
    render(
      <ControlPanel
        layer="temperature"
        region="bay_of_bengal"
        coordinates={null}
        onLayerChange={onLayerChange}
        onRegionChange={onRegionChange}
        onPick={() => {}}
        onResetView={onResetView}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /^uncertainty$/i }));
    expect(onLayerChange).toHaveBeenCalledWith('uncertainty');
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'arabian_sea' } });
    expect(onRegionChange).toHaveBeenCalledWith('arabian_sea');
    fireEvent.click(screen.getByRole('button', { name: /reset view/i }));
    expect(onResetView).toHaveBeenCalledTimes(1);
  });

  it('embeds keyboard coordinate inspection snapped to the real grid', () => {
    render(
      <ControlPanel
        layer="temperature"
        region="bay_of_bengal"
        coordinates={{ latitude: [15.0, 15.25], longitude: [87.0, 87.5] }}
        onLayerChange={() => {}}
        onRegionChange={() => {}}
        onPick={vi.fn()}
        onResetView={() => {}}
      />,
    );
    expect(screen.getByLabelText('Latitude')).toBeInTheDocument();
    expect(screen.getByLabelText('Longitude')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /inspect location/i })).toBeInTheDocument();
  });
});
