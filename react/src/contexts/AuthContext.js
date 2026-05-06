// src/contexts/AuthContext.js
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';

const AuthContext = createContext(null);

// ─── token helpers ──────────────────────────────────────────────────────────

function saveTokens(access, refresh) {
  localStorage.setItem('authToken', access);
  localStorage.setItem('refreshToken', refresh);
}

function clearTokens() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
}

// ─── provider ───────────────────────────────────────────────────────────────

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // On mount: if we have a stored access token, fetch /api/auth/me/ to verify
  // it is still valid and restore the user object.
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      setLoading(false);
      return;
    }

    apiClient
      .get('/auth/me/')
      .then((res) => {
        setUser(res.data.user);
        setIsAuthenticated(true);
      })
      .catch(() => {
        // Token expired or invalid — clear everything
        clearTokens();
      })
      .finally(() => setLoading(false));
  }, []);

  // ── register ──────────────────────────────────────────────────────────────

  const register = useCallback(async (userData) => {
    try {
      const payload = {
        full_name: userData.fullName || '',
        email: userData.email,
        password: userData.password,
        confirm_password: userData.confirmPassword,
        health_conditions: userData.healthConditions || [],
      };

      const res = await apiClient.post('/auth/register/', payload);
      const { user: newUser, access, refresh } = res.data;

      saveTokens(access, refresh);
      localStorage.setItem('user', JSON.stringify(newUser));
      setUser(newUser);
      setIsAuthenticated(true);

      return { success: true, user: newUser };
    } catch (err) {
      // DRF validation errors come back as { field: [msg] } or { error: msg }
      const data = err.response?.data;
      let message = 'Registration failed. Please try again.';
      if (data) {
        if (typeof data === 'string') message = data;
        else if (data.error) message = data.error;
        else {
          const firstKey = Object.keys(data)[0];
          const firstVal = data[firstKey];
          message = Array.isArray(firstVal) ? firstVal[0] : String(firstVal);
        }
      }
      return { success: false, error: message };
    }
  }, []);

  // ── login ─────────────────────────────────────────────────────────────────

  const login = useCallback(async (email, password) => {
    try {
      const res = await apiClient.post('/auth/login/', { email, password });
      const { user: loggedInUser, access, refresh } = res.data;

      saveTokens(access, refresh);
      localStorage.setItem('user', JSON.stringify(loggedInUser));
      setUser(loggedInUser);
      setIsAuthenticated(true);

      return { success: true, user: loggedInUser };
    } catch (err) {
      const message =
        err.response?.data?.error ||
        err.message ||
        'Login failed. Please check your credentials.';
      return { success: false, error: message };
    }
  }, []);

  // ── logout ────────────────────────────────────────────────────────────────

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refreshToken');
    try {
      if (refresh) await apiClient.post('/auth/logout/', { refresh });
    } catch {
      // Ignore errors — we still clear local state
    } finally {
      clearTokens();
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  // ── updateProfile ─────────────────────────────────────────────────────────

  const updateProfile = useCallback(async (updatedData) => {
    try {
      const res = await apiClient.patch('/profile/', updatedData);
      const updatedUser = res.data.user;
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      return { success: true, user: updatedUser };
    } catch (err) {
      return { success: false, error: err.message };
    }
  }, []);

  // ─────────────────────────────────────────────────────────────────────────

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    updateProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
