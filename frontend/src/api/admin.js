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
};

export default adminApi;
