import os
import kagglehub
import shutil
from PIL import Image
import random

# Download dataset
print("Downloading LFW dataset...")
path = kagglehub.dataset_download("jessicali9530/lfw-dataset")

print("Dataset downloaded at:", path)

# Target dataset folders
train_target = "dataset/efficientnet_skin/train/normal"
val_target = "dataset/efficientnet_skin/val/normal"

os.makedirs(train_target, exist_ok=True)
os.makedirs(val_target, exist_ok=True)

# Collect images
images = []

for root, dirs, files in os.walk(path):
    for file in files:
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            images.append(os.path.join(root, file))

print("Total images found:", len(images))

# Shuffle images
random.shuffle(images)

# Resize and split
split = int(len(images) * 0.8)

train_imgs = images[:split]
val_imgs = images[split:]

def process(images, target_folder):

    count = 0

    for img_path in images:

        try:
            img = Image.open(img_path).convert("RGB")

            # resize for EfficientNet
            img = img.resize((380,380))

            save_path = os.path.join(
                target_folder,
                f"normal_{count}.jpg"
            )

            img.save(save_path)

            count += 1

        except:
            pass

print("Processing training images...")
process(train_imgs, train_target)

print("Processing validation images...")
process(val_imgs, val_target)

print("Normal skin dataset ready!")


