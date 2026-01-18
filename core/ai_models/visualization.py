"""
Visualization utilities for AI pipeline results.

This module provides functions to visualize detected conditions,
segmentation masks, and bounding boxes on images.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional


def visualize_skin_conditions(
    original_image: np.ndarray,
    normalized_crop: np.ndarray,
    segmentation_mask: np.ndarray,
    roi_bbox: Tuple[int, int, int, int],
    detected_conditions: List[Dict],
    severity_scores: Dict[str, Dict]
) -> np.ndarray:
    """
    Visualize detected skin conditions on the image.
    
    Args:
        original_image: Original input image
        normalized_crop: 256×256 normalized crop from MediaPipe
        segmentation_mask: Binary segmentation mask (256×256)
        roi_bbox: Bounding box of ROI (x1, y1, x2, y2) in normalized crop coordinates
        detected_conditions: List of detected conditions
        severity_scores: Dictionary of severity scores
        
    Returns:
        Visualized image with overlays
    """
    # Create a copy of the normalized crop for visualization
    vis_image = normalized_crop.copy()
    
    # Convert mask to 3-channel for overlay
    mask_colored = cv2.applyColorMap(segmentation_mask, cv2.COLORMAP_JET)
    
    # Overlay segmentation mask with transparency
    alpha = 0.4
    vis_image = cv2.addWeighted(vis_image, 1 - alpha, mask_colored, alpha, 0)
    
    # Draw ROI bounding box
    x1, y1, x2, y2 = roi_bbox
    cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Draw condition labels on ROI
    y_offset = 20
    for i, condition in enumerate(detected_conditions):
        if condition['name'] == 'normal':
            continue
            
        name = condition['name'].replace('_', ' ').title()
        severity_info = severity_scores.get(condition['name'], {})
        score = severity_info.get('score', 0)
        level = severity_info.get('level', 'Mild')
        
        # Color based on severity
        if score >= 70:
            color = (0, 0, 255)  # Red for severe
        elif score >= 30:
            color = (0, 165, 255)  # Orange for moderate
        else:
            color = (0, 255, 0)  # Green for mild
        
        # Draw label
        label = f"{name}: {level} ({score}%)"
        cv2.putText(
            vis_image,
            label,
            (x1, y1 - y_offset - (i * 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )
    
    return vis_image


def visualize_scalp_conditions(
    original_image: np.ndarray,
    normalized_crop: np.ndarray,
    segmentation_mask: np.ndarray,
    roi_bbox: Tuple[int, int, int, int],
    detected_conditions: List[Dict],
    severity_scores: Dict[str, Dict]
) -> np.ndarray:
    """
    Visualize detected scalp conditions on the image.
    
    Args:
        original_image: Original input image
        normalized_crop: 256×256 normalized crop from MediaPipe
        segmentation_mask: Binary segmentation mask (256×256)
        roi_bbox: Bounding box of ROI (x1, y1, x2, y2) in normalized crop coordinates
        detected_conditions: List of detected conditions with bounding boxes
        severity_scores: Dictionary of severity scores
        
    Returns:
        Visualized image with overlays
    """
    # Create a copy of the normalized crop for visualization
    vis_image = normalized_crop.copy()
    
    # Convert mask to 3-channel for overlay
    mask_colored = cv2.applyColorMap(segmentation_mask, cv2.COLORMAP_JET)
    
    # Overlay segmentation mask with transparency
    alpha = 0.4
    vis_image = cv2.addWeighted(vis_image, 1 - alpha, mask_colored, alpha, 0)
    
    # Draw ROI bounding box
    x1, y1, x2, y2 = roi_bbox
    cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Draw detection bounding boxes and labels
    for i, condition in enumerate(detected_conditions):
        if condition['name'] == 'normal':
            continue
        
        # Get bounding box from detection (if available)
        if 'bbox' in condition and condition['bbox'] is not None:
            bbox = condition['bbox']
            # Adjust bbox coordinates relative to ROI
            det_x1 = x1 + bbox[0]
            det_y1 = y1 + bbox[1]
            det_x2 = x1 + bbox[2]
            det_y2 = y1 + bbox[3]
            
            # Draw detection bounding box
            severity_info = severity_scores.get(condition['name'], {})
            score = severity_info.get('score', 0)
            
            if score >= 70:
                color = (0, 0, 255)  # Red
            elif score >= 30:
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 255, 0)  # Green
            
            cv2.rectangle(vis_image, (det_x1, det_y1), (det_x2, det_y2), color, 2)
            
            # Draw label
            name = condition['name'].replace('_', ' ').title()
            level = severity_info.get('level', 'Mild')
            label = f"{name}: {level} ({score}%)"
            
            cv2.putText(
                vis_image,
                label,
                (det_x1, det_y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )
    
    return vis_image


def create_comparison_view(
    original_crop: np.ndarray,
    segmentation_mask: np.ndarray,
    visualized_image: np.ndarray
) -> np.ndarray:
    """
    Create a side-by-side comparison view.
    
    Args:
        original_crop: Original 256×256 crop
        segmentation_mask: Binary segmentation mask
        visualized_image: Image with visualizations
        
    Returns:
        Combined comparison image
    """
    # Resize all to same size if needed
    h, w = original_crop.shape[:2]
    
    # Convert mask to 3-channel for display
    mask_display = cv2.cvtColor(segmentation_mask, cv2.COLOR_GRAY2RGB)
    
    # Create side-by-side view
    comparison = np.hstack([original_crop, mask_display, visualized_image])
    
    return comparison


def visualize_efficientnet_scores(
    roi_image: np.ndarray,
    scores: dict,
    width: int = 380,
    height: int = 380
) -> np.ndarray:
    """
    Create a visualization for EfficientNet classification scores.

    Draws top class labels with horizontal bars on a white canvas alongside the ROI.
    """
    # Prepare canvas
    try:
        canvas = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Resize ROI to fit left half of canvas
        roi_h = height
        roi_w = int(width * 0.45)
        roi_resized = cv2.resize(roi_image, (roi_w, roi_h), interpolation=cv2.INTER_LINEAR)
        canvas[:, :roi_w] = roi_resized

        # Prepare bar area on right
        bar_x = roi_w + 10
        bar_width = width - roi_w - 20
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Draw title
        cv2.putText(canvas, 'EfficientNet - Scores', (bar_x, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)

        # Draw top labels with bars
        y = 70
        for name, score in sorted_scores:
            label = name.replace('_', ' ').title()
            percent = int(score * 100)

            # Draw label
            cv2.putText(canvas, f"{label}", (bar_x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 1)

            # Draw bar background
            y_bar = y + 6
            cv2.rectangle(canvas, (bar_x, y_bar), (bar_x + bar_width, y_bar + 18), (230,230,230), -1)

            # Draw filled portion
            filled_w = int(bar_width * (score if score >= 0 else 0))
            cv2.rectangle(canvas, (bar_x, y_bar), (bar_x + filled_w, y_bar + 18), (70,130,180), -1)

            # Draw percent text
            cv2.putText(canvas, f"{percent}%", (bar_x + bar_width - 50, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)

            y += 36

        return canvas
    except Exception as e:
        print(f"⚠️ Failed to create EfficientNet visualization: {e}")
        return roi_image


def visualize_yolo_detections(
    roi_image: np.ndarray,
    detections: list
) -> np.ndarray:
    """
    Draw YOLO detections (bounding boxes + labels) on the ROI image and return it.
    """
    vis = roi_image.copy()
    try:
        for det in detections:
            bbox = det.get('bbox')
            confidence = det.get('confidence', 0)
            name = det.get('condition', 'unknown').replace('_', ' ').title()

            if bbox is None:
                continue

            x1, y1, x2, y2 = bbox
            color = (0, 165, 255) if confidence >= 0.3 else (200, 200, 200)
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            label = f"{name} {int(confidence*100)}%"
            cv2.putText(vis, label, (x1, max(10, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return vis
    except Exception as e:
        print(f"⚠️ Failed to draw YOLO detections: {e}")
        return roi_image
