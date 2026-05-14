import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatCompactCurrency,
  formatPercentage,
  formatNumber,
  formatDate,
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
