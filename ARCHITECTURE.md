## AI Beauty Assistant - Architecture (current state)

## System Overview

This repository runs a full **Django backend** plus a **React single-page app (SPA)** for the UI and analysis workflow.

When `react/build` exists, Django serves the React SPA as the main frontend (including routes like `/analysis` and `/diagnosis`). The analysis workflow is backed by a wired JSON API:

- React uploads images to `POST /api/analysis/upload/`
- Django runs the AI pipeline and returns JSON (when the request asks for `application/json`)
- The React diagnosis page renders returned conditions and chart images (EfficientNet for skin, YOLO for scalp)

## Current Runtime Entry Points

- **React SPA**: served by Django at `/`, `/analysis`, `/diagnosis`, `/history`, `/analysis-history`, `/profile` (react-router renders the pages)
- **Legacy template UI**: `GET /upload/` and `POST /upload/` are still present, but the React SPA is the primary UI when `react/build` exists
- **Analysis API (JSON)**:
  - `POST /api/analysis/upload/` (multipart: `image`, `analysis_type`)
  - `GET /api/analysis/history/` (session-based list for scan history)
  - `GET /api/analysis/<analysis_id>/` and `DELETE /api/analysis/<analysis_id>/` (session-based record access)
- **Admin**: `/admin/`

## Implementation Status (high-signal, code-based)

| Area | Status | Notes (what exists in code today) |
|------|--------|------------------------------------|
| **Django template frontend** | ✅ Implemented | Multi-page UI and results rendering |
| **Upload + analysis flow (React + API)** | ✅ Implemented | `AnalyzeImageView` calls the AI pipeline and returns JSON for React |
| **AI pipeline orchestration** | ✅ Implemented | `core/ai_models/pipeline.py` singleton pipeline |
| **MediaPipe detection** | ✅ Implemented | `core/ai_models/mediapipe_detector.py` |
| **U-Net segmentation** | ✅ Implemented | `core/ai_models/unet_segmenter.py` loads checkpoints |
| **ROI extraction** | ✅ Implemented | `core/ai_models/roi_extractor.py` |
| **EfficientNet skin classifier** | ✅ Implemented + weights present | `core/ai_models/efficientnet_classifier.py` loads `core/ai_models/efficientnet_b4_skin.pth` |
| **YOLOv8 scalp detector** | ✅ Implemented + weights present | `core/ai_models/yolo_detector.py` loads `core/models/yolo_scalp.pt` |
| **XGBoost severity** | ✅ Implemented + weights present | `core/ai_models/xgboost_severity.py` loads `core/models/severity_model.json` |
| **LLM recommender** | ⏳ Optional/partial | Wrapper exists; requires local model path or API key to be useful |
| **REST API (analysis endpoints)** | ✅ Implemented | `POST /api/analysis/upload/`, `GET /api/analysis/history/`, `GET/DELETE /api/analysis/<analysis_id>/` |
| **Analysis DB models** | ❌ Not implemented | `image_analysis/models.py`, `diagnosis/models.py`, `recommendations/models.py` are placeholders |
| **Encryption utilities** | ❌ Placeholder | `core/encryption/__init__.py` is not implemented |

## Architecture Layers

### 1) Frontend Layer

#### Current Implementation: React SPA (primary) + legacy Django templates (fallback) ✅
- ✅ User interface for image upload/capture
- ✅ Display of analysis results with visualizations (severity scores, recommendations)
- ✅ User profile and medical history management (view/edit)
- ✅ Dashboard for history tracking
- ✅ Modern, responsive UI with CSS styling
- ✅ SPA routes (`/analysis`, `/diagnosis`, `/history`, `/profile`) that call the JSON analysis API
- ✅ Legacy template pages still exist for older flows (`/upload/`, results pages, etc.)

#### Legacy Template UI ⏳ (kept for compatibility)
- ⏳ Upload/analysis UI at `GET/POST /upload/` and server-rendered results
- ⏳ React SPA is the primary UI when `react/build` exists

### 2) API Layer (Django / DRF)

- **DRF + JWT are installed and configured**.
- The React workflow uses the JSON endpoint **`POST /api/analysis/upload/`** (and session-based `/api/analysis/history/` + `/api/analysis/<id>/`).
- For the current React demo flow, analysis endpoints disable authentication to work with the React mock auth (`authentication_classes = []` / `@authentication_classes([])` on analysis views).

### 3) Business Logic Layer (Django apps)

#### `users` ✅ Implemented (models/migrations exist)
- ✅ User authentication (username + password via Django)
- ✅ User registration and login (Django forms)
- ✅ User profile management (UserProfile model with age, gender, skin_type, hair_type)
- ✅ Medical history management (MedicalHistory model with all conditions)
- ❌ Role management (User, Admin, Salons, Dermatologist) - structure ready
- ❌ User feedback collection - moved to Feedback app

#### `image_analysis` ✅ Implemented (view exists), models ❌ pending
- ✅ Image upload/capture handling (AnalyzeImageView)
- ✅ Basic image validation (file size, format)
- ✅ Image type confirmation (skin/scalp selection)
- ✅ MediaPipe face/scalp detection and cropping
- ✅ Secure image storage (media/uploads/, media/processed/)
- ✅ U-Net segmentation integrated for region segmentation
- ✅ ROI extraction tested successfully
- ❌ Image validation (clarity, lighting) - needs implementation
- ❌ Image preprocessing and normalization - needs implementation
- ❌ Image anonymization for model training - needs implementation
- ❌ Database models (ImageUpload, ImageValidation) - not created yet

#### `diagnosis` ⏳ partial (logic in pipeline), models ❌ pending
- ✅ AI-based condition detection pipeline (U-Net integrated)
- ⏳ Skin condition detection (Acne, Dark Spots, Hyperpigmentation, Dryness)
- ⏳ Scalp condition detection (Dandruff, Dryness, Oiliness, Hair Fall)
- ✅ Severity classification (Mild, Moderate, Severe) - mock with 0-100 scoring
- ⏳ Result storage and history tracking (session-based, needs database)
- ❌ Progress comparison over time
- ❌ Database models (AnalysisResult, ConditionDetection, SeverityAssessment) - not created yet

#### `recommendations` ⏳ partial (logic in pipeline), models ❌ pending
- ✅ Personalized care suggestions (mock implementation with medical history filtering)
- ✅ Medical-history-aware filtering (basic safety checks implemented)
- ⏳ Product recommendations with safety checks (mock exists)
- ⏳ Care routine generation (mock exists)
- ❌ Educational content (lifestyle tips, habits)
- ❌ Transparent AI output explanations
- ❌ Database models (CareRoutine, ProductRecommendation, Product) - not created yet

### 4) AI/ML Service Layer (implemented pipeline)

The pipeline is implemented as a singleton orchestrator in `core/ai_models/pipeline.py` and is already wired into the upload flow. The default model paths (used when no config is passed) are:

- **U-Net checkpoints**: auto-detected under `core/models/unet_checkpoints/**` (prefers ResNet50+SCSE `resnet_unet_best.pth` when present)
- **EfficientNet**: `core/ai_models/efficientnet_b4_skin.pth`
- **YOLOv8**: `core/models/yolo_scalp.pt`
- **XGBoost severity**: `core/models/severity_model.json`

#### Processing flow (skin)

1. **MediaPipe** detects face region → normalized crop (pipeline uses fixed crop size in that stage)
2. **U-Net** segments affected regions → binary mask
3. **ROI extraction** from the mask
4. **EfficientNet-B4** classifies ROI into 4 skin conditions: `acne`, `dark_spots`, `dryness`, `normal`
5. **XGBoost** optionally maps detection features → severity (fallback rule-based severity if the model can’t load)
6. **LLM recommender** (optional) can generate routines/products if configured

#### Processing flow (scalp)

1. **MediaPipe** detects scalp/forehead region (depending on implementation)
2. **YOLOv8** detects scalp conditions (current `SCALP_CONDITIONS`: `dandruff`, `hair_fall`)
3. **XGBoost severity** optionally scores severity

#### Notes on model integration maturity

- **EfficientNet/YOLO/XGBoost are not “TODO”** anymore; wrappers are implemented and model files exist in the repository.
- **Database persistence** for results is still missing; results are primarily rendered in the frontend flow.

### 5) Data Layer

**Status**: ⏳ Partial Implementation

#### Database

- **Users + medical history**: implemented (`users` app migrations exist)
- **Analysis persistence**: **not implemented yet** (placeholders in `image_analysis/models.py`, `diagnosis/models.py`, `recommendations/models.py`)
- **DB backend**: Django is configured to support MySQL via env, but actual runtime depends on your `.env` and deployment config

#### File storage
- ✅ User-uploaded images stored in `media/uploads/`
- ✅ Processed images (face/scalp crops) in `media/processed/`
- ✅ Training datasets are stored under `dataset/` (EfficientNet and YOLO formats)
- ❌ Image encryption at rest is not implemented yet
- ❌ S3/Cloud storage integration - not implemented yet

### 6) Security Layer

**Status**: ⏳ Partially Implemented

- ✅ JWT authentication configured (djangorestframework-simplejwt)
- ✅ CORS headers configured for React frontend
- ✅ Environment variables support (`.env` file, python-dotenv)
- ✅ Secure password storage (Django default - PBKDF2)
- ✅ Comprehensive `.gitignore` (protects sensitive files)
- ❌ Encryption utilities are placeholders (`core/encryption/`)
- ⏳ JWT refresh tokens - Configured, needs API implementation
- ❌ HTTPS/TLS enforcement - Not configured (development mode)
- ❌ Data encryption at rest - Not implemented yet
- ❌ Role-based access control - Structure ready, needs implementation
- ❌ Image anonymization for training data - Not implemented yet
- ❌ User consent management - Not implemented yet

## User Roles & Permissions

### **User (Regular User)**
- Register and login
- Upload/capture images
- View analysis results
- Manage profile and medical history
- View history and progress
- Provide feedback
- Access educational content

### **Admin**
- All user permissions
- Manage users and roles
- System settings configuration
- AI model management and updates
- Database management
- System monitoring and analytics
- Access control management

### **Salons** (Future)
- Access to salon-specific features
- Client management
- Analysis history for clients
- Product recommendations for clients

### **Dermatologist** (Future)
- Professional review of AI results
- Provide expert feedback
- Model accuracy improvement
- Patient consultation integration

## Database Schema (Core Entities)

### Users & Authentication ✅ Implemented

- ✅ **User**: Django's built-in User model (username, email, password hash)
- ✅ **UserProfile**: Extended profile data
  - Fields: `user`, `age`, `gender`, `skin_type`, `hair_type`, `created_at`, `updated_at`
  - Status: Model created, migrations applied
- ✅ **MedicalHistory**: Medical conditions and history
  - Fields: `user`, `is_pregnant`, `has_cardio_issues`, `is_diabetic`, `has_allergies`, 
    `has_hypertension`, `has_asthma`, `has_skin_conditions`, `has_scalp_conditions`,
    `other_conditions`, `current_medications`, `known_allergens`, `created_at`, `updated_at`
  - Methods: `get_active_conditions()` - Returns list of active conditions
  - Status: Model created, migrations applied
- ❌ **UserRole**: Role assignment (User, Admin, Salons, Dermatologist) - Not created yet
- ❌ **UserConsent**: Consent tracking for data usage - Not created yet

### Image Analysis ❌ Not Created Yet

- ❌ **ImageUpload**: Uploaded images metadata (file path, upload date, image type)
- ❌ **ImageValidation**: Validation results (clarity, lighting, size)
- ❌ **AnalysisResult**: AI analysis results (timestamp, processing time)
- ❌ **ConditionDetection**: Detected conditions with severity scores
  - Skin: Acne, Dark Spots, Hyperpigmentation, Dryness
  - Scalp: Dandruff, Dryness, Oiliness, Hair Fall
- ❌ **SeverityAssessment**: Severity scores (0-100) per condition
- ❌ **SegmentationData**: U-Net segmentation masks and regions

**Note**: Currently using session-based storage for analysis results. Database models needed for persistence.

### Recommendations ❌ Not Created Yet

- ❌ **CareRoutine**: Personalized care routines (daily, weekly)
- ❌ **ProductRecommendation**: Suggested products with safety flags
- ❌ **Product**: Product catalog with ingredients and safety information
- ❌ **EducationalContent**: Lifestyle tips, habits, environmental factors
- ❌ **AIExplanation**: Transparent explanations of AI decisions

**Note**: Currently using mock recommendations with medical history filtering. Database models needed for persistence.

### Feedback & Improvement ❌ Not Created Yet

- ❌ **UserFeedback**: User ratings and comments on diagnosis
- ❌ **ModelVersion**: AI model versions and update history
- ❌ **ModelPerformance**: Accuracy metrics and improvement tracking

## Routes / endpoints (actual wiring)

### Django template views ✅

- ✅ `GET /` - Home page
- ✅ `GET /register/` - User registration (with medical history)
- ✅ `POST /register/` - Process registration
- ✅ `GET /login/` - Login page
- ✅ `POST /login/` - Process login
- ✅ `POST /logout/` - User logout
- ✅ `GET /upload/` - Image upload page
- ✅ `POST /upload/` - Process image upload and analysis
- ✅ `GET /results/<id>/` - Display analysis results
- ✅ `GET /profile/` - User profile page
- ✅ `GET /profile/view-medical-history/` - View medical history
- ✅ `GET /profile/edit-medical-history/` - Edit medical history
- ✅ `POST /profile/edit-medical-history/` - Update medical history
- ✅ `GET /history/` - Analysis history page

### REST API endpoints (actual wiring)

#### Authentication
- ❌ `POST /api/auth/register/` - User registration
- ❌ `POST /api/auth/login/` - User login (email/phone + password)
- ❌ `POST /api/auth/refresh/` - Token refresh
- ❌ `POST /api/auth/logout/` - User logout
- ❌ `POST /api/auth/verify-token/` - Token verification

#### User Management
- ❌ `GET /api/users/profile/` - Get user profile
- ❌ `PUT /api/users/profile/` - Update profile
- ❌ `GET /api/users/medical-history/` - Get medical history
- ❌ `POST /api/users/medical-history/` - Add/update medical history
- ❌ `GET /api/users/consent/` - Get consent status
- ❌ `POST /api/users/consent/` - Update consent

#### Image Analysis (session-based for now)
- ✅ `POST /api/analysis/upload/` - Upload image for analysis (multipart: `image`, `analysis_type`)
- ✅ `GET /api/analysis/history/` - List analysis summaries from the user's session
- ✅ `GET /api/analysis/<analysis_id>/` - Get one analysis record from the session
- ✅ `DELETE /api/analysis/<analysis_id>/` - Delete one analysis record from the session
- ❌ `GET /api/analysis/progress/{id}/` - Get analysis progress
- ❌ `GET /api/analysis/compare/` - Compare historical results

#### Diagnosis
- ❌ `GET /api/diagnosis/conditions/{analysis_id}/` - Get detected conditions
- ❌ `GET /api/diagnosis/severity/{analysis_id}/` - Get severity assessment
- ❌ `GET /api/diagnosis/explanation/{analysis_id}/` - Get AI explanation
- ❌ `GET /api/diagnosis/visualization/{analysis_id}/` - Get visualization data

#### Recommendations
- ❌ `GET /api/recommendations/care-routine/{analysis_id}/` - Get care routine
- ❌ `GET /api/recommendations/products/{analysis_id}/` - Get product recommendations
- ❌ `GET /api/recommendations/educational/{condition}/` - Get educational content
- ❌ `POST /api/recommendations/validate-safety/` - Validate product safety

#### Feedback
- ❌ `POST /api/feedback/diagnosis/` - Submit diagnosis feedback
- ❌ `POST /api/feedback/recommendation/` - Submit recommendation feedback
- ❌ `GET /api/feedback/history/` - Get feedback history

#### Admin (Protected)
- ❌ `GET /api/admin/users/` - List all users
- ❌ `PUT /api/admin/users/{id}/role/` - Update user role
- ❌ `GET /api/admin/models/` - List AI models
- ❌ `POST /api/admin/models/update/` - Update AI model
- ❌ `GET /api/admin/analytics/` - System analytics
- ❌ `GET /api/admin/feedback/` - View all feedback

**Legend**: ✅ Implemented | ⏳ Partial | ❌ Not Implemented

## Technology Stack (actual deps in `requirements.txt`)

### Backend ✅ Configured

- ✅ **Framework**: Django 4.2.7
- ✅ **API**: Django REST Framework 3.14.0
- ⏳ **Database**: 
  - Development: SQLite3 (currently in use)
  - Production: MySQL 8.0+ (configured, not connected)
- ✅ **Authentication**: JWT (djangorestframework-simplejwt 5.3.0) - Configured
- ✅ **Image Processing**: Pillow 10.1.0, OpenCV 4.8.1.78
- **AI/ML**:
  - ✅ MediaPipe (detection)
  - ✅ PyTorch (U-Net + EfficientNet)
  - ✅ Ultralytics YOLOv8 (scalp detector)
  - ✅ XGBoost (severity model loader + fallback rules)
  - ⏳ LLM integration (optional; requires configuration)
- **Async**: Celery/Redis are in dependencies, but the pipeline currently runs inline in the request path

### Development Tools
- **Environment**: python-dotenv
- **CORS**: django-cors-headers
- **Validation**: Django validators
- **Testing**: pytest-django
- **Code Quality**: black, flake8

## Functional Requirements (22 Total)

### FR1: User Authentication
- Secure registration and login (email/phone + password)
- JWT-based session handling

### FR2: Database Storage
- User profiles, authentication credentials (hashed)
- Uploaded images (secure media storage)
- Diagnostic results and reports

### FR3: User Image Input
- Upload or capture high-quality images (face/scalp)
- Web and mobile interface support

### FR4: Image Validation
- Validate clarity, lighting, file size (≤10MB)
- Confirm image type (skin/scalp) before processing
- Prompt user to retake if invalid

### FR5: AI-Based Detection Pipeline
- Mediapipe for face/scalp detection
- U-Net for segmentation 
- EfficientNet-B4 + YOLOv8 for classification
- XGBoost for severity scoring
- LLM for recommendations

### FR6: AI-Based Skin Condition Detection
- Detect: Acne, Dark Spots, Hyperpigmentation, Dryness
- Using pre-trained CNN models

### FR7: AI-Based Scalp Condition Detection
- Detect: Dandruff, Dryness, Oiliness, Hair Fall indicators

### FR8: Severity Classification
- Categorize conditions: Mild, Moderate, Severe

### FR9: Personalized Diagnosis and Care Suggestions
- Custom suggestions based on AI results, age, gender, lifestyle

### FR10: Medical-History-Aware Treatment Recommendation
- Filter unsafe products based on medical history
- Consider diabetes, allergies, pregnancy, heart issues
- Suggest medically appropriate alternatives

### FR11: Result Visualization and Report Generation
- Textual reports with detected issues, severity, treatments
- Visual indicators (color coding: red = serious)

### FR12: Result Storage and History Tracking
- Dashboard with past diagnoses
- Progress tracking over time
- Historical comparison

### FR13: User Profile Management
- Update personal profile
- Edit medical information
- View saved reports
- Manage uploaded images

### FR14: Feedback and Model Improvement
- User rating system for diagnosis accuracy
- Help refine AI models over time

### FR15: Data Security and Privacy
- Encrypt all stored data (medical info, images)
- Accessible only to authorized users
- AES-256 encryption

### FR16: Error Handling
- Informative error messages
- Handle poor quality images, network issues, processing errors

### FR17: Safe Recommendation Enforcement
- Ensure all recommendations are medically safe
- Avoid harmful or risky products

### FR18: Transparent AI Output Explanation
- Simple explanation of why condition was detected
- Highlighted regions, detected patterns

### FR19: User Education Module
- Educational tips on lifestyle, environment, habits
- Content related to detected conditions

### FR20: Quick Response Handling
- Notify if analysis takes longer than expected
- Progress indicators for user engagement

### FR21: Automatic Privacy Protection
- Anonymize user images before model improvement
- Anonymize for dataset expansion

### FR22: Regular Model Update Support
- Allow periodic AI model updates
- Improve accuracy based on new data and feedback

## Non-Functional Requirements

### Performance
- **Image Analysis**: 3-5 seconds per image
- **Real-time Scanning**: Minimum 20 FPS for camera-based scanning
- **Throughput**: 50 analyses per minute without degradation
- **API Response**: < 500ms for non-AI endpoints
- **AR Latency**: < 200ms for AR-based hair preview

### Accuracy
- **Target**: 75-80% accuracy on benchmark dermatology datasets
- **Consistency**: Repeatable outputs for similar images

### Scalability
- **Concurrent Users**: Support up to 1000 concurrent users
- **Auto-scaling**: Server resources scale based on request spikes
- **Cloud Storage**: Dynamic scaling for photo history

### Security
- **Encryption**: End-to-end encryption (AES-256) for images and data
- **Authentication**: Secure JWT-based authentication
- **Access Control**: Role-based access control
- **Data Protection**: Only authenticated users access their data
- **SSL/TLS**: All communications encrypted in transit

### Reliability
- **Uptime**: 99% availability (24/7)
- **Error Recovery**: Auto-switch to photo upload if real-time scanning fails
- **Backup**: Automatic cloud backup and recovery
- **Data Integrity**: Regular backups and system audits

### Usability
- **Interface**: Minimal, intuitive, clearly labeled
- **Instructions**: Clear instructions and progress indicators
- **Multilingual**: Support English/Urdu
- **Accessibility**: Large icons, simple layout
- **Real-time Feedback**: Progress indicators during analysis

### Maintainability
- **Modular Design**: Components easily updatable
- **Model Updates**: ML models upgradable without affecting main flow
- **Clean Architecture**: Easy patching, bug fixes, feature additions
- **Documentation**: Comprehensive code documentation
- **Version Control**: Git-based version control

### Compatibility
- **Browsers**: Run smoothly on web browsers
- **Mobile**: Support mobile devices
- **Formats**: Support JPG, PNG, JPEG
- **Deployment**: Deployable on AWS/Firebase with minimal reconfiguration

### Privacy
- **Consent**: Explicit consent before collecting medical data
- **Anonymization**: Anonymize data used for AI training
- **Access Control**: Registered User, Admin access levels
- **Data Withdrawal**: Users can withdraw consent anytime

### Health Safety Compliance
- **Medical Safety**: All treatment suggestions medically safe
- **Context-Aware**: Consider user's medical history
- **Standards**: Compliant with health-data handling standards

## Security Considerations

1. **Data Encryption**
   - AES-256 encryption for sensitive medical data at rest
   - HTTPS/TLS for all communications
   - Encrypt images before storage
   - Secure password hashing (bcrypt)

2. **Authentication & Authorization**
   - JWT tokens with refresh mechanism
   - Role-based access control (User, Admin, Salons, Dermatologist)
   - API rate limiting
   - Optional 2FA support

3. **Data Privacy**
   - GDPR compliance considerations
   - User consent management
   - Image anonymization for training
   - Secure image storage and deletion
   - User data withdrawal capability

4. **Access Control**
   - Role-based permissions
   - Secure API endpoints
   - Session management

## Performance Requirements

- **Image Processing**: 3-5 seconds per image
- **API Response Time**: < 500ms for non-AI endpoints
- **Concurrent Users**: 1000 concurrent users
- **Throughput**: 50 analyses per minute
- **Real-time Scanning**: 20 FPS minimum
- **AR Latency**: < 200ms
- **Accuracy Target**: 75-80% for condition detection

## Future Enhancements

1. **Advanced Skin Conditions**: Rosacea, fungal infections
2. **AI-Based Personalized Treatment Plans**: Daily progress tracking, environmental factors
3. **Real-Time Scalp Health Monitoring**: Early detection, smart scanning
4. **Hair Growth and Damage Tracking**: Before/after comparison, progress graphs
5. **Smart Device Integration**: Smart mirrors, wearables (UV exposure, moisture)
6. **Predictive Analysis**: Forecast future issues based on patterns
7. **AR Enhancements**: Live AR previews, 3D visualization
8. **Expert Collaboration**: Dermatologist review system
9. **Doctor Appointment Booking**: Integration with scheduling
10. **Multi-language Expansion**: Additional language support

## Project Structure (key folders)

```
fyp-development-be/
├── config/                 # Django project settings
│   ├── settings.py         # Main settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI configuration
│   └── asgi.py             # ASGI configuration
├── users/                  # User management app ✅
│   ├── models.py           # ✅ UserProfile, MedicalHistory (implemented)
│   ├── views.py            # ⏳ Basic views (not REST API yet)
│   └── migrations/         # ✅ Applied
├── frontend/               # Mock frontend app ✅
│   ├── views.py            # ✅ 9 view functions (implemented)
│   ├── urls.py             # ✅ URL routing (implemented)
│   └── templates/          # ✅ 9 HTML templates (implemented)
├── image_analysis/         # Upload + analysis entrypoint ✅ (models pending)
│   ├── models.py           # ❌ Placeholder
│   ├── views.py            # ✅ AnalyzeImageView
│   └── migrations/         # ⏳ Empty
├── diagnosis/              # App placeholder; logic is mainly in pipeline ⏳
│   ├── models.py           # ❌ Placeholder
│   ├── views.py            # ⏳
│   └── migrations/         # ⏳ Empty
├── recommendations/        # App placeholder; logic is mainly in pipeline ⏳
│   ├── models.py           # ❌ Placeholder
│   ├── views.py            # ⏳
│   └── migrations/         # ⏳ Empty
├── feedback/               # Feedback app ⏳
│   ├── models.py           # (currently empty)
│   ├── serializers.py      # ⏳ Structure exists
│   ├── views.py            # ❌ Empty
│   └── urls.py             # ⏳ Structure exists
├── core/                   # Shared utilities ✅ (AI pipeline lives here)
│   ├── ai_models/          # ✅ MediaPipe/U-Net/EfficientNet/YOLO/XGBoost wrappers + pipeline
│   │   ├── efficientnet_b4_skin.pth  # ✅ EfficientNet skin classifier weights
│   ├── models/             # ✅ model assets (YOLO .pt, XGBoost .json, U-Net checkpoints)
│   ├── encryption/         # ❌ Placeholder (not implemented yet)
│   └── validators/         # Custom validators ⏳
│       └── __init__.py     # ⏳ Empty (needs implementation)
├── templates/              # Global templates ✅
│   ├── base.html           # ✅ Base template
│   └── frontend/           # ✅ 9 page templates
├── static/                 # Source static files ✅
│   ├── css/
│   │   └── style.css       # ✅ Comprehensive styling
│   ├── images/             # Empty
│   └── js/                 # Empty
├── media/                  # User uploaded files ⏳
│   ├── uploads/            # ✅ 12 original images
│   └── processed/          # ✅ 24 processed images (face/scalp)
├── staticfiles/            # Collected static files ✅
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── SETUP.md               # Setup instructions
├── ARCHITECTURE.md        # This file
└── manage.py             # Django management script
```

## Model training + updating weights (how it fits the architecture)

This repo keeps **inference weights inside the repo** so the Django pipeline can load them by default:

- **EfficientNet (skin)**: `core/ai_models/efficientnet_b4_skin.pth`
- **YOLO (scalp)**: `core/models/yolo_scalp.pt`
- **XGBoost severity**: `core/models/severity_model.json`
- **U-Net**: `core/models/unet_checkpoints/**/resnet_unet_best.pth` (or other `best_model.pth`)

When you retrain/fine-tune EfficientNet, the safest flow is:

1. Train using your dataset folders (`dataset/efficientnet_b4/train`, `dataset/efficientnet_b4/val`)
2. Save the **best checkpoint** back to `core/ai_models/efficientnet_b4_skin.pth`
3. Restart Django so the singleton pipeline reloads the new weights

### Async Processing
- Use Celery for long-running AI tasks
- Real-time progress updates via WebSocket (future)
- Queue management for high load

## Critical next steps (highest impact)

1. Add **DB models** for storing `ImageUpload` + `AnalysisResult` + per-condition outputs.
2. Enable and implement **REST API routes** under `/api/...` (currently commented in `config/urls.py`).
3. Implement **encryption** utilities and decide what needs encryption at rest (medical history and/or images).
4. Add a small **evaluation script** for EfficientNet (per-class accuracy, confusion matrix) so improvements are measurable.

## Implementation Status Summary

### ✅ Completed
- Project structure and Django configuration
- User management (registration, login, profiles)
- Medical history management (full CRUD)
- Frontend mock interface (9 pages, modern UI)
- MediaPipe face/scalp detection integration
- U-Net segmentation integration
- Basic image upload and processing
- Mock analysis flow with severity scoring
- Medical history-aware recommendation filtering
- Session-based result storage
- Comprehensive documentation

### ⏳ In Progress / Partial
- REST API endpoints (structure defined, partial implementation)
- AI model integration (MediaPipe, U-Net done, others pending)
- Database models for analysis results (partial)
- Image validation (clarity, lighting)
- JWT authentication API implementation

### ❌ Pending
- EfficientNet, YOLOv8, XGBoost, LLM model integration
- Complete database models for ImageUpload, AnalysisResult, ConditionDetection, etc.
- Complete REST API endpoint implementations
- End-to-end encryption
- Role-based access control
- Unit and integration tests
- Production deployment configuration

## Deployment Considerations

- **Cloud Platforms**: AWS, Firebase, Azure (planned)
- **Containerization**: Docker support (not configured yet)
- **Database**: MySQL with replication for high availability (configured, not connected)
- **File Storage**: S3 or similar for scalable image storage (not implemented yet)
- **CDN**: For static assets and media (not configured yet)
- **Monitoring**: Application performance monitoring (not configured yet)
- **Logging**: Centralized logging system (not configured yet)

**Current Deployment**: Development server only (`python manage.py runserver`)
