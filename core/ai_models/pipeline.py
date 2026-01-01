"""
AI Processing Pipeline.

This module orchestrates the complete AI analysis pipeline:
1. Mediapipe detection
2. U-Net segmentation
3. EfficientNet-B4 + YOLOv8 classification
4. XGBoost severity assessment
5. LLM recommendation generation
"""

from .mediapipe_detector import MediapipeDetector
from .unet_segmenter import UNetSegmenter
from .efficientnet_classifier import EfficientNetClassifier
from .yolo_detector import YOLODetector
from .xgboost_severity import XGBoostSeverityClassifier
from .llm_recommender import LLMRecommender


class AIAnalysisPipeline:
    """
    Complete AI analysis pipeline orchestrator.
    
    This class coordinates all AI models to perform end-to-end analysis.
    """
    
    def __init__(self, model_configs=None):
        """
        Initialize the AI pipeline with all models.
        
        Args:
            model_configs: Dictionary of model configurations
        """
        # Initialize all models
        self.mediapipe = MediapipeDetector()
        self.unet = UNetSegmenter(model_configs.get('unet_path') if model_configs else None)
        self.efficientnet = EfficientNetClassifier(
            model_configs.get('efficientnet_path') if model_configs else None
        )
        self.yolo = YOLODetector(model_configs.get('yolo_path') if model_configs else None)
        self.xgboost = XGBoostSeverityClassifier(
            model_configs.get('xgboost_path') if model_configs else None
        )
        self.llm = LLMRecommender(
            model_path=model_configs.get('llm_path') if model_configs else None,
            api_key=model_configs.get('llm_api_key') if model_configs else None,
            use_api=model_configs.get('use_llm_api', False) if model_configs else False
        )
       
    
    def analyze_skin(self, image, user_profile=None, medical_history=None):
        """
        Complete skin analysis pipeline.
        
        Args:
            image: Input image (PIL Image or numpy array)
            user_profile: User profile information
            medical_history: User's medical history
            
        Returns:
            dict: Complete analysis results
        """
        results = {
            'detection': None,
            'segmentation': None,
            'conditions': None,
            'severity': None,
            'recommendations': None
        }
        
        # Step 1: Face detection
        face_regions = self.mediapipe.detect_face(image)
        results['detection'] = face_regions
        
        # Step 2: Segmentation
        segmented_regions = self.unet.segment_skin_regions(image, face_regions)
        results['segmentation'] = segmented_regions
        
        # Step 3: Condition classification
        conditions = self.efficientnet.classify_skin_conditions(image, segmented_regions)
        yolo_detections = self.yolo.detect_conditions(image, condition_type='skin')
        # Combine EfficientNet and YOLO results
        results['conditions'] = self._combine_classifications(conditions, yolo_detections)
        
        # Step 4: Severity assessment
        severity = {}
        for condition, data in results['conditions'].items():
            severity[condition] = self.xgboost.classify_severity(data, condition)
        results['severity'] = severity
        
        # Step 5: Recommendations
        if user_profile and medical_history:
            results['recommendations'] = self.llm.generate_care_routine(
                results, user_profile, medical_history
            )
        
        return results
    
    def analyze_scalp(self, image, user_profile=None, medical_history=None):
        """
        Complete scalp analysis pipeline.
        
        Args:
            image: Input image (PIL Image or numpy array)
            user_profile: User profile information
            medical_history: User's medical history
            
        Returns:
            dict: Complete analysis results
        """
        results = {
            'detection': None,
            'segmentation': None,
            'conditions': None,
            'severity': None,
            'recommendations': None
        }
        
        # Step 1: Scalp detection
        scalp_regions = self.mediapipe.detect_scalp(image)
        results['detection'] = scalp_regions
        
        # Step 2: Segmentation
        segmented_regions = self.unet.segment_scalp_regions(image, scalp_regions)
        results['segmentation'] = segmented_regions
        
        # Step 3: Condition classification
        conditions = self.efficientnet.classify_scalp_conditions(image, segmented_regions)
        yolo_detections = self.yolo.detect_conditions(image, condition_type='scalp')
        # Combine EfficientNet and YOLO results
        results['conditions'] = self._combine_classifications(conditions, yolo_detections)
        
        # Step 4: Severity assessment
        severity = {}
        for condition, data in results['conditions'].items():
            severity[condition] = self.xgboost.classify_severity(data, condition)
        results['severity'] = severity
        
        # Step 5: Recommendations
        if user_profile and medical_history:
            results['recommendations'] = self.llm.generate_care_routine(
                results, user_profile, medical_history
            )
        
        return results
    
    def _combine_classifications(self, efficientnet_results, yolo_results):
        """
        Combine results from EfficientNet and YOLO.
        
        Args:
            efficientnet_results: Results from EfficientNet
            yolo_results: Results from YOLO
            
        Returns:
            dict: Combined classification results
        """
        # TODO: Implement intelligent combination of both model results
        # Weighted average, confidence-based selection, etc.
        pass

