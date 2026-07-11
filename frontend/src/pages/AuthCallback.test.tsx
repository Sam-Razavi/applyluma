import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import AuthCallback from './AuthCallback';
import { authApi } from '../services/api';
import { useAuthStore } from '../stores';

vi.mock('../services/api', () => ({
  authApi: {
    me: vi.fn(),
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function setLocationHash(hash: string) {
  window.history.replaceState(null, '', `/auth/callback${hash}`);
}

describe('AuthCallback page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().logout();
    window.history.replaceState(null, '', '/auth/callback');
  });

  const renderCallback = () =>
    render(
      <BrowserRouter>
        <AuthCallback />
      </BrowserRouter>
    );

  it('reads the token from the URL fragment, not the query string', async () => {
    setLocationHash('#token=fragment-token');
    const mockUser = { id: '1', email: 'test@example.com', full_name: 'Test User' };
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser as any);

    renderCallback();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });

    const state = useAuthStore.getState();
    expect(state.token).toBe('fragment-token');
    expect(state.user).toEqual(mockUser);
  });

  it('strips the fragment from the URL immediately so the token does not linger', async () => {
    setLocationHash('#token=fragment-token');
    vi.mocked(authApi.me).mockResolvedValueOnce({ id: '1', email: 'a@b.com' } as any);

    renderCallback();

    await waitFor(() => {
      expect(window.location.hash).toBe('');
    });
  });

  it('ignores a token placed in the query string instead of the fragment', async () => {
    window.history.replaceState(null, '', '/auth/callback?token=query-token');

    renderCallback();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?error=oauth_failed', { replace: true });
    });
    expect(authApi.me).not.toHaveBeenCalled();
  });

  it('redirects to login with an error when no token is present', async () => {
    renderCallback();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?error=oauth_failed', { replace: true });
    });
    expect(authApi.me).not.toHaveBeenCalled();
  });

  it('redirects to login with an error when authApi.me() fails', async () => {
    setLocationHash('#token=fragment-token');
    vi.mocked(authApi.me).mockRejectedValueOnce(new Error('unauthorized'));

    renderCallback();

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login?error=oauth_failed', { replace: true });
    });
  });
});
