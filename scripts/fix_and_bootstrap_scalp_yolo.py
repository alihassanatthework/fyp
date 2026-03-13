from pathlib import Path
from tqdm import tqdm

# Define constants
DATASET_DIR = Path("dataset/scalp_yolo")
IMAGES_DIR = DATASET_DIR / "images"
LABELS_DIR = DATASET_DIR / "labels"
DEFAULT_PSEUDO_LABEL = "0 0.5 0.5 0.8 0.8\n"

# Ensure label directories exist
def ensure_label_directories():
    for split in ["train", "val", "test"]:
        (LABELS_DIR / split).mkdir(parents=True, exist_ok=True)

# Count files in a directory
def count_files(directory):
    return len(list(directory.glob("*.jpg")))

# Create missing label files with pseudo labels
def create_missing_labels():
    summary = {"train": 0, "val": 0, "test": 0}

    for split in ["train", "val", "test"]:
        image_files = (IMAGES_DIR / split).glob("*.jpg")
        for image_file in tqdm(image_files, desc=f"Processing {split}"):
            label_file = LABELS_DIR / split / f"{image_file.stem}.txt"
            if not label_file.exists():
                label_file.write_text(DEFAULT_PSEUDO_LABEL)
                summary[split] += 1

    return summary

# Generate or update the YAML file
def create_yaml_file():
    yaml_content = f"""
    path: {DATASET_DIR}

    train: images/train
    val: images/val
    test: images/test

    nc: 8
    names:
      0: alopecia
      1: dandruff
      2: psoriasis
      3: folliculitis
      4: contact_dermatitis
      5: seborrheic_dermatitis
      6: head_lice
      7: normal_scalp
    """
    with open(DATASET_DIR / "scalp.yaml", "w") as yaml_file:
        yaml_file.write(yaml_content)

if __name__ == "__main__":
    print("Inspecting and fixing dataset structure...")

    ensure_label_directories()

    print("Counting images and labels...")
    train_images = count_files(IMAGES_DIR / "train")
    val_images = count_files(IMAGES_DIR / "val")
    test_images = count_files(IMAGES_DIR / "test")

    print(f"Images - Train: {train_images}, Val: {val_images}, Test: {test_images}")

    train_labels = count_files(LABELS_DIR / "train")
    val_labels = count_files(LABELS_DIR / "val")
    test_labels = count_files(LABELS_DIR / "test")

    print(f"Labels - Train: {train_labels}, Val: {val_labels}, Test: {test_labels}")

    print("Creating missing labels...")
    label_summary = create_missing_labels()

    print("Summary of labels created:")
    for split, count in label_summary.items():
        print(f"{split.capitalize()}: {count} labels created")

    print("Creating YAML file...")
    create_yaml_file()

    print("\nFinal dataset structure is ready for YOLO training.")