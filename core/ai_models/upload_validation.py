"""
Upload validation helpers using MediaPipe.

  • has_face(...)       → requires a visible human face   (Makeup Assistance)
  • has_full_body(...)  → requires a full body in frame   (Fashion Assistance)

Both accept a Django UploadedFile (InMemory/Temporary) and validate from the
in-memory bytes BEFORE the file is persisted, so an invalid upload never
creates a database/media record.

If the image cannot be decoded by OpenCV (e.g. HEIC), the checks return True
(do not block) — the downstream pipeline handles format conversion, and we
prefer a false-accept over wrongly rejecting a valid HEIC photo.
"""

import cv2
import numpy as np
import mediapipe as mp


def _decode(image_field):
    """Decode a Django UploadedFile into a BGR ndarray, or None if it can't."""
    try:
        image_field.seek(0)
        buf = np.frombuffer(image_field.read(), np.uint8)
        image_field.seek(0)  # rewind so the caller can still .save() it
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def has_face(image_field) -> bool:
    """True if a human face is present (MediaPipe FaceMesh).
    Returns True when the image can't be decoded (don't block HEIC)."""
    img = _decode(image_field)
    if img is None:
        return True
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.5,
    ) as fm:
        res = fm.process(rgb)
    return bool(res.multi_face_landmarks)


# Full-body key landmarks: shoulders (11,12), hips (23,24),
# knees (25,26), ankles (27,28). All must be visible for a "full body" shot.
_FULL_BODY_LANDMARKS = [11, 12, 23, 24, 25, 26, 27, 28]


def has_full_body(image_field, min_visibility: float = 0.5) -> bool:
    """True if a full body is present (MediaPipe Pose) — i.e. shoulders, hips,
    knees and ankles are all detected with sufficient visibility.
    Returns True when the image can't be decoded (don't block HEIC)."""
    img = _decode(image_field)
    if img is None:
        return True
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    with mp.solutions.pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5,
    ) as pose:
        res = pose.process(rgb)
    if not res.pose_landmarks:
        return False
    lms = res.pose_landmarks.landmark
    for idx in _FULL_BODY_LANDMARKS:
        if lms[idx].visibility < min_visibility:
            return False
    return True
