// src/api/config.js
// API endpoints configuration

// Keep endpoints relative — axios baseURL is already set to '/api' in client.js,
// so these paths must NOT include '/api' prefix (would become '/api/api/...').

export const API_ENDPOINTS = {
  // ── Auth ────────────────────────────────────────────────────────────
  AUTH: {
    LOGIN:           '/auth/login/',
    REGISTER:        '/auth/register/',
    LOGOUT:          '/auth/logout/',
    ME:              '/auth/me/',
    REFRESH:         '/auth/token/refresh/',
    FORGOT_PASSWORD: '/auth/forgot-password/',
    RESET_PASSWORD:  '/auth/reset-password/',
    CHANGE_PASSWORD: '/auth/change-password/',
    MY_ROLE:         '/auth/my-role/',
  },

  // ── Profile (combined user + profile + medical_history) ────────────
  PROFILE: {
    GET:     '/profile/',
    UPDATE:  '/profile/',
    UPGRADE: '/account/upgrade/',
  },

  // ── Skin / scalp analysis pipeline ─────────────────────────────────
  ANALYSIS: {
    UPLOAD:  '/analysis/upload/',
    HISTORY: '/analysis/history/',
    STATS:   '/analysis/stats/',
    DETAIL:  (id) => `/analysis/${id}/`,
  },

  // ── Makeup assistance ─────────────────────────────────────────────
  MAKEUP: {
    SUGGEST: '/makeup/suggest/',
    HISTORY: '/makeup/history/',
  },

  // ── Fashion assistance ────────────────────────────────────────────
  FASHION: {
    SUGGEST: '/fashion/suggest/',
    HISTORY: '/fashion/history/',
  },

  // ── Providers (dermatologists / salons) ───────────────────────────
  PROVIDERS: {
    LIST:    '/providers/',
    NEARBY:  '/providers/nearby/',
    DETAIL:  (id) => `/providers/${id}/`,
  },

  // ── Bookings ─────────────────────────────────────────────────────
  BOOKINGS: {
    LIST:   '/bookings/',
    CREATE: '/bookings/',
    DETAIL: (id) => `/bookings/${id}/`,
    CANCEL: (id) => `/bookings/${id}/cancel/`,
  },

  // ── Admin (gated by IsAdmin permission) ──────────────────────────
  ADMIN: {
    USERS:        '/admin/users/',
    USER_ROLE:    (id) => `/admin/users/${id}/role/`,
    MODEL_STATUS: '/admin/models/status/',
  },
};

export default API_ENDPOINTS;
