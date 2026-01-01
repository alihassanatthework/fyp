# AI-Powered Skin and Scalp Treatment System - Backend

Django REST API backend for the AI-Powered Skin and Scalp Personalized Treatment system.

## Features

- **User Authentication**: JWT-based authentication system
- **Image Analysis**: AI-powered image processing for skin and scalp conditions
- **Condition Detection**: Detects acne, dark spots, dandruff, and hair fall
- **Severity Assessment**: AI-based severity scoring
- **Personalized Recommendations**: Care routines and product suggestions based on analysis and medical history
- **Medical History Integration**: Safety checks based on allergies and pregnancy status
- **End-to-End Encryption**: Secure handling of sensitive user data

## Technology Stack

- **Framework**: Django 4.2.7
- **API**: Django REST Framework 3.14.0
- **Database**: MySQL 8.0+
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Image Processing**: Pillow, OpenCV
- **AI/ML**: Mediapipe, TensorFlow (U-Net)

## Prerequisites

- Python 3.9+
- MySQL 8.0+
- pip

## Installation & Setup

### 1. Clone the repository

```bash
cd "/Users/alihassan/Desktop/fyp devlopment be"
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you encounter issues installing `mysqlclient`, you may need to install MySQL development libraries:

**macOS:**
```bash
brew install mysql-client
export PATH="/usr/local/opt/mysql-client/bin:$PATH"
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install default-libmysqlclient-dev build-essential
```

**Windows:**
Download MySQL Connector/C from MySQL website and add to PATH, or use `pymysql` as an alternative.

### 4. Configure MySQL Database

Create a MySQL database:

```sql
CREATE DATABASE skin_scalp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configure Environment Variables

Copy the example environment file and update with your values:

```bash
cp .env.example .env
```

Edit `.env` file with your configuration:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=skin_scalp_db
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306

JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440

ENCRYPTION_KEY=your-32-byte-encryption-key-here
```

**Generate a secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**Generate an encryption key (32 bytes):**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 6. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create superuser (optional)

```bash
python manage.py createsuperuser
```

### 8. Run development server

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`

## Project Structure

```
fyp-development-be/
├── config/                 # Django project settings
│   ├── settings.py        # Main settings file
│   ├── urls.py            # Root URL configuration
│   ├── wsgi.py            # WSGI configuration
│   └── asgi.py            # ASGI configuration
├── users/                 # User management app
├── image_analysis/        # Image processing & AI app
├── diagnosis/             # Condition detection app
├── recommendations/       # Care routines & products app
├── core/                  # Shared utilities (to be created)
├── media/                 # User uploaded files
├── staticfiles/           # Collected static files
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── .env.example           # Example environment file
├── .gitignore            # Git ignore rules
├── ARCHITECTURE.md        # System architecture documentation
└── manage.py             # Django management script
```

## API Endpoints (To be implemented)

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Token refresh
- `POST /api/auth/logout/` - User logout

### User Management
- `GET /api/users/profile/` - Get user profile
- `PUT /api/users/profile/` - Update profile
- `GET /api/users/medical-history/` - Get medical history
- `POST /api/users/medical-history/` - Add/update medical history

### Image Analysis
- `POST /api/analysis/upload/` - Upload image for analysis
- `GET /api/analysis/results/{id}/` - Get analysis result
- `GET /api/analysis/history/` - Get user's analysis history

### Recommendations
- `GET /api/recommendations/care-routine/{analysis_id}/` - Get care routine
- `GET /api/recommendations/products/{analysis_id}/` - Get product recommendations

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Linting

```bash
flake8 .
```

## Performance Requirements

- **Image Processing**: 3-5 seconds per image
- **API Response Time**: < 500ms for non-AI endpoints
- **Accuracy Target**: 75-80% for condition detection

## Security Considerations

- All sensitive data is encrypted at rest
- JWT tokens with refresh mechanism
- HTTPS enforced in production
- CORS configured for frontend access
- Input validation on all endpoints

## Future Enhancements

- AR integration for hairstyle preview
- Doctor appointment booking system
- Real-time analysis progress updates
- Mobile app backend support

## License

[Your License Here]

## Contributors

[Your Name/Team]

