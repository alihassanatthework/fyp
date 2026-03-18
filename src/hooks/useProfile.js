// src/hooks/useProfile.js
// Custom hook for profile operations

import { useState } from 'react';
import { profileService } from '../services/profileService';

export const useProfile = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(null);

  /**
   * Get user profile
   * @returns {Promise<object>} { success, data, error }
   */
  const getProfile = async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await profileService.getProfile();
      setProfile(data);

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update user profile
   * @param {object} profileData - Profile data to update
   * @returns {Promise<object>} { success, data, error }
   */
  const updateProfile = async (profileData) => {
    try {
      setLoading(true);
      setError(null);

      const data = await profileService.updateProfile(profileData);
      setProfile(data);

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update health profile
   * @param {object} healthData - Health data to update
   * @returns {Promise<object>} { success, data, error }
   */
  const updateHealthProfile = async (healthData) => {
    try {
      setLoading(true);
      setError(null);

      const data = await profileService.updateHealthProfile(healthData);
      setProfile({ ...profile, healthProfile: data });

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Upload profile picture
   * @param {File} imageFile - Profile image
   * @returns {Promise<object>} { success, data, error }
   */
  const uploadProfilePicture = async (imageFile) => {
    try {
      setLoading(true);
      setError(null);

      const data = await profileService.uploadProfilePicture(imageFile);
      setProfile(data);

      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  /**
   * Clear profile data
   */
  const clearProfile = () => {
    setProfile(null);
    setError(null);
  };

  return {
    loading,
    error,
    profile,
    getProfile,
    updateProfile,
    updateHealthProfile,
    uploadProfilePicture,
    clearProfile,
  };
};
