#!/bin/bash

# Script to run the Django development server
# Usage: ./run_server.sh

cd "/Users/alihassan/Desktop/fyp devlopment be"

# Activate virtual environment
source venv/bin/activate

# Check if migrations are needed
echo "Checking for pending migrations..."
python manage.py makemigrations --check --dry-run > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Creating migrations..."
    python manage.py makemigrations
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create media directories if they don't exist
echo "Creating media directories..."
mkdir -p media/uploads media/processed media/visualizations

# Collect static files (optional, for production-like setup)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the development server
echo ""
echo "=========================================="
echo "Starting Django Development Server"
echo "=========================================="
echo "Server will be available at: http://127.0.0.1:8000/"
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

python manage.py runserver
