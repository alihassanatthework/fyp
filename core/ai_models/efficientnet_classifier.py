"""
EfficientNet-based condition classification module for skin analysis.

This module provides functionality for classifying skin conditions
using EfficientNet architecture. Input ROI is resized to 380×380.
"""

import os
import json
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import cv2
from typing import Dict, List, Optional
from efficientnet_pytorch import EfficientNet


class EfficientNetClassifier:
    """
    EfficientNet classifier for skin condition detection.
    
    Attributes:
        model: Loaded EfficientNet model
        device: Device for inference
        skin_classes: List of skin condition classes
    """
    
    SKIN_CONDITIONS = [
        'acne',
        'dark_spots',
        'dryness',
        'normal'
    ]
    
    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        """
        Initialize the EfficientNet classifier.
        
        Args:
            model_path: Path to pre-trained model weights (.pth file)
            device: Device for inference ('cuda' or 'cpu')
        """
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.input_size = 380  # Fixed input size for EfficientNet

        # Inference-time calibration (set by _load_calibration). Defaults are
        # no-ops so behaviour is unchanged when no calibration file is present.
        self.use_tta = False        # average 5 augmented views
        self.temperature = 1.0      # logits / T before softmax (confidence only)

        # Initialize EfficientNet-B4
        self.model = EfficientNet.from_pretrained('efficientnet-b4', num_classes=len(self.SKIN_CONDITIONS))

        # Move model to device
        self.model.to(self.device)
        self.model.eval()

        # Load weights if provided
        if model_path:
            self.load_model(model_path)
            self._load_calibration(model_path)

    def _load_calibration(self, model_path: str):
        """Load TTA flag + temperature from <model>_calibration.json if it sits
        next to the weights. Specifically supports primary_v2_calibration.json.
        Silent no-op when absent (legacy model keeps default behaviour)."""
        candidates = []
        if 'primary_v2' in model_path:
            candidates.append(os.path.join(os.path.dirname(model_path),
                                           'primary_v2_calibration.json'))
        # generic: <weights_stem>_calibration.json
        stem = os.path.splitext(model_path)[0]
        candidates.append(stem + '_calibration.json')
        for c in candidates:
            if os.path.exists(c):
                try:
                    with open(c) as f:
                        calib = json.load(f)
                    self.use_tta = bool(calib.get('use_tta', False))
                    self.temperature = float(calib.get('temperature', 1.0)) or 1.0
                    print(f"✓ EfficientNet calibration loaded: TTA={self.use_tta} "
                          f"T={self.temperature:.3f} ({os.path.basename(c)})")
                    return
                except Exception as e:
                    print(f"⚠️ failed to read calibration {c}: {e}")
        # no calibration found — keep defaults
    
    def load_model(self, model_path: str):
        """
        Load EfficientNet model weights from file.
        
        Args:
            model_path: Path to model weights file (.pth)
        """
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            self.model.eval()
        except Exception as e:
            raise ValueError(f"Failed to load model from {model_path}: {str(e)}")
    
    def classify(self, roi_image: np.ndarray) -> Dict[str, float]:
        """
        Classify skin conditions in ROI.
        
        Args:
            roi_image: ROI image (any size, will be resized to 380×380)
            
        Returns:
            Dictionary mapping condition names to confidence scores
        """
        # If model failed to initialize, return default scores
        if self.model is None or hasattr(self, '_init_failed'):
            print("⚠️ EfficientNet model not available, returning default scores")
            return {condition: 0.25 if condition == 'normal' else 0.0 for condition in self.SKIN_CONDITIONS}
        
        try:
            with torch.no_grad():
                if self.use_tta:
                    # Average softmax over 5 light augmentations (TTA).
                    views = self._tta_views(roi_image)
                    probs_sum = None
                    for v in views:
                        t = self._preprocess(v)
                        logits = self.model(t) / self.temperature
                        p = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
                        probs_sum = p if probs_sum is None else probs_sum + p
                    probabilities_np = probs_sum / len(views)
                else:
                    image_tensor = self._preprocess(roi_image)
                    logits = self.model(image_tensor) / self.temperature
                    probabilities_np = torch.softmax(logits, dim=1).squeeze().cpu().numpy()

            # Create result dictionary
            results = {}
            for i, condition in enumerate(self.SKIN_CONDITIONS):
                results[condition] = float(probabilities_np[i])

            return results
        except Exception as e:
            print(f"⚠️ EfficientNet classification failed: {e}, returning default scores")
            import traceback
            traceback.print_exc()
            return {condition: 0.25 if condition == 'normal' else 0.0 for condition in self.SKIN_CONDITIONS}
    
    def _tta_views(self, image: np.ndarray) -> List[np.ndarray]:
        """Return 5 light augmentations of the ROI for test-time augmentation:
        original, horizontal flip, +10° rot, -10° rot, +15% brightness.
        Matches the views used to fit primary_v2_calibration.json."""
        views = [image]
        try:
            views.append(cv2.flip(image, 1))  # horizontal flip
            h, w = image.shape[:2]
            ctr = (w / 2, h / 2)
            for ang in (10, -10):
                M = cv2.getRotationMatrix2D(ctr, ang, 1.0)
                views.append(cv2.warpAffine(image, M, (w, h),
                                            borderMode=cv2.BORDER_REFLECT))
            bright = np.clip(image.astype(np.float32) * 1.15, 0, 255).astype(image.dtype)
            views.append(bright)
        except Exception:
            return [image]
        return views

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess ROI image for model input.
        
        Args:
            image: ROI image (HxWx3, uint8, RGB)
            
        Returns:
            Preprocessed tensor (1x3x380x380, float32, normalized)
        """
        # Resize to 380×380
        image_resized = cv2.resize(image, (self.input_size, self.input_size), interpolation=cv2.INTER_LINEAR)
        
        # Convert to RGB if needed
        if len(image_resized.shape) == 2:
            image_resized = cv2.cvtColor(image_resized, cv2.COLOR_GRAY2RGB)
        elif image_resized.shape[2] == 4:
            image_resized = cv2.cvtColor(image_resized, cv2.COLOR_RGBA2RGB)
        
        # Normalize to [0, 1]
        image_float = image_resized.astype(np.float32) / 255.0
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0)
        
        # Normalize with ImageNet statistics
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        image_tensor = (image_tensor - mean) / std
        
        return image_tensor.to(self.device)
