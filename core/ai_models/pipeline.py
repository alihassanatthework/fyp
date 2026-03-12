"""
AI Processing Pipeline - Production-Ready Implementation.

This module orchestrates the complete AI analysis pipeline with deterministic
processing flow, singleton pattern for model loading, and production-safe design.

Pipeline Flow:
1. MediaPipe detection → 256×256 crop
2. U-Net segmentation → binary mask
3. ROI extraction from mask
4. Task-specific classification (EfficientNet for skin, YOLOv8 for scalp)
"""

import numpy as np
import cv2
from typing import Dict, List, Optional, Union, Tuple
import threading

from .mediapipe_detector import FaceScalpDetector
from .unet_segmenter import UNetSegmenter
from .roi_extractor import extract_roi_from_mask
from .efficientnet_classifier import EfficientNetClassifier
from .yolo_detector import YOLODetector
from .xgboost_severity import XGBoostSeverityClassifier
from .llm_recommender import LLMRecommender


class AIAnalysisPipeline:
    """
    Complete AI analysis pipeline orchestrator with singleton pattern.
    
    This class coordinates all AI models to perform end-to-end analysis
    following a deterministic processing flow. Models are loaded once
    and reused across all requests.
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, model_configs: Optional[Dict] = None):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIAnalysisPipeline, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, model_configs: Optional[Dict] = None):
        """
        Initialize the AI pipeline with all models (singleton pattern).
        
        Args:
            model_configs: Dictionary of model configurations:
                - 'unet_path': Path to U-Net model weights
                - 'efficientnet_path': Path to EfficientNet model weights
                - 'yolo_path': Path to YOLOv8 model weights
                - 'device': Device for inference ('cuda' or 'cpu')
        """
        # Prevent re-initialization in singleton pattern
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            # Default configurations
            if model_configs is None:
                model_configs = {}
            
            self.device = model_configs.get('device', 'cpu')
            
            # Initialize all models (loaded once, reused)
            self.detector = FaceScalpDetector()
            self.unet = UNetSegmenter(
                model_path=model_configs.get('unet_path'),
                device=self.device
            )
            self.efficientnet = EfficientNetClassifier(
                model_path=model_configs.get('efficientnet_path'),
                device=self.device
            )
            self.yolo = YOLODetector(
                model_path=model_configs.get('yolo_path')
            )
            self.xgboost_severity = XGBoostSeverityClassifier(
            model_path=model_configs.get('xgboost_path')
            )
            self.llm_recommender = LLMRecommender(
                model_path=model_configs.get('llm_path'),
                api_key=model_configs.get('llm_api_key'),
                use_api=model_configs.get('llm_use_api', False)
            )
            
            self._initialized = True
    
    def process_image(
        self,
        image: Union[np.ndarray, str],
        analysis_type: str = 'skin'
    ) -> Dict:
        """
        Process image through complete AI pipeline.
        
        This is the main entry point for image analysis. It follows a
        deterministic processing flow:
        1. MediaPipe detection → 256×256 crop
        2. U-Net segmentation → binary mask
        3. ROI extraction from mask
        4. Task-specific classification
        
        Args:
            image: Input image (numpy array or path to image file)
            analysis_type: 'skin' or 'scalp'
            
        Returns:
            Dictionary containing:
                - 'analysis_type': Type of analysis performed
                - 'detected_conditions': List of detected conditions
                - 'severity_scores': Severity scores for each condition
                - 'roi_bbox': Bounding box of extracted ROI
                - 'segmentation_mask': Binary segmentation mask
                - 'processing_metadata': Additional metadata
        """
        # Load image if path provided
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                raise ValueError(f"Failed to load image from {image}")
        
        # Validate analysis type
        if analysis_type not in ['skin', 'scalp']:
            raise ValueError(f"analysis_type must be 'skin' or 'scalp', got '{analysis_type}'")
        
        # Step 1: use provided image directly if already cropped/resized by the caller.
        # views.py now passes face/scalp crop when available, otherwise a skin fallback crop.
        normalized_crop = image

        # If caller passed BGR/RGB image with unexpected size, normalize it here.
        if not isinstance(normalized_crop, np.ndarray):
            raise ValueError("Input image must be a numpy array after loading")

        if normalized_crop.ndim != 3 or normalized_crop.shape[2] != 3:
            raise ValueError(f"Expected HxWx3 image, got {normalized_crop.shape}")

        if normalized_crop.shape[:2] != (256, 256):
            normalized_crop = cv2.resize(normalized_crop, (256, 256), interpolation=cv2.INTER_LINEAR)

        normalized_crop = normalized_crop.astype(np.uint8)
        
        # Step 2: U-Net segmentation → binary mask
        try:
            binary_mask = self.unet.segment(normalized_crop)
            
            # Validate mask
            if binary_mask.shape != (256, 256):
                raise ValueError(
                    f"Segmentation mask must be 256×256, got {binary_mask.shape}"
                )
        except Exception as e:
            # Fallback: create empty mask if U-Net fails
            print(f"⚠️ U-Net segmentation failed: {e}, using empty mask")
            binary_mask = np.zeros((256, 256), dtype=np.uint8)
        
        # Step 3: ROI extraction from mask
        roi_image, roi_bbox = extract_roi_from_mask(
            binary_mask,
            normalized_crop,
            min_region_size=32,
            padding=10
        )
        
        # Step 4: Task-specific classification
        try:
            if analysis_type == 'skin':

                # Apply segmentation mask before classification
                if binary_mask is not None:

                    mask = (binary_mask > 0).astype("uint8")
                    mask = cv2.resize(mask, (roi_image.shape[1], roi_image.shape[0]))

                    masked_roi = roi_image.copy()
                    masked_roi[mask == 0] = 0

                    roi_for_classification = masked_roi

                else:
                    roi_for_classification = roi_image

                # EfficientNet classification
                condition_scores = self.efficientnet.classify(roi_for_classification)

                raw_scores = condition_scores
                detected_conditions = self._process_skin_conditions(condition_scores)
            else:
                # YOLOv8 detection (returns bounding boxes)
                detections = self.yolo.detect(roi_image)
                # Keep raw detections for visualization
                raw_detections = detections
                detected_conditions = self._process_scalp_conditions(detections, roi_bbox)
        except Exception as e:
            # Fallback: return normal condition if classification fails
            print(f"⚠️ Classification failed: {e}, using default condition")
            detected_conditions = [{'name': 'normal', 'confidence': 0.5, 'type': analysis_type}]
        
        # Calculate severity scores (0-100 scale)
        severity_scores = self._calculate_severity(detected_conditions)
        
        # Build result dictionary
        result = {
            'analysis_type': analysis_type,
            'detected_conditions': detected_conditions,
            'severity_scores': severity_scores,
            'roi_bbox': roi_bbox,
            'segmentation_mask': binary_mask.tolist(),  # Convert to list for JSON serialization
            'classification_scores': raw_scores, 
            'processing_metadata': {
                'normalized_crop_size': (256, 256),
                'roi_size': roi_image.shape[:2],
                'device': self.device
            }
        }

        # Attach raw model outputs for downstream visualization (not required)
        if analysis_type == 'skin' and 'raw_scores' in locals():
            result['efficientnet_scores'] = raw_scores
        if analysis_type == 'scalp' and 'raw_detections' in locals():
            result['yolo_detections'] = raw_detections
        
        return result
    
    def _process_skin_conditions(self, condition_scores: Dict[str, float]) -> List[Dict]:
        """
        Process EfficientNet classification results for skin.
        
        Args:
            condition_scores: Dictionary of condition scores from EfficientNet
            
        Returns:
            List of detected conditions with confidence scores
        """
        detected = []
        threshold = 0.3  # Confidence threshold
        
        for condition, score in condition_scores.items():
            if condition != 'normal' and score > threshold:
                detected.append({
                    'name': condition,
                    'confidence': float(score),
                    'type': 'skin'
                })
        
        # If no conditions detected, mark as normal
        if not detected:
            detected.append({
                'name': 'normal',
                'confidence': float(condition_scores.get('normal', 0.5)),
                'type': 'skin'
            })
        
        return detected
    
    def _process_scalp_conditions(
        self,
        detections: List[Dict],
        roi_bbox: Tuple[int, int, int, int]
    ) -> List[Dict]:
        """
        Process YOLOv8 detection results for scalp.
        
        Args:
            detections: List of YOLOv8 detections
            roi_bbox: Bounding box of ROI in normalized crop coordinates
            
        Returns:
            List of detected conditions with bounding boxes
        """
        detected = []
        
        for detection in detections:
            detected.append({
                'name': detection['condition'],
                'confidence': detection['confidence'],
                'bbox': detection['bbox'],
                'roi_bbox': roi_bbox,
                'type': 'scalp'
            })
        
        # If no conditions detected, mark as normal
        if not detected:
            detected.append({
                'name': 'normal',
                'confidence': 0.5,
                'bbox': None,
                'roi_bbox': roi_bbox,
                'type': 'scalp'
            })
        
        return detected
    
    def _calculate_severity(self, conditions: List[Dict]) -> Dict[str, int]:
        """
        Calculate severity scores (0-100) for detected conditions.
        
        Args:
            conditions: List of detected conditions
            
        Returns:
            Dictionary mapping condition names to severity scores (0-100)
        """
        severity_scores = {}
        
        for condition in conditions:
            name = condition['name']
            confidence = condition.get('confidence', 0.0)
            
            # Convert confidence to severity score (0-100)
            # Higher confidence = higher severity
            severity = int(confidence * 100)
            
            # Classify severity level
            if severity < 30:
                level = 'Mild'
            elif severity < 70:
                level = 'Moderate'
            else:
                level = 'Severe'
            
            severity_scores[name] = {
                'score': severity,
                'level': level
            }
        
        return severity_scores


# Global singleton instance
_pipeline_instance = None
_pipeline_lock = threading.Lock()


def get_pipeline(model_configs: Optional[Dict] = None) -> AIAnalysisPipeline:
    """
    Get or create the singleton pipeline instance.
    
    This function ensures that models are loaded only once and reused
    across all requests, preventing memory exhaustion.
    
    Args:
        model_configs: Dictionary of model configurations
        
    Returns:
        AIAnalysisPipeline instance
    """
    global _pipeline_instance
    
    # If no model_configs provided, try sensible defaults: look for a trained
    # U-Net checkpoint under `core/models/unet_checkpoints/`.
    # Priority order:
    # 1. ResNet-50 + SCSE transfer learning model (resnet_unet_best.pth) - better accuracy
    # 2. Baseline models (best_model.pth)
    if model_configs is None:
        model_configs = {}
        # prefer ResNet-50 + SCSE checkpoint (transfer learning) for better accuracy
        possible_paths = [
            # Transfer learning models (ResNet-50 + SCSE attention) - higher priority
            'core/models/unet_checkpoints/eczema_resnet50_scse/resnet_unet_best.pth',
            'core/models/unet_checkpoints/resnet_unet_best.pth',
            # Baseline models (ResNet-34, no attention) - fallback
            'core/models/unet_checkpoints/eczema_pseudo/best_model.pth',
            'core/models/unet_checkpoints/best_model.pth'
        ]
        model_configs["efficientnet_path"] = "core/ai_models/efficientnet_b4_skin.pth"
        for p in possible_paths:
            try:
                from pathlib import Path
                if Path(p).exists():
                    model_configs['unet_path'] = p
                    break
            except Exception:
                pass
        # set device to cuda if available
        try:
            import torch
            model_configs['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        except Exception:
            model_configs['device'] = 'cpu'

    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = AIAnalysisPipeline(model_configs)
    
    return _pipeline_instance


def process_image(
    image: Union[np.ndarray, str],
    analysis_type: str = 'skin',
    model_configs: Optional[Dict] = None
) -> Dict:
    """
    Convenience function to process an image through the pipeline.
    
    This is the main entry point for external code. It automatically
    handles singleton pattern and provides a clean interface.
    
    Args:
        image: Input image (numpy array or path to image file)
        analysis_type: 'skin' or 'scalp'
        model_configs: Dictionary of model configurations (only used on first call)
        
    Returns:
        Dictionary containing complete analysis results
    """
    pipeline = get_pipeline(model_configs)
    return pipeline.process_image(image, analysis_type)
