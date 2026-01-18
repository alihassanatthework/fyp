# Quick Start Guide - Local Server

## ✅ Server is Running!

Your Django development server should now be running at:

**http://127.0.0.1:8000/**

## 🚀 Testing the Functionality

### Step 1: Open the Application
Open your browser and go to: **http://127.0.0.1:8000/**

### Step 2: Register a New Account
1. Click on "Register" or go to: http://127.0.0.1:8000/register/
2. Fill in:
   - Username
   - Password
   - Medical history (optional checkboxes)
3. Click "Register"

### Step 3: Upload and Analyze an Image
1. Go to "Upload" page: http://127.0.0.1:8000/upload/
2. Click "Choose File" and select an image with a **clear, front-facing face**
3. Select analysis type:
   - **Skin** - for facial skin conditions (acne, dark spots, etc.)
   - **Scalp** - for scalp conditions (dandruff, hair fall, etc.)
4. Click "Analyze Image"

### Step 4: View Results
You'll see:
- **4 Visual Images**:
  1. Original Image
  2. Detected Region (256×256 crop)
  3. Segmentation Mask (color-coded)
  4. Detected Conditions (with overlays and labels)
- **Detected Conditions** with severity scores
- **Personalized Recommendations**

## 📸 What to Expect

### For Skin Analysis:
- Face detection and cropping
- Segmentation mask showing affected areas
- Condition labels: Acne, Dark Spots, Dryness, etc.
- Severity scores (0-100) with color coding

### For Scalp Analysis:
- Scalp detection and cropping
- Segmentation mask
- Bounding boxes for dandruff/hair fall
- Condition labels with confidence scores

## ⚠️ Important Notes

### Image Requirements:
- **Clear face visible** (front-facing is best)
- **Good lighting**
- **JPG, PNG, or JPEG format**
- **Max 10MB file size**

### Model Status:
- **MediaPipe**: ✅ Fully functional (face/scalp detection)
- **U-Net**: ⚠️ Uses default weights (needs training for accuracy)
- **EfficientNet**: ⚠️ Uses default weights (needs training for accuracy)
- **YOLOv8**: ⚠️ Uses default weights (needs training for accuracy)

**Note**: The pipeline will work and show visualizations, but for accurate condition detection, you need to train the models on your dataset.

## 🛠️ Troubleshooting

### Server Not Starting?
```bash
cd "/Users/alihassan/Desktop/fyp devlopment be"
source venv/bin/activate
python manage.py runserver
```

### "No face detected" Error?
- Use images with clear, front-facing faces
- Ensure good lighting
- Try a different image

### Images Not Displaying?
- Check that `media/` directory exists
- Ensure static files are collected: `python manage.py collectstatic --noinput`

### Slow Processing?
- First request is slower (model loading)
- Subsequent requests are faster (singleton pattern)
- Processing takes ~1-3 seconds on CPU

## 📁 File Locations

- **Uploaded images**: `media/uploads/`
- **Processed images**: `media/processed/`
- **Visualizations**: `media/visualizations/`

## 🎯 Test Checklist

- [ ] Server starts successfully
- [ ] Can register new account
- [ ] Can login
- [ ] Can upload image
- [ ] Skin analysis works
- [ ] Scalp analysis works
- [ ] Visualizations display correctly
- [ ] Conditions are detected (may show "normal" without trained models)
- [ ] Recommendations are shown
- [ ] Medical history can be viewed/edited

## 🔄 Restarting the Server

If you need to restart:
1. Press `Ctrl+C` in the terminal to stop
2. Run: `python manage.py runserver`

Or use the script:
```bash
./run_server.sh
```

## 📞 Next Steps

1. **Test with different images** (skin and scalp)
2. **Check visualizations** - all 4 images should display
3. **Test medical history** - update and see how it affects recommendations
4. **Train models** - for accurate condition detection

---

**Enjoy testing your AI-powered skin and scalp analysis system!** 🎉
