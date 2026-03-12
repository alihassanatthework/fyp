import os
import shutil
import random
from PIL import Image

# SOURCE ROOT (your current datasets)
SOURCE_ROOT = "dataset"

# TARGET DATASET
TARGET_ROOT = "dataset/efficientnet_skin"

# image size for EfficientNet B4
IMAGE_SIZE = 380

# train validation split
TRAIN_SPLIT = 0.8

# allowed extensions
EXTENSIONS = (".jpg", ".jpeg", ".png")

# map dermatology folders → target classes
CLASS_MAPPING = {

    "acne": [
        "acne",
        "Acne and Rosacea Photos"
    ],

    "dryness": [
        "Eczema Photos",
        "Atopic Dermatitis Photos",
        "Psoriasis pictures Lichen Planus and related diseases"
    ],

    "dark_spots": [
        "Light Diseases and Disorders of Pigmentation"
    ],

    "normal": [
        "normal",
        "healthy",
        "clear_skin"
    ]
}


def create_target_structure():

    for split in ["train", "val"]:
        for cls in CLASS_MAPPING.keys():

            path = os.path.join(TARGET_ROOT, split, cls)

            os.makedirs(path, exist_ok=True)


def find_images():

    collected = {c: [] for c in CLASS_MAPPING}

    for root, dirs, files in os.walk(SOURCE_ROOT):

        folder = os.path.basename(root)

        for target_class, names in CLASS_MAPPING.items():

            if folder in names:

                for file in files:

                    if file.lower().endswith(EXTENSIONS):

                        collected[target_class].append(
                            os.path.join(root, file)
                        )

    return collected


def resize_and_copy(img_path, target_path):

    try:

        img = Image.open(img_path).convert("RGB")

        img = img.resize((IMAGE_SIZE, IMAGE_SIZE))

        img.save(target_path, "JPEG")

    except:
        pass


def process_dataset():

    data = find_images()

    for cls, images in data.items():

        random.shuffle(images)

        split = int(len(images) * TRAIN_SPLIT)

        train_imgs = images[:split]
        val_imgs = images[split:]

        print(f"{cls} → {len(images)} images")

        for img in train_imgs:

            filename = os.path.basename(img)

            target = os.path.join(
                TARGET_ROOT,
                "train",
                cls,
                filename
            )

            resize_and_copy(img, target)

        for img in val_imgs:

            filename = os.path.basename(img)

            target = os.path.join(
                TARGET_ROOT,
                "val",
                cls,
                filename
            )

            resize_and_copy(img, target)


# Dynamically process all datasets in the SOURCE_ROOT directory

def process_all_datasets():
    
    datasets = [d for d in os.listdir(SOURCE_ROOT) if os.path.isdir(os.path.join(SOURCE_ROOT, d))]

    for dataset in datasets:
        
        global TARGET_ROOT
        TARGET_ROOT = os.path.join(SOURCE_ROOT, dataset + "_organized")

        print(f"Processing dataset: {dataset}")

        create_target_structure()
        process_dataset()

        print(f"Dataset {dataset} organized successfully!")


# Consolidate all datasets into a single folder for EfficientNet B4

def consolidate_datasets():
    
    consolidated_root = os.path.join(SOURCE_ROOT, "efficientnet_b4")
    os.makedirs(consolidated_root, exist_ok=True)

    datasets = [d for d in os.listdir(SOURCE_ROOT) if os.path.isdir(os.path.join(SOURCE_ROOT, d)) and d != "efficientnet_b4"]

    for dataset in datasets:
        
        dataset_path = os.path.join(SOURCE_ROOT, dataset)

        for root, dirs, files in os.walk(dataset_path):

            for file in files:

                if file.lower().endswith(EXTENSIONS):

                    target_path = os.path.join(consolidated_root, os.path.relpath(root, dataset_path))
                    os.makedirs(target_path, exist_ok=True)

                    shutil.copy(os.path.join(root, file), os.path.join(target_path, file))

    print("All datasets consolidated into efficientnet_b4 folder.")


if __name__ == "__main__":

    print("Consolidating datasets...")

    consolidate_datasets()

    print("Organizing consolidated dataset...")

    TARGET_ROOT = os.path.join(SOURCE_ROOT, "efficientnet_b4")
    create_target_structure()
    process_dataset()

    print("EfficientNet B4 dataset is ready!")