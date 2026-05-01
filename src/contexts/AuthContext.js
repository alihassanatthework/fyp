// src/contexts/AuthContext.js
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
// import apiClient from '../api/client'; // ── API disabled for local dev ──

const AuthContext = createContext(null);

// ─── Mock user for local development ────────────────────────────────────────
const MOCK_USER = {
  id: 1,
  full_name: 'Test User',
  email: 'test@example.com',
  health_conditions: [],
};

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

  // ── On mount: restore session from localStorage (no backend call) ─────────
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    const storedUser = localStorage.getItem('user');

    if (token && storedUser) {
      try { setUser(JSON.parse(storedUser)); } catch (e) {}
      setIsAuthenticated(true);
    }
    setLoading(false);

    // ── REAL API call (commented out — requires backend on :8000) ─────────
    // const token = localStorage.getItem('authToken');
    // if (!token) { setLoading(false); return; }
    // apiClient
    //   .get('/auth/me/')
    //   .then((res) => {
    //     setUser(res.data.user);
    //     setIsAuthenticated(true);
    //   })
    //   .catch(() => clearTokens())
    //   .finally(() => setLoading(false));
  }, []);

  // ── register ──────────────────────────────────────────────────────────────

  const register = useCallback(async (userData) => {
    // ── MOCK register (no backend) ────────────────────────────────────────
    const newUser = {
      ...MOCK_USER,
      full_name: userData.fullName || 'New User',
      email: userData.email,
      health_conditions: userData.healthConditions || [],
    };
    saveTokens('mock-access-token', 'mock-refresh-token');
    localStorage.setItem('user', JSON.stringify(newUser));
    setUser(newUser);
    setIsAuthenticated(true);
    return { success: true, user: newUser };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const payload = {
    //     full_name: userData.fullName || '',
    //     email: userData.email,
    //     password: userData.password,
    //     confirm_password: userData.confirmPassword,
    //     health_conditions: userData.healthConditions || [],
    //   };
    //   const res = await apiClient.post('/auth/register/', payload);
    //   const { user: newUser, access, refresh } = res.data;
    //   saveTokens(access, refresh);
    //   localStorage.setItem('user', JSON.stringify(newUser));
    //   setUser(newUser);
    //   setIsAuthenticated(true);
    //   return { success: true, user: newUser };
    // } catch (err) {
    //   const data = err.response?.data;
    //   let message = 'Registration failed. Please try again.';
    //   if (data) {
    //     if (typeof data === 'string') message = data;
    //     else if (data.error) message = data.error;
    //     else {
    //       const firstKey = Object.keys(data)[0];
    //       const firstVal = data[firstKey];
    //       message = Array.isArray(firstVal) ? firstVal[0] : String(firstVal);
    //     }
    //   }
    //   return { success: false, error: message };
    // }
  }, []);

  // ── login ─────────────────────────────────────────────────────────────────

  const login = useCallback(async (email, password) => {
    // ── MOCK login (any credentials accepted) ─────────────────────────────
    const loggedInUser = { ...MOCK_USER, email };
    saveTokens('mock-access-token', 'mock-refresh-token');
    localStorage.setItem('user', JSON.stringify(loggedInUser));
    setUser(loggedInUser);
    setIsAuthenticated(true);
    return { success: true, user: loggedInUser };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const res = await apiClient.post('/auth/login/', { email, password });
    //   const { user: loggedInUser, access, refresh } = res.data;
    //   saveTokens(access, refresh);
    //   localStorage.setItem('user', JSON.stringify(loggedInUser));
    //   setUser(loggedInUser);
    //   setIsAuthenticated(true);
    //   return { success: true, user: loggedInUser };
    // } catch (err) {
    //   const message =
    //     err.response?.data?.error ||
    //     err.message ||
    //     'Login failed. Please check your credentials.';
    //   return { success: false, error: message };
    // }
  }, []);

  // ── logout ────────────────────────────────────────────────────────────────

  const logout = useCallback(async () => {
    // ── MOCK logout ────────────────────────────────────────────────────────
    clearTokens();
    setUser(null);
    setIsAuthenticated(false);

    // ── REAL API call (commented out) ──────────────────────────────────────
    // const refresh = localStorage.getItem('refreshToken');
    // try {
    //   if (refresh) await apiClient.post('/auth/logout/', { refresh });
    // } catch {} finally {
    //   clearTokens();
    //   setUser(null);
    //   setIsAuthenticated(false);
    // }
  }, []);

  // ── updateProfile ─────────────────────────────────────────────────────────

  const updateProfile = useCallback(async (updatedData) => {
    // ── MOCK updateProfile ─────────────────────────────────────────────────
    const updatedUser = { ...user, ...updatedData };
    localStorage.setItem('user', JSON.stringify(updatedUser));
    setUser(updatedUser);
    return { success: true, user: updatedUser };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const res = await apiClient.patch('/profile/', updatedData);
    //   const updatedUser = res.data.user;
    //   localStorage.setItem('user', JSON.stringify(updatedUser));
    //   setUser(updatedUser);
    //   return { success: true, user: updatedUser };
    // } catch (err) {
    //   return { success: false, error: err.message };
    // }
  }, [user]);

  const value = { user, isAuthenticated, loading, login, register, logout, updateProfile };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
