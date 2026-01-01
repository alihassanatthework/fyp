"""
AI Model wrappers and utilities.

This package contains all AI model integrations:
- MediapipeDetector: Face and scalp detection
- UNetSegmenter: Image segmentation
- EfficientNetClassifier: Condition classification
- YOLODetector: Condition detection
- XGBoostSeverityClassifier: Severity assessment
- LLMRecommender: Recommendation generation
- AIAnalysisPipeline: Complete analysis pipeline
"""

from .mediapipe_detector import MediapipeDetector
from .unet_segmenter import UNetSegmenter
from .efficientnet_classifier import EfficientNetClassifier
from .yolo_detector import YOLODetector
from .xgboost_severity import XGBoostSeverityClassifier
from .llm_recommender import LLMRecommender
from .pipeline import AIAnalysisPipeline

__all__ = [
    'MediapipeDetector',
    'UNetSegmenter',
    'EfficientNetClassifier',
    'YOLODetector',
    'XGBoostSeverityClassifier',
    'LLMRecommender',
    'AIAnalysisPipeline',
]
