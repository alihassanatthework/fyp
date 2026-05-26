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
from .normal_detector import NormalDetector


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
            model_path=model_configs.get("xgboost_path")
            )
            self.llm_recommender = LLMRecommender(
                model_path=model_configs.get('llm_path'),
                api_key=model_configs.get('llm_api_key'),
                use_api=model_configs.get('llm_use_api', False)
            )
            # Specialist binary normal-vs-abnormal detector. If the .pth file
            # does not exist this object is created but reports
            # is_available()==False and the pipeline falls back to legacy
            # B4-only behaviour transparently.
            self.normal_detector = NormalDetector(
                model_path=model_configs.get('normal_binary_path'),
                device=self.device,
            )

            self._initialized = True
    
    def process_image(
        self,
        image: Union[np.ndarray, str],
        analysis_type: str = 'skin',
        user_profile: Optional[Dict] = None,
        medical_history: Optional[Dict] = None,
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
            user_profile: Dict with keys: age, gender, skin_type, hair_type
            medical_history: Dict with keys: is_pregnant, is_diabetic, has_cardio_issues,
                             has_asthma, has_hypertension, known_allergens, current_medications

        Returns:
            Dictionary containing:
                - 'analysis_type': Type of analysis performed
                - 'detected_conditions': List of detected conditions
                - 'severity_scores': Severity scores for each condition
                - 'roi_bbox': Bounding box of extracted ROI
                - 'segmentation_mask': Binary segmentation mask
                - 'recommendations': LLM-generated personalised recommendations
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
        raw_scores = None
        raw_detections = None
        try:
            if analysis_type == 'skin':
                # IMPORTANT: do NOT use the U-Net mask to gate the classifier.
                # The U-Net was trained on eczema masks and produces large
                # false-positive regions on normal skin (often 30-50% coverage
                # on healthy faces), which used to black out most of the image
                # before classification and forced the classifier to predict
                # disease classes (typically "dryness") with near-100%
                # confidence. EfficientNet was trained on whole faces, so we
                # classify on the full ROI. The U-Net mask is still produced
                # and is used purely for the visual overlay shown to the user.
                roi_for_classification = roi_image

                # EfficientNet classification (4-class: acne, dark_spots, dryness, normal)
                condition_scores = self.efficientnet.classify(roi_for_classification)

                # ── Ensemble-of-specialists: override the (broken) "normal"
                # output from B4 with the dedicated B0 binary classifier when
                # it is available. B4's disease distribution (acne / dark_spots
                # / dryness) is preserved exactly — we only rescale it to fill
                # the remaining 1 - P(normal) probability mass.
                if self.normal_detector is not None and self.normal_detector.is_available():
                    p_normal = self.normal_detector.predict(roi_for_classification)
                    if p_normal is not None:
                        disease_keys = [k for k in condition_scores if k != 'normal']
                        disease_sum  = sum(condition_scores[k] for k in disease_keys)
                        if disease_sum > 1e-9:
                            scale = (1.0 - p_normal) / disease_sum
                            for k in disease_keys:
                                condition_scores[k] = float(condition_scores[k] * scale)
                        else:
                            # B4 gave near-zero on every disease → just spread
                            # the remaining (1 - p_normal) evenly across them.
                            even = (1.0 - p_normal) / max(len(disease_keys), 1)
                            for k in disease_keys:
                                condition_scores[k] = float(even)
                        condition_scores['normal'] = float(p_normal)
                        print(f"🧪 NormalDetector applied: p_normal={p_normal:.3f}  "
                              f"final_scores={condition_scores}")

                raw_scores = condition_scores
                detected_conditions = self._process_skin_conditions(condition_scores)
            else:
                # Same rationale as skin: U-Net mask was hurting more than
                # helping because it blacked out large portions of the ROI
                # before detection. YOLOv8 was trained on whole crops, so we
                # run it on the full ROI. The mask remains available for the
                # visualization overlay only.
                roi_for_yolo = roi_image

                detections = self.yolo.detect(roi_for_yolo)
                # Keep raw detections for visualization
                raw_detections = detections
                detected_conditions = self._process_scalp_conditions(
                    detections,
                    roi_bbox,
                    
            )

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
            'yolo_detections': raw_detections,
            'processing_metadata': {
                'normalized_crop_size': (256, 256),
                'roi_size': roi_image.shape[:2],
                'device': self.device
            }
        }

        print("PIPELINE ANALYSIS TYPE:", analysis_type)
        if analysis_type == "skin":
            print("EfficientNet scores:", raw_scores)
        if analysis_type == "scalp":
            print("YOLO detections:", raw_detections)

        # Step 5: LLM personalised recommendations
        try:
            recommendations = self.llm_recommender.generate_care_routine(
                analysis_results=result,
                user_profile=user_profile or {},
                medical_history=medical_history or {},
            )
            result['recommendations'] = recommendations
            print("✅ LLM recommendations generated")
        except Exception as e:
            print(f"⚠️ LLM recommendation failed: {e}")
            result['recommendations'] = {
                'daily_routine': {'morning': [], 'evening': []},
                'weekly_routine': [],
                'medicines': [],
                'products': [],
                'dermatologist_consult': 'Consult a dermatologist if condition worsens.',
                'safety_notes': [],
            }

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
        """

        detected = []

        for detection in detections:
            for detection in detections:
                if detection.get("confidence",0) < 0.25:
                    continue
            try:
                condition_name = detection.get('condition') or detection.get('class') or 'unknown'
                confidence = float(detection.get('confidence', 0))
                bbox = detection.get('bbox')

                if bbox is not None:
                    bbox = tuple(map(int, bbox))

                detected.append({
                    'name': condition_name,
                    'class': condition_name,
                    'confidence': confidence,
                    'bbox': bbox,
                    'roi_bbox': roi_bbox,
                    'type': 'scalp'
                })

            except Exception as e:
                print("SCALP CONDITION PARSE ERROR:", e)
                continue

        # only return normal if YOLO truly found nothing
        if not detected:
            detected.append({
                'name': 'normal',
                'class': 'normal',
                'confidence': 0.0,
                'bbox': None,
                'roi_bbox': roi_bbox,
                'type': 'scalp'
            })

        return detected

    
    def _calculate_severity(self, conditions: List[Dict]) -> Dict[str, int]:
        """
        Calculate severity scores using XGBoost model.

        Args:
            conditions: List of detected conditions

        Returns:
            Dictionary mapping condition names to severity scores (0-100)
        """

        severity_scores = {}

        for condition in conditions:

            name = condition['name']
            confidence = condition.get('confidence', 0.0)

            # ---------- Build feature dictionary for XGBoost ----------
            condition_data = {
                "confidence": confidence,
                "roi_area": condition.get("roi_area", 0.0),
                "condition_type": name,
                "num_regions": condition.get("num_regions", 1),
                "avg_region_size": condition.get("avg_region_size", 0.0)
            }

            # ---------- Run XGBoost severity model ----------
            severity_result = self.xgboost_severity.classify_severity(
                condition_data,
                name
            )

            severity_level = severity_result["severity"]
            severity_score = int(severity_result["confidence"] * 100)

            severity_scores[name] = {
                "score": severity_score,
                "level": severity_level.capitalize()
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
        model_configs["yolo_path"] = "core/models/yolo_scalp.pt"
        model_configs["efficientnet_path"] = "core/ai_models/efficientnet_b4_skin.pth"
        model_configs["xgboost_path"] = "core/models/severity_model.json"
        # Optional specialist binary normal/abnormal classifier. If the file
        # does not exist the pipeline runs in legacy B4-only mode.
        model_configs["normal_binary_path"] = "core/ai_models/efficientnet_b0_normal_binary.pth"
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
            if torch.backends.mps.is_available():
                model_configs['device'] = 'mps'
            elif torch.cuda.is_available():
                model_configs['device'] = 'cuda'
            else:
                model_configs['device'] = 'cpu'
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
    model_configs: Optional[Dict] = None,
    user_profile: Optional[Dict] = None,
    medical_history: Optional[Dict] = None,
) -> Dict:
    """
    Convenience function to process an image through the pipeline.

    Args:
        image: Input image (numpy array or path to image file)
        analysis_type: 'skin' or 'scalp'
        model_configs: Dictionary of model configurations (only used on first call)
        user_profile: Dict with age, gender, skin_type, hair_type
        medical_history: Dict with medical flags and allergens

    Returns:
        Dictionary containing complete analysis results including LLM recommendations
    """
    pipeline = get_pipeline(model_configs)
    return pipeline.process_image(
        image,
        analysis_type,
        user_profile=user_profile,
        medical_history=medical_history,
    )
