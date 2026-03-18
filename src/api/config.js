// src/api/config.js
// API endpoints configuration

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const API_ENDPOINTS = {
  // Auth endpoints
  AUTH: {
    LOGIN: `${API_BASE_URL}/auth/login/`,
    REGISTER: `${API_BASE_URL}/auth/register/`,
    LOGOUT: `${API_BASE_URL}/auth/logout/`,
    ME: `${API_BASE_URL}/auth/me/`,
  },

  // Analysis endpoints
  ANALYSIS: {
    UPLOAD: `${API_BASE_URL}/analysis/upload/`,
    HISTORY: `${API_BASE_URL}/analysis/history/`,
    DETAIL: (id) => `${API_BASE_URL}/analysis/${id}/`,
  },

  // Profile endpoints
  PROFILE: {
    GET: `${API_BASE_URL}/profile/`,
    UPDATE: `${API_BASE_URL}/profile/update/`,
    HEALTH: `${API_BASE_URL}/profile/health/`,
  },
};

export default API_BASE_URL;
