import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App Root Component', () => {
  it('renders the application header and honest footer without error', () => {
    render(<App />);
    expect(screen.getByText('OCEANEMBED')).toBeInTheDocument();
    expect(screen.getByText('Subsurface Ocean Explorer')).toBeInTheDocument();
    expect(
      screen.getByText(/Modeled reconstruction; trained on data through 2023-12-31\./i),
    ).toBeInTheDocument();
  });
});
