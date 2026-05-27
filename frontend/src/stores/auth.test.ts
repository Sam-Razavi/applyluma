import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './index';

describe('AuthStore', () => {
  beforeEach(() => {
    // Reset the store state before each test
    useAuthStore.getState().logout();
  });

  it('should initialize with default values', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should login and set user/token/refreshToken', () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      role: 'user',
      created_at: '',
      updated_at: '',
    };
    const mockToken = 'mock-token';
    const mockRefreshToken = 'mock-refresh-token';

    useAuthStore.getState().login(mockToken, mockRefreshToken, mockUser as any);

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.token).toBe(mockToken);
    expect(state.refreshToken).toBe(mockRefreshToken);
    expect(state.isAuthenticated).toBe(true);
  });

  it('should logout and clear state including refreshToken', () => {
    const mockUser = { id: '1', email: 'test@example.com' };
    const mockToken = 'mock-token';

    useAuthStore.getState().login(mockToken, 'mock-refresh-token', mockUser as any);
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should update user with setUser', () => {
    const mockUser = { id: '1', email: 'test@example.com' };
    useAuthStore.getState().setUser(mockUser as any);

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('should set loading state', () => {
    useAuthStore.getState().setLoading(true);
    expect(useAuthStore.getState().isLoading).toBe(true);

    useAuthStore.getState().setLoading(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});
