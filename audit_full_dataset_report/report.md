# Full Dataset Audit — Read-Only Report

- Root scanned: `dataset`
- Total folders: **96**, leaf class folders: **76**
- Total files: **109459**, total size: **15.68 GB**
- Scan time: 1.8 min  ·  cv2 available: True

## Executive summary (top 5 findings)

- **[INFO]** No corrupted files found in sampled images.
- **[CRITICAL]** 837 near-duplicate file pairs cross split boundaries (train↔val/test). Reported val accuracy is inflated.
- **[CRITICAL]** 200 exact-duplicate file groups exist across DIFFERENT class folders — same image labelled as multiple classes.
- **[WARNING]** `dataset/efficientnet_b4/IMG_CLASSES` class imbalance **6.3×** — `5. Melanocytic Nevi (NV) - 7970` dominates.
- **[WARNING]** `dataset/efficientnet_b4/dermnet_dataset/test` class imbalance **6.6×** — `Psoriasis pictures Lichen Planus and related diseases` dominates.
- **[WARNING]** `dataset/efficientnet_b4/dermnet_dataset/train` class imbalance **6.6×** — `Psoriasis pictures Lichen Planus and related diseases` dominates.
- **[CRITICAL]** `dataset/efficientnet_b4/train` class imbalance **12.2×** — `normal` dominates.
- **[WARNING]** `dataset/scalp_yolo/images` class imbalance **10.0×** — `train` dominates.

## 1. Structure mapping

Top-level folders (image count = images directly in folder):

```
dataset/   (0 imgs, 1 other, 0.0 MB)
  efficientnet_b4/   (0 imgs, 1 other, 0.0 MB)
    IMG_CLASSES/   (0 imgs, 1 other, 0.0 MB)
      1. Eczema 1677/   (1677 imgs, 0 other, 138.6 MB)
      10. Warts Molluscum and other Viral Infections - 2103/   (2103 imgs, 0 other, 132.3 MB)
      2. Melanoma 15.75k/   (3140 imgs, 0 other, 226.9 MB)
      3. Atopic Dermatitis - 1.25k/   (1257 imgs, 0 other, 64.6 MB)
      4. Basal Cell Carcinoma (BCC) 3323/   (3323 imgs, 0 other, 1476.7 MB)
      5. Melanocytic Nevi (NV) - 7970/   (7970 imgs, 0 other, 1963.2 MB)
      6. Benign Keratosis-like Lesions (BKL) 2624/   (2079 imgs, 0 other, 832.5 MB)
      7. Psoriasis pictures Lichen Planus and related diseases - 2k/   (2055 imgs, 0 other, 168.0 MB)
      8. Seborrheic Keratoses and other Benign Tumors - 1.8k/   (1847 imgs, 0 other, 166.2 MB)
      9. Tinea Ringworm Candidiasis and other Fungal Infections - 1.7k/   (1702 imgs, 0 other, 152.3 MB)
    acne_dataset/   (0 imgs, 1 other, 0.0 MB)
      Acne/   (1832 imgs, 0 other, 168.9 MB)
    data_eczema/   (0 imgs, 1 other, 0.0 MB)
      images/   (1677 imgs, 0 other, 138.6 MB)
      masks/   (1677 imgs, 0 other, 5.4 MB)
    dermnet_dataset/   (0 imgs, 1 other, 0.0 MB)
      test/   (0 imgs, 1 other, 0.0 MB)
        Acne and Rosacea Photos/   (312 imgs, 0 other, 28.4 MB)
        Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions/   (288 imgs, 0 other, 28.0 MB)
        Atopic Dermatitis Photos/   (123 imgs, 0 other, 10.3 MB)
        Bullous Disease Photos/   (113 imgs, 0 other, 10.3 MB)
        Cellulitis Impetigo and other Bacterial Infections/   (73 imgs, 0 other, 6.5 MB)
        Eczema Photos/   (309 imgs, 0 other, 27.4 MB)
        Exanthems and Drug Eruptions/   (101 imgs, 0 other, 8.2 MB)
        Hair Loss Photos Alopecia and other Hair Diseases/   (60 imgs, 0 other, 6.5 MB)
        Herpes HPV and other STDs Photos/   (102 imgs, 0 other, 10.0 MB)
        Light Diseases and Disorders of Pigmentation/   (143 imgs, 0 other, 12.6 MB)
        Lupus and other Connective Tissue diseases/   (105 imgs, 0 other, 10.0 MB)
        Melanoma Skin Cancer Nevi and Moles/   (116 imgs, 0 other, 11.0 MB)
        Nail Fungus and other Nail Disease/   (261 imgs, 0 other, 19.7 MB)
        Poison Ivy Photos and other Contact Dermatitis/   (65 imgs, 0 other, 5.6 MB)
        Psoriasis pictures Lichen Planus and related diseases/   (352 imgs, 0 other, 32.3 MB)
        Scabies Lyme Disease and other Infestations and Bites/   (108 imgs, 0 other, 8.8 MB)
        Seborrheic Keratoses and other Benign Tumors/   (343 imgs, 0 other, 33.0 MB)
        Systemic Disease/   (152 imgs, 0 other, 14.4 MB)
        Tinea Ringworm Candidiasis and other Fungal Infections/   (325 imgs, 0 other, 29.7 MB)
        Urticaria Hives/   (53 imgs, 0 other, 4.3 MB)
        Vascular Tumors/   (121 imgs, 0 other, 10.6 MB)
        Vasculitis Photos/   (105 imgs, 0 other, 8.4 MB)
        Warts Molluscum and other Viral Infections/   (272 imgs, 0 other, 23.8 MB)
      train/   (0 imgs, 1 other, 0.0 MB)
        Acne and Rosacea Photos/   (840 imgs, 0 other, 76.2 MB)
        Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions/   (1149 imgs, 0 other, 114.0 MB)
        Atopic Dermatitis Photos/   (489 imgs, 0 other, 41.4 MB)
        Bullous Disease Photos/   (448 imgs, 0 other, 40.7 MB)
        Cellulitis Impetigo and other Bacterial Infections/   (288 imgs, 0 other, 25.8 MB)
        Eczema Photos/   (1235 imgs, 0 other, 108.7 MB)
        Exanthems and Drug Eruptions/   (404 imgs, 0 other, 31.8 MB)
        Hair Loss Photos Alopecia and other Hair Diseases/   (239 imgs, 0 other, 27.3 MB)
        Herpes HPV and other STDs Photos/   (405 imgs, 0 other, 39.1 MB)
        Light Diseases and Disorders of Pigmentation/   (568 imgs, 0 other, 50.2 MB)
        Lupus and other Connective Tissue diseases/   (420 imgs, 0 other, 38.0 MB)
        Melanoma Skin Cancer Nevi and Moles/   (463 imgs, 0 other, 43.9 MB)
        Nail Fungus and other Nail Disease/   (1040 imgs, 0 other, 78.9 MB)
        Poison Ivy Photos and other Contact Dermatitis/   (260 imgs, 0 other, 25.2 MB)
        Psoriasis pictures Lichen Planus and related diseases/   (1405 imgs, 0 other, 129.9 MB)
        Scabies Lyme Disease and other Infestations and Bites/   (431 imgs, 0 other, 36.4 MB)
        Seborrheic Keratoses and other Benign Tumors/   (1371 imgs, 0 other, 130.3 MB)
        Systemic Disease/   (606 imgs, 0 other, 58.7 MB)
        Tinea Ringworm Candidiasis and other Fungal Infections/   (1300 imgs, 0 other, 121.1 MB)
        Urticaria Hives/   (212 imgs, 0 other, 16.8 MB)
        Vascular Tumors/   (482 imgs, 0 other, 41.2 MB)
        Vasculitis Photos/   (416 imgs, 0 other, 34.3 MB)
        Warts Molluscum and other Viral Infections/   (1086 imgs, 0 other, 95.1 MB)
    dryness/   (0 imgs, 1 other, 0.0 MB)
      test/   (0 imgs, 1 other, 0.0 MB)
        dry/   (113 imgs, 0 other, 4.7 MB)
        not_dry/   (296 imgs, 0 other, 11.6 MB)
      train/   (0 imgs, 0 other, 0.0 MB)
        dry/   (833 imgs, 0 other, 33.8 MB)
        not_dry/   (2039 imgs, 0 other, 81.6 MB)
      val/   (0 imgs, 0 other, 0.0 MB)
        dry/   (257 imgs, 0 other, 10.0 MB)
        not_dry/   (555 imgs, 0 other, 21.9 MB)
    train/   (0 imgs, 1 other, 0.0 MB)
      acne/   (865 imgs, 0 other, 19.1 MB)
      dark_spots/   (1267 imgs, 0 other, 28.7 MB)
      dryness/   (3909 imgs, 0 other, 85.8 MB)
      normal/   (10586 imgs, 0 other, 149.7 MB)
    val/   (0 imgs, 1 other, 0.0 MB)
      acne/   (843 imgs, 0 other, 18.5 MB)
      dark_spots/   (714 imgs, 0 other, 16.0 MB)
      dryness/   (2891 imgs, 0 other, 63.3 MB)
      normal/   (2647 imgs, 0 other, 37.4 MB)
  scalp_yolo/   (0 imgs, 2 other, 0.0 MB)
    images/   (0 imgs, 1 other, 0.0 MB)
      test/   (1239 imgs, 0 other, 697.1 MB)
      train/   (12386 imgs, 0 other, 6690.4 MB)
      val/   (1239 imgs, 0 other, 681.2 MB)
    labels/   (0 imgs, 3 other, 2.8 MB)
      test/   (0 imgs, 1239 other, 0.0 MB)
      train/   (0 imgs, 12386 other, 0.2 MB)
      val/   (0 imgs, 1239 other, 0.0 MB)
```

Leaf class folders identified: **76**

| Leaf folder | n images |
|---|---|
| `dataset/scalp_yolo/images/train` | 12386 |
| `dataset/efficientnet_b4/train/normal` | 10586 |
| `dataset/efficientnet_b4/IMG_CLASSES/5. Melanocytic Nevi (NV) - 7970` | 7970 |
| `dataset/efficientnet_b4/train/dryness` | 3909 |
| `dataset/efficientnet_b4/IMG_CLASSES/4. Basal Cell Carcinoma (BCC) 3323` | 3323 |
| `dataset/efficientnet_b4/IMG_CLASSES/2. Melanoma 15.75k` | 3140 |
| `dataset/efficientnet_b4/val/dryness` | 2891 |
| `dataset/efficientnet_b4/val/normal` | 2647 |
| `dataset/efficientnet_b4/IMG_CLASSES/10. Warts Molluscum and other Viral Infections - 2103` | 2103 |
| `dataset/efficientnet_b4/IMG_CLASSES/6. Benign Keratosis-like Lesions (BKL) 2624` | 2079 |
| `dataset/efficientnet_b4/IMG_CLASSES/7. Psoriasis pictures Lichen Planus and related diseases - 2k` | 2055 |
| `dataset/efficientnet_b4/dryness/train/not_dry` | 2039 |
| `dataset/efficientnet_b4/IMG_CLASSES/8. Seborrheic Keratoses and other Benign Tumors - 1.8k` | 1847 |
| `dataset/efficientnet_b4/acne_dataset/Acne` | 1832 |
| `dataset/efficientnet_b4/IMG_CLASSES/9. Tinea Ringworm Candidiasis and other Fungal Infections - 1.7k` | 1702 |
| `dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677` | 1677 |
| `dataset/efficientnet_b4/data_eczema/images` | 1677 |
| `dataset/efficientnet_b4/data_eczema/masks` | 1677 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Psoriasis pictures Lichen Planus and related diseases` | 1405 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Seborrheic Keratoses and other Benign Tumors` | 1371 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Tinea Ringworm Candidiasis and other Fungal Infections` | 1300 |
| `dataset/efficientnet_b4/train/dark_spots` | 1267 |
| `dataset/efficientnet_b4/IMG_CLASSES/3. Atopic Dermatitis - 1.25k` | 1257 |
| `dataset/scalp_yolo/images/test` | 1239 |
| `dataset/scalp_yolo/images/val` | 1239 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos` | 1235 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 1149 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Warts Molluscum and other Viral Infections` | 1086 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Nail Fungus and other Nail Disease` | 1040 |
| `dataset/efficientnet_b4/train/acne` | 865 |
| `dataset/efficientnet_b4/val/acne` | 843 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Acne and Rosacea Photos` | 840 |
| `dataset/efficientnet_b4/dryness/train/dry` | 833 |
| `dataset/efficientnet_b4/val/dark_spots` | 714 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Systemic Disease` | 606 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Light Diseases and Disorders of Pigmentation` | 568 |
| `dataset/efficientnet_b4/dryness/val/not_dry` | 555 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Atopic Dermatitis Photos` | 489 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Vascular Tumors` | 482 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Melanoma Skin Cancer Nevi and Moles` | 463 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Bullous Disease Photos` | 448 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Scabies Lyme Disease and other Infestations and Bites` | 431 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Lupus and other Connective Tissue diseases` | 420 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Vasculitis Photos` | 416 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Herpes HPV and other STDs Photos` | 405 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Exanthems and Drug Eruptions` | 404 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Psoriasis pictures Lichen Planus and related diseases` | 352 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Seborrheic Keratoses and other Benign Tumors` | 343 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Tinea Ringworm Candidiasis and other Fungal Infections` | 325 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Acne and Rosacea Photos` | 312 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos` | 309 |
| `dataset/efficientnet_b4/dryness/test/not_dry` | 296 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 288 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Cellulitis Impetigo and other Bacterial Infections` | 288 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Warts Molluscum and other Viral Infections` | 272 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Nail Fungus and other Nail Disease` | 261 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Poison Ivy Photos and other Contact Dermatitis` | 260 |
| `dataset/efficientnet_b4/dryness/val/dry` | 257 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Hair Loss Photos Alopecia and other Hair Diseases` | 239 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Urticaria Hives` | 212 |
| … | (16 more, see structure.json) |

## 2. Image quality summary

Sampled 150 images per leaf for stats.

| Leaf | sampled | corrupt | format(s) | res mean | bright | quality |
|---|---|---|---|---|---|---|
| `dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677` | 150 | 0 | .jpg | 619×504 | 109±27 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/10. Warts Molluscum and other Viral Infections - 2103` | 150 | 0 | .jpg | 548×413 | 127±31 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/2. Melanoma 15.75k` | 150 | 0 | .jpg | 512×512 | 172±35 | 91.8 |
| `dataset/efficientnet_b4/IMG_CLASSES/3. Atopic Dermatitis - 1.25k` | 150 | 0 | .jpg | 466×391 | 113±29 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/4. Basal Cell Carcinoma (BCC) 3323` | 150 | 0 | .jpg | 962×940 | 132±35 | 99.8 |
| `dataset/efficientnet_b4/IMG_CLASSES/5. Melanocytic Nevi (NV) - 7970` | 150 | 0 | .jpg | 699×517 | 158±20 | 99.2 |
| `dataset/efficientnet_b4/IMG_CLASSES/6. Benign Keratosis-like Lesions (BKL) 2624` | 150 | 0 | .jpg | 806×729 | 144±25 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/7. Psoriasis pictures Lichen Planus and related diseases - 2k` | 150 | 0 | .jpg | 582×494 | 113±30 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/8. Seborrheic Keratoses and other Benign Tumors - 1.8k` | 150 | 0 | .jpg | 653×494 | 122±30 | 100.0 |
| `dataset/efficientnet_b4/IMG_CLASSES/9. Tinea Ringworm Candidiasis and other Fungal Infections - 1.7k` | 150 | 0 | .jpg | 644×523 | 117±29 | 99.8 |
| `dataset/efficientnet_b4/acne_dataset/Acne` | 150 | 0 | .jpeg,.jpg,.png | 678×577 | 133±27 | 100.0 |
| `dataset/efficientnet_b4/data_eczema/images` | 150 | 0 | .jpg | 615×521 | 101±28 | 99.8 |
| `dataset/efficientnet_b4/data_eczema/masks` | 150 | 0 | .png | 624×525 | 77±48 | 92.4 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Acne and Rosacea Photos` | 150 | 0 | .jpg | 642×551 | 121±31 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 150 | 0 | .jpg | 655×545 | 122±28 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Atopic Dermatitis Photos` | 123 | 0 | .jpg | 653×544 | 107±31 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Bullous Disease Photos` | 113 | 0 | .jpg | 655×555 | 117±34 | 99.7 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Cellulitis Impetigo and other Bacterial Infections` | 73 | 0 | .jpg | 671×546 | 104±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos` | 150 | 0 | .jpg | 642×561 | 104±30 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Exanthems and Drug Eruptions` | 101 | 0 | .jpg | 638×574 | 103±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Hair Loss Photos Alopecia and other Hair Diseases` | 60 | 0 | .jpg | 670×536 | 82±31 | 97.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Herpes HPV and other STDs Photos` | 102 | 0 | .jpg | 667×540 | 117±31 | 99.7 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Light Diseases and Disorders of Pigmentation` | 143 | 0 | .jpg | 653×547 | 103±31 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Lupus and other Connective Tissue diseases` | 105 | 0 | .jpg | 672×538 | 103±33 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Melanoma Skin Cancer Nevi and Moles` | 116 | 0 | .jpg | 676×527 | 126±34 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Nail Fungus and other Nail Disease` | 150 | 0 | .jpg | 646×551 | 109±33 | 99.6 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Poison Ivy Photos and other Contact Dermatitis` | 65 | 0 | .jpg | 643×563 | 112±36 | 99.5 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Psoriasis pictures Lichen Planus and related diseases` | 150 | 0 | .jpg | 657×546 | 112±33 | 99.6 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Scabies Lyme Disease and other Infestations and Bites` | 108 | 0 | .jpg | 666×538 | 117±35 | 99.7 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Seborrheic Keratoses and other Benign Tumors` | 150 | 0 | .jpg | 681×520 | 121±33 | 99.6 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Systemic Disease` | 150 | 0 | .jpg | 633×571 | 119±36 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Tinea Ringworm Candidiasis and other Fungal Infections` | 150 | 0 | .jpg | 672×525 | 114±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Urticaria Hives` | 53 | 0 | .jpg | 646×584 | 113±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Vascular Tumors` | 121 | 0 | .jpg | 648×555 | 118±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Vasculitis Photos` | 105 | 0 | .jpg | 623×579 | 106±26 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Warts Molluscum and other Viral Infections` | 150 | 0 | .jpg | 689×519 | 119±33 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Acne and Rosacea Photos` | 150 | 0 | .jpg | 654×550 | 122±29 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 150 | 0 | .jpg | 660×544 | 119±29 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Atopic Dermatitis Photos` | 150 | 0 | .jpg | 648×555 | 106±31 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Bullous Disease Photos` | 150 | 0 | .jpg | 655×554 | 117±34 | 99.4 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Cellulitis Impetigo and other Bacterial Infections` | 150 | 0 | .jpg | 663×546 | 113±29 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos` | 150 | 0 | .jpg | 648×550 | 104±26 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Exanthems and Drug Eruptions` | 150 | 0 | .jpg | 637×574 | 104±30 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Hair Loss Photos Alopecia and other Hair Diseases` | 150 | 0 | .jpg | 679×533 | 90±37 | 97.6 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Herpes HPV and other STDs Photos` | 150 | 0 | .jpg | 653×548 | 122±30 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Light Diseases and Disorders of Pigmentation` | 150 | 0 | .jpg | 649×553 | 104±32 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Lupus and other Connective Tissue diseases` | 150 | 0 | .jpg | 666×539 | 108±31 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Melanoma Skin Cancer Nevi and Moles` | 150 | 0 | .jpg | 680×524 | 126±34 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Nail Fungus and other Nail Disease` | 150 | 0 | .jpg | 644×554 | 115±35 | 99.2 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Poison Ivy Photos and other Contact Dermatitis` | 150 | 0 | .jpg | 662×546 | 112±34 | 99.4 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Psoriasis pictures Lichen Planus and related diseases` | 150 | 0 | .jpg | 655×548 | 114±30 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Scabies Lyme Disease and other Infestations and Bites` | 150 | 0 | .jpg | 674×533 | 116±37 | 99.4 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Seborrheic Keratoses and other Benign Tumors` | 150 | 0 | .jpg | 679×521 | 123±30 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Systemic Disease` | 150 | 0 | .jpg | 638×566 | 122±35 | 99.4 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Tinea Ringworm Candidiasis and other Fungal Infections` | 150 | 0 | .jpg | 677×522 | 113±32 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Urticaria Hives` | 150 | 0 | .jpg | 613×606 | 112±30 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Vascular Tumors` | 150 | 0 | .jpg | 667×533 | 117±27 | 100.0 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Vasculitis Photos` | 150 | 0 | .jpg | 652×551 | 109±35 | 99.8 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Warts Molluscum and other Viral Infections` | 150 | 0 | .jpg | 707×503 | 121±29 | 99.8 |
| `dataset/efficientnet_b4/dryness/test/dry` | 113 | 0 | .jpg | 640×640 | 110±34 | 98.9 |
| `dataset/efficientnet_b4/dryness/test/not_dry` | 150 | 0 | .jpg | 640×640 | 102±30 | 99.8 |
| `dataset/efficientnet_b4/dryness/train/dry` | 150 | 0 | .jpg | 640×640 | 107±32 | 99.8 |
| `dataset/efficientnet_b4/dryness/train/not_dry` | 150 | 0 | .jpg | 640×640 | 100±35 | 99.8 |
| `dataset/efficientnet_b4/dryness/val/dry` | 150 | 0 | .jpg | 640×640 | 101±32 | 99.0 |
| `dataset/efficientnet_b4/dryness/val/not_dry` | 150 | 0 | .jpg | 640×640 | 108±38 | 99.0 |
| `dataset/efficientnet_b4/train/acne` | 150 | 0 | .jpg | 380×380 | 117±30 | 99.8 |
| `dataset/efficientnet_b4/train/dark_spots` | 150 | 0 | .jpg | 380×380 | 112±31 | 100.0 |
| `dataset/efficientnet_b4/train/dryness` | 150 | 0 | .jpg | 380×380 | 108±30 | 99.4 |
| `dataset/efficientnet_b4/train/normal` | 150 | 0 | .jpg | 380×380 | 93±26 | 100.0 |
| `dataset/efficientnet_b4/val/acne` | 150 | 0 | .jpg | 380×380 | 121±29 | 100.0 |
| `dataset/efficientnet_b4/val/dark_spots` | 150 | 0 | .jpg | 380×380 | 106±35 | 99.8 |
| `dataset/efficientnet_b4/val/dryness` | 150 | 0 | .jpg | 380×380 | 106±33 | 99.2 |
| `dataset/efficientnet_b4/val/normal` | 150 | 0 | .jpg | 380×380 | 94±26 | 99.8 |
| `dataset/scalp_yolo/images/test` | 150 | 0 | .jpg | 1117×731 | 108±24 | 99.4 |
| `dataset/scalp_yolo/images/train` | 150 | 0 | .jpg | 1201×762 | 106±20 | 100.0 |
| `dataset/scalp_yolo/images/val` | 150 | 0 | .jpg | 1054×705 | 112±28 | 99.6 |

## 3. Duplicates & leakage

- Exact duplicates within same leaf folder: **52** folders have ≥1 duplicate group.
- Cross-class exact duplicate groups (same image in 2+ class folders): **200**
- Cross-split near-duplicate pair groups: **56** pair groups, **837** near-duplicate files total

**Top cross-class duplicate groups:**

| occurrences | folders involved |
|---|---|
| 5 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/IMG_CLASSES/3. Atopic Dermatitis - 1.25k, dataset/efficientnet_b4/dermnet_dataset/train/Atopic Dermatitis Photos, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/train |
| 5 | dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/test, dataset/scalp_yolo/images/val |
| 5 | dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/test, dataset/scalp_yolo/images/val |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos, dataset/scalp_yolo/images/val |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/train |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/train |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/test |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos, dataset/scalp_yolo/images/val |
| 4 | dataset/efficientnet_b4/IMG_CLASSES/1. Eczema 1677, dataset/efficientnet_b4/data_eczema/images, dataset/efficientnet_b4/dermnet_dataset/train/Eczema Photos, dataset/scalp_yolo/images/test |

**Cross-split near-duplicate leak rates:**

| dataset | split pair | leaves | leak count | leak % of split_b |
|---|---|---|---|---|
| `dataset/efficientnet_b4` | train↔val | `acne↔acne` | 200 | 50.0% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Acne and Rosacea Photos↔Acne and Rosacea Photos` | 133 | 42.63% |
| `dataset/efficientnet_b4` | train↔val | `dark_spots↔dark_spots` | 124 | 31.0% |
| `dataset/efficientnet_b4` | train↔val | `dryness↔dryness` | 55 | 13.75% |
| `dataset/scalp_yolo/images` | train↔val | `train↔val` | 29 | 7.25% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Hair Loss Photos Alopecia and other Hair Diseases↔Nail Fungus and other Nail Disease` | 21 | 8.05% |
| `dataset/scalp_yolo/images` | train↔test | `train↔test` | 21 | 5.25% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Herpes HPV and other STDs Photos↔Warts Molluscum and other Viral Infections` | 19 | 6.99% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Exanthems and Drug Eruptions↔Exanthems and Drug Eruptions` | 18 | 17.82% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Eczema Photos↔Eczema Photos` | 16 | 5.18% |
| `dataset/scalp_yolo/images` | val↔test | `val↔test` | 13 | 3.25% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Nail Fungus and other Nail Disease↔Nail Fungus and other Nail Disease` | 10 | 3.83% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Nail Fungus and other Nail Disease↔Psoriasis pictures Lichen Planus and related diseases` | 9 | 2.56% |
| `dataset/efficientnet_b4/dryness` | train↔val | `dry↔dry` | 9 | 3.5% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Bullous Disease Photos↔Bullous Disease Photos` | 8 | 7.08% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Tinea Ringworm Candidiasis and other Fungal Infections↔Tinea Ringworm Candidiasis and other Fungal Infections` | 8 | 2.46% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Warts Molluscum and other Viral Infections↔Warts Molluscum and other Viral Infections` | 8 | 2.94% |
| `dataset/efficientnet_b4/dryness` | train↔val | `not_dry↔not_dry` | 8 | 2.0% |
| `dataset/efficientnet_b4/dryness` | val↔test | `not_dry↔not_dry` | 8 | 2.7% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions↔Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 7 | 2.43% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Melanoma Skin Cancer Nevi and Moles↔Melanoma Skin Cancer Nevi and Moles` | 7 | 6.03% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Scabies Lyme Disease and other Infestations and Bites↔Scabies Lyme Disease and other Infestations and Bites` | 7 | 6.48% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Hair Loss Photos Alopecia and other Hair Diseases↔Hair Loss Photos Alopecia and other Hair Diseases` | 6 | 10.0% |
| `dataset/efficientnet_b4/dermnet_dataset` | train↔test | `Poison Ivy Photos and other Contact Dermatitis↔Poison Ivy Photos and other Contact Dermatitis` | 6 | 9.23% |
| `dataset/efficientnet_b4/dryness` | train↔test | `dry↔dry` | 6 | 5.31% |

## 4. Class boundary risk (visual statistics)

Lowest-distance class pairs (highest confusion risk):

| leaf A | leaf B | distance | Δbright | Δcontrast |
|---|---|---|---|---|
| `not_dry` | `dry` | 0.0017 | -0.99 | 0.06 |
| `3. Atopic Dermatitis - 1.25k` | `Psoriasis pictures Lichen Planus and related diseases` | 0.0025 | -0.67 | 0.85 |
| `Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | `Seborrheic Keratoses and other Benign Tumors` | 0.0029 | 0.62 | -0.04 |
| `Exanthems and Drug Eruptions` | `Lupus and other Connective Tissue diseases` | 0.003 | 0.55 | -0.26 |
| `8. Seborrheic Keratoses and other Benign Tumors - 1.8k` | `Seborrheic Keratoses and other Benign Tumors` | 0.0034 | 0.67 | -0.67 |
| `Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | `Seborrheic Keratoses and other Benign Tumors` | 0.0038 | -1.26 | 0.72 |
| `8. Seborrheic Keratoses and other Benign Tumors - 1.8k` | `Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 0.0041 | 0.05 | -0.63 |
| `Eczema Photos` | `Eczema Photos` | 0.0048 | 0.36 | -0.57 |
| `Herpes HPV and other STDs Photos` | `Warts Molluscum and other Viral Infections` | 0.0052 | 0.3 | 1.08 |
| `8. Seborrheic Keratoses and other Benign Tumors - 1.8k` | `Seborrheic Keratoses and other Benign Tumors` | 0.0054 | -1.21 | 0.09 |
| `dry` | `not_dry` | 0.0056 | -1.03 | 1.35 |
| `Seborrheic Keratoses and other Benign Tumors` | `Seborrheic Keratoses and other Benign Tumors` | 0.0059 | -1.88 | 0.76 |
| `Vasculitis Photos` | `Vasculitis Photos` | 0.006 | -3.08 | -0.53 |
| `Atopic Dermatitis Photos` | `Light Diseases and Disorders of Pigmentation` | 0.0062 | 2.05 | 0.88 |
| `Acne and Rosacea Photos` | `Acne and Rosacea Photos` | 0.0065 | -1.56 | -0.14 |

⚠ Visual-statistic similarity does NOT mean true semantic overlap, but a low distance means the model cannot rely on global lighting / colour cues — it must learn texture, which is harder. Cross-reference with the Grad-CAM grids from the previous audit (`audit_efficientnet_b4_report/gradcam_*.png`).

## 5. Training feasibility

### 5.1 Minimum samples per class

⚠ **58 leaf class folders fall below 1500 images** (recommended minimum for reliable fine-tune):

| leaf | count |
|---|---|
| `dataset/efficientnet_b4/dermnet_dataset/test/Urticaria Hives` | 53 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Hair Loss Photos Alopecia and other Hair Diseases` | 60 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Poison Ivy Photos and other Contact Dermatitis` | 65 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Cellulitis Impetigo and other Bacterial Infections` | 73 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Exanthems and Drug Eruptions` | 101 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Herpes HPV and other STDs Photos` | 102 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Lupus and other Connective Tissue diseases` | 105 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Vasculitis Photos` | 105 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Scabies Lyme Disease and other Infestations and Bites` | 108 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Bullous Disease Photos` | 113 |
| `dataset/efficientnet_b4/dryness/test/dry` | 113 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Melanoma Skin Cancer Nevi and Moles` | 116 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Vascular Tumors` | 121 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Atopic Dermatitis Photos` | 123 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Light Diseases and Disorders of Pigmentation` | 143 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Systemic Disease` | 152 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Urticaria Hives` | 212 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Hair Loss Photos Alopecia and other Hair Diseases` | 239 |
| `dataset/efficientnet_b4/dryness/val/dry` | 257 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Poison Ivy Photos and other Contact Dermatitis` | 260 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Nail Fungus and other Nail Disease` | 261 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Warts Molluscum and other Viral Infections` | 272 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions` | 288 |
| `dataset/efficientnet_b4/dermnet_dataset/train/Cellulitis Impetigo and other Bacterial Infections` | 288 |
| `dataset/efficientnet_b4/dryness/test/not_dry` | 296 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Eczema Photos` | 309 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Acne and Rosacea Photos` | 312 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Tinea Ringworm Candidiasis and other Fungal Infections` | 325 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Seborrheic Keratoses and other Benign Tumors` | 343 |
| `dataset/efficientnet_b4/dermnet_dataset/test/Psoriasis pictures Lichen Planus and related diseases` | 352 |

### 5.2 Estimated training time

- `dataset/efficientnet_b4/IMG_CLASSES` (27153 images): ~**113.1 h** on MPS, ~**1357.7 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/data_eczema` (3354 images): ~**14.0 h** on MPS, ~**167.7 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/dermnet_dataset/test` (4002 images): ~**16.7 h** on MPS, ~**200.1 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/dermnet_dataset/train` (15557 images): ~**64.8 h** on MPS, ~**777.9 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/dryness/test` (409 images): ~**1.7 h** on MPS, ~**20.4 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/dryness/train` (2872 images): ~**12.0 h** on MPS, ~**143.6 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/dryness/val` (812 images): ~**3.4 h** on MPS, ~**40.6 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/train` (16627 images): ~**69.3 h** on MPS, ~**831.4 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/efficientnet_b4/val` (7095 images): ~**29.6 h** on MPS, ~**354.8 h** on CPU for a full 50-epoch B4 fine-tune.
- `dataset/scalp_yolo/images` (14864 images): ~**61.9 h** on MPS, ~**743.2 h** on CPU for a full 50-epoch B4 fine-tune.

### 5.3 Unified vs specialist strategy

**Pros of unified multi-class model:**
- One file to ship, one inference call.
- Shared representation across related skin conditions can help generalisation.

**Cons / risks for THIS dataset:**
- High train↔val leakage will produce fake-good numbers (proven in the previous audit).
- Class imbalance >10× biases the model toward the majority class.
- Visually overlapping classes (not_dry↔dry, 3. Atopic Dermatitis - 1.25k↔Psoriasis pictures Lichen Planus and related diseases, Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions↔Seborrheic Keratoses and other Benign Tumors) produce systematic confusion.

**Recommended strategy:** **per-condition specialists**, trained on de-duplicated, balanced subsets, then combined at inference via Pattern-1 specialist override (same approach you already validated with `dryness_v2.pth`).

## 6. Results projection (if trained today, as-is)

### 6.1 Output format if you train the unified 4-class B4

- Softmax over 4 classes: `{acne, dark_spots, dryness, normal}`
- Pick **top-1** for headline label; show **per-class probabilities** in a bar chart on the diagnosis page.
- For UI honesty, show **top-3** if the gap between top-1 and top-2 is < 0.15.

### 6.2 Recommended confidence thresholds (based on data quality)

| Class | Suggested threshold | Reason |
|---|---|---|
| dryness | 0.53 (TTA) | proven via Option B, F1=0.866, AUC=0.963 |
| acne | 0.65 | dataset heavily leaked (47%) — high default keeps false positives low |
| dark_spots | 0.65 | model over-predicts; high threshold to reduce FPs |
| normal | 0.50 | clean class (no leakage); default is fine |

### 6.3 Expected real-world accuracy ranges

- **dryness** (clean external dataset): 88–93% test acc (specialist).
- **normal**: 90–95% test acc (clean, abundant).
- **acne** (under-represented + leaked): 55–72% real-world acc if untreated, 80–88% with specialist + clean data.
- **dark_spots** (under-represented + leaked, over-predicting model): 50–70% real-world acc until precision is fixed.

### 6.4 Pipeline integration

- Keep `efficientnet_b4_skin.pth` as the **base** prediction for `normal` only.
- Replace its `dryness` slot with `dryness_v2.pth` + TTA + threshold 0.53.
- Add `acne_v2.pth` and `dark_spots_v2.pth` over the next 2 weeks.
- Final output: max probability across specialists wins. Tie-break with the base model's normal probability.

## 7. Prioritised recommendation list (before any training)

**P0 (do first):**
1. De-duplicate `efficientnet_b4/train` ↔ `efficientnet_b4/val` with pHash. Move val duplicates to a quarantine folder. (Acne: 47%, dark_spots: 30%, dryness: 12%.)
2. Investigate the cross-class exact duplicate groups (`duplicates.json` → `cross_class_exact_dup_groups`) — those are literal label errors.
3. Decide: keep IMG_CLASSES (10 dermatology classes) for a separate dermatology model, or exclude. It is unrelated to the current 4-class skin model.

**P1 (do next):**
4. Train `acne_v2.pth` on an external clean dataset (mirror of dryness_v2 recipe).
5. Train `dark_spots_v2.pth` similarly.
6. Run Option B (TTA + threshold) on each specialist before integrating.

**P2 (nice to have):**
7. Add Fitzpatrick-stratified evaluation for skin-tone diversity.
8. Build an OOD detector (e.g. brightness/contrast clip) for the inference pipeline so obviously non-skin photos return "can't tell".

## 8. Final verdict

**✅ Ready to train specialists (NOT the unified model).**

The unified 4-class model trained on this data as-is will continue to produce fake-good val numbers and fail on real photos. The specialist route you already validated with `dryness_v2.pth` is the correct path for the next 2-3 weeks.


*Total audit runtime: 1.8 min.*  
*No files outside `audit_full_dataset_report/` were created or modified.*
