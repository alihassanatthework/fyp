"""
core/ai_models/normal_detector.py
─────────────────────────────────
Specialist binary classifier (normal vs abnormal skin) used alongside the
existing 4-class EfficientNet-B4 classifier. See AIAnalysisPipeline for how
the two outputs are combined.

If the checkpoint file is missing the class returns is_available() == False
and the pipeline transparently falls back to the original (B4-only) behaviour.
"""
from __future__ import annotations
import os
import threading
from typing import Optional

import cv2
import numpy as np
import torch
import torch.nn as nn

try:
    from efficientnet_pytorch import EfficientNet
    _HAS_EFFNET = True
except Exception:
    _HAS_EFFNET = False


class NormalDetector:
    """Thread-safe singleton-style wrapper for the binary normal/abnormal model."""

    _lock = threading.Lock()

    IMAGENET_MEAN = (0.485, 0.456, 0.406)
    IMAGENET_STD  = (0.229, 0.224, 0.225)

    def __init__(self, model_path: Optional[str] = None, device: str = "cpu",
                 img_size: int = 224):
        self.model_path = model_path
        self.device = torch.device(device)
        self.img_size = img_size
        self.model = None
        self._available = False
        self._load()

    # ── Public API ─────────────────────────────────────────────────────
    def is_available(self) -> bool:
        return self._available

    def predict(self, image_rgb: np.ndarray) -> Optional[float]:
        """
        Returns P(normal) as a float in [0, 1] — or None if the model is not
        available. The caller MUST treat None as "no opinion" and continue
        with the legacy 4-class pipeline.
        """
        if not self._available or self.model is None:
            return None
        try:
            t = self._preprocess(image_rgb)
            with torch.no_grad():
                logits = self.model(t)
                probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
            # Class 0 = normal, Class 1 = abnormal (matches training script)
            return float(probs[0])
        except Exception as e:
            print(f"⚠️ NormalDetector.predict failed: {e}")
            return None

    # ── Internals ──────────────────────────────────────────────────────
    def _load(self):
        if not _HAS_EFFNET:
            print("⚠️ NormalDetector: efficientnet_pytorch not installed; skipping.")
            return
        if not self.model_path or not os.path.isfile(self.model_path):
            # Soft-fail: pipeline falls back to legacy behaviour
            print(f"ℹ️ NormalDetector: checkpoint not found at "
                  f"{self.model_path or '(none)'}. Specialist disabled.")
            return
        try:
            with self._lock:
                model = EfficientNet.from_name("efficientnet-b0")
                model._fc = nn.Linear(model._fc.in_features, 2)
                ckpt = torch.load(self.model_path, map_location=self.device)
                state = ckpt["model_state_dict"] if isinstance(ckpt, dict) \
                                                   and "model_state_dict" in ckpt else ckpt
                if isinstance(ckpt, dict) and "img_size" in ckpt:
                    self.img_size = int(ckpt["img_size"])
                model.load_state_dict(state, strict=True)
                model.to(self.device)
                model.eval()
                self.model = model
                self._available = True
                print(f"✅ NormalDetector loaded (B0 binary) on {self.device} "
                      f"from {self.model_path}")
        except Exception as e:
            print(f"⚠️ NormalDetector failed to load: {e}")
            self._available = False
            self.model = None

    def _preprocess(self, image_rgb: np.ndarray) -> torch.Tensor:
        img = image_rgb
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        img = cv2.resize(img, (self.img_size, self.img_size),
                         interpolation=cv2.INTER_LINEAR)
        x = img.astype(np.float32) / 255.0
        x = torch.from_numpy(x).permute(2, 0, 1).unsqueeze(0)
        mean = torch.tensor(self.IMAGENET_MEAN).view(1, 3, 1, 1)
        std  = torch.tensor(self.IMAGENET_STD).view(1, 3, 1, 1)
        x = (x - mean) / std
        return x.to(self.device)
