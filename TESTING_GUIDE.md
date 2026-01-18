# Testing Guide - Visual Output

## Current Status

The system is now configured to **always show MediaPipe outputs** (face and scalp crops) even if the AI pipeline fails. This ensures you can see the visual results immediately.

## What You Should See

After uploading an image, you should see **up to 5 images**:

1. **Original Image** - Your uploaded image
2. **MediaPipe - Face Detection** - 256×256 face crop (always shown if face detected)
3. **MediaPipe - Scalp Detection** - 256×256 scalp crop (always shown if scalp detected)
4. **U-Net Segmentation Mask** - Color-coded mask (shown if segmentation works)
5. **Detected Conditions** - Visualization with overlays (shown if classification works)

## Debugging Steps

### Step 1: Check Server Terminal
When you upload an image, look for these messages in the terminal:

```
✅ Face crop shape: (256, 256, 3)
✅ Scalp crop shape: (256, 256, 3)
✅ Saved face crop: /path/to/media/processed/face_xxxxx.jpg
✅ Saved scalp crop: /path/to/media/processed/scalp_xxxxx.jpg
✅ U-Net model initialized on cpu
✅ Segmentation mask shape: (256, 256), max: 255
✅ Saved segmentation mask: /path/to/media/processed/mask_xxxxx.jpg
✅ Saved visualization: /path/to/media/visualizations/vis_xxxxx.jpg
📦 Session data keys: ['analysis_id', 'original_image', 'face_crop', 'scalp_crop', ...]
```

### Step 2: Check Browser Console
1. Open browser DevTools (F12)
2. Go to **Console** tab
3. Look for any image loading errors
4. Go to **Network** tab
5. Filter by "Img" or "media"
6. Check if images are being requested and their status codes

### Step 3: Verify Files Exist
```bash
cd "/Users/alihassan/Desktop/fyp devlopment be"
ls -la media/processed/ | tail -10
ls -la media/visualizations/ | tail -10
```

You should see files like:
- `face_xxxxx.jpg`
- `scalp_xxxxx.jpg`
- `mask_xxxxx.jpg`
- `vis_xxxxx.jpg`

### Step 4: Test Image URLs Directly
Try accessing images directly in browser:
- http://127.0.0.1:8000/media/processed/face_xxxxx.jpg
- http://127.0.0.1:8000/media/processed/scalp_xxxxx.jpg
- http://127.0.0.1:8000/media/processed/mask_xxxxx.jpg
- http://127.0.0.1:8000/media/visualizations/vis_xxxxx.jpg

## Common Issues & Solutions

### Issue: Only Original Image Shows
**Possible Causes:**
1. MediaPipe detection failed (no face in image)
2. Images not being saved
3. Session data not being passed correctly

**Solution:**
- Check server terminal for error messages
- Verify image has a clear, front-facing face
- Check that files are being created in `media/processed/`

### Issue: Face/Scalp Images Not Showing
**Possible Causes:**
1. MediaPipe failed to detect face
2. Images not saved properly
3. URLs incorrect in session data

**Solution:**
- Use images with clear faces
- Check server logs for MediaPipe errors
- Verify file paths in session data

### Issue: Segmentation Mask Not Showing
**Possible Causes:**
1. U-Net model initialization failed
2. Segmentation failed during inference
3. Mask file not saved

**Solution:**
- Check server logs for U-Net errors
- The system will show an empty mask if U-Net fails
- This is expected if models aren't trained yet

### Issue: Visualization Not Showing
**Possible Causes:**
1. Visualization creation failed
2. File not saved
3. URL incorrect

**Solution:**
- Check server logs for visualization errors
- Verify `media/visualizations/` directory exists
- Check file permissions

## Expected Behavior

### With Trained Models:
- All 5 images should display
- Segmentation mask shows actual affected areas
- Conditions are accurately detected

### Without Trained Models (Current State):
- **Original Image**: ✅ Always shows
- **Face Crop**: ✅ Shows if face detected
- **Scalp Crop**: ✅ Shows if scalp detected
- **Segmentation Mask**: ⚠️ May show empty/black mask (expected)
- **Visualization**: ⚠️ May show just the crop without overlays (expected)

## Next Steps

1. **Upload a new image** and check server terminal
2. **Verify all 5 image slots** appear (even if some are empty)
3. **Check browser console** for any errors
4. **Verify files are created** in media directories
5. **Test image URLs directly** in browser

The system is now more robust and will show MediaPipe outputs even if AI models fail!
