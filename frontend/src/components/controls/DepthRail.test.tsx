import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DepthRail } from './DepthRail';

describe('DepthRail', () => {
  it('lists exactly the 15 canonical model depths with surface first', () => {
    render(<DepthRail depth={100} onDepthChange={() => {}} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(15);
    expect(buttons[0]).toHaveTextContent(/surface/i);
    expect(buttons[buttons.length - 1]).toHaveTextContent(/1000/);
  });

  it('marks the active slice and reports selections', () => {
    const onDepthChange = vi.fn();
    render(<DepthRail depth={100} onDepthChange={onDepthChange} />);
    expect(screen.getByRole('button', { name: '100 m' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: '200 m' }));
    expect(onDepthChange).toHaveBeenCalledWith(200);
  });
});
