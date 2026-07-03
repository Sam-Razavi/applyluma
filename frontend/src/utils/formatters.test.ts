import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  formatCurrency,
  formatCompactCurrency,
  formatPercentage,
  formatNumber,
  formatDate,
  formatRelativeDate,
  titleCase,
} from './formatters';

describe('Formatters Utility', () => {
  describe('formatCurrency', () => {
    it('formats numbers as USD currency', () => {
      expect(formatCurrency(123456)).toBe('$123,456');
    });

    it('returns n/a for null or undefined', () => {
      expect(formatCurrency(null)).toBe('n/a');
      expect(formatCurrency(undefined)).toBe('n/a');
    });
  });

  describe('formatCompactCurrency', () => {
    it('returns n/a for null or undefined', () => {
      expect(formatCompactCurrency(null)).toBe('n/a');
      expect(formatCompactCurrency(undefined)).toBe('n/a');
    });

    it('formats millions with M suffix', () => {
      expect(formatCompactCurrency(1200000)).toBe('$1.2M');
    });

    it('formats thousands with k suffix', () => {
      expect(formatCompactCurrency(45000)).toBe('$45k');
    });

    it('formats small numbers without suffix', () => {
      expect(formatCompactCurrency(500)).toBe('$500');
    });
  });

  describe('formatPercentage', () => {
    it('formats numbers as percentages', () => {
      expect(formatPercentage(12.34)).toBe('12.3%');
      expect(formatPercentage(12.34, 2)).toBe('12.34%');
    });

    it('returns 0% for null or undefined', () => {
      expect(formatPercentage(null)).toBe('0%');
    });
  });

  describe('formatNumber', () => {
    it('formats numbers with commas', () => {
      expect(formatNumber(1234567)).toBe('1,234,567');
    });

    it('returns 0 for null or undefined', () => {
      expect(formatNumber(null)).toBe('0');
    });
  });

  describe('formatDate', () => {
    it('formats ISO strings to readable dates', () => {
      const date = '2026-05-12T00:00:00Z';
      // Use a regex or check for parts as timezones can affect the exact output
      const result = formatDate(date);
      expect(result).toContain('2026');
      expect(result).toContain('May');
    });
  });

  describe('titleCase', () => {
    it('converts snake_case to Title Case', () => {
      expect(titleCase('hello_world')).toBe('Hello World');
    });

    it('capitalizes words', () => {
      expect(titleCase('software engineering')).toBe('Software Engineering');
    });
  });
});

import { formatShortDate, formatPeriod } from './formatters';

describe('formatShortDate', () => {
  it('formats ISO date strings to short month/day format', () => {
    const result = formatShortDate('2026-05-12T00:00:00Z');
    expect(result).toContain('May');
  });
});

describe('formatRelativeDate', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "Today" for a timestamp from earlier today', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-04T12:00:00Z'));
    expect(formatRelativeDate('2026-01-04T00:00:00Z')).toBe('Today');
  });

  it('returns "Yesterday" for a timestamp exactly one day ago', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-04T00:00:00Z'));
    expect(formatRelativeDate('2026-01-03T00:00:00Z')).toBe('Yesterday');
  });

  it('returns "N days ago" for a timestamp under a week old', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-04T00:00:00Z'));
    expect(formatRelativeDate('2026-01-01T00:00:00Z')).toBe('3 days ago');
  });

  it('returns "N weeks ago" for a timestamp under a month old', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-15T00:00:00Z'));
    expect(formatRelativeDate('2026-01-01T00:00:00Z')).toBe('2 weeks ago');
  });

  it('returns "N months ago" for an older timestamp', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-01T00:00:00Z'));
    expect(formatRelativeDate('2026-01-01T00:00:00Z')).toBe('1 month ago');
  });

  it('clamps a future timestamp (clock skew) to "Today"', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
    expect(formatRelativeDate('2026-01-02T00:00:00Z')).toBe('Today');
  });
});

describe('formatPeriod', () => {
  it('formats YYYY-MM-DD strings using formatShortDate', () => {
    const result = formatPeriod('2026-05-12');
    expect(result).toContain('May');
  });

  it('returns non-date strings unchanged', () => {
    expect(formatPeriod('Q1 2026')).toBe('Q1 2026');
    expect(formatPeriod('custom period')).toBe('custom period');
  });
});
