export const ANALYTICS_COLORS = {
  // Primary Brand (Indigo)
  primary: {
    50: '#eef2ff',
    100: '#e0e7ff',
    500: '#6366f1',
    600: '#4f46e5',
    700: '#4338ca',
  },

  // Chart Colors (for data visualization variety)
  chart: {
    blue: '#3b82f6',
    purple: '#8b5cf6',
    cyan: '#06b6d4',
    pink: '#ec4899',
    teal: '#14b8a6',
    amber: '#f59e0b',
    green: '#10b981',
    red: '#ef4444',
    indigo: '#6366f1',
  },

  // Chart Palette Array (for multi-series charts)
  chartPalette: [
    '#3b82f6',
    '#8b5cf6',
    '#06b6d4',
    '#ec4899',
    '#14b8a6',
    '#f59e0b',
    '#10b981',
    '#ef4444',
  ],

  // Semantic Colors (for trends and states)
  semantic: {
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
  },

  // Neutral Grays
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
} as const

export const CHART_COLORS = ANALYTICS_COLORS.chartPalette

export const LOCATION_COLORS = [
  '#6366f1',
  '#3b82f6',
  '#8b5cf6',
  '#06b6d4',
  '#14b8a6',
  '#10b981',
  '#f59e0b',
  '#ec4899',
]

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  padding: '12px',
}

export const CHART_AXIS_TICK = { fontSize: 12, fill: '#6b7280' }
export const CHART_DARK_AXIS_TICK = { fontSize: 12, fill: '#374151' }
