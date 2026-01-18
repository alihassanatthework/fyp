"""
Region of Interest (ROI) extraction from segmentation masks.

This module provides functionality to convert binary segmentation masks
into precise regions of interest using OpenCV.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


def extract_roi_from_mask(
    binary_mask: np.ndarray,
    source_image: np.ndarray,
    min_region_size: int = 32,
    padding: int = 10
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Extract region of interest from binary segmentation mask.
    
    This function analyzes the binary mask, identifies the bounding box
    surrounding all positive pixels using OpenCV, and returns a tightly
    cropped region. If no affected pixels are detected, returns the full
    source image. Extremely small regions are padded to preserve context.
    
    Args:
        binary_mask: Binary mask (HxW, uint8, 0=healthy, 255=affected)
        source_image: Source image to crop from (HxWx3, uint8, RGB)
        min_region_size: Minimum size for valid region (default: 32)
        padding: Padding to add around bounding box (default: 10)
        
    Returns:
        Tuple of:
            - ROI image (cropped region, uint8, RGB)
            - Bounding box coordinates (x1, y1, x2, y2)
    """
    # Validate inputs
    if binary_mask.shape[:2] != source_image.shape[:2]:
        raise ValueError(
            f"Mask shape {binary_mask.shape[:2]} must match image shape {source_image.shape[:2]}"
        )
    
    # Find contours of positive pixels
    contours, _ = cv2.findContours(
        binary_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    # If no contours found, return full image
    if len(contours) == 0:
        return source_image.copy(), (0, 0, source_image.shape[1], source_image.shape[0])
    
    # Find bounding box of all contours
    all_points = np.concatenate(contours, axis=0).squeeze()
    x_coords = all_points[:, 0]
    y_coords = all_points[:, 1]
    
    x1 = int(np.min(x_coords))
    y1 = int(np.min(y_coords))
    x2 = int(np.max(x_coords))
    y2 = int(np.max(y_coords))
    
    # Add padding
    h, w = source_image.shape[:2]
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(w, x2 + padding)
    y2 = min(h, y2 + padding)
    
    # Check if region is too small
    region_width = x2 - x1
    region_height = y2 - y1
    
    if region_width < min_region_size or region_height < min_region_size:
        # If region is too small, return full image to preserve context
        return source_image.copy(), (0, 0, w, h)
    
    # Extract ROI
    roi = source_image[y1:y2, x1:x2].copy()
    
    return roi, (x1, y1, x2, y2)
