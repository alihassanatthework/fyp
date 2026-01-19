#!/usr/bin/env python3
"""
Download and extract the Kaggle "ismailpromus/skin-diseases-image-dataset" dataset
using `kagglehub` and place the extracted files into the project's
`dataset/skin_dataset` folder.

Usage:
  python scripts/download_kaggle_dataset.py

Notes:
- This script expects the `kagglehub` Python package to be installed and
  configured. If `kagglehub` relies on Kaggle API credentials, ensure
  those are present in your environment (e.g., ~/.kaggle/kaggle.json).
- If credentials are missing or `kagglehub` cannot download, the script
  prints an error that you can use to fix the environment.
"""
import sys
from pathlib import Path
import zipfile
import shutil
import os

OUT_DIR = Path(__file__).resolve().parents[1] / 'dataset' / 'skin_dataset'
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    import kagglehub
except Exception as e:
    print('ERROR: kagglehub not available in this environment:', e)
    print('Please install it (pip install kagglehub) or run the download locally where kagglehub is available.')
    sys.exit(2)

print('Using output directory:', OUT_DIR)

def download_with_retries(handle: str, attempts=3, backoff=5):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            print(f'Starting download via kagglehub (attempt {attempt}/{attempts})...')
            path = kagglehub.dataset_download(handle)
            print('kagglehub returned:', path)
            return Path(path)
        except Exception as e:
            print(f'Attempt {attempt} failed: {e}')
            last_exc = e
            if attempt < attempts:
                wait = backoff * attempt
                print(f'Waiting {wait}s before retry...')
                import time
                time.sleep(wait)
    # all attempts failed
    raise last_exc


try:
    zip_path = download_with_retries('ismailpromus/skin-diseases-image-dataset', attempts=4, backoff=10)
    if zip_path.is_file() and zipfile.is_zipfile(zip_path):
        print('Detected zip archive, extracting...')
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(OUT_DIR)
        print('Extraction complete to', OUT_DIR)
    elif zip_path.is_dir():
        # Already a folder
        print('kagglehub returned a folder path; copying contents...')
        for item in zip_path.iterdir():
            dest = OUT_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        print('Copy complete to', OUT_DIR)
    else:
        # Unknown path type; attempt to copy
        try:
            shutil.copy2(zip_path, OUT_DIR / zip_path.name)
            print('Copied returned file to', OUT_DIR / zip_path.name)
        except Exception:
            print('Warning: could not interpret kagglehub return value; please inspect:', zip_path)

    print('Download step finished. Listing top-level of dataset folder:')
    for p in sorted(OUT_DIR.iterdir()):
        print('-', p.name)

    print('\nIf you want only eczema examples prepared for training, reply "prepare eczema" and I will filter and prepare the dataset into the layout expected by the trainer.')

except Exception as exc:
    print('Download failed or raised an exception:')
    import traceback
    traceback.print_exc()
    print('\nCommon reasons: missing Kaggle credentials (~/.kaggle/kaggle.json), network problems, or kagglehub not installed.')
    sys.exit(1)
