import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

const SESSION_CACHE_KEY = 'produck_session_cache';

// Helper to transform session data to user object
const transformSessionToUser = (sessionData) => ({
  id: sessionData.user_id,
  email: sessionData.email,
  name: sessionData.name,
  role: sessionData.role, // Legacy single role
  roles: sessionData.roles || [], // Multiple roles for RBAC
  organization_id: sessionData.organization_id,
  organization_name: sessionData.organization_name,
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false); // Changed to false - non-blocking by default
  const [error, setError] = useState(null);
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // Check for existing session on mount - optimistic with cache
  useEffect(() => {
    // Try to load from cache first (instant, optimistic)
    try {
      const cached = localStorage.getItem(SESSION_CACHE_KEY);
      if (cached) {
        const cachedUser = JSON.parse(cached);
        setUser(cachedUser); // Optimistically set user from cache
      }
    } catch (e) {
      // Ignore cache errors, will verify with server
      console.warn('Failed to load cached session:', e);
    }

    // Then verify with server in background (non-blocking)
    checkSession();
  }, []);

  const checkSession = async () => {
    try {
      const sessionData = await authApi.getSession();
      const user = transformSessionToUser(sessionData);

      setUser(user);
      setError(null);

      // Cache the session for fast subsequent loads
      try {
        localStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(user));
      } catch (e) {
        console.warn('Failed to cache session:', e);
      }
    } catch (err) {
      // No active session or session expired
      setUser(null);

      // Clear cache
      try {
        localStorage.removeItem(SESSION_CACHE_KEY);
      } catch (e) {
        // Ignore
      }
    } finally {
      setInitialCheckDone(true);
    }
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authApi.login({ email, password });
      console.log('Login response:', response);

      const user = transformSessionToUser(response);
      console.log('Setting user:', user);
      setUser(user);

      // Cache the session
      try {
        localStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(user));
      } catch (e) {
        console.warn('Failed to cache session:', e);
      }

      console.log('User state should be updated');
      return { success: true };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const register = async (email, password, fullName, organizationName) => {
    try {
      setError(null);
      const response = await authApi.register({
        email,
        password,
        full_name: fullName,
        organization_name: organizationName,
      });

      const user = transformSessionToUser(response);
      setUser(user);

      // Cache the session
      try {
        localStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(user));
      } catch (e) {
        console.warn('Failed to cache session:', e);
      }

      return { success: true };
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Registration failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      setError(null);

      // Clear cache
      try {
        localStorage.removeItem(SESSION_CACHE_KEY);
      } catch (e) {
        // Ignore
      }
    }
  };

  const value = {
    user,
    loading,
    error,
    initialCheckDone,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
