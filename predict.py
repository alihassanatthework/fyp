import torch
import cv2
import numpy as np
import os
import sys

# 1. Add the core path to sys so it can find your modules without __init__ conflicts
sys.path.append(os.path.join(os.getcwd(), 'core', 'ai_models'))
from unet_segmenter import UNetSegmenter

def main():
    # --- CONFIGURATION ---
    MODEL_PATH = './checkpoints/resnet_unet_best.pth'
    IMAGE_DIR = './data_eczema/images'
    OUTPUT_NAME = 'prediction_result.png'
    DEVICE = 'cpu'  # Using CPU to ensure compatibility with SCSE layers on Mac
    
    print(f"🚀 Starting Inference...")
    print(f"🖥️  Device set to: {DEVICE}")

    # 2. Verify Checkpoint Exists
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Checkpoint not found at {MODEL_PATH}")
        return

    # 3. Find a Real Image
    if not os.path.exists(IMAGE_DIR):
        print(f"❌ Error: Image directory {IMAGE_DIR} not found.")
        return

    image_files = [f for f in os.listdir(IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print(f"❌ Error: No images found in {IMAGE_DIR}")
        return

    test_image_path = os.path.join(IMAGE_DIR, image_files[0])
    print(f"📸 Testing on image: {test_image_path}")


    # 4. Initialize the Segmenter
    try:
        segmenter = UNetSegmenter(model_path=MODEL_PATH, device=DEVICE)
        
        # --- FORCE OVERRIDE FIX ---
        # 1. Manually remove the failure flag if it exists
        if hasattr(segmenter, '_init_failed'):
            delattr(segmenter, '_init_failed')
        
        # 2. Ensure the model is in eval mode
        if segmenter.model is not None:
            segmenter.model.eval()
        else:
            print("❌ self.model is still None after initialization!")
            return
        # --- END FIX ---

    except Exception as e:
        print(f"❌ Failed to initialize segmenter: {e}")
        return

    # 5. Load and Preprocess Image
    raw_image = cv2.imread(test_image_path)
    if raw_image is None:
        print(f"❌ Error: Could not read image at {test_image_path}")
        return

    # Resize to 256x256 (U-Net expected input)
    resized_img = cv2.resize(raw_image, (256, 256))
    image_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)

    # 6. Generate Prediction
    print("🧠 AI is analyzing...")
    mask = segmenter.segment(image_rgb)

    # 7. Visualization logic
    if mask is None or np.sum(mask) == 0:
        print("⚠️  Warning: AI returned an empty mask. The model may need more training.")
        # Create a "Failed" output just so you can see the resized image
        final_output = resized_img
    else:
        print(f"✅ Success! Detected {np.sum(mask > 0)} pixels of affected area.")
        
        # Create a red overlay
        # mask is (256, 256) with values 0 or 255.
        overlay = resized_img.copy()
        overlay[mask > 0] = [0, 0, 255] # Red in BGR
        
        # Blend the original with the red mask (70% original, 30% red)
        final_output = cv2.addWeighted(resized_img, 0.7, overlay, 0.3, 0)

    # 8. Save Result
    cv2.imwrite(OUTPUT_NAME, final_output)
    print(f"💾 Result saved to: {os.getcwd()}/{OUTPUT_NAME}")
    print(f"💡 Open this file to see the red-highlighted segmentation.")

if __name__ == "__main__":
    main()