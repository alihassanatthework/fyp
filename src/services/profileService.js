// src/services/profileService.js

// import apiClient from '../api/client';       // ── API disabled for local dev ──
// import { API_ENDPOINTS } from '../api/config';

// ─── Mock data ───────────────────────────────────────────────────────────────
const MOCK_PROFILE = {
  id: 1,
  full_name: 'Test User',
  email: 'test@example.com',
  health_conditions: [],
  profile_picture: null,
};

export const profileService = {
  async getProfile() {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return MOCK_PROFILE;

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.get(API_ENDPOINTS.PROFILE.GET);
    //   return response.data;
    // } catch (error) { throw error; }
  },

  async updateProfile(profileData) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return { ...MOCK_PROFILE, ...profileData };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.patch(API_ENDPOINTS.PROFILE.UPDATE, profileData);
    //   return response.data;
    // } catch (error) { throw error; }
  },

  async updateHealthProfile(healthData) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return { ...MOCK_PROFILE, health_conditions: healthData.health_conditions || [] };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const response = await apiClient.put(API_ENDPOINTS.PROFILE.HEALTH, healthData);
    //   return response.data;
    // } catch (error) { throw error; }
  },

  async uploadProfilePicture(imageFile) {
    // ── MOCK (no backend) ────────────────────────────────────────────────
    return { ...MOCK_PROFILE, profile_picture: URL.createObjectURL(imageFile) };

    // ── REAL API call (commented out) ──────────────────────────────────────
    // try {
    //   const formData = new FormData();
    //   formData.append('profile_picture', imageFile);
    //   const response = await apiClient.post(
    //     `${API_ENDPOINTS.PROFILE.UPDATE}/picture/`,
    //     formData
    //   );
    //   return response.data;
    // } catch (error) { throw error; }
  },
};
