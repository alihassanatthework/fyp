# Django Frontend - HTML/CSS Mock Interface

## Overview

This is a Django-based HTML/CSS frontend interface for the AI-Powered Skin & Scalp Analysis system. It provides a complete mock UI for testing and development before the React frontend is implemented.

## Features

### Pages Implemented

1. **Home/Landing Page** (`/`)
   - Hero section with call-to-action
   - Features showcase
   - How it works section

2. **Authentication**
   - **Login** (`/login/`) - User login page
   - **Register** (`/register/`) - User registration page
   - **Logout** (`/logout/`) - User logout

3. **Image Upload** (`/upload/`)
   - Image type selection (Skin/Scalp)
   - Drag and drop file upload
   - Image preview
   - Upload tips and guidelines

4. **Analysis Results** (`/results/`)
   - Detected conditions display
   - Severity badges (Mild, Moderate, Severe)
   - Confidence scores
   - Personalized recommendations

5. **User Profile** (`/profile/`)
   - Account information
   - Medical history (placeholder)

6. **Analysis History** (`/history/`)
   - List of past analyses
   - Quick access to results

## Design Features

- **Modern UI**: Clean, professional design with gradient hero section
- **Responsive**: Mobile-friendly layout
- **User-Friendly**: Intuitive navigation and clear call-to-actions
- **Color-Coded**: Severity indicators with color coding
- **Interactive**: Drag-and-drop upload, hover effects, smooth transitions

## File Structure

```
templates/
├── base.html                    # Base template with navigation
└── frontend/
    ├── home.html                # Landing page
    ├── login.html               # Login page
    ├── register.html            # Registration page
    ├── upload.html              # Image upload page
    ├── results.html             # Analysis results page
    ├── profile.html             # User profile page
    └── history.html             # Analysis history page

static/
└── css/
    └── style.css               # Main stylesheet
```

## Running the Frontend

### Prerequisites
- Django project set up
- Database configured (or use SQLite for testing)
- Static files configured

### Steps

1. **Collect static files** (if needed):
   ```bash
   python manage.py collectstatic
   ```

2. **Run migrations** (if database is set up):
   ```bash
   python manage.py migrate
   ```

3. **Create superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

4. **Run development server**:
   ```bash
   python manage.py runserver
   ```

5. **Access the frontend**:
   - Open browser: `http://127.0.0.1:8000/`
   - Home page will be displayed

## Navigation Flow

1. **Unauthenticated User**:
   - Home → Register/Login → Upload → Results → History/Profile

2. **Authenticated User**:
   - Home → Upload → Results → History/Profile

## Current Status

### ✅ Implemented
- All page templates
- Complete CSS styling
- Navigation system
- Authentication pages (login/register/logout)
- Image upload interface
- Results display
- Profile and history pages
- Responsive design

### ⚠️ Mock Data
- Analysis results use mock data
- History uses sample data
- Image upload doesn't process images yet (UI only)
- Profile shows placeholder data

### 🔄 To Be Integrated
- Connect to actual API endpoints
- Real image processing
- Actual analysis results
- Database integration for history
- Medical history management

## Customization

### Colors
Edit CSS variables in `static/css/style.css`:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    /* ... */
}
```

### Styling
All styles are in `static/css/style.css`. The design uses:
- CSS Grid for layouts
- Flexbox for components
- CSS variables for theming
- Modern CSS features (transitions, shadows, gradients)

## Notes

- This is a **mock frontend** for development and testing
- The actual production frontend will be built with React
- All forms currently use Django's built-in authentication
- Image upload form is ready but needs backend integration
- Results page displays mock data for demonstration

## Next Steps

1. Connect upload form to image analysis API
2. Integrate with actual analysis results
3. Add real-time progress indicators
4. Connect to database for history
5. Add medical history management
6. Implement actual image preview with processing

