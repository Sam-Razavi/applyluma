import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import posthog from 'posthog-js';
import { usePageTracking } from './usePageTracking';

vi.mock('posthog-js', () => ({ default: { capture: vi.fn() } }));

function renderAt(path: string) {
  return renderHook(() => usePageTracking(), {
    wrapper: ({ children }) => <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>,
  });
}

describe('usePageTracking', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('captures a pageview for a normal route', () => {
    renderAt('/dashboard');

    expect(posthog.capture).toHaveBeenCalledWith('$pageview', {
      $current_url: window.location.href,
    });
  });

  it('does not capture a pageview for /auth/callback, where the URL can carry a live token', () => {
    renderAt('/auth/callback');

    expect(posthog.capture).not.toHaveBeenCalled();
  });

  it('tracks other routes normally, independent of the callback exclusion', () => {
    renderAt('/settings');

    expect(posthog.capture).toHaveBeenCalledTimes(1);
    expect(posthog.capture).toHaveBeenCalledWith('$pageview', {
      $current_url: window.location.href,
    });
  });
});
