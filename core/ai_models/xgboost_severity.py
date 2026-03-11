import xgboost as xgb
import numpy as np
from typing import Dict, List, Optional, Union

class XGBoostSeverityClassifier:
    SEVERITY_LEVELS = ['mild', 'moderate', 'severe']
    def __init__(self, model_path=None):
        self.model = None
        self.model_path = model_path
        
        if model_path:
            self.load_model(model_path)
    def load_model(self, model_path):
        """Load XGBoost model from file."""
        try:
            # XGBoost can load .json, .ubj, or .pkl files
            self.model = xgb.Booster()
            self.model.load_model(model_path)
            self.model_path = model_path
            print(f"✅ XGBoost model loaded from {model_path}")
        except Exception as e:
            print(f"⚠️ Failed to load XGBoost model: {e}")
            self.model = None     
    def _extract_features(self, condition_data):
        """
        Extract features for severity classification.
        
        Features to extract:
        - Confidence score
        - ROI area percentage
        - Condition type (encoded)
        - Number of detected regions
        """
        features = []
        
        # Feature 1: Confidence score
        confidence = condition_data.get('confidence', 0.0)
        features.append(confidence)
        
        # Feature 2: ROI area (if available)
        roi_area = condition_data.get('roi_area', 0.0)
        features.append(roi_area)
        
        # Feature 3: Condition type (one-hot encoded)
        condition_type = condition_data.get('condition_type', 'unknown')
        condition_types = ['acne', 'dark_spots', 'dryness', 'dandruff', 'hair_fall', 'normal']
        for ct in condition_types:
            features.append(1.0 if ct == condition_type else 0.0)
        
        # Feature 4: Number of regions detected
        num_regions = condition_data.get('num_regions', 0)
        features.append(float(num_regions))
        
        # Feature 5: Average region size
        avg_region_size = condition_data.get('avg_region_size', 0.0)
        features.append(avg_region_size)
        
        return np.array([features], dtype=np.float32)
    def classify_severity(self, condition_data, condition_type):
        """
        Classify severity of detected conditions.

        Returns:
            dict: {
                'severity': 'mild'|'moderate'|'severe',
                'confidence': float,
                'probabilities': {'mild': float, 'moderate': float, 'severe': float},
                'features_used': list
            }
        """
        if self.model is None:
            # Fallback: use simple rule-based classification
            confidence = condition_data.get('confidence', 0.0)
            if confidence < 0.3:
                severity = 'mild'
            elif confidence < 0.7:
                severity = 'moderate'
            else:
                severity = 'severe'

            return {
                'severity': severity,
                'confidence': confidence,
                'probabilities': {
                    'mild': 1.0 if severity == 'mild' else 0.0,
                    'moderate': 1.0 if severity == 'moderate' else 0.0,
                    'severe': 1.0 if severity == 'severe' else 0.0
                },
                'features_used': ['confidence']
            }

        try:
            # Extract features
            features = self._extract_features(condition_data)

            # Predict
            dmatrix = xgb.DMatrix(features)
            prediction = self.model.predict(dmatrix)

            # If model outputs probabilities (3 values)
            pred = np.atleast_1d(prediction)
            if pred.ndim > 1 and pred.shape[1] == 3:
                probs = pred[0]
                severity_idx = int(np.argmax(probs))
                severity = self.SEVERITY_LEVELS[severity_idx]
                confidence = float(probs[severity_idx])
                probabilities = {
                    'mild': float(probs[0]),
                    'moderate': float(probs[1]),
                    'severe': float(probs[2])
                }
            else:
                severity_idx = int(pred[0])
                severity_idx = min(severity_idx, len(self.SEVERITY_LEVELS) - 1)
                severity = self.SEVERITY_LEVELS[severity_idx]
                confidence = 0.8
                probabilities = {level: 0.33 for level in self.SEVERITY_LEVELS}
                probabilities[severity] = 0.67

            return {
                'severity': severity,
                'confidence': confidence,
                'probabilities': probabilities,
                'features_used': list(features[0])
            }
        except Exception as e:
            print(f"⚠️ XGBoost severity classification failed: {e}")
            return {
                'severity': 'moderate',
                'confidence': 0.5,
                'probabilities': {'mild': 0.33, 'moderate': 0.34, 'severe': 0.33},
                'features_used': []
            }

# """
# XGBoost-based severity classification module.

# This module provides functionality for classifying condition severity
# (Mild, Moderate, Severe) using XGBoost.
# """


# class XGBoostSeverityClassifier:
#     """
#     XGBoost classifier for severity assessment.
    
#     Attributes:
#         model: Loaded XGBoost model
#         severity_levels: List of severity levels
#     """
    
#     SEVERITY_LEVELS = ['mild', 'moderate', 'severe']
    
#     def __init__(self, model_path=None):
#         """
#         Initialize the XGBoost severity classifier.
        
#         Args:
#             model_path: Path to pre-trained XGBoost model
#         """
#         # TODO: Load XGBoost model
#         # import xgboost as xgb
#         # self.model = xgb.Booster()
#         # if model_path:
#         #     self.model.load_model(model_path)
#         self.model_path = model_path
    
#     def classify_severity(self, condition_data, condition_type):
#         """
#         Classify severity of detected conditions.
        
#         Args:
#             condition_data: Features extracted from detected conditions
#             condition_type: Type of condition (e.g., 'acne', 'dandruff')
            
#         Returns:
#             dict: Severity classification with confidence scores
#                 {
#                     'severity': 'mild'|'moderate'|'severe',
#                     'confidence': float,
#                     'features_used': list
#                 }
#         """
#         # TODO: Implement severity classification
#         # features = self._extract_features(condition_data)
#         # prediction = self.model.predict(features)
#         # severity = self.SEVERITY_LEVELS[prediction]
#         pass
    
#     def _extract_features(self, condition_data):
#         """
#         Extract features for severity classification.
        
#         Args:
#             condition_data: Raw condition detection data
            
#         Returns:
#             numpy array: Feature vector
#         """
#         # TODO: Extract relevant features
#         pass
    
#     def load_model(self, model_path):
#         """Load XGBoost model from file."""
#         # TODO: Implement model loading
#         pass

