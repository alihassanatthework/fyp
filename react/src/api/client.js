// src/api/client.js
// Axios HTTP client with JWT auto-refresh

import axios from 'axios';

// Relative path works for both:
//   - Production: Django serves React, so /api hits the same origin.
//   - Development: CRA's proxy (package.json "proxy") forwards /api → localhost:8000.
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Accept': 'application/json' },
  withCredentials: true,
  timeout: 120000, // 120s — AI pipeline can be slow on first run
});

// ── Request interceptor: attach access token to every request ──────────────
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: silent JWT refresh on 401 ───────────────────────
// When an access token expires (default 60 min) Django returns 401.
// We silently call /api/auth/token/refresh/ with the stored refresh token.
// If that succeeds we retry the original request with the new access token.
// If the refresh itself fails (refresh token expired / blacklisted after logout)
// we clear storage and redirect to login.

let isRefreshing = false;
let failedQueue  = [];   // requests waiting while refresh is in-flight

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    error ? reject(error) : resolve(token);
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh on 401 that hasn't already been retried,
    // and never on auth endpoints themselves (login/register/refresh).
    const isAuthEndpoint = originalRequest.url?.includes('/auth/login') ||
                           originalRequest.url?.includes('/auth/register') ||
                           originalRequest.url?.includes('/auth/token/refresh');

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      const refreshToken = localStorage.getItem('refreshToken');

      // No refresh token stored → send to login immediately
      if (!refreshToken) {
        localStorage.clear();
        window.location.href = '/';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Another request already triggered a refresh — queue this one
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        }).catch(Promise.reject);
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // simplejwt's built-in refresh endpoint
        const { data } = await axios.post(
          `${API_BASE_URL}/auth/token/refresh/`,
          { refresh: refreshToken }
        );

        const newAccess = data.access;
        localStorage.setItem('authToken', newAccess);
        // simplejwt rotates refresh tokens when ROTATE_REFRESH_TOKENS=True
        if (data.refresh) localStorage.setItem('refreshToken', data.refresh);

        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
        processQueue(null, newAccess);

        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.clear();
        window.location.href = '/';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // For all other errors extract a readable message. This also handles DRF
    // field-validation errors like { email: ["user with this email already
    // exists."] } or { password: ["too short"] } so the UI shows the REASON,
    // not a generic "Request failed with status code 400".
    const data = error.response?.data;
    let message =
      data?.detail ||
      data?.error  ||
      data?.message;

    if (!message && data && typeof data === 'object') {
      // First field error: "email: user with this email already exists."
      const firstKey = Object.keys(data)[0];
      if (firstKey) {
        const v = data[firstKey];
        const text = Array.isArray(v) ? v[0] : String(v);
        // Common auth fields already mention themselves ("An account with this
        // email…") — show them bare. Other fields keep a "field: msg" prefix.
        const bare = ['non_field_errors', 'email', 'password', 'detail'];
        message = bare.includes(firstKey) ? text : `${firstKey}: ${text}`;
      }
    } else if (!message && typeof data === 'string') {
      message = data;
    }

    message = message || error.message || 'Something went wrong';

    // Preserve the original response so downstream handlers (e.g. extractError
    // in AuthContext) can still inspect the raw error body if they want.
    const wrapped = new Error(message);
    wrapped.response = error.response;
    wrapped.status = error.response?.status;
    return Promise.reject(wrapped);
  }
);

export default apiClient;
