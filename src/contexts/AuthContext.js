// src/context/AuthContext.js
import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedToken = localStorage.getItem('authToken');
    
    if (storedUser && storedToken) {
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  // Login function (MOCK - replace with real API later)
  const login = async (email, password) => {
    try {
      // MOCK: In real app, call API here
      const mockUser = {
        id: 1,
        email: email,
        name: 'Test User',
        healthProfile: {}
      };
      
      const mockToken = 'mock-jwt-token-' + Date.now();
      
      // Store in localStorage
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('authToken', mockToken);
      
      // Update state
      setUser(mockUser);
      setIsAuthenticated(true);
      
      return { success: true, user: mockUser };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      const mockUser = {
        id: Date.now(),
        email: userData.email,
        name: userData.fullName || 'User',
        healthProfile: userData.healthProfile || {}
      };
      
      const mockToken = 'mock-jwt-token-' + Date.now();
      
      localStorage.setItem('user', JSON.stringify(mockUser));
      localStorage.setItem('authToken', mockToken);
      
      setUser(mockUser);
      setIsAuthenticated(true);
      
      return { success: true, user: mockUser };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('authToken');
    setUser(null);
    setIsAuthenticated(false);
  };

  // Update profile
  const updateProfile = (updatedData) => {
    const updatedUser = { ...user, ...updatedData };
    localStorage.setItem('user', JSON.stringify(updatedUser));
    setUser(updatedUser);
    return { success: true, user: updatedUser };
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    register,
    logout,
    updateProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook to use auth
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
