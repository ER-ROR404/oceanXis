import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DateBar } from './DateBar';

const DATES = ['2023-06-01', '2023-08-31', '2023-12-28'];

describe('DateBar', () => {
  it('steps to the previous and next available dates', () => {
    const onDateChange = vi.fn();
    render(<DateBar date="2023-08-31" dates={DATES} onDateChange={onDateChange} />);
    fireEvent.click(screen.getByRole('button', { name: /previous date/i }));
    expect(onDateChange).toHaveBeenCalledWith('2023-06-01');
    fireEvent.click(screen.getByRole('button', { name: /next date/i }));
    expect(onDateChange).toHaveBeenCalledWith('2023-12-28');
  });

  it('disables stepping past the available range', () => {
    render(<DateBar date="2023-06-01" dates={DATES} onDateChange={() => {}} />);
    expect(screen.getByRole('button', { name: /previous date/i }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: /next date/i }).hasAttribute('disabled')).toBe(false);
  });

  it('keeps the full date select for direct jumps', () => {
    const onDateChange = vi.fn();
    render(<DateBar date="2023-08-31" dates={DATES} onDateChange={onDateChange} />);
    const select = screen.getByLabelText('Date');
    expect((select as HTMLSelectElement).options.length).toBe(3);
    fireEvent.change(select, { target: { value: '2023-12-28' } });
    expect(onDateChange).toHaveBeenCalledWith('2023-12-28');
  });
});
