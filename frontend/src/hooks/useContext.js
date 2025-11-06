import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contextApi } from '../api/context';

// Query keys
export const contextKeys = {
  all: ['context'],
  current: () => [...contextKeys.all, 'current'],
  versions: () => [...contextKeys.all, 'versions'],
  version: (version) => [...contextKeys.all, 'version', version],
};

// Get current context
export function useCurrentContext() {
  return useQuery({
    queryKey: contextKeys.current(),
    queryFn: () => contextApi.getCurrent(),
    retry: 1,
  });
}

// Get all versions
export function useContextVersions() {
  return useQuery({
    queryKey: contextKeys.versions(),
    queryFn: () => contextApi.listVersions(),
  });
}

// Get specific version
export function useContextVersion(version) {
  return useQuery({
    queryKey: contextKeys.version(version),
    queryFn: () => contextApi.getVersion(version),
    enabled: !!version,
  });
}

// Create new context version
export function useCreateContext() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (contextData) => contextApi.create(contextData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextKeys.all });
    },
  });
}

// Make version current
export function useMakeCurrent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (contextId) => contextApi.makeCurrent(contextId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextKeys.all });
    },
  });
}

// Delete version
export function useDeleteContext() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (contextId) => contextApi.deleteVersion(contextId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextKeys.all });
    },
  });
}
