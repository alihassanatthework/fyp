// src/api/config.js
// API endpoints configuration

// Keep endpoints relative — axios baseURL is already set to '/api' in client.js,
// so these paths must NOT include '/api' prefix (would become '/api/api/...').
const API_BASE_URL = '';

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
