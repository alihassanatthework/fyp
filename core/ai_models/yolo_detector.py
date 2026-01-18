"""
YOLOv8-based condition detection module for scalp analysis.

This module provides functionality for detecting scalp conditions
using YOLOv8 architecture, returning bounding boxes and confidence scores.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from ultralytics import YOLO


class YOLODetector:
    """
    YOLOv8 detector for scalp condition detection.
    
    Attributes:
        model: Loaded YOLOv8 model
        scalp_classes: List of scalp condition classes
    """
    
    SCALP_CONDITIONS = [
        'dandruff',
        'hair_fall'
    ]
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the YOLOv8 detector.
        
        Args:
            model_path: Path to pre-trained YOLOv8 model weights (.pt file)
        """
        try:
            if model_path:
                self.model = YOLO(model_path)
            else:
                # Initialize with default YOLOv8n if no path provided
                # In production, this should always have a model_path
                self.model = YOLO('yolov8n.pt')
            print(f"✅ YOLOv8 model initialized")
        except Exception as e:
            print(f"⚠️ YOLOv8 initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self._init_failed = True
    
    def detect(self, roi_image: np.ndarray, conf_threshold: float = 0.25) -> List[Dict]:
        """
        Detect scalp conditions in ROI.
        
        Args:
            roi_image: ROI image (any size)
            conf_threshold: Confidence threshold for detections
            
        Returns:
            List of detection dictionaries, each containing:
                - 'condition': Condition name
                - 'confidence': Confidence score
                - 'bbox': Bounding box coordinates (x1, y1, x2, y2)
        """
        # If model failed to initialize, return empty detections
        if self.model is None or hasattr(self, '_init_failed'):
            print("⚠️ YOLOv8 model not available, returning empty detections")
            return []
        
        try:
            # Run inference
            results = self.model(roi_image, conf=conf_threshold, verbose=False)
        except Exception as e:
            # THIS WAS MISSING: Catch errors during inference so the server doesn't crash
            print(f"⚠️ Inference failed: {e}")
            return []
        
        # Parse results
        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                # Get box coordinates
                box = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = box.astype(int)
                
                # Get confidence
                confidence = float(boxes.conf[i].cpu().numpy())
                
                # Get class (map to condition name)
                class_id = int(boxes.cls[i].cpu().numpy())
                # Safety check for class_id range
                if class_id < len(self.SCALP_CONDITIONS):
                    condition = self.SCALP_CONDITIONS[class_id] 
                else:
                    condition = 'unknown'
                
                detections.append({
                    'condition': condition,
                    'confidence': confidence,
                    'bbox': (x1, y1, x2, y2)
                })
        
        return detections