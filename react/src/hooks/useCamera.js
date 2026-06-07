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
    setError(null);

    // ── HTTPS guard. mediaDevices is undefined on insecure origins
    // (http://) on every modern mobile browser — without this guard,
    // accessing .getUserMedia throws an uncaught TypeError.
    const hasSecureContext =
      typeof window !== 'undefined' ? window.isSecureContext !== false : true;
    const hasApi =
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === 'function';
    if (!hasSecureContext || !hasApi) {
      const msg = 'Camera requires HTTPS or localhost. Please upload a photo instead.';
      setError(msg);
      return { success: false, error: msg };
    }

    try {
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
      const map = {
        NotAllowedError:      'Camera access denied. Please allow camera access in your browser settings.',
        NotFoundError:        'No camera found on this device.',
        NotReadableError:     'Camera is in use by another app. Close it and retry.',
        OverconstrainedError: 'Camera does not support the requested settings.',
        SecurityError:        'Camera requires HTTPS or localhost.',
        AbortError:           'Camera start was interrupted. Please retry.',
      };
      const errorMessage = map[err?.name] || `Failed to access camera: ${err?.message || 'unknown error'}.`;
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
