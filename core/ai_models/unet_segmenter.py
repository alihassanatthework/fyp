"""
U-Net-based image segmentation module.

This module provides functionality for segmenting skin and scalp regions
to localize conditions using U-Net architecture.

Supports two model variants:
1. Baseline: ResNet-34 backbone without attention (best_model.pth)
2. Transfer Learning: ResNet-50 backbone with SCSE attention (resnet_unet_best.pth)
"""

import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import cv2
from typing import Tuple, Optional, Union
import segmentation_models_pytorch as smp


class UNetSegmenter:
    """
    U-Net-based segmenter for condition localization.
    
    Uses segmentation-models-pytorch with configurable backbone:
    - ResNet-34 (baseline, no attention)
    - ResNet-50 with SCSE attention (transfer learning variant)
    
    Attributes:
        model: Loaded U-Net model
        device: Device for inference (cuda, mps, or cpu)
        threshold: Threshold for binary mask (default: 0.5)
        encoder_name: Name of the encoder backbone used
    """
    
    # Model architecture configurations
    MODEL_CONFIGS = {
        'baseline': {
            'encoder_name': 'resnet34',
            'decoder_attention_type': None,
        },
        'resnet50_scse': {
            'encoder_name': 'resnet50',
            'decoder_attention_type': 'scse',
        }
    }
    
    def __init__(
        self, 
        model_path: Optional[str] = None, 
        device: str = 'cpu',
        encoder_name: Optional[str] = None,
        decoder_attention_type: Optional[str] = None,
    ):
        """
        Initialize the U-Net segmenter.
        
        Args:
            model_path: Path to pre-trained U-Net model weights (.pth file).
                        If filename contains 'resnet_unet', automatically uses
                        ResNet-50 + SCSE configuration.
            device: Device for inference ('cuda', 'mps', or 'cpu')
            encoder_name: Override encoder backbone (e.g., 'resnet34', 'resnet50')
            decoder_attention_type: Override attention type (e.g., None, 'scse')
        """
        # Setup device: prefer CUDA, then Apple MPS, else CPU
        if device.lower() == 'cuda' and torch.cuda.is_available():
            self.device = torch.device('cuda')
        elif device.lower() == 'mps':
            try:
                if getattr(torch.backends, 'mps', None) and torch.backends.mps.is_available():
                    self.device = torch.device('mps')
                else:
                    self.device = torch.device('cpu')
            except Exception:
                self.device = torch.device('cpu')
        else:
            self.device = torch.device('cpu')
        
        self.threshold = 0.5
        self.model = None
        self._init_failed = False
        
        # Determine architecture from model_path or explicit parameters
        self.encoder_name = encoder_name
        self.decoder_attention_type = decoder_attention_type
        
        # Auto-detect architecture from checkpoint filename
        if model_path and self.encoder_name is None:
            self._auto_detect_architecture(model_path)
        
        # Default to baseline if not specified
        if self.encoder_name is None:
            self.encoder_name = 'resnet34'
            self.decoder_attention_type = None
        
        # Initialize the model
        self._init_model()
        
        # Load weights if provided
        if model_path:
            self.load_model(model_path)
    
    def _auto_detect_architecture(self, model_path: str):
        """
        Auto-detect model architecture from checkpoint file.
        
        Args:
            model_path: Path to the checkpoint file
        """
        import os
        filename = os.path.basename(model_path).lower()
        
        # Check if this is a ResNet-50 + SCSE checkpoint
        if 'resnet_unet' in filename or 'resnet50' in filename:
            self.encoder_name = 'resnet50'
            self.decoder_attention_type = 'scse'
            print(f"🔍 Auto-detected ResNet-50 + SCSE architecture from: {filename}")
        else:
            # Try to load checkpoint metadata to detect encoder
            try:
                checkpoint = torch.load(model_path, map_location='cpu')
                if isinstance(checkpoint, dict) and 'encoder' in checkpoint:
                    encoder = checkpoint['encoder']
                    self.encoder_name = encoder
                    # If encoder is resnet50, assume SCSE attention was used
                    if 'resnet50' in encoder.lower():
                        self.decoder_attention_type = 'scse'
                        print(f"🔍 Auto-detected {encoder} + SCSE from checkpoint metadata")
                    else:
                        self.decoder_attention_type = None
                        print(f"🔍 Auto-detected {encoder} (baseline) from checkpoint metadata")
            except Exception:
                # Fall back to baseline
                pass
    
    def _init_model(self):
        """Initialize the U-Net model with the configured architecture."""
        try:
            self.model = smp.Unet(
                encoder_name=self.encoder_name,
                encoder_weights="imagenet",
                in_channels=3,
                classes=1,  # Binary segmentation (healthy vs affected)
                decoder_attention_type=self.decoder_attention_type,
                activation=None  # We'll apply sigmoid manually
            )
            
            # Move model to device
            self.model.to(self.device)
            self.model.eval()
            
            attention_str = f" + {self.decoder_attention_type.upper()} attention" if self.decoder_attention_type else ""
            print(f"✅ U-Net model initialized ({self.encoder_name}{attention_str}) on {self.device}")
            
        except Exception as e:
            print(f"⚠️ U-Net initialization failed: {e}")
            self.model = None
            self._init_failed = True
    
    def load_model(self, model_path: str):
        """
        Load U-Net model weights from file.
        
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
    
    def segment(self, image: np.ndarray) -> np.ndarray:
        """
        Segment image to produce binary mask.
        
        Args:
            image: Input image as numpy array (256x256x3, RGB, uint8)
            
        Returns:
            Binary segmentation mask (256x256, uint8, 0=healthy, 255=affected)
        """
        # Validate input shape
        if image.shape != (256, 256, 3):
            raise ValueError(f"Input image must be 256x256x3, got {image.shape}")
        
        # If model failed to initialize, return empty mask
        if self.model is None or self._init_failed:
            print("⚠️ U-Net model not available, returning empty mask")
            return np.zeros((256, 256), dtype=np.uint8)
        
        try:
            # Preprocess image
            image_tensor = self._preprocess(image)
            
            # Inference
            with torch.no_grad():
                output = self.model(image_tensor)
                
                # Apply sigmoid activation
                output = torch.sigmoid(output)
                
                # Threshold to create binary mask
                binary_mask = (output > self.threshold).float()
                
                # Convert to numpy
                binary_mask_np = binary_mask.squeeze().cpu().numpy()
                
                # Convert to uint8 (0 or 255)
                binary_mask_uint8 = (binary_mask_np * 255).astype(np.uint8)
            
            return binary_mask_uint8
        except Exception as e:
            print(f"⚠️ U-Net segmentation failed: {e}, returning empty mask")
            import traceback
            traceback.print_exc()
            return np.zeros((256, 256), dtype=np.uint8)
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Args:
            image: Input image (256x256x3, RGB, uint8)
            
        Returns:
            Preprocessed tensor (1x3x256x256, float32, normalized)
        """
        # Normalize to [0, 1]
        image_float = image.astype(np.float32) / 255.0
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image_float).permute(2, 0, 1).unsqueeze(0)
        
        # Normalize with ImageNet statistics
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
        image_tensor = (image_tensor - mean) / std
        
        return image_tensor.to(self.device)
