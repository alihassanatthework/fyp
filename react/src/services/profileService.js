// src/services/profileService.js
// Wired to /api/profile/ which returns and accepts a combined object:
//   { user, profile, medical_history }
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export const profileService = {
  /**
   * Fetch the full profile bundle.
   * Returns { user, profile, medical_history }.
   */
  async getProfile() {
    const response = await apiClient.get(API_ENDPOINTS.PROFILE.GET);
    return response.data;
  },

  /**
   * Update the user, profile, or medical_history.
   * Send any subset of {user, profile, medical_history}. Each sub-object
   * is PATCHed (partial update) on the backend.
   */
  async updateProfile(profileData) {
    const response = await apiClient.patch(API_ENDPOINTS.PROFILE.UPDATE, profileData);
    return response.data;
  },

  /**
   * Convenience wrapper for editing only the medical_history block.
   */
  async updateHealthProfile(medicalHistory) {
    const response = await apiClient.patch(
      API_ENDPOINTS.PROFILE.UPDATE,
      { medical_history: medicalHistory }
    );
    return response.data;
  },

  /**
   * Profile picture is not supported by the backend yet. Stub kept so
   * existing UI code does not crash. Returns the local object URL so the
   * user still sees an immediate preview; the upload is a no-op until the
   * backend adds a profile_picture field on UserProfile.
   */
  async uploadProfilePicture(imageFile) {
    // TODO: backend endpoint not implemented yet.
    return { profile_picture: URL.createObjectURL(imageFile), _unsynced: true };
  },
};
