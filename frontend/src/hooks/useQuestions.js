import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { questionsApi } from '../api/questions';
import { initiativeKeys } from './useInitiatives';

// Query keys
export const questionKeys = {
  all: ['questions'],
  lists: () => [...questionKeys.all, 'list'],
  list: (initiativeId, filters) => [...questionKeys.lists(), initiativeId, filters],
  details: () => [...questionKeys.all, 'detail'],
  detail: (initiativeId, questionId) => [...questionKeys.details(), initiativeId, questionId],
  unansweredCount: (initiativeId) => [...questionKeys.all, 'unanswered', initiativeId],
};

// Fetch questions for initiative
export function useQuestions(initiativeId, filters = {}) {
  return useQuery({
    queryKey: questionKeys.list(initiativeId, filters),
    queryFn: () => questionsApi.list(initiativeId, filters),
    enabled: !!initiativeId,
  });
}

// Fetch single question
export function useQuestion(initiativeId, questionId) {
  return useQuery({
    queryKey: questionKeys.detail(initiativeId, questionId),
    queryFn: () => questionsApi.get(initiativeId, questionId),
    enabled: !!initiativeId && !!questionId,
  });
}

// Answer question
export function useAnswerQuestion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ initiativeId, questionId, answerData }) =>
      questionsApi.answer(initiativeId, questionId, answerData),
    onSuccess: (data, variables) => {
      // Invalidate question lists
      queryClient.invalidateQueries({
        queryKey: questionKeys.lists()
      });
      // Invalidate specific question
      queryClient.invalidateQueries({
        queryKey: questionKeys.detail(variables.initiativeId, variables.questionId)
      });
      // Invalidate unanswered count
      queryClient.invalidateQueries({
        queryKey: questionKeys.unansweredCount(variables.initiativeId)
      });
      // Invalidate initiative details (affects readiness)
      queryClient.invalidateQueries({
        queryKey: initiativeKeys.detail(variables.initiativeId)
      });
    },
  });
}

// Get unanswered count
export function useUnansweredCount(initiativeId) {
  return useQuery({
    queryKey: questionKeys.unansweredCount(initiativeId),
    queryFn: () => questionsApi.getUnansweredCount(initiativeId),
    enabled: !!initiativeId,
  });
}
