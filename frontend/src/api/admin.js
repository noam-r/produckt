/**
 * Admin API functions for user management
 */
import apiClient from './client';

const adminApi = {
  // Role endpoints
  getRoles: async () => {
    const { data } = await apiClient.get('/api/admin/roles');
    return data;
  },

  // User endpoints
  getUsers: async () => {
    const { data } = await apiClient.get('/api/admin/users');
    return data;
  },

  getUser: async (userId) => {
    const { data } = await apiClient.get(`/api/admin/users/${userId}`);
    return data;
  },

  createUser: async (userData) => {
    const { data } = await apiClient.post('/api/admin/users', userData);
    return data;
  },

  updateUser: async (userId, userData) => {
    const { data } = await apiClient.patch(`/api/admin/users/${userId}`, userData);
    return data;
  },

  changePassword: async (userId, passwordData) => {
    const { data } = await apiClient.post(`/api/admin/users/${userId}/change-password`, passwordData);
    return data;
  },

  deleteUser: async (userId) => {
    await apiClient.delete(`/api/admin/users/${userId}`);
  },

  updateUserBudget: async (userId, budgetData) => {
    const { data } = await apiClient.put(`/api/admin/users/${userId}/budget`, budgetData);
    return data;
  },

  // Analytics endpoints
  getAnalyticsOverview: async (days = 30) => {
    const { data } = await apiClient.get('/api/admin/analytics/overview', {
      params: { days }
    });
    return data;
  },

  getAnalyticsByUser: async (days = 30, limit = 50) => {
    const { data } = await apiClient.get('/api/admin/analytics/by-user', {
      params: { days, limit }
    });
    return data;
  },

  getAnalyticsByAgent: async (days = 30) => {
    const { data } = await apiClient.get('/api/admin/analytics/by-agent', {
      params: { days }
    });
    return data;
  },

  getAnalyticsByModel: async (days = 30) => {
    const { data } = await apiClient.get('/api/admin/analytics/by-model', {
      params: { days }
    });
    return data;
  },

  getAnalyticsOverTime: async (days = 30, granularity = 'day') => {
    const { data } = await apiClient.get('/api/admin/analytics/over-time', {
      params: { days, granularity }
    });
    return data;
  },
};

export default adminApi;
