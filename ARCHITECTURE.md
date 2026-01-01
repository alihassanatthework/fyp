# AI-Powered Skin and Scalp Treatment System - Architecture

## System Overview

The system is a full-stack application with React frontend and Django REST API backend, designed to diagnose skin and scalp conditions using AI-powered image analysis. The system analyzes user-uploaded images to detect conditions like acne, dark spots, dandruff, and hair fall, then provides personalized treatment recommendations based on medical history.

## Architecture Layers

### 1. **Frontend Layer (React)**
- User interface for image upload/capture
- Real-time camera-based scanning (20 FPS minimum)
- Display of analysis results with visualizations
- User profile and medical history management
- Product recommendations display
- Progress indicators and feedback
- Dashboard for history tracking
- Multilingual support (English/Urdu)
- Future: AR hairstyle preview

### 2. **API Gateway Layer (Django REST Framework)**
- RESTful API endpoints
- Request/Response handling
- Authentication & Authorization (JWT-based)
- Role-based access control (User, Admin, Salons, Dermatologist)
- Rate limiting
- Input validation
- Error handling with informative messages
- Progress tracking for long-running operations

### 3. **Business Logic Layer (Django Apps)**

#### **Users App**
- User authentication (email/phone + password)
- User registration and login
- User profile management
- Medical history management (allergies, pregnancy, diabetes, heart issues)
- Role management (User, Admin, Salons, Dermatologist)
- User feedback collection

#### **Image Analysis App**
- Image upload/capture handling
- Image validation (clarity, lighting, file size ≤10MB)
- Image type confirmation (skin/scalp)
- Image preprocessing and normalization
- Secure image storage
- Image anonymization for model training

#### **Diagnosis App**
- AI-based condition detection pipeline
- Skin condition detection (acne, dark spots, hyperpigmentation, dryness)
- Scalp condition detection (dandruff, dryness, oiliness, hair fall)
- Severity classification (Mild, Moderate, Severe)
- Result storage and history tracking
- Progress comparison over time

#### **Recommendations App**
- Personalized care suggestions based on AI results
- Medical-history-aware filtering
- Product recommendations with safety checks
- Care routine generation
- Educational content (lifestyle tips, habits)
- Transparent AI output explanations

#### **Feedback App** (Future)
- User rating system for diagnosis accuracy
- Model improvement feedback loop
- Expert review system (dermatologists)

### 4. **AI/ML Service Layer**

#### **Detection Models**
- **Mediapipe**: Face & Scalp Detection
- **U-Net**: Image Segmentation for condition localization
- **EfficientNet-B4 + YOLOv8**: Condition Classification
  - Skin: Acne, Dark Spots, Hyperpigmentation, Dryness
  - Scalp: Dandruff, Dryness, Oiliness, Hair Fall Indicators

#### **Analysis Models**
- **XGBoost**: Severity Scoring (Mild, Moderate, Severe)
- **LLM**: Recommendation Engine for personalized care suggestions

#### **Processing Pipeline**
1. Image Preprocessing (normalization, enhancement)
2. Face/Scalp Detection (Mediapipe)
3. Region Segmentation (U-Net)
4. Condition Classification (EfficientNet-B4 + YOLOv8)
5. Severity Assessment (XGBoost)
6. Recommendation Generation (LLM with medical history filtering)

### 5. **Data Layer**
- **MySQL Database**: User data, medical history, analysis results
- **File Storage**: User-uploaded images (encrypted, local/S3)
- **Cache Layer**: Redis (optional, for performance)
- **Backup System**: Automatic cloud backup and recovery

### 6. **Security Layer**
- End-to-end encryption (AES-256) for sensitive data
- JWT authentication with refresh tokens
- HTTPS/TLS enforcement
- Data encryption at rest
- Role-based access control
- Image anonymization for training data
- User consent management
- Secure password storage (bcrypt)

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

### Users & Authentication
- **User**: Basic user information (email, phone, password hash)
- **UserProfile**: Extended profile data (name, gender, age, skin type, hair type)
- **MedicalHistory**: Allergies, pregnancy status, medications, chronic conditions
- **UserRole**: Role assignment (User, Admin, Salons, Dermatologist)
- **UserConsent**: Consent tracking for data usage

### Image Analysis
- **ImageUpload**: Uploaded images metadata (file path, upload date, image type)
- **ImageValidation**: Validation results (clarity, lighting, size)
- **AnalysisResult**: AI analysis results (timestamp, processing time)
- **ConditionDetection**: Detected conditions with confidence scores
  - Skin: Acne, Dark Spots, Hyperpigmentation, Dryness
  - Scalp: Dandruff, Dryness, Oiliness, Hair Fall
- **SeverityAssessment**: Severity scores (Mild, Moderate, Severe) per condition
- **SegmentationData**: U-Net segmentation masks and regions

### Recommendations
- **CareRoutine**: Personalized care routines (daily, weekly)
- **ProductRecommendation**: Suggested products with safety flags
- **Product**: Product catalog with ingredients and safety information
- **EducationalContent**: Lifestyle tips, habits, environmental factors
- **AIExplanation**: Transparent explanations of AI decisions

### Feedback & Improvement
- **UserFeedback**: User ratings and comments on diagnosis
- **ModelVersion**: AI model versions and update history
- **ModelPerformance**: Accuracy metrics and improvement tracking

## API Endpoints Structure

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login (email/phone + password)
- `POST /api/auth/refresh/` - Token refresh
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/verify-token/` - Token verification

### User Management
- `GET /api/users/profile/` - Get user profile
- `PUT /api/users/profile/` - Update profile
- `GET /api/users/medical-history/` - Get medical history
- `POST /api/users/medical-history/` - Add/update medical history
- `GET /api/users/consent/` - Get consent status
- `POST /api/users/consent/` - Update consent

### Image Analysis
- `POST /api/analysis/upload/` - Upload image for analysis
- `POST /api/analysis/validate/` - Validate image before upload
- `POST /api/analysis/confirm-type/` - Confirm image type (skin/scalp)
- `GET /api/analysis/results/{id}/` - Get analysis result
- `GET /api/analysis/history/` - Get user's analysis history
- `GET /api/analysis/progress/{id}/` - Get analysis progress
- `GET /api/analysis/compare/` - Compare historical results

### Diagnosis
- `GET /api/diagnosis/conditions/{analysis_id}/` - Get detected conditions
- `GET /api/diagnosis/severity/{analysis_id}/` - Get severity assessment
- `GET /api/diagnosis/explanation/{analysis_id}/` - Get AI explanation
- `GET /api/diagnosis/visualization/{analysis_id}/` - Get visualization data

### Recommendations
- `GET /api/recommendations/care-routine/{analysis_id}/` - Get care routine
- `GET /api/recommendations/products/{analysis_id}/` - Get product recommendations
- `GET /api/recommendations/educational/{condition}/` - Get educational content
- `POST /api/recommendations/validate-safety/` - Validate product safety

### Feedback
- `POST /api/feedback/diagnosis/` - Submit diagnosis feedback
- `POST /api/feedback/recommendation/` - Submit recommendation feedback
- `GET /api/feedback/history/` - Get feedback history

### Admin (Protected)
- `GET /api/admin/users/` - List all users
- `PUT /api/admin/users/{id}/role/` - Update user role
- `GET /api/admin/models/` - List AI models
- `POST /api/admin/models/update/` - Update AI model
- `GET /api/admin/analytics/` - System analytics
- `GET /api/admin/feedback/` - View all feedback

## Technology Stack

### Backend
- **Framework**: Django 4.2.7
- **API**: Django REST Framework 3.14.0
- **Database**: MySQL 8.0+
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Image Processing**: Pillow, OpenCV
- **AI/ML Libraries**:
  - **Mediapipe**: Face & Scalp Detection
  - **PyTorch/TensorFlow**: U-Net, EfficientNet-B4, YOLOv8
  - **XGBoost**: Severity Classification
  - **LLM Integration**: For recommendation engine (OpenAI/Anthropic API or local model)
- **Encryption**: cryptography library (AES-256)
- **Task Queue**: Celery (for async AI processing)
- **Cache**: Redis (optional)

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

## Project Structure

```
fyp-development-be/
├── config/                 # Django project settings
│   ├── settings.py         # Main settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI configuration
│   └── asgi.py             # ASGI configuration
├── users/                  # User management app
│   ├── models.py           # User, UserProfile, MedicalHistory, UserRole
│   ├── serializers.py      # DRF serializers
│   ├── views.py            # API views
│   ├── urls.py             # App URLs
│   └── permissions.py      # Role-based permissions
├── image_analysis/         # Image processing app
│   ├── models.py           # ImageUpload, ImageValidation
│   ├── serializers.py      # Image serializers
│   ├── views.py            # Upload/validation views
│   ├── validators.py       # Image validation logic
│   └── urls.py             # App URLs
├── diagnosis/              # Condition detection app
│   ├── models.py           # AnalysisResult, ConditionDetection, SeverityAssessment
│   ├── serializers.py      # Diagnosis serializers
│   ├── views.py            # Analysis views
│   └── urls.py             # App URLs
├── recommendations/        # Care routines & products app
│   ├── models.py           # CareRoutine, ProductRecommendation, Product
│   ├── serializers.py      # Recommendation serializers
│   ├── views.py            # Recommendation views
│   ├── safety_checker.py   # Medical history filtering
│   └── urls.py             # App URLs
├── feedback/               # Feedback app (future)
│   ├── models.py           # UserFeedback, ModelVersion
│   └── views.py            # Feedback views
├── core/                   # Shared utilities
│   ├── ai_models/          # AI model wrappers
│   │   ├── mediapipe_detector.py
│   │   ├── unet_segmenter.py
│   │   ├── efficientnet_classifier.py
│   │   ├── yolo_detector.py
│   │   ├── xgboost_severity.py
│   │   └── llm_recommender.py
│   ├── encryption/         # Encryption utilities
│   │   └── encryptor.py    # AES-256 encryption
│   ├── validators/         # Custom validators
│   │   └── image_validators.py
│   └── permissions.py      # Custom permissions
├── media/                  # User uploaded files (encrypted)
├── staticfiles/            # Collected static files
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── SETUP.md               # Setup instructions
├── ARCHITECTURE.md        # This file
└── manage.py             # Django management script
```

## AI Model Integration Architecture

### Model Loading & Management
- Models loaded on startup or lazy-loaded
- Version tracking for model updates
- Model performance monitoring
- A/B testing support for new models

### Processing Pipeline
1. **Image Reception**: Receive and validate image
2. **Preprocessing**: Normalize, enhance, resize
3. **Detection**: Mediapipe detects face/scalp regions
4. **Segmentation**: U-Net segments condition regions
5. **Classification**: EfficientNet-B4 + YGBoost classify conditions
6. **Severity**: XGBoost scores severity
7. **Recommendation**: LLM generates personalized suggestions
8. **Safety Check**: Filter based on medical history
9. **Result Storage**: Save to database
10. **Response**: Return to user

### Async Processing
- Use Celery for long-running AI tasks
- Real-time progress updates via WebSocket (future)
- Queue management for high load

## Deployment Considerations

- **Cloud Platforms**: AWS, Firebase, Azure
- **Containerization**: Docker support
- **Database**: MySQL with replication for high availability
- **File Storage**: S3 or similar for scalable image storage
- **CDN**: For static assets and media
- **Monitoring**: Application performance monitoring
- **Logging**: Centralized logging system
