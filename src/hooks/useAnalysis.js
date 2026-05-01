// src/hooks/useAnalysis.js
// Custom hook for analysis operations

import { useState } from 'react';
import { analysisService } from '../services/analysisService';

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  /**
   * Upload image for analysis
   * @param {File} imageFile - Image file
   * @param {string} analysisType - 'skin' or 'scalp'
   * @returns {Promise<object>} { success, data, error }
   */
  const uploadImage = async (imageFile, analysisType) => {
    try {
      setLoading(true);
      setError(null);

      const data = await analysisService.uploadImage(imageFile, analysisType);
      setResult(data);

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Get analysis history
   * @param {object} filters - Optional filters
   * @returns {Promise<object>} { success, data, error }
   */
  const getHistory = async (filters) => {
    try {
      setLoading(true);
      setError(null);

      const data = await analysisService.getHistory(filters);
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Get analysis by ID
   * @param {string} id - Analysis ID
   * @returns {Promise<object>} { success, data, error }
   */
  const getAnalysisById = async (id) => {
    try {
      setLoading(true);
      setError(null);

      const data = await analysisService.getAnalysisById(id);
      setResult(data);

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Delete analysis
   * @param {string} id - Analysis ID
   * @returns {Promise<object>} { success, error }
   */
  const deleteAnalysis = async (id) => {
    try {
      setLoading(true);
      setError(null);

      await analysisService.deleteAnalysis(id);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Clear current result
   */
  const clearResult = () => {
    setResult(null);
    setError(null);
  };

  return {
    loading,
    error,
    result,
    uploadImage,
    getHistory,
    getAnalysisById,
    deleteAnalysis,
    clearResult,
  };
};
