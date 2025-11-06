/**
 * Context API endpoints
 */
import apiClient from './client';

export const contextApi = {
  // Get current context
  getCurrent: async () => {
    const { data } = await apiClient.get('/api/context/current');
    return data;
  },

  // Create new context version
  create: async (contextData) => {
    const { data } = await apiClient.post('/api/context', contextData);
    return data;
  },

  // List all versions
  listVersions: async () => {
    const { data } = await apiClient.get('/api/context/versions');
    // Backend returns { contexts: [], total }
    return data.contexts || [];
  },

  // Get specific version
  getVersion: async (version) => {
    const { data } = await apiClient.get(`/api/context/versions/${version}`);
    return data;
  },

  // Set version as current
  makeCurrent: async (contextId) => {
    const { data } = await apiClient.put(`/api/context/${contextId}/make-current`);
    return data;
  },

  // Delete version
  deleteVersion: async (contextId) => {
    await apiClient.delete(`/api/context/${contextId}`);
  },
};
