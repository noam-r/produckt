import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { initiativesApi } from '../api/initiatives';

// Query keys
export const initiativeKeys = {
  all: ['initiatives'],
  lists: () => [...initiativeKeys.all, 'list'],
  list: (filters) => [...initiativeKeys.lists(), filters],
  details: () => [...initiativeKeys.all, 'detail'],
  detail: (id) => [...initiativeKeys.details(), id],
};

// Fetch all initiatives
export function useInitiatives(filters = {}) {
  return useQuery({
    queryKey: initiativeKeys.list(filters),
    queryFn: () => initiativesApi.list(filters),
  });
}

// Fetch single initiative
export function useInitiative(id) {
  return useQuery({
    queryKey: initiativeKeys.detail(id),
    queryFn: () => initiativesApi.get(id),
    enabled: !!id,
  });
}

// Create initiative
export function useCreateInitiative() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => initiativesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.lists() });
    },
  });
}

// Update initiative
export function useUpdateInitiative() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }) => initiativesApi.update(id, data),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: initiativeKeys.lists() });
    },
  });
}

// Delete initiative
export function useDeleteInitiative() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => initiativesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.lists() });
    },
  });
}

// Update status
export function useUpdateInitiativeStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status }) => initiativesApi.updateStatus(id, status),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: initiativeKeys.lists() });
    },
  });
}

// Generate questions
export function useGenerateQuestions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => initiativesApi.generateQuestions(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.detail(id) });
    },
  });
}

// Generate MRD
export function useGenerateMRD() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => initiativesApi.generateMRD(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.detail(id) });
    },
  });
}

// Calculate scores
export function useCalculateScores() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => initiativesApi.calculateScores(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: initiativeKeys.detail(id) });
    },
  });
}
