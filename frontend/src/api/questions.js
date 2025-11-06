/**
 * Questions and Answers API endpoints
 */
import apiClient from './client';

export const questionsApi = {
  // List questions for initiative
  list: async (initiativeId, filters = {}) => {
    const { data } = await apiClient.get(
      `/api/initiatives/${initiativeId}/questions`,
      { params: filters }
    );
    // Backend returns { questions: [], total, answered_count, p0_count, p1_count, p2_count }
    // Return just the questions array for now
    return data.questions || [];
  },

  // Get single question
  get: async (initiativeId, questionId) => {
    const { data } = await apiClient.get(
      `/api/initiatives/${initiativeId}/questions/${questionId}`
    );
    return data;
  },

  // Answer question
  answer: async (initiativeId, questionId, answerData) => {
    const { data } = await apiClient.put(
      `/api/initiatives/${initiativeId}/questions/${questionId}/answer`,
      answerData
    );
    return data;
  },

  // Get unanswered count
  getUnansweredCount: async (initiativeId) => {
    const { data } = await apiClient.get(
      `/api/initiatives/${initiativeId}/questions/unanswered/count`
    );
    return data;
  },
};
