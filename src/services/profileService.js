// src/services/profileService.js
// Profile API calls

import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';

export const profileService = {
  /**
   * Get user profile
   * @returns {Promise<object>} User profile data
   */
  async getProfile() {
    try {
      const response = await apiClient.get(API_ENDPOINTS.PROFILE.GET);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update user profile
   * @param {object} profileData - Profile data to update
   * @returns {Promise<object>} Updated profile
   */
  async updateProfile(profileData) {
    try {
      const response = await apiClient.put(
        API_ENDPOINTS.PROFILE.UPDATE,
        profileData
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Update health profile
   * @param {object} healthData - Health profile data
   * @returns {Promise<object>} Updated health profile
   */
  async updateHealthProfile(healthData) {
    try {
      const response = await apiClient.put(
        API_ENDPOINTS.PROFILE.HEALTH,
        healthData
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  /**
   * Upload profile picture
   * @param {File} imageFile - Profile image file
   * @returns {Promise<object>} Updated profile with new image URL
   */
  async uploadProfilePicture(imageFile) {
    try {
      const formData = new FormData();
      formData.append('profile_picture', imageFile);

      const response = await apiClient.post(
        `${API_ENDPOINTS.PROFILE.UPDATE}/picture/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};
