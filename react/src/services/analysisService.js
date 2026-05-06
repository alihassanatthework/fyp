// src/services/analysisService.js
// Analysis API calls

import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export const analysisService = {
  /**
   * Upload image for analysis
   * @param {File} imageFile - The image file to upload
   * @param {string} analysisType - 'skin' or 'scalp'
   * @returns {Promise<object>} Analysis result
   */
  uploadImage: async (imageFile, analysisType) => {
  try {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('analysis_type', analysisType);

    const response = await apiClient.post(
      API_ENDPOINTS.ANALYSIS.UPLOAD,
      formData,
      {
        headers: {
          'Accept': 'application/json',
        },
      }
    );

    return response.data;
  } catch (error) {
    throw error;
  }
},

  /**
   * Get analysis history
   * @param {object} filters - Optional filters { type, severity, startDate, endDate }
   * @returns {Promise<Array>} List of past analyses
   */
  async getHistory(filters = {}) {
    try {
      const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.HISTORY, {
        params: filters,
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Get single analysis detail by ID
   * @param {string} id - Analysis ID
   * @returns {Promise<object>} Analysis details
   */
  async getAnalysisById(id) {
    try {
      const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.DETAIL(id));
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Delete analysis
   * @param {string} id - Analysis ID
   * @returns {Promise<object>} Delete confirmation
   */
  async deleteAnalysis(id) {
    try {
      const response = await apiClient.delete(API_ENDPOINTS.ANALYSIS.DETAIL(id));
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};
