# Debug Guide - Visualizations Not Showing

## Quick Fix Steps

1. **Check Server Logs**: Look at the terminal where `runserver` is running
   - You should see messages like:
     - `✅ Face crop shape: (256, 256, 3)`
     - `✅ Scalp crop shape: (256, 256, 3)`
     - `✅ Saved face crop: ...`
     - `✅ Saved segmentation mask: ...`

2. **Check Media Directories**:
   ```bash
   ls -la media/processed/
   ls -la media/visualizations/
   ```
   - Files should be created with names like `face_*.jpg`, `scalp_*.jpg`, `mask_*.jpg`, `vis_*.jpg`

3. **Check Browser Console**: 
   - Open browser DevTools (F12)
   - Check Console tab for image loading errors
   - Check Network tab to see if images are being requested

4. **Verify Image URLs**:
   - Images should be accessible at:
     - `/media/uploads/...`
     - `/media/processed/face_*.jpg`
     - `/media/processed/scalp_*.jpg`
     - `/media/processed/mask_*.jpg`
     - `/media/visualizations/vis_*.jpg`

## Common Issues

### Issue 1: Only Original Image Shows
**Cause**: Pipeline is failing silently
**Solution**: Check server logs for error messages

### Issue 2: Images Not Loading (404 errors)
**Cause**: Media files not being served
**Solution**: 
- Check `config/urls.py` has media serving in DEBUG mode
- Verify `MEDIA_ROOT` and `MEDIA_URL` in settings

### Issue 3: Face/Scalp Detection Fails
**Cause**: No face detected in image
**Solution**: 
- Use images with clear, front-facing faces
- Ensure good lighting
- Try different image

### Issue 4: U-Net Segmentation Fails
**Cause**: Model not trained or initialization error
**Solution**: 
- Check server logs for U-Net errors
- The code now has fallback (empty mask) if U-Net fails
- MediaPipe images should still show

## Testing

Try uploading an image and check:
1. Server terminal for debug messages
2. `media/processed/` directory for new files
3. `media/visualizations/` directory for visualization files
4. Browser Network tab to see which images are loading
