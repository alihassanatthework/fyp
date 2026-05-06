// src/hooks/useCamera.js
// Custom hook for camera operations

import { useState, useRef } from 'react';

export const useCamera = () => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [error, setError] = useState(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  /**
   * Open device camera
   * @returns {Promise<object>} { success, error }
   */
  const openCamera = async () => {
    try {
      setError(null);

      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' }, // Use front camera
        audio: false,
      });

      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      setIsCameraOpen(true);
      return { success: true };
    } catch (err) {
      const errorMessage = 
        err.name === 'NotAllowedError' 
          ? 'Camera access denied. Please allow camera access in your browser settings.'
          : err.name === 'NotFoundError'
          ? 'No camera found on this device.'
          : 'Failed to access camera. Please try again.';
      
      setError(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  /**
   * Close camera and stop stream
   */
  const closeCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraOpen(false);
  };

  /**
   * Capture photo from video stream
   * @returns {string|null} Base64 image data URL
   */
  const capturePhoto = () => {
    if (!videoRef.current) return null;

    try {
      // Create canvas to capture frame
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;

      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0);

      // Convert to blob and create file
      canvas.toBlob((blob) => {
        const file = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
        setCapturedImage(file);
      }, 'image/jpeg');

      // Close camera after capture
      closeCamera();

      // Return base64 data URL
      return canvas.toDataURL('image/jpeg');
    } catch (err) {
      setError('Failed to capture photo. Please try again.');
      return null;
    }
  };

  /**
   * Simple file input method (mobile-friendly alternative)
   * Opens native camera app on mobile
   * @param {Function} onCapture - Callback with captured file
   */
  const openNativeCamera = (onCapture) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'user'; // Opens camera on mobile

    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        setCapturedImage(file);
        if (onCapture) onCapture(file);
      }
    };

    input.click();
  };

  /**
   * Clear captured image
   */
  const clearCapturedImage = () => {
    setCapturedImage(null);
    setError(null);
  };

  /**
   * Check if camera is available
   * @returns {Promise<boolean>}
   */
  const checkCameraAvailability = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.some(device => device.kind === 'videoinput');
    } catch {
      return false;
    }
  };

  return {
    isCameraOpen,
    error,
    capturedImage,
    videoRef,
    openCamera,
    closeCamera,
    capturePhoto,
    openNativeCamera,
    clearCapturedImage,
    checkCameraAvailability,
  };
};
