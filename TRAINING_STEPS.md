# EfficientNet training – step-by-step (Mac M1, 8GB RAM)

You asked to **update your existing .pth for best accuracy** and to be **asked at every step**. Training uses **MPS** on Mac M1 and is tuned for **8GB RAM**.

---

## Step 1: Confirm dataset and device

- **Train data:** `dataset/efficientnet_b4/train` (classes: acne, dark_spots, dryness, normal)
- **Val data:** `dataset/efficientnet_b4/val`
- **Device:** MPS (Mac M1) when available; otherwise CPU.

**Confirm:** Are these paths correct and does your Mac have MPS? (Script will print `Using device: mps` if yes.)

---

## Step 2: Confirm resume from existing weights

The script will look for your existing weights in this order:

1. `core/ai_models/efficientnet_b4_skin.pth` (same file the app uses)
2. `models/efficientnet_b4_skin.pth`

If found, it **resumes from that .pth** (no need to retrain from scratch).  
To train from ImageNet only (ignore your current .pth), run with `--no-resume`.

**Confirm:** Do you want to **resume from existing weights**? (Default: yes.)

---

## Step 3: Run training (8GB-safe defaults)

Defaults:

- **Batch size:** 2 (safe for 8GB RAM)
- **Epochs:** 12 (extra epochs after your previous 8)
- **LR:** 5e-5 (smaller because we’re fine-tuning)
- **Device:** MPS

Before the training loop, the script will ask: **Proceed with training? [y/N]** — say `y` to start.

---

## Step 4: Where the updated .pth is saved

Best model is saved to:

- **`core/ai_models/efficientnet_b4_skin.pth`**

So the **app keeps using the same path**; no copy step. Your previous weights are overwritten by the new best checkpoint.

---

## Commands

**Resume from existing .pth, use MPS, 8GB-safe (ask before training):**
```bash
cd "/Users/alihassan/Desktop/fyp devlopment be"
source venv/bin/activate
python train_efficientnet.py
```

**Skip the “Proceed with training?” prompt:**
```bash
python train_efficientnet.py --yes
```

**Train from ImageNet only (ignore current .pth):**
```bash
python train_efficientnet.py --no-resume
```

**More epochs / different batch size:**
```bash
python train_efficientnet.py --epochs 20 --batch-size 2
```

**Force CPU (if MPS gives issues):**
```bash
python train_efficientnet.py --device cpu
```

---

## Summary

| Item              | Value                                              |
|-------------------|----------------------------------------------------|
| Resume            | Yes (from `core/ai_models/efficientnet_b4_skin.pth` or `models/`) |
| Device            | MPS (Mac M1)                                       |
| 8GB RAM           | Batch size 2, num_workers=0                        |
| Save path         | `core/ai_models/efficientnet_b4_skin.pth` (app path) |
| Ask at step       | “Proceed with training?” before loop (unless `--yes`) |
