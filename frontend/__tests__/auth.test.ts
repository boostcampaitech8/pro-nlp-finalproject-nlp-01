import { useAuthStore } from '@/stores/useAuthStore';
import { act } from 'react';

describe('useAuthStore (Zustand)', () => {
    beforeEach(() => {
        // Clear store before each test
        act(() => {
            useAuthStore.getState().logout();
        });
        localStorage.clear();
    });

    it('should have initial state', () => {
        const state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.token).toBeNull();
        expect(state.isAuthenticated).toBe(false);
    });

    it('should update state on login', () => {
        const mockUser = { id: 1, email: 'test@example.com', name: 'Test User' };
        const mockToken = 'mock-token';

        act(() => {
            useAuthStore.getState().login(mockUser, mockToken);
        });

        const state = useAuthStore.getState();
        expect(state.user).toEqual(mockUser);
        expect(state.token).toBe(mockToken);
        expect(state.isAuthenticated).toBe(true);
    });

    it('should clear state on logout', () => {
        const mockUser = { id: 1, email: 'test@example.com', name: 'Test User' };

        act(() => {
            useAuthStore.getState().login(mockUser, 'token');
            useAuthStore.getState().logout();
        });

        const state = useAuthStore.getState();
        expect(state.user).toBeNull();
        expect(state.isAuthenticated).toBe(false);
    });

    it('should persist state in localStorage', () => {
        const mockUser = { id: 1, email: 'persist@example.com', name: 'Persist User' };

        act(() => {
            useAuthStore.getState().login(mockUser, 'persist-token');
        });

        const storedData = JSON.parse(localStorage.getItem('auth-storage') || '{}');
        expect(storedData.state.user).toEqual(mockUser);
        expect(storedData.state.isAuthenticated).toBe(true);
    });
});
