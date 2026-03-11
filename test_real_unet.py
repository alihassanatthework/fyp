import os
import cv2
import numpy as np

from core.ai_models.unet_segmenter import UNetSegmenter

IMAGE_FOLDER = "real_tests"
OUTPUT_FOLDER = "real_tests/output"
MODEL_PATH = "core/models/unet_checkpoints/eczema_resnet50_scse/resnet_unet_best.pth"

DEVICE = "mps"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("Loading trained U-Net...")
segmenter = UNetSegmenter(model_path=MODEL_PATH, device=DEVICE)

images = ["test1.jpg", "test2.jpg"]

for img_name in images:

    image_path = os.path.join(IMAGE_FOLDER, img_name)

    print("Processing:", image_path)

    img = cv2.imread(image_path)

    if img is None:
        print("Image not found:", image_path)
        continue

    h, w, _ = img.shape

    # crop center square
    crop_size = min(h, w)

    start_x = w//2 - crop_size//2
    start_y = h//2 - crop_size//2

    crop = img[start_y:start_y+crop_size, start_x:start_x+crop_size]

    # resize crop to model size
    img = cv2.resize(crop, (256,256))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    mask = segmenter.segment(img_rgb)
    print("Mask unique values:", np.unique(mask))
    print("Mask pixel sum:", mask.sum())

    overlay = img.copy()
    overlay[mask > 0] = [0,255,0]

    cv2.imwrite(os.path.join(OUTPUT_FOLDER, f"{img_name}_original.jpg"), img)
    cv2.imwrite(os.path.join(OUTPUT_FOLDER, f"{img_name}_mask.png"), mask)
    cv2.imwrite(os.path.join(OUTPUT_FOLDER, f"{img_name}_overlay.jpg"), overlay)

print("Finished testing.")
print("Results saved in:", OUTPUT_FOLDER)