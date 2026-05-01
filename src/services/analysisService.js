// src/services/analysisService.js

// import apiClient from '../api/client';       // ── API disabled for local dev ──
// import { API_ENDPOINTS } from '../api/config';

// ─── Mock data ───────────────────────────────────────────────────────────────
const MOCK_ANALYSIS = {
  analysis_id: '1',
  analysis_type: 'skin',
  conditions: [
    { name: 'Acne',         severity_level: 'Mild',     severity_score: 28 },
    { name: 'Redness',      severity_level: 'Mild',     severity_score: 18 },
    { name: 'Dryness',      severity_level: 'Mild',     severity_score: 22 },
  ],
  recommendations: [
    'Use a gentle, non-comedogenic cleanser twice daily.',
    'Apply broad-spectrum SPF 30+ each morning.',
    'Introduce a salicylic-acid spot treatment if breakouts persist.',
    'Re-scan in 4–6 weeks to track progress.',
  ],
  original_image: '',
  visualized_image: '',
};

const MOCK_HISTORY = [
  { ...MOCK_ANALYSIS, analysis_id: '1', date: '12 Mar 2025 · 09:24 AM' },
  { ...MOCK_ANALYSIS, analysis_id: '2', analysis_type: 'scalp', date: '03 Mar 2025 · 06:15 PM' },
];

export const analysisService = {
  // ── uploadImage ──────────────────────────────────────────────────────────
  uploadImage: async (imageFile, analysisType) => {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    await new Promise((r) => setTimeout(r, 1000));
    return {
      ...MOCK_ANALYSIS,
      analysis_type: analysisType,
      analysis_id: String(Date.now()),
    };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const formData = new FormData();
    //   formData.append('image', imageFile);
    //   formData.append('analysis_type', analysisType);
    //   const response = await apiClient.post(
    //     API_ENDPOINTS.ANALYSIS.UPLOAD,
    //     formData,
    //     { headers: { 'Accept': 'application/json' } }
    //   );
    //   return response.data;
    // } catch (error) {
    //   throw error;
    // }
  },

  // ── getHistory ───────────────────────────────────────────────────────────
  async getHistory(filters = {}) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return MOCK_HISTORY;

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.HISTORY, { params: filters });
    //   return response.data;
    // } catch (error) {
    //   throw error;
    // }
  },

  // ── getAnalysisById ──────────────────────────────────────────────────────
  async getAnalysisById(id) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return MOCK_HISTORY.find((a) => a.analysis_id === id) || { ...MOCK_ANALYSIS, analysis_id: id };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.get(API_ENDPOINTS.ANALYSIS.DETAIL(id));
    //   return response.data;
    // } catch (error) {
    //   throw error;
    // }
  },

  // ── deleteAnalysis ───────────────────────────────────────────────────────
  async deleteAnalysis(id) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return { success: true };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.delete(API_ENDPOINTS.ANALYSIS.DETAIL(id));
    //   return response.data;
    // } catch (error) {
    //   throw error;
    // }
  },
};
