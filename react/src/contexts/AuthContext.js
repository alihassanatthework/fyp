// src/contexts/AuthContext.js
// Real authentication wired to Django backend.
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

const AuthContext = createContext(null);

// ── token helpers ────────────────────────────────────────────────────
function saveTokens(access, refresh) {
  localStorage.setItem('authToken', access);
  if (refresh) localStorage.setItem('refreshToken', refresh);
}
function clearTokens() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
}

// Convert the backend error envelope into a single readable string.
function extractError(err, fallback = 'Something went wrong') {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === 'string') return data;
  if (data.error)   return data.error;
  if (data.detail)  return data.detail;
  // DRF field validation errors: { email: ['already exists'] }
  const firstKey = Object.keys(data)[0];
  if (firstKey) {
    const v = data[firstKey];
    return Array.isArray(v) ? `${firstKey}: ${v[0]}` : String(v);
  }
  return fallback;
}

// ── provider ─────────────────────────────────────────────────────────
export function AuthProvider({ children }) {
  const [user, setUser]                     = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading]               = useState(true);

  // On mount: if we have a token, verify it by hitting /auth/me/.
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient.get(API_ENDPOINTS.AUTH.ME)
      .then((res) => {
        // /auth/me/ returns { user, profile, medical_history }
        const u = res.data.user || res.data;
        setUser(u);
        localStorage.setItem('user', JSON.stringify(u));
        setIsAuthenticated(true);
      })
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  // ── register ────────────────────────────────────────────────────────
  // Frontend SignUp form is now Option B (first_name + last_name).
  // Backend serializer accepts: first_name, last_name, email, password.
  const register = useCallback(async (userData) => {
    try {
      const payload = {
        first_name: userData.firstName || '',
        last_name:  userData.lastName  || '',
        email:      userData.email,
        password:   userData.password,
      };
      const res = await apiClient.post(API_ENDPOINTS.AUTH.REGISTER, payload);
      const { user: newUser, access, refresh } = res.data;
      saveTokens(access, refresh);
      localStorage.setItem('user', JSON.stringify(newUser));
      setUser(newUser);
      setIsAuthenticated(true);

      // If the SignUp page sent health-condition flags, persist them via /profile/
      if (userData.medical_history) {
        try {
          await apiClient.patch(API_ENDPOINTS.PROFILE.UPDATE, {
            medical_history: userData.medical_history,
          });
        } catch (e) {
          // non-fatal — user can fill medical history later from profile page
          console.warn('Medical history save failed:', e);
        }
      }

      return { success: true, user: newUser };
    } catch (err) {
      return { success: false, error: extractError(err, 'Registration failed.') };
    }
  }, []);

  // ── login ───────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    try {
      const res = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, { email, password });
      const { user: loggedInUser, access, refresh } = res.data;
      saveTokens(access, refresh);
      localStorage.setItem('user', JSON.stringify(loggedInUser));
      setUser(loggedInUser);
      setIsAuthenticated(true);
      return { success: true, user: loggedInUser };
    } catch (err) {
      return { success: false, error: extractError(err, 'Invalid email or password.') };
    }
  }, []);

  // ── logout ──────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refreshToken');
    try {
      if (refresh) {
        await apiClient.post(API_ENDPOINTS.AUTH.LOGOUT, { refresh });
      }
    } catch {
      // refresh token may have been invalidated already — proceed anyway
    } finally {
      clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  // ── updateProfile (called by EditProfileModal) ────────────────────
  // payload may contain { user: {...}, profile: {...}, medical_history: {...} }
  const updateProfile = useCallback(async (payload) => {
    try {
      const res = await apiClient.patch(API_ENDPOINTS.PROFILE.UPDATE, payload);
      const updatedUser = res.data.user || res.data;
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      return { success: true, user: updatedUser, data: res.data };
    } catch (err) {
      return { success: false, error: extractError(err, 'Profile update failed.') };
    }
  }, []);

  const value = { user, isAuthenticated, loading, login, register, logout, updateProfile };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
