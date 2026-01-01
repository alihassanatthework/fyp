from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def home(request):
    """Home/Landing page"""
    return render(request, 'frontend/home.html')


def register_view(request):
    """User registration page"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('frontend:home')
    else:
        form = UserCreationForm()
    return render(request, 'frontend/register.html', {'form': form})


def login_view(request):
    """User login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('frontend:home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'frontend/login.html')


@login_required
def upload_image(request):
    """Image upload page"""
    return render(request, 'frontend/upload.html')


@login_required
def analysis_results(request, analysis_id=None):
    """Analysis results page"""
    # Mock data for demonstration
    context = {
        'analysis_id': analysis_id or '12345',
        'conditions': [
            {'name': 'Acne', 'severity': 'Moderate', 'confidence': 85},
            {'name': 'Dark Spots', 'severity': 'Mild', 'confidence': 72},
        ],
        'recommendations': [
            'Use gentle face wash',
            'Apply aloe vera gel',
            'Use vitamin C serum',
        ],
    }
    return render(request, 'frontend/results.html', context)


@login_required
def profile(request):
    """User profile page"""
    return render(request, 'frontend/profile.html')


@login_required
def history(request):
    """Analysis history page"""
    # Mock data for demonstration
    context = {
        'analyses': [
            {'id': 1, 'date': '2025-01-02', 'type': 'Skin', 'conditions': ['Acne', 'Dark Spots']},
            {'id': 2, 'date': '2025-01-01', 'type': 'Scalp', 'conditions': ['Dandruff']},
        ]
    }
    return render(request, 'frontend/history.html', context)


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('frontend:home')

