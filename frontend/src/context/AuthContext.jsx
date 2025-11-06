import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    checkSession();
  }, []);

  const checkSession = async () => {
    try {
      setLoading(true);
      const sessionData = await authApi.getSession();
      // Backend returns flat structure, create user object
      const user = {
        id: sessionData.user_id,
        email: sessionData.email,
        name: sessionData.name,
        role: sessionData.role,
        organization_id: sessionData.organization_id,
        organization_name: sessionData.organization_name,
      };
      setUser(user);
      setError(null);
    } catch (err) {
      // No active session or session expired
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authApi.login({ email, password });
      console.log('Login response:', response);
      // Backend returns flat structure, create user object
      const user = {
        id: response.user_id,
        email: response.email,
        name: response.name,
        role: response.role,
        organization_id: response.organization_id,
        organization_name: response.organization_name,
      };
      console.log('Setting user:', user);
      setUser(user);
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
      // Backend returns flat structure, create user object
      const user = {
        id: response.user_id,
        email: response.email,
        name: response.name,
        role: response.role,
        organization_id: response.organization_id,
        organization_name: response.organization_name,
      };
      setUser(user);
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
    }
  };

  const value = {
    user,
    loading,
    error,
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
