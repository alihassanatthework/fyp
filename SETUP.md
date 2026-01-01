# Quick Setup Guide

## Step-by-Step Setup Instructions

### 1. Virtual Environment (Already Created)
```bash
# Virtual environment is already created at: venv/
# To activate:
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### 2. Install All Dependencies
```bash
# Make sure virtual environment is activated
pip install -r requirements.txt
```

**Note on MySQL Client:**
If you encounter issues installing `mysqlclient`, you have two options:

**Option A: Install MySQL development libraries**
- **macOS**: `brew install mysql-client`
- **Linux**: `sudo apt-get install default-libmysqlclient-dev`
- **Windows**: Download MySQL Connector/C

**Option B: Use PyMySQL as alternative**
```bash
pip install pymysql
```
Then add to `config/__init__.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

### 3. Create MySQL Database
```sql
CREATE DATABASE skin_scalp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials and generate secret keys:

```bash
# Generate Django SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate ENCRYPTION_KEY (32 bytes)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. Run Initial Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Test the Setup
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` to verify the setup.

## Next Steps

1. Implement user authentication endpoints
2. Create database models for users, images, and analysis
3. Integrate AI models (Mediapipe, U-Net)
4. Implement image upload and processing
5. Build recommendation engine

## Troubleshooting

### MySQL Connection Issues
- Verify MySQL is running: `mysql -u root -p`
- Check database exists: `SHOW DATABASES;`
- Verify credentials in `.env` file

### Import Errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

### Port Already in Use
- Change port: `python manage.py runserver 8001`
- Or kill process using port 8000

