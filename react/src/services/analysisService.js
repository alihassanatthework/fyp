// src/services/analysisService.js
// Real wiring to the Django AI-analysis backend.
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export const analysisService = {
  /**
   * Upload an image to the AI pipeline.
   * @param {File}   imageFile
   * @param {string} analysisType  'skin' | 'scalp'
   * @returns {Promise<object>}    Pipeline result with conditions, severity,
   *                               recommendations, image URLs, charts, etc.
   */
  uploadImage: async (imageFile, analysisType) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('analysis_type', analysisType);

    const response = await apiClient.post(
      API_ENDPOINTS.ANALYSIS.UPLOAD,
      formData,
      {
        // axios sets multipart boundary automatically when you pass FormData
        headers: { 'Accept': 'application/json' },
        // Pipeline can take 30+ seconds (Ollama call). Allow a generous timeout.
        timeout: 180000,
      }
    );
    // Backend returns either the context dict directly or { success, data }
    return response.data?.data || response.data;
  },

  /**
   * Get the authenticated user's past analyses.
   */
  async getHistory(filters = {}) {
    const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.HISTORY, { params: filters });
    return response.data?.results || response.data || [];
  },

  /**
   * Get one analysis by ID (full pipeline payload).
   */
  async getAnalysisById(id) {
    const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.DETAIL(id));
    return response.data?.data || response.data;
  },

  /**
   * Delete an analysis record.
   */
  async deleteAnalysis(id) {
    const response = await apiClient.delete(API_ENDPOINTS.ANALYSIS.DETAIL(id));
    return response.data;
  },

  /**
   * Aggregate stats for the History/Home dashboard.
   */
  async getStats() {
    const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.STATS);
    return response.data;
  },
};
