"""
Dryness specialist detector (Pattern-1 specialist override).

Loads the binary dryness model (dryness_v2.pth) trained on cosmetic
dry-vs-not_dry facial skin, and exposes P(dry) for a given ROI. This catches
everyday cosmetic dryness that the 4-class primary model (trained on dermnet
dermatology photos) tends to misread as acne.

Used by pipeline.py: when P(dry) >= decision threshold, the dryness slot in
the 4-class result is boosted/overridden.

If the .pth is missing the object reports is_available()==False and the
pipeline runs unchanged.
"""

import os
import json
import numpy as np
import cv2
import torch
import torch.nn as nn
from typing import Optional, List

try:
    from torchvision.models import efficientnet_b4
    _HAS_TV = True
except Exception:
    _HAS_TV = False


class DrynessDetector:
    def __init__(self, model_path: Optional[str] = None, device: str = 'cpu'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.dry_idx = 0
        self.img_size = 224
        self.mean = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)
        self.use_tta = False
        self.threshold = 0.50

        if model_path and os.path.exists(model_path) and _HAS_TV:
            try:
                self._load(model_path)
                self._load_calibration(model_path)
            except Exception as e:
                print(f"⚠️ DrynessDetector failed to load: {e}")
                self.model = None

    def is_available(self) -> bool:
        return self.model is not None

    def _load(self, model_path: str):
        ck = torch.load(model_path, map_location='cpu', weights_only=False)
        classes = ck.get('classes', ['dry', 'not_dry'])
        self.dry_idx = classes.index('dry') if 'dry' in classes else 0
        self.img_size = int(ck.get('img_size', 224))
        self.mean = tuple(ck.get('normalize_mean', self.mean))
        self.std = tuple(ck.get('normalize_std', self.std))
        m = efficientnet_b4(weights=None)
        m.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(m.classifier[1].in_features, len(classes)),
        )
        m.load_state_dict(ck['state_dict'])
        m.to(self.device).eval()
        self.model = m
        print(f"✓ DrynessDetector loaded {os.path.basename(model_path)} "
              f"(classes={classes}, img={self.img_size})")

    def _load_calibration(self, model_path: str):
        calib_path = os.path.join(os.path.dirname(model_path),
                                  'dryness_v2_calibration.json')
        if os.path.exists(calib_path):
            try:
                with open(calib_path) as f:
                    c = json.load(f)
                self.use_tta = bool(c.get('use_tta', False))
                self.threshold = float(c.get('decision_threshold', 0.50))
                print(f"✓ Dryness calibration: TTA={self.use_tta} "
                      f"threshold={self.threshold:.2f}")
            except Exception as e:
                print(f"⚠️ dryness calibration read failed: {e}")

    def _tta_views(self, image: np.ndarray) -> List[np.ndarray]:
        views = [image]
        try:
            views.append(cv2.flip(image, 1))
            h, w = image.shape[:2]
            ctr = (w / 2, h / 2)
            for ang in (10, -10):
                M = cv2.getRotationMatrix2D(ctr, ang, 1.0)
                views.append(cv2.warpAffine(image, M, (w, h),
                                            borderMode=cv2.BORDER_REFLECT))
            views.append(np.clip(image.astype(np.float32) * 1.15, 0, 255).astype(image.dtype))
        except Exception:
            return [image]
        return views

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        img = cv2.resize(image, (self.img_size, self.img_size), interpolation=cv2.INTER_LINEAR)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        t = torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        mean = torch.tensor(self.mean).view(1, 3, 1, 1)
        std = torch.tensor(self.std).view(1, 3, 1, 1)
        return ((t - mean) / std).to(self.device)

    def predict(self, roi_image: np.ndarray) -> Optional[float]:
        """Return P(dry) in [0,1], or None if unavailable."""
        if self.model is None:
            return None
        try:
            with torch.no_grad():
                views = self._tta_views(roi_image) if self.use_tta else [roi_image]
                acc = None
                for v in views:
                    t = self._preprocess(v)
                    p = torch.softmax(self.model(t), dim=1).squeeze().cpu().numpy()
                    acc = p if acc is None else acc + p
                p_avg = acc / len(views)
            return float(p_avg[self.dry_idx])
        except Exception as e:
            print(f"⚠️ DrynessDetector.predict failed: {e}")
            return None
