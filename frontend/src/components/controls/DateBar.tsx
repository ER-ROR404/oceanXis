interface DateBarProps {
  date: string;
  dates: string[];
  onDateChange: (date: string) => void;
}

const stepClass =
  'rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-200 ' +
  'disabled:opacity-40 disabled:pointer-events-none hover:text-white ' +
  'focus:outline-none focus:ring-2 focus:ring-teal-600/40';

/**
 * Reference-viewer style time stepper: previous/next arrows walk the real
 * availability list; the select allows direct jumps. Never invents dates.
 */
export function DateBar({ date, dates, onDateChange }: DateBarProps) {
  const idx = dates.indexOf(date);
  const prev = idx > 0 ? dates[idx - 1] : null;
  const next = idx >= 0 && idx < dates.length - 1 ? dates[idx + 1] : null;
  return (
    <div data-testid="date-bar" aria-label="Date navigation" className="flex items-center gap-1.5 rounded-md border border-zinc-700/80 bg-zinc-950/85 px-2 py-1.5 backdrop-blur-sm">
      <button
        type="button"
        aria-label="Previous date"
        disabled={prev === null}
        onClick={() => prev && onDateChange(prev)}
        className={stepClass}
      >
        ◀
      </button>
      <select
        aria-label="Date"
        value={date}
        onChange={(e) => onDateChange(e.target.value)}
        className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 font-mono-data text-xs text-zinc-100 focus:outline-none focus:ring-2 focus:ring-teal-600/40"
      >
        {dates.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
      <button
        type="button"
        aria-label="Next date"
        disabled={next === null}
        onClick={() => next && onDateChange(next)}
        className={stepClass}
      >
        ▶
      </button>
    </div>
  );
}
