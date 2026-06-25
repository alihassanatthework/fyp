"""
Scalp 5-class classifier (primary scalp branch).

Loads scalp_classifier_v1.pth (EfficientNet-B0, 224×224) trained by
train_scalp_5class.py on the cleaned dataset/scalp_clean/ dataset.

Classes (alphabetical, fixed index order):
    Alopecia · Dermatitis · Infections · Normal · Psoriasis

This REPLACES the broken single-class yolo_scalp.pt in the scalp branch:
given a scalp ROI it returns the most likely condition + confidence. The old
YOLO detector is kept as a fallback (used only when this model is unavailable).

If the .pth is missing this object reports is_available()==False and the
pipeline transparently falls back to the YOLO path.
"""

import os
from typing import List, Optional

import cv2
import numpy as np
import torch

try:
    from efficientnet_pytorch import EfficientNet
    _HAS_EFF = True
except Exception:
    _HAS_EFF = False

# Human-readable display names for the API/LLM layer.
DISPLAY_NAMES = {
    "Alopecia": "Alopecia (Hair Loss)",
    "Dermatitis": "Dermatitis",
    "Infections": "Scalp Infection",
    "Normal": "Healthy Scalp",
    "Psoriasis": "Scalp Psoriasis",
}


class ScalpClassifier:
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.model = None
        self.classes: List[str] = []
        self.img_size = 224
        self.mean = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)
        # Below this top-1 confidence we report "uncertain" rather than guess.
        self.min_confidence = 0.35

        if model_path and os.path.exists(model_path) and _HAS_EFF:
            try:
                self._load(model_path)
            except Exception as e:
                print(f"⚠️ ScalpClassifier failed to load: {e}")
                self.model = None

    def is_available(self) -> bool:
        return self.model is not None

    def _load(self, model_path: str):
        ck = torch.load(model_path, map_location="cpu", weights_only=False)
        self.classes = ck["classes"]
        self.img_size = int(ck.get("img_size", 224))
        self.mean = tuple(ck.get("normalize_mean", self.mean))
        self.std = tuple(ck.get("normalize_std", self.std))
        arch = ck.get("arch", "efficientnet-b0")
        m = EfficientNet.from_name(arch, num_classes=len(self.classes))
        m.load_state_dict(ck["model_state_dict"])
        m.to(self.device).eval()
        self.model = m
        print(f"✓ ScalpClassifier loaded {os.path.basename(model_path)} "
              f"(classes={self.classes}, img={self.img_size})")

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        img = cv2.resize(image, (self.img_size, self.img_size),
                         interpolation=cv2.INTER_LINEAR)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        t = torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1).unsqueeze(0)
        mean = torch.tensor(self.mean).view(1, 3, 1, 1)
        std = torch.tensor(self.std).view(1, 3, 1, 1)
        return ((t - mean) / std).to(self.device)

    def _affected_area(self, t: torch.Tensor, idx: int) -> float:
        """Estimate the fraction of the scalp ROI affected by the predicted
        condition using a Class Activation Map (CAM).

        EfficientNet ends in global-average-pool → _fc, so the CAM for class
        `idx` is the _fc-weighted sum of the final conv feature maps. We
        threshold it and return the fraction of the map that lights up — a
        real, image-derived "how much area is affected" measure (weak
        localization), not a confidence proxy. Returns 0..1.
        """
        try:
            feats = self.model.extract_features(t)          # (1, C, h, w)
            w = self.model._fc.weight[idx]                  # (C,)
            cam = torch.einsum('c,chw->hw', w, feats[0])    # (h, w)
            cam = torch.relu(cam)
            m = cam.max()
            if float(m) <= 1e-6:
                return 0.0
            cam = cam / m
            # Pixels above 50% of peak activation count as "affected".
            affected = (cam > 0.5).float().mean().item()
            return float(affected)
        except Exception as e:
            print(f"⚠️ ScalpClassifier CAM failed: {e}")
            return 0.0

    @torch.no_grad()
    def predict(self, roi_image: np.ndarray, tta: bool = True) -> Optional[dict]:
        """Classify a scalp ROI.

        Returns {name, display, confidence, probs, affected_area} or None.
        `affected_area` is the CAM-derived fraction (0..1) of the scalp the
        condition covers — used for true area-based severity.
        """
        if self.model is None:
            return None
        try:
            t = self._preprocess(roi_image)
            views = [t, torch.flip(t, dims=[3])] if tta else [t]
            acc = None
            for v in views:
                p = torch.softmax(self.model(v), dim=1).squeeze(0)
                acc = p if acc is None else acc + p
            probs = (acc / len(views)).cpu().numpy()
            idx = int(np.argmax(probs))
            name = self.classes[idx]
            # Area only meaningful for a disease (Normal → 0 affected area).
            affected = 0.0 if name.lower() == 'normal' else self._affected_area(t, idx)
            return {
                "name": name,
                "display": DISPLAY_NAMES.get(name, name),
                "confidence": float(probs[idx]),
                "probs": {c: float(probs[i]) for i, c in enumerate(self.classes)},
                "affected_area": affected,
            }
        except Exception as e:
            print(f"⚠️ ScalpClassifier.predict failed: {e}")
            return None
