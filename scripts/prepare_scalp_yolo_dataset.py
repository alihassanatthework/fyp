import os
import shutil
from kagglehub import dataset_download
from tqdm import tqdm

# Define constants
OUTPUT_DIR = "dataset/scalp_yolo"
CLASSES_TO_KEEP = ["alopecia", "psoriasis", "eczema", "contact dermatitis", "seborrheic dermatitis"]
DATASET_LINKS = [
    "tapakah68/dataset-of-bald-people",
    "ismailpromus/skin-diseases-image-dataset",
    "shubhamgoel27/dermnet",
    "abubakar4u900/hair-and-scalp-disease-dataset",
    "jcwang10000/pumch-scalp-and-aa",
    "brijlaldhankour/hair-loss-dataset",
    "amitvkulkarni/hair-health",
    "sithukaungset/hairlossdataset"
]

# Function to download datasets
def download_datasets():
    downloaded_paths = []
    for link in DATASET_LINKS:
        print(f"Downloading dataset: {link}")
        path = dataset_download(link)
        downloaded_paths.append(path)
        print(f"Downloaded to: {path}")
    return downloaded_paths

# Function to filter and merge datasets
def filter_and_merge_datasets(downloaded_paths):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    images_dir = os.path.join(OUTPUT_DIR, "images")
    labels_dir = os.path.join(OUTPUT_DIR, "labels")

    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(images_dir, split), exist_ok=True)
        os.makedirs(os.path.join(labels_dir, split), exist_ok=True)

    for path in downloaded_paths:
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png"):
                    # Check if the file belongs to the classes to keep
                    class_name = os.path.basename(root).lower()
                    if any(cls in class_name for cls in CLASSES_TO_KEEP):
                        # Copy image and corresponding label
                        split = "train"  # Default split, can be adjusted
                        shutil.copy(
                            os.path.join(root, file),
                            os.path.join(images_dir, split, file)
                        )

                        label_file = file.rsplit(".", 1)[0] + ".txt"
                        label_path = os.path.join(root, label_file)
                        if os.path.exists(label_path):
                            shutil.copy(
                                label_path,
                                os.path.join(labels_dir, split, label_file)
                            )

# Function to create the YAML file
def create_yaml_file():
    yaml_content = f"""
    train: {OUTPUT_DIR}/images/train
    val: {OUTPUT_DIR}/images/val
    test: {OUTPUT_DIR}/images/test

    nc: {len(CLASSES_TO_KEEP)}
    names: {CLASSES_TO_KEEP}
    """
    with open(os.path.join(OUTPUT_DIR, "scalp.yaml"), "w") as yaml_file:
        yaml_file.write(yaml_content)

if __name__ == "__main__":
    print("Downloading datasets...")
    downloaded_paths = download_datasets()

    print("Filtering and merging datasets...")
    filter_and_merge_datasets(downloaded_paths)

    print("Creating YAML file...")
    create_yaml_file()

    print("Dataset is ready in YOLOv8 format!")