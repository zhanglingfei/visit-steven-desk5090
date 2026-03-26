import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses - don't redirect for 2FA endpoints
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      // Don't redirect for 2FA setup/verify/disable endpoints
      // These return 401 for invalid credentials/code, not for auth token issues
      const is2FAEndpoint = url.includes('/2fa/setup') || url.includes('/2fa/verify') || url.includes('/2fa/disable');
      if (!is2FAEndpoint) {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
