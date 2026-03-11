import kagglehub

# Download latest version
path = kagglehub.dataset_download("nayanchaure/acne-dataset")

print("Path to dataset files:", path)