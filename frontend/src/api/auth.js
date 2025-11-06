/**
 * Authentication API endpoints
 */
import apiClient from './client';

export const authApi = {
  // Register new user
  register: async (userData) => {
    const { data } = await apiClient.post('/auth/register', userData);
    return data;
  },

  // Login user
  login: async (credentials) => {
    const { data } = await apiClient.post('/auth/login', credentials);
    return data;
  },

  // Logout user
  logout: async () => {
    await apiClient.post('/auth/logout');
  },

  // Get current session
  getSession: async () => {
    const { data } = await apiClient.get('/auth/session');
    return data;
  },
};
