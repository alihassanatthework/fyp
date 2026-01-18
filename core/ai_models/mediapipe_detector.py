"""
MediaPipe-based face and scalp detection module.

This module provides functionality for detecting and extracting
face and scalp regions from input images, returning 256×256 crops.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Tuple, Optional, Union


class FaceScalpDetector:
    """
    MediaPipe-based detector for face and scalp regions.
    
    Detects face/scalp regions and returns normalized 256×256 crops.
    """
    
    TARGET_SIZE = 256  # Fixed output size
    
    def __init__(self):
        """Initialize MediaPipe face mesh detector."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.3
        )
    
    def detect_and_crop_face(self, image: np.ndarray) -> np.ndarray:
        """
        Detect face region and return 256×256 crop.
        
        Args:
            image: Input image (HxWx3, BGR or RGB)
            
        Returns:
            256×256 face crop (RGB, uint8)
        """
        # Convert to RGB if needed
        if len(image.shape) == 2:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:
            # Assume BGR if from cv2.imread
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        
        h, w = rgb_image.shape[:2]
        
        # Detect face
        results = self.face_mesh.process(rgb_image)
        if not results.multi_face_landmarks:
            raise ValueError("No human face detected in image")
        
        # Get face bounding box from landmarks
        landmarks = results.multi_face_landmarks[0].landmark
        x_points = [int(pt.x * w) for pt in landmarks]
        y_points = [int(pt.y * h) for pt in landmarks]
        
        # Calculate bounding box
        x1 = max(0, min(x_points))
        y1 = max(0, min(y_points))
        x2 = min(w, max(x_points))
        y2 = min(h, max(y_points))
        
        # Crop face region
        face_crop = rgb_image[y1:y2, x1:x2]
        
        # Resize to 256×256
        face_resized = cv2.resize(face_crop, (self.TARGET_SIZE, self.TARGET_SIZE), interpolation=cv2.INTER_LINEAR)
        
        return face_resized
    
    def detect_and_crop_scalp(self, image: np.ndarray) -> np.ndarray:
        """
        Detect scalp region and return 256×256 crop.
        
        Args:
            image: Input image (HxWx3, BGR or RGB)
            
        Returns:
            256×256 scalp crop (RGB, uint8)
        """
        # Convert to RGB if needed
        if len(image.shape) == 2:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:
            # Assume BGR if from cv2.imread
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        
        h, w = rgb_image.shape[:2]
        
        # Try to detect face landmarks to locate the forehead/scalp region
        results = self.face_mesh.process(rgb_image)

        scalp_crop = None

        if results.multi_face_landmarks:
            # Use landmarks to compute forehead/scalp region
            landmarks = results.multi_face_landmarks[0].landmark
            x_points = [int(pt.x * w) for pt in landmarks]
            y_points = [int(pt.y * h) for pt in landmarks]

            # Calculate face bounding box
            face_x1 = max(0, min(x_points))
            face_y1 = max(0, min(y_points))
            face_x2 = min(w, max(x_points))
            face_y2 = min(h, max(y_points))

            # Calculate scalp region (above forehead)
            forehead_y = int(landmarks[10].y * h)
            face_height = max(1, face_y2 - face_y1)
            scalp_extension = int(face_height * 0.5)

            scalp_x1 = face_x1
            scalp_x2 = face_x2
            scalp_y2 = forehead_y
            scalp_y1 = max(0, forehead_y - scalp_extension)

            # Ensure valid coordinates
            scalp_x1 = max(0, min(scalp_x1, w - 1))
            scalp_x2 = max(1, min(scalp_x2, w))
            scalp_y1 = max(0, min(scalp_y1, h - 1))
            scalp_y2 = max(1, min(scalp_y2, h))

            scalp_crop = rgb_image[scalp_y1:scalp_y2, scalp_x1:scalp_x2]

        else:
            # No face detected — fall back to a top-center crop (best-effort scalp region)
            top_frac = 0.40  # take top 40% of image
            side_margin = 0.15  # leave 15% margin on each side
            y1 = 0
            y2 = max(1, int(h * top_frac))
            x1 = int(w * side_margin)
            x2 = max(x1 + 1, int(w * (1.0 - side_margin)))

            scalp_crop = rgb_image[y1:y2, x1:x2]

            # If that fails, try a small top-center fallback crop
            if scalp_crop.size == 0:
                min_side = min(h, w)
                cx = w // 2
                cy = max(0, h // 8)
                half = max(1, min_side // 6)
                sx1 = max(0, cx - half)
                sx2 = min(w, cx + half)
                sy1 = max(0, cy - half)
                sy2 = min(h, cy + half)
                scalp_crop = rgb_image[sy1:sy2, sx1:sx2]

        # If we still have no crop or crop is empty, consider scalp not found
        if scalp_crop is None or scalp_crop.size == 0:
            raise ValueError("No scalp region could be extracted from the image")

        # Quick heuristic to verify scalp/hair presence in the crop
        def _is_scalp_present(crop: np.ndarray) -> bool:
            try:
                gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
                h_c, w_c = gray.shape[:2]
                if h_c * w_c == 0:
                    return False

                # Edge density: hair/scalp often has higher edge texture than plain background
                edges = cv2.Canny(gray, 50, 150)
                edge_density = (edges > 0).sum() / (h_c * w_c)

                # Contrast/variance check
                variance = float(gray.var()) / 255.0

                # Heuristic thresholds (conservative)
                if edge_density > 0.005 or variance > 0.02:
                    return True
                return False
            except Exception:
                return False

        if not _is_scalp_present(scalp_crop):
            # Heuristic says no scalp/hair present — treat as not detected
            raise ValueError("Scalp not detected in image")

        # Resize to 256×256
        scalp_resized = cv2.resize(scalp_crop, (self.TARGET_SIZE, self.TARGET_SIZE), interpolation=cv2.INTER_LINEAR)

        return scalp_resized
    
    def process_and_crop(self, image_path: str, output_dir: str) -> Tuple[str, str]:
        """
        Legacy method for backward compatibility.
        Detects face and scalp, saves crops, and returns paths.
        
        Args:
            image_path: Path to input image
            output_dir: Directory to save crops
            
        Returns:
            Tuple of (face_path, scalp_path)
        """
        import os
        import uuid
        
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Error: Could not read image file.")
        
        # Get crops
        face_crop = self.detect_and_crop_face(image)
        scalp_crop = self.detect_and_crop_scalp(image)
        
        # Save crops
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        unique_id = str(uuid.uuid4())[:8]
        face_path = os.path.join(output_dir, f"face_{unique_id}.jpg")
        scalp_path = os.path.join(output_dir, f"scalp_{unique_id}.jpg")
        
        # Convert RGB to BGR for saving
        cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
        cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
        
        return face_path, scalp_path
