# EfficientNet-B4 (4-class) — Read-Only Audit Report

Weights: `core/ai_models/efficientnet_b4_skin.pth`  ·  Data (read-only): `dataset/efficientnet_b4/train`, `dataset/efficientnet_b4/val`

> This audit modified NOTHING — model and data are untouched.

## 1. Overall validation performance

- **Overall accuracy:** 0.9667
- **Macro F1:** 0.9490
- **Macro precision:** 0.9364
- **Macro recall:** 0.9680

| Class | Acc | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| acne | 0.951 | 0.971 | 0.951 | 0.961 | 843 |
| dark_spots | 0.985 | 0.779 | 0.985 | 0.870 | 714 |
| dryness | 0.938 | 0.995 | 0.938 | 0.966 | 2891 |
| normal | 0.998 | 1.000 | 0.998 | 0.999 | 2647 |

See `confusion_matrix.png` for the full 4×4 confusion grid.

## 2. Dataset distribution (train + val only)

- Train total: **16627** · imbalance **12.24×**
- Val total:   **7095** · imbalance **4.05×**

| Class | train | train % | val | val % |
|---|---|---|---|---|
| acne | 865 | 5.2% | 843 | 11.88% |
| dark_spots | 1267 | 7.62% | 714 | 10.06% |
| dryness | 3909 | 23.51% | 2891 | 40.75% |
| normal | 10586 | 63.67% | 2647 | 37.31% |

⚠ **Train imbalance is 12.2×** — minority classes are likely under-fitted. The model can score high overall accuracy by leaning toward the majority class (`normal`).

⚠ **Train and val have very different class proportions** — val accuracy is *not* directly comparable to real-world deployment.

## 3. Train vs Val image-statistic drift

Sample size per class per split: **200**

| Class | split | brightness | contrast | mean R/G/B | mean H/S/V | res |
|---|---|---|---|---|---|---|
| acne | train | 119.1±29.1 | 39.6 | 146/109/102 | 56/88/147 | 380×380 |
| acne | val | 115.3±29.1 | 38.0 | 142/105/98 | 48/90/144 | 380×380 |
| dark_spots | train | 113.6±34.1 | 41.2 | 135/106/97 | 53/90/138 | 380×380 |
| dark_spots | val | 104.9±30.5 | 42.5 | 127/97/89 | 52/94/130 | 380×380 |
| dryness | train | 105.0±30.8 | 44.4 | 129/96/87 | 47/98/130 | 380×380 |
| dryness | val | 107.9±30.2 | 44.5 | 133/99/89 | 49/98/134 | 380×380 |
| normal | train | 93.9±28.4 | 63.7 | 104/91/81 | 44/91/111 | 380×380 |
| normal | val | 95.0±25.4 | 63.5 | 106/92/82 | 45/93/113 | 380×380 |

## 4. Train↔Val leakage (perceptual hash)

Threshold: Hamming distance ≤ **6** on 64-bit DCT pHash.

| Class | val hashed | near-dup count | near-dup % |
|---|---|---|---|
| acne | 300 | 141 | 47.0% |
| dark_spots | 300 | 91 | 30.33% |
| dryness | 300 | 36 | 12.0% |
| normal | 300 | 0 | 0.0% |

⚠ **Leakage suspected** — val images are very similar to train images for: `acne` (47.0%), `dark_spots` (30.33%), `dryness` (12.0%). When val is contaminated by train look-alikes, the reported val accuracy is **inflated** and the model memorises the dataset rather than learning the condition. Example file pairs are in `leakage.json`.

## 5. Top confused class pairs

| (true → predicted) | count |
|---|---|
| dryness->dark_spots | 164 |
| acne->dark_spots | 30 |
| dryness->acne | 15 |
| acne->dryness | 11 |
| dark_spots->acne | 9 |
| normal->dark_spots | 5 |
| dark_spots->dryness | 2 |

Grad-CAM grids per true class are in `gradcam_<class>.png` — these show **what the model is actually looking at** when it makes mistakes. Use them to verify whether the model focuses on real skin features (pores, pigmentation, texture) or on irrelevant cues (background, hair, lighting, watermarks).

## 6. Per-class root-cause hypotheses & recommended fixes

### acne

- Val accuracy: **0.951**  · F1: **0.961** · support: 843
- Under-represented in training (5.2%) — the model sees `acne` rarely vs the majority class.
- ~47.0% of val samples look almost identical to train — val accuracy here is partly memorisation.
- Most often confused with: **dark_spots (30), dryness (11)** — see Grad-CAM to check whether the model is looking at the right region for these failures.

**Recommended fixes:**
- Add more training data OR use class-weighted loss / WeightedRandomSampler.
- De-duplicate train↔val using pHash before trusting any future re-training metrics.
- For the most common confusion (acne->dark_spots), inspect Grad-CAM grid: if the model attends to background / hair, crop tighter to facial ROI before classification.

### dark_spots

- Val accuracy: **0.985**  · F1: **0.870** · support: 714
- Under-represented in training (7.62%) — the model sees `dark_spots` rarely vs the majority class.
- High recall, low precision → model **over-predicts** dark_spots — many false positives from other classes.
- ~30.33% of val samples look almost identical to train — val accuracy here is partly memorisation.
- Most often confused with: **acne (9), dryness (2)** — see Grad-CAM to check whether the model is looking at the right region for these failures.

**Recommended fixes:**
- Add more training data OR use class-weighted loss / WeightedRandomSampler.
- De-duplicate train↔val using pHash before trusting any future re-training metrics.
- For the most common confusion (dark_spots->acne), inspect Grad-CAM grid: if the model attends to background / hair, crop tighter to facial ROI before classification.

### dryness

- Val accuracy: **0.938**  · F1: **0.966** · support: 2891
- ~12.0% of val samples look almost identical to train — val accuracy here is partly memorisation.
- Most often confused with: **dark_spots (164), acne (15)** — see Grad-CAM to check whether the model is looking at the right region for these failures.

**Recommended fixes:**
- De-duplicate train↔val using pHash before trusting any future re-training metrics.
- For the most common confusion (dryness->dark_spots), inspect Grad-CAM grid: if the model attends to background / hair, crop tighter to facial ROI before classification.

### normal

- Val accuracy: **0.998**  · F1: **0.999** · support: 2647
- Over-represented in training (63.67%) — the model may default to this class on ambiguous inputs.
- Most often confused with: **dark_spots (5)** — see Grad-CAM to check whether the model is looking at the right region for these failures.

**Recommended fixes:**
- For the most common confusion (normal->dark_spots), inspect Grad-CAM grid: if the model attends to background / hair, crop tighter to facial ROI before classification.

## 7. Strategic summary

- Weakest class: **dark_spots** (F1 0.870)
- Strongest class: **normal** (F1 0.999)
- The gap between weakest and strongest tells you whether to (a) build a single new general model, or (b) train one or two specialists (like `dryness_v2.pth`) and use specialist-override at inference. Specialists win when one class is dramatically worse than the others.

> Next decision is yours — this report is read-only. Reply with which class(es) you want to address first.
