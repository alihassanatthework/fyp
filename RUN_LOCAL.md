# Running the Project Locally

## Quick Start Guide

Follow these steps to run the project on your local server:

### Step 1: Activate Virtual Environment

```bash
cd "/Users/alihassan/Desktop/fyp devlopment be"
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: Some packages may require additional system libraries:
- For `segmentation-models-pytorch`: May need to install `torch` and `torchvision` first
- For `opencv-python`: Usually installs without issues
- For `mediapipe`: Usually installs without issues

If you encounter issues, install PyTorch first:
```bash
pip install torch torchvision
pip install -r requirements.txt
```

### Step 3: Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### Step 5: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 6: Start Development Server

```bash
python manage.py runserver
```

The server will start at: **http://127.0.0.1:8000/**

## Testing the Functionality

### 1. Access the Application
- Open browser: http://127.0.0.1:8000/
- You should see the home page

### 2. Register/Login
- Click "Register" to create an account
- Fill in medical history (optional)
- Or use existing account to login

### 3. Upload and Analyze Image
- Go to "Upload" page
- Select an image with a clear face
- Choose "skin" or "scalp" option
- Click "Analyze Image"

### 4. View Results
- You'll see 4 images:
  - Original image
  - Detected region (256×256)
  - Segmentation mask
  - Visualized conditions with overlays
- Detected conditions with severity scores
- Personalized recommendations

## Important Notes

### Model Files
The pipeline will work, but for accurate results, you need trained models:
- U-Net model (`.pth` file) - for segmentation
- EfficientNet model (`.pth` file) - for skin classification
- YOLOv8 model (`.pt` file) - for scalp detection

**Without trained models**: The pipeline will use default/pretrained weights which may not be accurate for your specific use case.

### Media Directory
Make sure these directories exist:
- `media/uploads/` - for uploaded images
- `media/processed/` - for processed images
- `media/visualizations/` - for visualized results

They should be created automatically, but if not:
```bash
mkdir -p media/uploads media/processed media/visualizations
```

### Troubleshooting

#### Issue: "No module named 'django'"
**Solution**: Activate virtual environment first
```bash
source venv/bin/activate
```

#### Issue: "ModuleNotFoundError: No module named 'segmentation_models_pytorch'"
**Solution**: Install the package
```bash
pip install segmentation-models-pytorch
```

#### Issue: "No face detected"
**Solution**: 
- Use images with clear, front-facing faces
- Ensure good lighting
- Face should be clearly visible

#### Issue: "CUDA out of memory" or slow processing
**Solution**: 
- The pipeline defaults to CPU
- For GPU, ensure CUDA is installed and PyTorch is GPU-enabled
- Models will run on CPU but slower

## Development Server Features

- **Auto-reload**: Server automatically reloads on code changes
- **Debug mode**: Enabled by default (shows detailed error pages)
- **Media files**: Served automatically in development
- **Static files**: Collected to `staticfiles/` directory

## Access Points

- **Home**: http://127.0.0.1:8000/
- **Register**: http://127.0.0.1:8000/register/
- **Login**: http://127.0.0.1:8000/login/
- **Upload**: http://127.0.0.1:8000/upload/
- **Admin**: http://127.0.0.1:8000/admin/

## Next Steps After Running

1. **Test Image Upload**: Upload a clear face image
2. **Test Skin Analysis**: Select "skin" option
3. **Test Scalp Analysis**: Select "scalp" option
4. **Check Visualizations**: Verify all 4 images display correctly
5. **Test Medical History**: Update medical history in profile
6. **View History**: Check analysis history page

## Performance Notes

- First request may be slower (model loading)
- Subsequent requests will be faster (singleton pattern)
- Image processing: ~1-3 seconds on CPU
- GPU will significantly speed up processing
