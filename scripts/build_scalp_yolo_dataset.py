import os
from pathlib import Path
import shutil
from tqdm import tqdm
from sklearn.model_selection import train_test_split

# Define constants
RAW_DATASET_DIR = Path("dataset/scalp_yolo/images/train")
OUTPUT_DIR = Path("dataset/scalp_yolo")
VALID_CLASSES = [
    "alopecia", "dandruff", "psoriasis", "folliculitis",
    "contact_dermatitis", "seborrheic_dermatitis", "head_lice", "normal_scalp"
]
SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}

# Create necessary directories
def create_directories():
    for split in ["images/train", "images/val", "images/test", "labels/train", "labels/val", "labels/test"]:
        (OUTPUT_DIR / split).mkdir(parents=True, exist_ok=True)

# Filter and collect valid images
def filter_images():
    valid_images = []
    for image_file in RAW_DATASET_DIR.glob("*.jpg"):
        valid_images.append(image_file)
    return valid_images

# Split dataset into train, val, and test
def split_dataset(images):
    train_val, test = train_test_split(images, test_size=SPLIT_RATIOS["test"], random_state=42)
    train, val = train_test_split(train_val, test_size=SPLIT_RATIOS["val"] / (1 - SPLIT_RATIOS["test"]), random_state=42)
    return {"train": train, "val": val, "test": test}

# Copy images and create empty label files
def prepare_yolo_structure(splits):
    for split, image_files in splits.items():
        for image_file in tqdm(image_files, desc=f"Processing {split}"):
            target_image_path = OUTPUT_DIR / f"images/{split}" / image_file.name
            target_label_path = OUTPUT_DIR / f"labels/{split}" / f"{image_file.stem}.txt"

            if image_file.resolve() == target_image_path.resolve():
                continue  # Skip if source and target are the same

            shutil.copy(image_file, target_image_path)
            target_label_path.touch()

# Create YAML file
def create_yaml_file():
    yaml_content = f"""
    path: {OUTPUT_DIR}

    train: images/train
    val: images/val
    test: images/test

    nc: {len(VALID_CLASSES)}

    names:
"""
    for idx, class_name in enumerate(VALID_CLASSES):
        yaml_content += f"  {idx}: {class_name}\n"

    with open(OUTPUT_DIR / "scalp.yaml", "w") as yaml_file:
        yaml_file.write(yaml_content)

# Generate dataset statistics
def generate_statistics(splits):
    print("\nDataset Statistics:")
    total_images = sum(len(files) for files in splits.values())
    print(f"Total images: {total_images}")
    for split, files in splits.items():
        print(f"{split.capitalize()} images: {len(files)}")

if __name__ == "__main__":
    print("Preparing YOLO dataset...")

    create_directories()

    print("Filtering images...")
    valid_images = filter_images()

    print("Splitting dataset...")
    splits = split_dataset(valid_images)

    print("Preparing YOLO structure...")
    prepare_yolo_structure(splits)

    print("Creating YAML file...")
    create_yaml_file()

    generate_statistics(splits)

    print("\nYOLO dataset successfully prepared")