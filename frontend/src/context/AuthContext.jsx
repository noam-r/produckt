import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

// Only cache minimal UI state - NO sensitive user data
const UI_STATE_CACHE_KEY = 'produck_ui_state';

// Helper to transform session data to user object
const transformSessionToUser = (sessionData) => ({
  id: sessionData.user_id,
  email: sessionData.email,
  name: sessionData.name,
  role: sessionData.role, // Legacy single role
  roles: sessionData.roles || [], // Multiple roles for RBAC
  organization_id: sessionData.organization_id,
  organization_name: sessionData.organization_name,
  force_password_change: sessionData.force_password_change || false,
});

// Helper to extract only safe UI state for caching
const extractSafeUIState = (user) => ({
  // Only cache non-sensitive UI preferences
  hasActiveSession: true,
  lastLoginTime: Date.now()
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false); // Changed to false - non-blocking by default
  const [error, setError] = useState(null);
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // Check for existing session on mount - always verify with server
  useEffect(() => {
    // SECURITY: Clean up any existing sensitive data from localStorage
    try {
      const oldSessionData = localStorage.getItem('produck_session_cache');
      if (oldSessionData) {
        console.warn('Removing sensitive session data from localStorage for security');
        localStorage.removeItem('produck_session_cache');
      }
    } catch (e) {
      // Ignore cleanup errors
    }

    // Check if we might have a session (non-sensitive indicator only)
    let shouldCheckSession = true;
    try {
      const uiState = localStorage.getItem(UI_STATE_CACHE_KEY);
      if (uiState) {
        const parsed = JSON.parse(uiState);
        // Only use this as a hint to check session faster, never trust it
        shouldCheckSession = parsed.hasActiveSession;
      }
    } catch (e) {
      // Ignore cache errors
    }

    // Always verify with server - never trust localStorage for auth
    if (shouldCheckSession) {
      checkSession();
    } else {
      setInitialCheckDone(true);
    }
  }, []);

  const checkSession = async () => {
    try {
      const sessionData = await authApi.getSession();
      const user = transformSessionToUser(sessionData);

      setUser(user);
      setError(null);

      // Cache only safe UI state - NO user data
      try {
        const safeState = extractSafeUIState(user);
        localStorage.setItem(UI_STATE_CACHE_KEY, JSON.stringify(safeState));
      } catch (e) {
        console.warn('Failed to cache UI state:', e);
      }
    } catch (err) {
      // No active session or session expired
      setUser(null);

      // Clear UI state cache
      try {
        localStorage.removeItem(UI_STATE_CACHE_KEY);
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

      // Cache only safe UI state - NO user data
      try {
        const safeState = extractSafeUIState(user);
        localStorage.setItem(UI_STATE_CACHE_KEY, JSON.stringify(safeState));
      } catch (e) {
        console.warn('Failed to cache UI state:', e);
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

      // Cache only safe UI state - NO user data
      try {
        const safeState = extractSafeUIState(user);
        localStorage.setItem(UI_STATE_CACHE_KEY, JSON.stringify(safeState));
      } catch (e) {
        console.warn('Failed to cache UI state:', e);
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

      // Clear UI state cache
      try {
        localStorage.removeItem(UI_STATE_CACHE_KEY);
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
