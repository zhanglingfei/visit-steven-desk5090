import { create } from 'zustand';
import { login as apiLogin, getMe } from '../api/auth';

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  loading: boolean;
  error: string | null;
  requires2FA: boolean;
  tempUsername: string | null;
  tempPassword: string | null;
  requiresPasswordChange: boolean;
  passwordChangeReason: string | null;
  login: (username: string, password: string, totpCode?: string) => Promise<boolean>;
  logout: () => void;
  init: () => Promise<void>;
  clear2FA: () => void;
  clearPasswordChange: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  username: localStorage.getItem('username'),
  role: null,
  loading: false,
  error: null,
  requires2FA: false,
  tempUsername: null,
  tempPassword: null,
  requiresPasswordChange: false,
  passwordChangeReason: null,

  login: async (username: string, password: string, totpCode?: string) => {
    set({ loading: true, error: null });
    try {
      const data = await apiLogin(username, password, totpCode);

      // Check if 2FA is required
      if (data.requires_2fa) {
        set({
          requires2FA: true,
          tempUsername: username,
          tempPassword: password,
          loading: false,
          error: null,
        });
        return false; // Not fully logged in yet
      }

      // Login successful - check if password change required
      localStorage.setItem('token', data.token);
      localStorage.setItem('username', data.username);

      // Get user info to check password change requirement
      const { getMe } = await import('../api/auth');
      const user = await getMe();

      if (user.password_change_required) {
        set({
          token: data.token,
          username: data.username,
          requiresPasswordChange: true,
          passwordChangeReason: user.password_change_reason || 'Password change required',
          requires2FA: false,
          tempUsername: null,
          tempPassword: null,
          loading: false,
        });
        return true; // Logged in but needs password change
      }

      set({
        token: data.token,
        username: data.username,
        role: user.role,
        requires2FA: false,
        tempUsername: null,
        tempPassword: null,
        requiresPasswordChange: false,
        passwordChangeReason: null,
        loading: false,
      });
      return true;
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Login failed';
      set({ error: msg, loading: false });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    set({ token: null, username: null, role: null, requires2FA: false, requiresPasswordChange: false, passwordChangeReason: null });
  },

  init: async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const user = await getMe();
      set({ username: user.username, role: user.role });
      if (user.password_change_required) {
        set({ requiresPasswordChange: true, passwordChangeReason: user.password_change_reason || 'Password change required' });
      }
    } catch {
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      set({ token: null, username: null, role: null });
    }
  },

  clear2FA: () => {
    set({ requires2FA: false, tempUsername: null, tempPassword: null });
  },

  clearPasswordChange: () => {
    set({ requiresPasswordChange: false, passwordChangeReason: null });
  },
}));
