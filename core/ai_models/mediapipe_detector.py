import cv2
import mediapipe as mp
import os
import uuid

class FaceScalpDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.3
        )

    def process_and_crop(self, image_path, output_dir):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("Error: Could not read image file.")
        
        h, w, _ = image.shape
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        results = self.face_mesh.process(rgb_image)
        if not results.multi_face_landmarks:
            raise ValueError("Validation Failed: No human face detected.")

        landmarks = results.multi_face_landmarks[0].landmark

        x_points = [int(pt.x * w) for pt in landmarks]
        y_points = [int(pt.y * h) for pt in landmarks]

        face_x1, face_x2 = max(0, min(x_points)), min(w, max(x_points))
        face_y1, face_y2 = max(0, min(y_points)), min(h, max(y_points))

        forehead_y = int(landmarks[10].y * h)
        face_height = face_y2 - face_y1
        scalp_extension = int(face_height * 0.5)
        
        scalp_x1, scalp_x2 = face_x1, face_x2
        scalp_y2 = forehead_y
        scalp_y1 = max(0, forehead_y - scalp_extension)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        unique_id = str(uuid.uuid4())[:8]
        face_path = os.path.join(output_dir, f"face_{unique_id}.jpg")
        scalp_path = os.path.join(output_dir, f"scalp_{unique_id}.jpg")

        cv2.imwrite(face_path, image[face_y1:face_y2, face_x1:face_x2])
        cv2.imwrite(scalp_path, image[scalp_y1:scalp_y2, scalp_x1:scalp_x2])

        return face_path, scalp_path