/**
 * Initiative API endpoints
 */
import apiClient from './client';

export const initiativesApi = {
  // List all initiatives
  list: async (filters = {}) => {
    const { data } = await apiClient.get('/api/initiatives', { params: filters });
    // Backend returns { initiatives: [], total, limit, offset }
    // Return just the initiatives array for now
    return data.initiatives || [];
  },

  // Get single initiative
  get: async (id) => {
    const { data } = await apiClient.get(`/api/initiatives/${id}`);
    return data;
  },

  // Create new initiative
  create: async (initiativeData) => {
    const { data } = await apiClient.post('/api/initiatives', initiativeData);
    return data;
  },

  // Update initiative
  update: async (id, initiativeData) => {
    const { data } = await apiClient.patch(`/api/initiatives/${id}`, initiativeData);
    return data;
  },

  // Delete initiative
  delete: async (id) => {
    await apiClient.delete(`/api/initiatives/${id}`);
  },

  // Update status
  updateStatus: async (id, status) => {
    const { data } = await apiClient.put(`/api/initiatives/${id}/status`, { status });
    return data;
  },

  // Search initiatives
  search: async (searchTerm) => {
    const { data } = await apiClient.get(`/api/initiatives/search/${searchTerm}`);
    return data;
  },

  // Generate questions
  generateQuestions: async (id) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/generate-questions`);
    return data;
  },

  // Regenerate questions
  regenerateQuestions: async (id, keepUnanswered = false) => {
    const { data } = await apiClient.post(
      `/api/agents/initiatives/${id}/regenerate-questions`,
      null,
      { params: { keep_unanswered: keepUnanswered } }
    );
    return data;
  },

  // Generate MRD
  generateMRD: async (id) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/generate-mrd`);
    return data;
  },

  // Get MRD
  getMRD: async (id) => {
    const { data } = await apiClient.get(`/api/agents/initiatives/${id}/mrd`);
    return data;
  },

  // Get MRD content (for export)
  getMRDContent: async (id) => {
    const { data } = await apiClient.get(`/api/agents/initiatives/${id}/mrd/content`);
    return data;
  },

  // Calculate scores
  calculateScores: async (id) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/calculate-scores`);
    return data;
  },

  // Get scores
  getScores: async (id) => {
    const { data } = await apiClient.get(`/api/agents/initiatives/${id}/scores`);
    return data;
  },

  // Export scores as PDF
  exportScoresPdf: async (id) => {
    const { data } = await apiClient.get(`/api/agents/initiatives/${id}/scores/pdf`, {
      responseType: 'blob',
    });
    return data;
  },

  // Get evaluation
  getEvaluation: async (id) => {
    const { data } = await apiClient.get(`/api/agents/initiatives/${id}/evaluate-readiness`);
    return data;
  },

  // Recalculate quality score
  recalculateQuality: async (id) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/recalculate-quality`);
    return data;
  },

  // Analyze scoring gaps
  analyzeScoringGaps: async (id) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/analyze-scoring-gaps`);
    return data;
  },

  // Answer gap question with estimation
  answerGapQuestion: async (id, questionId, answerText, estimationConfidence) => {
    const { data } = await apiClient.post(`/api/agents/initiatives/${id}/answer-gap-question`, {
      question_id: questionId,
      answer_text: answerText,
      estimation_confidence: estimationConfidence,
    });
    return data;
  },
};
