from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from users.models import MedicalHistory, UserProfile
import json


def home(request):
    """Home/Landing page"""
    return render(request, 'frontend/home.html')


def register_view(request):
    """User registration page with medical history"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            # Create medical history
            medical_history = MedicalHistory.objects.create(
                user=user,
                is_pregnant=request.POST.get('is_pregnant') == 'on',
                has_cardio_issues=request.POST.get('has_cardio_issues') == 'on',
                is_diabetic=request.POST.get('is_diabetic') == 'on',
                has_allergies=request.POST.get('has_allergies') == 'on',
                has_hypertension=request.POST.get('has_hypertension') == 'on',
                has_asthma=request.POST.get('has_asthma') == 'on',
                has_skin_conditions=request.POST.get('has_skin_conditions') == 'on',
                has_scalp_conditions=request.POST.get('has_scalp_conditions') == 'on',
                other_conditions=request.POST.get('other_conditions', ''),
                current_medications=request.POST.get('current_medications', ''),
                known_allergens=request.POST.get('known_allergens', ''),
            )
            
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


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('frontend:home')


@login_required
def upload_image(request):
    """Image upload page - follows flowchart: upload -> validate -> analyze -> results"""
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        image_type = request.POST.get('image_type', 'skin')
        
        # Validate image (following flowchart)
        if not validate_image(image_file):
            messages.error(request, 'Invalid image. Please upload a clear image of skin or scalp.')
            return render(request, 'frontend/upload.html')
        
        # Fetch medical history from database (flowchart step)
        try:
            medical_history = request.user.medical_history
        except MedicalHistory.DoesNotExist:
            medical_history = MedicalHistory.objects.create(user=request.user)
        
        # Detect disease (ML Model - flowchart step)
        # TODO: Integrate actual ML model here
        detected_conditions = detect_conditions_mock(image_type)
        
        # Detect Severity (ML Model - flowchart step)
        # TODO: Integrate actual ML model here
        severity_results = detect_severity_mock(detected_conditions)
        
        # Check if any condition has severity > 70 (recommend dermatologist)
        max_severity = max([severity_results[c['name']]['score'] for c in detected_conditions], default=0)
        recommend_dermatologist = max_severity > 70
        
        # Generate recommendations based on medical history
        recommendations = generate_recommendations(detected_conditions, severity_results, medical_history, recommend_dermatologist)
        
        # Store analysis result (for history)
        analysis_id = store_analysis_result(request.user, image_file, image_type, detected_conditions, severity_results)
        
        # Store results in session for results page
        request.session['last_analysis'] = {
            'analysis_id': analysis_id,
            'image_type': image_type,
            'conditions': [
                {
                    'name': condition['name'],
                    'severity_level': severity_results[condition['name']]['level'],
                    'severity_score': severity_results[condition['name']]['score']
                }
                for condition in detected_conditions
            ],
            'recommendations': recommendations,
            'recommend_dermatologist': recommend_dermatologist,
            'max_severity': max_severity,
        }
        
        # Redirect to results page
        return redirect('frontend:results', analysis_id=analysis_id)
    
    return render(request, 'frontend/upload.html')


def validate_image(image_file):
    """Validate image according to flowchart requirements"""
    # Check file size (max 10MB)
    if image_file.size > 10 * 1024 * 1024:
        return False
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
    if image_file.content_type not in allowed_types:
        return False
    
    # Additional validation can be added here (clarity, lighting, etc.)
    return True


def detect_conditions_mock(image_type):
    """Mock function for disease detection (ML Model) - to be replaced with actual model"""
    if image_type == 'skin':
        return [
            {'name': 'Acne'},
            {'name': 'Dark Spots'},
        ]
    else:  # scalp
        return [
            {'name': 'Dandruff'},
            {'name': 'Dryness'},
        ]


def detect_severity_mock(conditions):
    """Mock function for severity detection (ML Model) - returns severity score and level"""
    # Severity scores: 0-100 (0-30: Mild, 31-70: Moderate, 71-100: Severe)
    severity_data = {
        'Acne': {'score': 75, 'level': 'Severe'},
        'Dark Spots': {'score': 45, 'level': 'Moderate'},
        'Dandruff': {'score': 65, 'level': 'Moderate'},
        'Dryness': {'score': 35, 'level': 'Moderate'},
        'Hair Fall': {'score': 85, 'level': 'Severe'},
        'Hyperpigmentation': {'score': 55, 'level': 'Moderate'},
        'Oiliness': {'score': 40, 'level': 'Moderate'},
    }
    
    results = {}
    for condition in conditions:
        name = condition['name']
        default = {'score': 50, 'level': 'Moderate'}
        results[name] = severity_data.get(name, default)
    
    return results


def generate_recommendations(conditions, severity_results, medical_history, recommend_dermatologist=False):
    """Generate personalized recommendations based on medical history and severity"""
    recommendations = []
    
    # If severity > 70, prioritize dermatologist consultation
    if recommend_dermatologist:
        recommendations.append('🚨 **HIGH SEVERITY DETECTED** - We strongly recommend consulting with a dermatologist for professional evaluation and treatment.')
        recommendations.append('📞 Book an appointment with a dermatologist as soon as possible.')
    
    # Base recommendations
    base_recommendations = {
        'Acne': ['Use gentle face wash', 'Apply aloe vera gel', 'Avoid harsh chemicals'],
        'Dark Spots': ['Use vitamin C serum', 'Apply sunscreen daily', 'Consider retinol'],
        'Dandruff': ['Use anti-dandruff shampoo', 'Apply tea tree oil', 'Maintain scalp hygiene'],
        'Dryness': ['Use moisturizer', 'Drink more water', 'Avoid hot water'],
    }
    
    # Filter based on medical history
    for condition in conditions:
        name = condition['name']
        severity_score = severity_results[name]['score']
        
        # Only add general recommendations if severity is not too high
        if severity_score <= 70 and name in base_recommendations:
            for rec in base_recommendations[name]:
                # Safety check: filter unsafe recommendations
                if is_safe_recommendation(rec, medical_history):
                    recommendations.append(rec)
    
    # Add medical history-specific warnings
    if medical_history.is_pregnant:
        recommendations.append('⚠️ Consult with dermatologist before using any new products (Pregnancy)')
    if medical_history.is_diabetic:
        recommendations.append('⚠️ Monitor skin condition closely (Diabetes)')
    if medical_history.has_allergies:
        recommendations.append('⚠️ Check product ingredients for known allergens')
    
    # If no recommendations, add general advice
    if not recommendations:
        recommendations = ['Maintain good hygiene', 'Stay hydrated', 'Consult dermatologist if condition persists']
    
    return recommendations


def is_safe_recommendation(recommendation, medical_history):
    """Check if recommendation is safe based on medical history"""
    # Filter out unsafe recommendations
    unsafe_keywords = {
        'pregnancy': ['retinol', 'salicylic acid', 'benzoyl peroxide'],
        'diabetic': ['strong acids'],
        'allergies': ['fragrance', 'parabens'],
    }
    
    if medical_history.is_pregnant:
        for keyword in unsafe_keywords.get('pregnancy', []):
            if keyword.lower() in recommendation.lower():
                return False
    
    if medical_history.is_diabetic:
        for keyword in unsafe_keywords.get('diabetic', []):
            if keyword.lower() in recommendation.lower():
                return False
    
    return True


def store_analysis_result(user, image_file, image_type, conditions, severity_results):
    """Store analysis result in database (for history tracking)"""
    # TODO: Create AnalysisResult model and store actual data
    # For now, return a mock ID
    import random
    return random.randint(1000, 9999)


@login_required
def analysis_results(request, analysis_id=None):
    """Analysis results page - shows after image analysis"""
    # In real implementation, fetch from database
    # For now, use session or pass data
    
    # Mock data - in production, fetch from AnalysisResult model
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
    
    # Try to get from session if available (from upload/analysis)
    if 'last_analysis' in request.session:
        context = request.session['last_analysis']
        # Clear session after displaying
        del request.session['last_analysis']
    
    return render(request, 'frontend/results.html', context)


@login_required
def profile(request):
    """User profile page"""
    try:
        medical_history = request.user.medical_history
    except MedicalHistory.DoesNotExist:
        medical_history = None
    
    context = {
        'medical_history': medical_history,
    }
    return render(request, 'frontend/profile.html', context)


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
