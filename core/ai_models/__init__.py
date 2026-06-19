"""
AI Model wrappers and utilities.

This package contains all AI model integrations:
- MediapipeDetector: Face and scalp detection
- UNetSegmenter: Image segmentation with ResNet-34 backbone
- EfficientNetClassifier: Condition classification for skin
- YOLODetector: Condition detection for scalp
- XGBoostSeverityClassifier: Severity assessment
- LLMRecommender: Recommendation generation
- AIAnalysisPipeline: Complete analysis pipeline (singleton pattern)
- extract_roi_from_mask: ROI extraction utility
- process_image: Convenience function for pipeline processing
"""

from .mediapipe_detector import FaceScalpDetector
from .unet_segmenter import UNetSegmenter
from .efficientnet_classifier import EfficientNetClassifier
from .yolo_detector import YOLODetector
from .scalp_classifier import ScalpClassifier
from .xgboost_severity import XGBoostSeverityClassifier
from .llm_recommender import LLMRecommender
from .pipeline import AIAnalysisPipeline, get_pipeline, process_image
from .roi_extractor import extract_roi_from_mask
from .visualization import visualize_skin_conditions, visualize_scalp_conditions, create_comparison_view

__all__ = [
    'FaceScalpDetector',
    'UNetSegmenter',
    'EfficientNetClassifier',
    'YOLODetector',
    'ScalpClassifier',
    'XGBoostSeverityClassifier',
    'LLMRecommender',
    'AIAnalysisPipeline',
    'get_pipeline',
    'process_image',
    'extract_roi_from_mask',
    'visualize_skin_conditions',
    'visualize_scalp_conditions',
    'create_comparison_view',
]
