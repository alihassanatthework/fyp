## ME — AI Skin & Scalp Assistant — Architecture

> **Phase 1**: ✅ Complete — JWT auth, profiles, skin/scalp AI pipeline, analysis DB, diagnosis, recommendations, feedback, password reset.
> **Phase 2**: ✅ Complete — Providers, Bookings, Makeup assistance, Fashion assistance, premium tier, mobile UI.
> **Phase 3 (current)**: ✅ Groq LLM integration, 5-class scalp classifier, skin-tone-driven makeup/fashion, medication recommendations with medical-history safety filtering, server-side reporting, legal/consent pages.

---

## Current State (as of 19 June 2026)

Key changes layered on top of the original Phase 1/2 build:

### AI / ML
- **LLM = Groq** (`llama-3.3-70b`, `core/llm_groq.py`) is the **primary** recommender for skin/scalp care, makeup, and fashion, with **Ollama** as local fallback. Zero-shot prompting (no training). Browser User-Agent header added to bypass Cloudflare.
- **Scalp branch rebuilt**: replaced the broken single-class `yolo_scalp.pt` with a **5-class EfficientNet-B0 classifier** (`core/ai_models/scalp_classifier.py`, `scalp_classifier_v1.pth`): Alopecia · Dermatitis · Infections · Normal · Psoriasis. **98.6% test accuracy.** Pipeline prefers it; YOLO kept as fallback. U-Net (skin eczema) untouched.
  - Dataset built by `scripts/clean_organize_scalp.py` (pHash dedup, quality filter, 5-class map, 80/10/10 split → `dataset/scalp_clean/`). Trained by `train_scalp_5class.py` / `scripts/train_scalp.sh`. Evaluated by `scripts/evaluate_scalp.py`.
- **Makeup & Fashion** now derive palettes/shades from **skin tone + undertone + season + event** (MediaPipe FaceMesh/Pose, LAB skin-tone + Fitzpatrick + undertone), with per-request variety. No more identical results for everyone.
- **Medication recommendations**: LLM returns real pharmaceutical drugs (generic + brand + form + strength). Strengthened safety rules + a **deterministic backend filter** (`_filter_unsafe_medicines`) that drops contraindicated drugs based on the user's medical history (pregnancy, allergies, cardiovascular, etc.).

### Backend
- **Accounts**: `UserProfile.account_type` (free/premium); `POST /api/account/upgrade/`. Free tier daily scan limit (`FREE_DAILY_SCAN_LIMIT=5`, 429 when exceeded); premium unlimited.
- **History API** returns full list, ordered, with ISO `created_at` + conditions (fixes "Invalid Date" + sorting).
- **Reporting**: `POST /api/report/` emails the official inbox (`me.offical.team.system@gmail.com`) via Django mail (needs SMTP env to deliver).
- **Scalp severity** derived from classifier confidence in `image_analysis/views.py`.

### Frontend (React)
- Axios interceptor parses DRF field errors (shows real reason, not "status code 400").
- Diagnosis report: all-class scalp chart, **Recommended Medications** card with OTC/Rx badges + per-medicine "safe for you" note, uniform Analysis Images frames.
- Uniform square `object-fit: contain` upload previews across skin/scalp/makeup/fashion.
- History: shows 6 recent + "View all" toggle.
- Legal pages (Terms, Privacy, Consent) rewritten professional + project-specific; signup requires consent checkbox (Terms + Privacy + Consent) before registering.
- Footer/Contact wired to official Instagram, LinkedIn, Gmail.

### Config / Secrets
- `.env` (gitignored): `GROQ_API_KEY`, optional `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` (Gmail app password) for live report email.
- `.claude/` gitignored; commits never credit Claude as co-author.

---

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
| **React SPA + JWT auth** | ✅ Implemented | Real JWT auth, Axios auto-refresh interceptor, HEIC support |
| **Upload + analysis flow (React + API)** | ✅ Implemented | `AnalyzeImageView` calls the AI pipeline and returns JSON for React |
| **AI pipeline orchestration** | ✅ Implemented | `core/ai_models/pipeline.py` singleton pipeline |
| **MediaPipe detection** | ✅ Implemented | `core/ai_models/mediapipe_detector.py` (scalp detection fix for top-down photos included) |
| **U-Net segmentation** | ✅ Implemented | `core/ai_models/unet_segmenter.py` loads checkpoints |
| **ROI extraction** | ✅ Implemented | `core/ai_models/roi_extractor.py` |
| **EfficientNet skin classifier** | ✅ Implemented + weights present | `core/ai_models/efficientnet_classifier.py` loads `core/ai_models/efficientnet_b4_skin.pth` |
| **YOLOv8 scalp detector** | ✅ Implemented + weights present | `core/ai_models/yolo_detector.py` loads `core/models/yolo_scalp.pt` |
| **XGBoost severity** | ✅ Implemented + weights present | `core/ai_models/xgboost_severity.py` loads `core/models/severity_model.json` |
| **LLM recommender** | ⏳ Optional/partial | Wrapper exists; requires local model path or API key to be useful |
| **REST API — Auth** | ✅ Implemented | register, login, logout (blacklist), me, change-password, forgot/reset-password, token refresh |
| **REST API — Profile** | ✅ Implemented | `GET/PATCH /api/profile/` |
| **REST API — Analysis** | ✅ Implemented | upload, history, stats, detail, delete |
| **REST API — Diagnosis** | ✅ Implemented | `GET /api/diagnosis/`, `GET /api/diagnosis/<analysis_id>/` |
| **REST API — Recommendations** | ✅ Implemented | `GET /api/recommendations/`, `GET /api/recommendations/<analysis_id>/` |
| **REST API — Feedback** | ✅ Implemented | `GET /api/feedback/<id>/`, `POST /api/feedback/<id>/submit/` |
| **Analysis DB models** | ✅ Implemented | `AnalysisResult`, `DiagnosisReport`, `Recommendation`, `AnalysisFeedback` — all with migrations |
| **PostgreSQL database** | ✅ Implemented | Default; `USE_SQLITE` env flag for local dev |
| **JWT token blacklist on logout** | ✅ Implemented | simplejwt blacklist app wired to logout endpoint |
| **Email backend** | ✅ Implemented | Console in dev; SMTP in prod via `EMAIL_HOST_USER` env |
| **Password reset via email** | ✅ Implemented | One-time token flow (`forgot-password` + `reset-password`) |
| **Rate limiting** | ✅ Implemented | Disabled locally; Redis-backed in prod |
| **WhiteNoise static files** | ✅ Implemented | Production static file serving |
| **CORS from env** | ✅ Implemented | `CORS_ALLOWED_ORIGINS` controlled via env variable |
| **Production security flags** | ✅ Implemented | HSTS + SSL redirect auto-enabled when `DEBUG=False` |
| **Test suite** | ✅ 39 tests passing | `test_auth.py`, `test_analysis.py`, `test_profile.py`, `test_password_reset.py` |
| **Encryption utilities** | ❌ Placeholder | `core/encryption/__init__.py` is not implemented |
| **Role-based access control** | ❌ Not implemented | Structure ready, needs implementation |
| **AI model training** | ❌ Scripts exist, not trained | EfficientNet + U-Net need GPU training; scripts are present |
| **Deployment** | 🔲 Not yet done | Render + Neon + Vercel — planned |

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

#### `users` ✅ Implemented (models/migrations/REST API exist)
- ✅ User registration and login via REST API (`POST /api/auth/register/`, `POST /api/auth/login/`)
- ✅ JWT logout with refresh token blacklisting (`POST /api/auth/logout/`)
- ✅ Token refresh (`POST /api/auth/token/refresh/`)
- ✅ Current user endpoint (`GET /api/auth/me/`)
- ✅ Change password (`POST /api/auth/change-password/`)
- ✅ Password reset via email (`POST /api/auth/forgot-password/`, `POST /api/auth/reset-password/`)
- ✅ User profile management via REST API (`GET/PATCH /api/profile/`)
- ✅ UserProfile model (age, gender, skin_type, hair_type) and MedicalHistory model
- ✅ Email backend (console dev / SMTP prod)
- ❌ Role management (User, Admin, Salons, Dermatologist) - structure ready, not implemented
- ❌ User consent management - not implemented

#### `image_analysis` ✅ Implemented (view + DB model + migrations exist)
- ✅ Image upload/capture handling (`AnalyzeImageView`)
- ✅ Basic image validation (file size, format; HEIC supported via pillow-heif)
- ✅ Image type confirmation (skin/scalp selection)
- ✅ MediaPipe face/scalp detection and cropping (scalp detection fix for top-down photos)
- ✅ Secure image storage (`media/uploads/`, `media/processed/`)
- ✅ U-Net segmentation integrated for region segmentation
- ✅ ROI extraction tested successfully
- ✅ `AnalysisResult` DB model with all fields and migrations applied
- ✅ REST API: `POST /api/analysis/upload/`, `GET /api/analysis/history/`, `GET /api/analysis/stats/`, `GET/DELETE /api/analysis/<id>/`
- ❌ Image validation (clarity, lighting) - needs implementation
- ❌ Image anonymization for model training - needs implementation

#### `diagnosis` ✅ Implemented (model + migrations + REST API exist)
- ✅ AI-based condition detection pipeline (U-Net integrated)
- ✅ Skin condition detection (Acne, Dark Spots, Hyperpigmentation, Dryness)
- ✅ Scalp condition detection (Dandruff, Dryness, Oiliness, Hair Fall)
- ✅ Severity classification (Mild, Moderate, Severe) with 0-100 scoring
- ✅ `DiagnosisReport` DB model with migrations applied
- ✅ REST API: `GET /api/diagnosis/`, `GET /api/diagnosis/<analysis_id>/`
- ❌ Progress comparison over time — not implemented
- ❌ Transparent AI output explanation — not implemented

#### `recommendations` ✅ Implemented (model + migrations + REST API exist)
- ✅ Personalized care suggestions with medical history filtering
- ✅ Medical-history-aware safety checks
- ✅ `Recommendation` DB model with migrations applied
- ✅ REST API: `GET /api/recommendations/`, `GET /api/recommendations/<analysis_id>/`
- ❌ Educational content (lifestyle tips, habits) — not implemented
- ❌ Transparent AI output explanations — not implemented
- ❌ Product catalog (CareRoutine, ProductRecommendation, Product models) — not created yet

#### `feedback` ✅ Implemented (model + migrations + REST API exist)
- ✅ `AnalysisFeedback` DB model with migrations applied
- ✅ REST API: `GET /api/feedback/<id>/`, `POST /api/feedback/<id>/submit/`
- ❌ Aggregate feedback reporting / model improvement loop — not implemented

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
- **Database persistence** for results is implemented (`AnalysisResult`, `DiagnosisReport`, `Recommendation`, `AnalysisFeedback` models with migrations).

### 5) Data Layer

**Status**: ✅ Implemented

#### Database

- **Users + medical history**: implemented (`users` app migrations exist)
- **Analysis persistence**: implemented — `AnalysisResult`, `DiagnosisReport`, `Recommendation`, `AnalysisFeedback` models all have migrations applied
- **DB backend**: PostgreSQL by default; `USE_SQLITE=true` env flag switches to SQLite for local dev

#### File storage
- ✅ User-uploaded images stored in `media/uploads/`
- ✅ Processed images (face/scalp crops) in `media/processed/`
- ✅ Training datasets are stored under `dataset/` (EfficientNet and YOLO formats)
- ❌ Image encryption at rest is not implemented yet
- ❌ S3/Cloud storage integration - not implemented yet

### 6) Security Layer

**Status**: ✅ Mostly Implemented (encryption + RBAC pending)

- ✅ JWT authentication fully wired (register, login, logout with blacklist, token refresh)
- ✅ CORS headers configured via env variable (`CORS_ALLOWED_ORIGINS`)
- ✅ Environment variables support (`.env` file, python-dotenv)
- ✅ Secure password storage (Django default — PBKDF2)
- ✅ Comprehensive `.gitignore` (protects sensitive files)
- ✅ JWT refresh token blacklist on logout (simplejwt blacklist app)
- ✅ Password reset via one-time email token
- ✅ Rate limiting (disabled locally; Redis-backed in prod)
- ✅ Production security flags: HSTS + SSL redirect auto-enabled when `DEBUG=False`
- ✅ WhiteNoise for production static file serving
- ❌ Encryption utilities are placeholders (`core/encryption/`)
- ❌ Data encryption at rest — not implemented yet
- ❌ Role-based access control — structure ready, needs implementation
- ❌ Image anonymization for training data — not implemented yet
- ❌ User consent management — not implemented yet

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

### Image Analysis ✅ Implemented

- ✅ **AnalysisResult**: AI analysis results (image path, analysis type, conditions detected, severity scores, recommendations, chart images, timestamp) — migrations applied
- ❌ **ImageValidation**: Clarity/lighting validation results — not created yet
- ❌ **SegmentationData**: U-Net segmentation masks — not stored separately yet

### Diagnosis ✅ Implemented

- ✅ **DiagnosisReport**: Linked to `AnalysisResult`; stores structured condition + severity output — migrations applied
- ❌ **ConditionDetection** (separate per-condition rows) — folded into DiagnosisReport for now

### Recommendations ✅ Implemented

- ✅ **Recommendation**: Linked to `AnalysisResult`; stores personalized care suggestions with medical-history-aware filtering — migrations applied
- ❌ **Product**: Product catalog — not created yet
- ❌ **EducationalContent**: Lifestyle tips — not created yet

### Feedback & Improvement ✅ Implemented

- ✅ **AnalysisFeedback**: User ratings and comments on diagnosis — migrations applied
- ❌ **ModelVersion**: AI model versions and update history — not created yet
- ❌ **ModelPerformance**: Accuracy metrics — not created yet

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
- ✅ `POST /api/auth/register/` - User registration
- ✅ `POST /api/auth/login/` - User login (email + password)
- ✅ `POST /api/auth/logout/` - User logout (blacklists refresh token)
- ✅ `GET /api/auth/me/` - Current user info
- ✅ `POST /api/auth/change-password/` - Change password
- ✅ `POST /api/auth/forgot-password/` - Request password reset email
- ✅ `POST /api/auth/reset-password/` - Confirm reset with one-time token
- ✅ `POST /api/auth/token/refresh/` - JWT token refresh

#### User Management
- ✅ `GET /api/profile/` - Get user profile
- ✅ `PATCH /api/profile/` - Update profile
- ❌ `GET /api/users/consent/` - Get consent status — not implemented
- ❌ `POST /api/users/consent/` - Update consent — not implemented

#### Image Analysis
- ✅ `POST /api/analysis/upload/` - Upload image for analysis (multipart: `image`, `analysis_type`)
- ✅ `GET /api/analysis/history/` - List past analysis records (DB-backed)
- ✅ `GET /api/analysis/stats/` - Aggregated analysis statistics
- ✅ `GET /api/analysis/<id>/` - Get one analysis record
- ✅ `DELETE /api/analysis/<id>/` - Delete one analysis record
- ❌ `GET /api/analysis/compare/` - Compare historical results — not implemented

#### Diagnosis
- ✅ `GET /api/diagnosis/` - List all diagnosis reports for current user
- ✅ `GET /api/diagnosis/<analysis_id>/` - Get diagnosis for a specific analysis
- ❌ `GET /api/diagnosis/explanation/{analysis_id}/` - AI explanation — not implemented
- ❌ `GET /api/diagnosis/visualization/{analysis_id}/` - Visualization data — not implemented

#### Recommendations
- ✅ `GET /api/recommendations/` - List all recommendations for current user
- ✅ `GET /api/recommendations/<analysis_id>/` - Get recommendations for a specific analysis
- ❌ `GET /api/recommendations/educational/{condition}/` - Educational content — not implemented
- ❌ `POST /api/recommendations/validate-safety/` - Product safety validation — not implemented

#### Feedback
- ✅ `GET /api/feedback/<id>/` - Get feedback for an analysis
- ✅ `POST /api/feedback/<id>/submit/` - Submit feedback for an analysis

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
- ✅ **Database**: 
  - Development: SQLite3 (via `USE_SQLITE=true` env flag) or PostgreSQL
  - Production: PostgreSQL (default; Neon planned for deployment)
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

## Phase 2 — New Apps (In Progress)

### `providers` app ✅ Implemented
- **Model**: Provider (name, type, address, city, phone, lat/lng, working hours)
- **Endpoints**:
  - `GET /api/providers/` — list all providers (filter by type/city)
  - `GET /api/providers/nearby/?lat=&lng=&radius=` — nearby providers using Haversine formula
  - `GET /api/providers/<id>/` — provider detail
- **Admin**: Add dermatologists/salons manually via Django admin
- **Provider types**: dermatologist, salon, clinic

### `bookings` app ✅ Implemented
- **Model**: Booking (user FK, provider FK, date, time, notes, status)
- **Endpoints**:
  - `POST /api/bookings/` — create booking (sends confirmation email)
  - `GET  /api/bookings/` — user's bookings (filter by status)
  - `GET  /api/bookings/<id>/` — booking detail
  - `PATCH /api/bookings/<id>/cancel/` — cancel booking
  - `DELETE /api/bookings/<id>/` — delete booking
- **Status flow**: pending → confirmed → completed / cancelled
- **Email**: Confirmation email sent on booking (uses existing email config)

### `makeup` app ✅ Implemented
- **Model**: MakeupSuggestion (user, image, face_shape, skin_tone, suggestions JSON)
- **Pipeline**:
  1. MediaPipe FaceMesh (468 landmarks) → face shape classification (Oval/Round/Square/Heart/Oblong)
  2. OpenCV Lab color space → skin tone classification (Fair/Light/Medium/Tan/Deep)
  3. Ollama LLM (llama3.2) → personalized makeup suggestions JSON
  4. Rule-based fallback if Ollama is not running
- **Endpoints**:
  - `POST /api/makeup/suggest/` — upload face photo, returns suggestions
  - `GET  /api/makeup/history/` — user's past suggestions
- **No new ML model needed** — uses existing MediaPipe + OpenCV

### `fashion` app ✅ Implemented
- **Model**: FashionSuggestion (user, image, event_type, body_type, skin_tone, suggestions JSON)
- **Pipeline**:
  1. MediaPipe Pose (33 landmarks) → body type classification (Hourglass/Pear/Apple/Rectangle/Inverted Triangle)
  2. OpenCV → skin tone (reused from makeup app)
  3. Ollama LLM (llama3.2) → outfit suggestions JSON
  4. Rule-based fallback if Ollama is not running
- **Endpoints**:
  - `POST /api/fashion/suggest/` — upload photo + event type, returns suggestions
  - `GET  /api/fashion/history/` — user's past suggestions
- **Event types**: casual, formal, wedding, party, business, outdoor, sports
- **No new ML model needed** — uses existing MediaPipe Pose (already installed)

### Ollama Integration
- Local LLM server running at `http://localhost:11434`
- Model: `llama3.2` (text) — install with `ollama pull llama3.2`
- Both makeup and fashion have **full rule-based fallback** — app works without Ollama
- Future: swap to Groq API by changing one URL in services.py

## Future Enhancements

1. **Advanced Skin Conditions**: Rosacea, fungal infections
2. **AI-Based Personalized Treatment Plans**: Daily progress tracking, environmental factors
3. **Real-Time Scalp Health Monitoring**: Early detection, smart scanning
4. **Hair Growth and Damage Tracking**: Before/after comparison, progress graphs
5. **Smart Device Integration**: Smart mirrors, wearables (UV exposure, moisture)
6. **Predictive Analysis**: Forecast future issues based on patterns
7. **AR Enhancements**: Live AR previews, 3D visualization
8. **Groq API**: Replace Ollama with Groq for cloud-based LLM suggestions
9. **Multi-language Expansion**: English/Urdu support

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
│   ├── views.py            # ✅ Full REST API (register, login, logout, me, change-password, forgot/reset-password, token refresh)
│   ├── serializers.py      # ✅ Auth + profile serializers
│   ├── urls.py             # ✅ /api/auth/ and /api/profile/ routing
│   └── migrations/         # ✅ Applied
├── frontend/               # Legacy template UI ✅ (kept for compatibility)
│   ├── views.py            # ✅ 9 view functions (implemented)
│   ├── urls.py             # ✅ URL routing (implemented)
│   └── templates/          # ✅ 9 HTML templates (implemented)
├── image_analysis/         # Upload + analysis app ✅
│   ├── models.py           # ✅ AnalysisResult model
│   ├── views.py            # ✅ upload, history, stats, detail, delete
│   └── migrations/         # ✅ Applied
├── diagnosis/              # Diagnosis app ✅
│   ├── models.py           # ✅ DiagnosisReport model
│   ├── views.py            # ✅ list + detail endpoints
│   ├── urls.py             # ✅ /api/diagnosis/ routing
│   └── migrations/         # ✅ Applied
├── recommendations/        # Recommendations app ✅
│   ├── models.py           # ✅ Recommendation model
│   ├── views.py            # ✅ list + detail endpoints
│   ├── urls.py             # ✅ /api/recommendations/ routing
│   └── migrations/         # ✅ Applied
├── providers/              # Phase 2 — Provider listings ✅
│   ├── models.py           # ✅ Provider model
│   ├── views.py            # ✅ list, nearby, detail
│   └── urls.py             # ✅ /api/providers/
├── bookings/               # Phase 2 — Appointment booking ✅
│   ├── models.py           # ✅ Booking model
│   ├── views.py            # ✅ create, list, cancel
│   └── urls.py             # ✅ /api/bookings/
├── makeup/                 # Phase 2 — Makeup assistance ✅
│   ├── models.py           # ✅ MakeupSuggestion model
│   ├── services.py         # ✅ MediaPipe face shape + skin tone + Ollama
│   ├── views.py            # ✅ suggest, history
│   └── urls.py             # ✅ /api/makeup/
├── fashion/                # Phase 2 — Fashion assistance ✅
│   ├── models.py           # ✅ FashionSuggestion model
│   ├── services.py         # ✅ MediaPipe body type + Ollama
│   ├── views.py            # ✅ suggest, history
│   └── urls.py             # ✅ /api/fashion/
├── feedback/               # Feedback app ✅
│   ├── models.py           # ✅ AnalysisFeedback model
│   ├── serializers.py      # ✅ Feedback serializer
│   ├── views.py            # ✅ get + submit endpoints
│   ├── urls.py             # ✅ /api/feedback/ routing
│   └── migrations/         # ✅ Applied
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

1. **Train AI models** on GPU — EfficientNet and U-Net training scripts exist; run them to produce production-quality weights.
2. **Deploy** to Render (backend) + Neon (PostgreSQL) + Vercel (React SPA).
3. Implement **encryption** utilities (`core/encryption/`) and decide what needs AES-256 at rest.
4. Implement **role-based access control** (User, Admin, Salons, Dermatologist).
5. Add **educational content and product catalog** models for richer recommendations.

## Implementation Status Summary

### ✅ Completed (Phase 1)
- Project structure and Django configuration
- PostgreSQL database (USE_SQLITE flag for local dev)
- User management REST API: register, login, logout (blacklist), me, change-password, forgot/reset-password, token refresh
- Profile REST API: GET/PATCH /api/profile/
- Medical history management (full CRUD via UserProfile/MedicalHistory models)
- React SPA with real JWT auth and Axios auto-refresh interceptor
- HEIC image support (pillow-heif)
- MediaPipe face/scalp detection (scalp detection fix for top-down photos)
- U-Net segmentation integration
- EfficientNet-B4 skin classifier (weights present)
- YOLOv8 scalp detector (weights present)
- XGBoost severity model (weights present)
- Analysis REST API: upload, history, stats, detail, delete
- AnalysisResult DB model with migrations
- Diagnosis REST API: GET /api/diagnosis/, GET /api/diagnosis/<analysis_id>/
- DiagnosisReport DB model with migrations
- Recommendations REST API: GET /api/recommendations/, GET /api/recommendations/<analysis_id>/
- Recommendation DB model with migrations
- Feedback REST API: GET /api/feedback/<id>/, POST /api/feedback/<id>/submit/
- AnalysisFeedback DB model with migrations
- Email backend (console dev / SMTP prod)
- Password reset via one-time email token
- Rate limiting (Redis-backed in prod)
- WhiteNoise for production static files
- CORS from env variable
- Production security flags (HSTS, SSL redirect) auto-enabled when DEBUG=False
- 39 tests passing (test_auth.py, test_analysis.py, test_profile.py, test_password_reset.py)
- Comprehensive documentation

### ⏳ In Progress / Partial
- LLM recommender (wrapper exists; requires model path or API key)
- Image validation (clarity, lighting checks)

### ❌ Pending
- Encryption utilities (`core/encryption/` still placeholder)
- Role-based access control
- AI model training (EfficientNet + U-Net scripts exist, need GPU training run)
- Educational content and product catalog models
- Image anonymization for training data
- User consent management
- Production deployment (Render + Neon + Vercel — not yet done)

## Deployment Considerations

- **Cloud Platforms**: AWS, Firebase, Azure (planned)
- **Containerization**: Docker support (not configured yet)
- **Database**: MySQL with replication for high availability (configured, not connected)
- **File Storage**: S3 or similar for scalable image storage (not implemented yet)
- **CDN**: For static assets and media (not configured yet)
- **Monitoring**: Application performance monitoring (not configured yet)
- **Logging**: Centralized logging system (not configured yet)

**Current Deployment**: Development server only (`python manage.py runserver`)
