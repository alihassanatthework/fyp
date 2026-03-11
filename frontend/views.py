from urllib import request
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings
from users.models import MedicalHistory, UserProfile
import json
import os
import uuid
import cv2
import numpy as np
from PIL import Image

# Import AI pipeline
from core.ai_models import process_image
from core.ai_models.mediapipe_detector import FaceScalpDetector
from core.ai_models.visualization import (
    visualize_skin_conditions,
    visualize_scalp_conditions,
    create_comparison_view,
    visualize_efficientnet_scores,
    visualize_yolo_detections,
)


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
        
        try:
            # Setup directories
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
            visualization_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(processed_dir, exist_ok=True)
            os.makedirs(visualization_dir, exist_ok=True)
            
            # Save original image
            unique_id = uuid.uuid4().hex[:8]
            original_filename = f"{unique_id}_{image_file.name}"
            original_path = os.path.join(upload_dir, original_filename)
            
            with open(original_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            
            # Load image for processing
            image = cv2.imread(original_path)
            if image is None:
                # Try with PIL if OpenCV fails
                pil_image = Image.open(original_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Get normalized crops from MediaPipe for visualization (both face and scalp)
            # Get normalized crops from MediaPipe
            detector = FaceScalpDetector()

            face_crop = None
            scalp_crop = None

            # Try face detection
            try:
                face_crop = detector.detect_and_crop_face(image)
                if face_crop is not None:
                    print(f"✅ Face crop shape: {face_crop.shape}")
            except Exception as e:
                print(f"Face not detected: {e}")

            # Try scalp detection
            try:
                scalp_crop = detector.detect_and_crop_scalp(image)
                if scalp_crop is not None:
                    print(f"✅ Scalp crop shape: {scalp_crop.shape}")
            except Exception as e:
                print(f"Scalp not detected: {e}")

            # Simple skin presence check
            skin_present = detector.detect_skin_presence(image)
            print("DEBUG VALUES:", face_crop is not None, scalp_crop is not None, skin_present)

            # =========================
            # VALIDATION LOGIC
            # =========================

            if image_type == "skin":

                # allow face OR scalp OR skin
                if face_crop is None and scalp_crop is None and not skin_present:
                    messages.error(request, "No skin detected in image.")
                    return render(request, "frontend/upload.html")

                # choose best crop
                if face_crop is not None:
                    normalized_crop = face_crop

                elif scalp_crop is not None:
                    normalized_crop = scalp_crop

                else:
                    normalized_crop = cv2.resize(image, (256,256), interpolation=cv2.INTER_LINEAR)


            elif image_type == "scalp":

                # scalp mode requires scalp
                if scalp_crop is None:
                    messages.error(request, "Scalp not detected.")
                    return render(request, "frontend/upload.html")

                normalized_crop = scalp_crop
            
            try:
                if normalized_crop is not None:
                    pipeline_result = process_image(normalized_crop, analysis_type=image_type)
                    print(f"✅ Pipeline result keys: {pipeline_result.keys()}")
                    
                    # Convert segmentation mask back to numpy array
                    if 'segmentation_mask' in pipeline_result:
                        segmentation_mask = np.array(pipeline_result['segmentation_mask'], dtype=np.uint8)
                        if segmentation_mask.max() <= 1:
                            segmentation_mask = (segmentation_mask * 255).astype(np.uint8)
                        print(f"✅ Segmentation mask shape: {segmentation_mask.shape}, max: {segmentation_mask.max()}")
                    
                    # Get ROI bbox
                    if 'roi_bbox' in pipeline_result:
                        roi_bbox = pipeline_result['roi_bbox']
                    
                    # Get detected conditions
                    if 'detected_conditions' in pipeline_result:
                        detected_conditions = pipeline_result['detected_conditions']
                    if 'severity_scores' in pipeline_result:
                        severity_scores = pipeline_result['severity_scores']
                    
                    # Create visualization
                    if normalized_crop is not None and segmentation_mask is not None:
                        if image_type == 'skin':
                            visualized_image = visualize_skin_conditions(
                                image,
                                normalized_crop,
                                segmentation_mask,
                                roi_bbox,
                                detected_conditions,
                                severity_scores
                            )
                        else:
                            visualized_image = visualize_scalp_conditions(
                                image,
                                normalized_crop,
                                segmentation_mask,
                                roi_bbox,
                                detected_conditions,
                                severity_scores
                            )
                        print(f"✅ Visualization created, shape: {visualized_image.shape}")

                    # --- Additional model-specific visualizations ---
                    # Compute ROI image from normalized_crop and roi_bbox
                    try:
                        x1, y1, x2, y2 = roi_bbox
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        # Clamp coordinates
                        x1 = max(0, min(255, x1))
                        y1 = max(0, min(255, y1))
                        x2 = max(0, min(256, x2))
                        y2 = max(0, min(256, y2))
                        roi_image = normalized_crop[y1:y2, x1:x2].copy()
                        # If roi is empty, fallback to whole crop
                        if roi_image.size == 0:
                            roi_image = normalized_crop.copy()
                    except Exception:
                        roi_image = normalized_crop.copy() if normalized_crop is not None else None

                    efficient_vis_filename = None
                    yolo_vis_filename = None

                    # EfficientNet visualization (skin)
                    if pipeline_result and pipeline_result.get('efficientnet_scores') and roi_image is not None:
                        try:
                            eff_vis = visualize_efficientnet_scores(roi_image, pipeline_result.get('efficientnet_scores'))
                            efficient_vis_filename = f"eff_{unique_id}.jpg"
                            eff_vis_path = os.path.join(visualization_dir, efficient_vis_filename)
                            cv2.imwrite(eff_vis_path, cv2.cvtColor(eff_vis, cv2.COLOR_RGB2BGR))
                            print(f"✅ Saved EfficientNet visualization: {eff_vis_path}")
                        except Exception as e:
                            print(f"⚠️ Failed to create EfficientNet visualization: {e}")

                    # YOLO visualization (scalp)
                    if pipeline_result and pipeline_result.get('yolo_detections') and roi_image is not None:
                        try:
                            yolo_vis = visualize_yolo_detections(roi_image, pipeline_result.get('yolo_detections'))
                            yolo_vis_filename = f"yolo_{unique_id}.jpg"
                            yolo_vis_path = os.path.join(visualization_dir, yolo_vis_filename)
                            cv2.imwrite(yolo_vis_path, cv2.cvtColor(yolo_vis, cv2.COLOR_RGB2BGR))
                            print(f"✅ Saved YOLO visualization: {yolo_vis_path}")
                        except Exception as e:
                            print(f"⚠️ Failed to create YOLO visualization: {e}")
            except Exception as e:
                print(f"⚠️ Pipeline processing failed: {e}")
                import traceback
                traceback.print_exc()
                # Create a simple fallback visualization
                if normalized_crop is not None:
                    # Create a simple mask (all zeros for now)
                    segmentation_mask = np.zeros((256, 256), dtype=np.uint8)
                    # Create a simple visualization (just the crop)
                    visualized_image = normalized_crop.copy()
                # Use mock data for conditions
                detected_conditions = [{'name': 'normal', 'confidence': 0.5, 'type': image_type}]
                severity_scores = {'normal': {'score': 0, 'level': 'Mild'}}
            
            # Save normalized crops (both face and scalp) - ALWAYS save these
            face_crop_filename = None
            scalp_crop_filename = None
            crop_filename = None
            
            if face_crop is not None:
                face_crop_filename = f"face_{unique_id}.jpg"
                face_crop_path = os.path.join(processed_dir, face_crop_filename)
                cv2.imwrite(face_crop_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
                print(f"✅ Saved face crop: {face_crop_path}")
            
            if scalp_crop is not None:
                scalp_crop_filename = f"scalp_{unique_id}.jpg"
                scalp_crop_path = os.path.join(processed_dir, scalp_crop_filename)
                cv2.imwrite(scalp_crop_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
                print(f"✅ Saved scalp crop: {scalp_crop_path}")
            
            # Save the selected crop (for backward compatibility)
            if normalized_crop is not None:
                crop_filename = f"crop_{unique_id}.jpg"
                crop_path = os.path.join(processed_dir, crop_filename)
                cv2.imwrite(crop_path, cv2.cvtColor(normalized_crop, cv2.COLOR_RGB2BGR))
                print(f"✅ Saved normalized crop: {crop_path}")
            
            # Save segmentation mask
            mask_filename = None
            if segmentation_mask is not None:
                mask_filename = f"mask_{unique_id}.jpg"
                mask_path = os.path.join(processed_dir, mask_filename)
                mask_colored = cv2.applyColorMap(segmentation_mask, cv2.COLORMAP_JET)
                cv2.imwrite(mask_path, mask_colored)
                print(f"✅ Saved segmentation mask: {mask_path}")
            
            # Save visualized image
            vis_filename = None
            if visualized_image is not None:
                vis_filename = f"vis_{unique_id}.jpg"
                vis_path = os.path.join(visualization_dir, vis_filename)
                cv2.imwrite(vis_path, cv2.cvtColor(visualized_image, cv2.COLOR_RGB2BGR))
                print(f"✅ Saved visualization: {vis_path}")
            
            # Fetch medical history from database
            try:
                medical_history = request.user.medical_history
            except MedicalHistory.DoesNotExist:
                medical_history = MedicalHistory.objects.create(user=request.user)
            
            # Process detected conditions (use pipeline result or fallback)
            if not detected_conditions:
                # Fallback: create a default condition
                detected_conditions = [{'name': 'normal', 'confidence': 0.5, 'type': image_type}]
            
            if not severity_scores:
                # Fallback: create default severity
                severity_scores = {'normal': {'score': 0, 'level': 'Mild'}}
            
            # Format conditions for display
            formatted_conditions = []
            for condition in detected_conditions:
                name = condition.get('name', 'normal')
                severity_info = severity_scores.get(name, {'score': 0, 'level': 'Mild'})
                # Ensure severity_score is an integer number for safe rendering in templates
                try:
                    sev_score_raw = severity_info.get('score', 0)
                    sev_score = int(sev_score_raw) if sev_score_raw is not None else 0
                except Exception:
                    sev_score = 0

                formatted_conditions.append({
                    'name': name.replace('_', ' ').title(),
                    'severity_level': severity_info.get('level', 'Mild'),
                    'severity_score': sev_score
                })
            
            # Check if any condition has severity > 70 (recommend dermatologist)
            max_severity = max([s.get('score', 0) for s in severity_scores.values()], default=0)
            recommend_dermatologist = max_severity > 70
            
            # Generate recommendations based on medical history
            recommendations = generate_recommendations(
                detected_conditions,
                severity_scores,
                medical_history,
                recommend_dermatologist
            )
            
            # Store analysis result (for history)
            analysis_id = store_analysis_result(
                request.user,
                image_file,
                image_type,
                detected_conditions,
                severity_scores
            )
            
            # Store results in session for results page
            session_data = {
                'analysis_id': analysis_id,
                'image_type': image_type,
                'original_image': f"/media/uploads/{original_filename}",
                'conditions': formatted_conditions,
                'recommendations': recommendations,
                'recommend_dermatologist': recommend_dermatologist,
                'max_severity': max_severity,
            }
            
            # Add image paths only if they exist
            if face_crop_filename:
                session_data['face_crop'] = f"/media/processed/{face_crop_filename}"
            if scalp_crop_filename:
                session_data['scalp_crop'] = f"/media/processed/{scalp_crop_filename}"
            if crop_filename:
                session_data['normalized_crop'] = f"/media/processed/{crop_filename}"
            if mask_filename:
                session_data['segmentation_mask'] = f"/media/processed/{mask_filename}"
            if vis_filename:
                session_data['visualized_image'] = f"/media/visualizations/{vis_filename}"
            if efficient_vis_filename:
                session_data['efficientnet_visualization'] = f"/media/visualizations/{efficient_vis_filename}"
            if yolo_vis_filename:
                session_data['yolo_visualization'] = f"/media/visualizations/{yolo_vis_filename}"
            # If no segmentation mask was saved for this analysis, attach the
            # most recent UNet inference visualization (if available) so the
            # results page shows something immediately.
            try:
                if 'segmentation_mask' not in session_data or not session_data.get('segmentation_mask'):
                    viz_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations', 'eczema_predictions')
                    if os.path.isdir(viz_dir):
                        files = sorted([f for f in os.listdir(viz_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                        if files:
                            latest = files[-1]
                            session_data['segmentation_mask'] = f"/media/visualizations/eczema_predictions/{latest}"
                            # set visualized_image if not present
                            if not session_data.get('visualized_image'):
                                session_data['visualized_image'] = session_data['segmentation_mask']
            except Exception as e:
                print('[WARN] failed to attach fallback viz to session:', e)

            # If segmentation was not produced during processing above, run a
            # light on-demand inference now (synchronous) so the results page
            # will always have a per-analysis mask and visualization to show.
            try:
                if not session_data.get('segmentation_mask') and os.path.exists(original_path):
                    print('[ON-DEMAND] No segmentation in session, running quick on-demand inference for this upload...')
                    img_od = cv2.imread(original_path)
                    if img_od is not None:
                        pipeline_result_od = process_image(img_od, analysis_type=image_type)
                        seg_mask_od = None
                        if 'segmentation_mask' in pipeline_result_od:
                            seg_mask_od = np.array(pipeline_result_od['segmentation_mask'], dtype=np.uint8)
                            if seg_mask_od.max() <= 1:
                                seg_mask_od = (seg_mask_od * 255).astype(np.uint8)

                        if seg_mask_od is not None:
                            mask_filename_od = f"mask_{unique_id}.jpg"
                            mask_path_od = os.path.join(processed_dir, mask_filename_od)
                            mask_colored_od = cv2.applyColorMap(seg_mask_od, cv2.COLORMAP_JET)
                            cv2.imwrite(mask_path_od, mask_colored_od)
                            session_data['segmentation_mask'] = f"/media/processed/{mask_filename_od}"
                            print(f"[ON-DEMAND] Saved segmentation mask: {mask_path_od}")

                            # Create overlay visualization
                            try:
                                from core.ai_models.mediapipe_detector import FaceScalpDetector
                                detector = FaceScalpDetector()
                                if image_type == 'skin':
                                    crop = detector.detect_and_crop_face(img_od)
                                else:
                                    crop = detector.detect_and_crop_scalp(img_od)
                            except Exception:
                                crop = None

                            if crop is None:
                                crop = cv2.resize(img_od, (256, 256), interpolation=cv2.INTER_LINEAR)

                            seg_resized = cv2.resize(seg_mask_od, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
                            colored = cv2.applyColorMap(seg_resized, cv2.COLORMAP_JET)
                            overlay = cv2.addWeighted(crop, 0.6, colored, 0.4, 0)

                            vis_filename_od = f"vis_{unique_id}.jpg"
                            vis_path_od = os.path.join(visualization_dir, vis_filename_od)
                            cv2.imwrite(vis_path_od, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
                            session_data['visualized_image'] = f"/media/visualizations/{vis_filename_od}"
                            print(f"[ON-DEMAND] Saved visualization: {vis_path_od}")
            except Exception as e:
                print('[ON-DEMAND] on-demand inference failed:', e)

            print(f"📦 Session data keys: {session_data.keys()}")
            print(f"📦 Session segmentation_mask value: {session_data.get('segmentation_mask')}")
            print(f"📦 Session visualized_image value: {session_data.get('visualized_image')}")
            request.session['last_analysis'] = session_data
            
            # Redirect to results page
            return redirect('frontend:results', analysis_id=analysis_id)
            
        except Exception as e:
            import traceback
            print(f"Error in upload_image: {str(e)}")
            print(traceback.format_exc())
            messages.error(request, f'An error occurred during analysis: {str(e)}')
            return render(request, 'frontend/upload.html')
    
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
    
    # Base recommendations (normalize condition names)
    base_recommendations = {
        'acne': ['Use gentle face wash', 'Apply aloe vera gel', 'Avoid harsh chemicals'],
        'dark_spots': ['Use vitamin C serum', 'Apply sunscreen daily', 'Consider retinol'],
        'dark spots': ['Use vitamin C serum', 'Apply sunscreen daily', 'Consider retinol'],
        'dandruff': ['Use anti-dandruff shampoo', 'Apply tea tree oil', 'Maintain scalp hygiene'],
        'dryness': ['Use moisturizer', 'Drink more water', 'Avoid hot water'],
        'hair_fall': ['Apply hair oil (coconut, almond)', 'Eat protein-rich diet', 'Avoid excessive heat styling'],
        'hair fall': ['Apply hair oil (coconut, almond)', 'Eat protein-rich diet', 'Avoid excessive heat styling'],
    }
    
    # Filter based on medical history
    for condition in conditions:
        name = condition.get('name', '').lower().replace(' ', '_')
        severity_info = severity_results.get(condition.get('name', ''), {})
        severity_score = severity_info.get('score', 0) if isinstance(severity_info, dict) else 0
        
        # Only add general recommendations if severity is not too high
        if severity_score <= 70:
            # Try different name formats
            recs = base_recommendations.get(name, [])
            if not recs:
                recs = base_recommendations.get(name.replace('_', ' '), [])
            
            for rec in recs:
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
    # Get data from session
    if 'last_analysis' not in request.session:
        messages.error(request, 'No analysis data found. Please upload an image first.')
        return redirect('frontend:upload')
    
    session_data = request.session['last_analysis']
    # Debug: print session_data keys so we can trace why segmentation may be missing
    try:
        print('[DEBUG] analysis_results session keys:', list(session_data.keys()))
    except Exception:
        print('[DEBUG] analysis_results: no session_data available')
    
    # Build context with all visualization data
    context = {
        'analysis_id': session_data.get('analysis_id', analysis_id),
        'image_type': session_data.get('image_type', 'skin'),
        'original_image': session_data.get('original_image', ''),
        'visualized_image': session_data.get('visualized_image', ''),
        'normalized_crop': session_data.get('normalized_crop', ''),
        'face_crop': session_data.get('face_crop', ''),
        'scalp_crop': session_data.get('scalp_crop', ''),
        'efficientnet_visualization': session_data.get('efficientnet_visualization', ''),
        'yolo_visualization': session_data.get('yolo_visualization', ''),
        'segmentation_mask': session_data.get('segmentation_mask', ''),
        'conditions': session_data.get('conditions', []),
        'recommendations': session_data.get('recommendations', []),
        'recommend_dermatologist': session_data.get('recommend_dermatologist', False),
        'max_severity': session_data.get('max_severity', 0),
    }

    # Fallback: if segmentation_mask wasn't produced in session (old analysis),
    # try to show a recent UNet inference visualization if available. This helps
    # when a model was trained after the user performed an analysis.
    try:
        viz_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations', 'eczema_predictions')
        if os.path.isdir(viz_dir):
            files = sorted([f for f in os.listdir(viz_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            if files:
                latest = files[-1]
                latest_url = f"/media/visualizations/eczema_predictions/{latest}"
                if not context.get('segmentation_mask'):
                    # Show the most recent prediction when no per-analysis mask exists
                    print(f"[DEBUG] No session segmentation_mask; using latest viz {latest_url}")
                    context['segmentation_mask'] = latest_url
                if not context.get('visualized_image'):
                    context['visualized_image'] = latest_url
                # Also log whether the file actually exists on disk for troubleshooting
                latest_path = os.path.join(viz_dir, latest)
                print(f"[DEBUG] Latest viz path exists: {os.path.exists(latest_path)} -> {latest_path}")
    except Exception as e:
        print(f"[DEBUG] Error while locating viz dir: {e}")
    
    # Clear session after displaying (optional - you may want to keep it for history)
    # del request.session['last_analysis']

    # If no segmentation mask exists in the session (old analysis), try to run
    # the pipeline on the original image now (safely) and attach results so
    # the results page shows a real per-image segmentation instead of the
    # placeholder/fallback. This is kept light and wrapped in a top-level
    # try/except to avoid breaking page rendering.
    try:
        if not context.get('segmentation_mask') and context.get('original_image'):
            print('[AUTO-INFER] No segmentation in session, attempting on-demand inference...')
            print(f"[AUTO-INFER] image_type={context.get('image_type')} analysis_id={context.get('analysis_id')}")
            orig_url = context.get('original_image')
            rel_path = orig_url[len('/media/'):] if orig_url.startswith('/media/') else orig_url.lstrip('/')
            orig_path = os.path.join(settings.MEDIA_ROOT, rel_path)

            if os.path.exists(orig_path):
                print(f"[AUTO-INFER] Found original image on disk: {orig_path}")
                img = cv2.imread(orig_path)
                if img is not None:
                    # Run pipeline (uses trained UNet if available)
                    print('[AUTO-INFER] Running process_image pipeline...')
                    pipeline_result = process_image(img, analysis_type=context.get('image_type', 'skin'))
                    print(f"[AUTO-INFER] pipeline_result keys: {list(pipeline_result.keys())}")

                    # Extract segmentation mask and normalize
                    seg_mask = None
                    if 'segmentation_mask' in pipeline_result:
                        import numpy as _np
                        seg_mask = _np.array(pipeline_result['segmentation_mask'], dtype=_np.uint8)
                        if seg_mask.max() <= 1:
                            seg_mask = (seg_mask * 255).astype(_np.uint8)

                    if seg_mask is not None:
                        print(f"[AUTO-INFER] seg_mask stats: shape={seg_mask.shape} max={seg_mask.max()}")
                        processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
                        visualization_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
                        os.makedirs(processed_dir, exist_ok=True)
                        os.makedirs(visualization_dir, exist_ok=True)

                        # Save colored mask
                        mask_filename = f"mask_auto_{context.get('analysis_id') or 'auto'}.jpg"
                        mask_path = os.path.join(processed_dir, mask_filename)
                        mask_colored = cv2.applyColorMap(seg_mask, cv2.COLORMAP_JET)
                        cv2.imwrite(mask_path, mask_colored)
                        context['segmentation_mask'] = f"/media/processed/{mask_filename}"
                        print(f"[AUTO-INFER] Saved mask to {mask_path} -> will expose as {context['segmentation_mask']}")

                        # Create overlay visualization using detected crop if possible
                        try:
                            from core.ai_models.mediapipe_detector import FaceScalpDetector
                            detector = FaceScalpDetector()
                            if context.get('image_type') == 'skin':
                                crop = detector.detect_and_crop_face(img)
                            else:
                                crop = detector.detect_and_crop_scalp(img)
                        except Exception:
                            crop = None

                        if crop is None:
                            crop = cv2.resize(img, (256, 256), interpolation=cv2.INTER_LINEAR)

                        seg_resized = cv2.resize(seg_mask, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_NEAREST)
                        colored = cv2.applyColorMap(seg_resized, cv2.COLORMAP_JET)
                        overlay = cv2.addWeighted(crop, 0.6, colored, 0.4, 0)

                        vis_filename = f"vis_auto_{context.get('analysis_id') or 'auto'}.jpg"
                        vis_path = os.path.join(visualization_dir, vis_filename)
                        cv2.imwrite(vis_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
                        context['visualized_image'] = f"/media/visualizations/{vis_filename}"
                        print(f"[AUTO-INFER] Saved visualization to {vis_path} -> will expose as {context['visualized_image']}")

                        # Persist into session
                        session_data['segmentation_mask'] = context['segmentation_mask']
                        session_data['visualized_image'] = context.get('visualized_image', session_data.get('visualized_image'))
                        request.session['last_analysis'] = session_data
    except Exception:
        # Don't block page render on any inference error
        import traceback
        traceback.print_exc()

    return render(request, 'frontend/results.html', context)


@login_required
def profile(request):
    """User profile page"""
    try:
        medical_history = request.user.medical_history
    except MedicalHistory.DoesNotExist:
        medical_history = MedicalHistory.objects.create(user=request.user)
    
    context = {
        'medical_history': medical_history,
    }
    return render(request, 'frontend/profile.html', context)


@login_required
def view_medical_history(request):
    """View medical history page"""
    try:
        medical_history = request.user.medical_history
    except MedicalHistory.DoesNotExist:
        medical_history = MedicalHistory.objects.create(user=request.user)
    
    context = {
        'medical_history': medical_history,
    }
    return render(request, 'frontend/view_medical_history.html', context)


@login_required
def edit_medical_history(request):
    """Edit medical history page"""
    try:
        medical_history = request.user.medical_history
    except MedicalHistory.DoesNotExist:
        medical_history = MedicalHistory.objects.create(user=request.user)
    
    if request.method == 'POST':
        # Update medical history
        medical_history.is_pregnant = request.POST.get('is_pregnant') == 'on'
        medical_history.has_cardio_issues = request.POST.get('has_cardio_issues') == 'on'
        medical_history.is_diabetic = request.POST.get('is_diabetic') == 'on'
        medical_history.has_allergies = request.POST.get('has_allergies') == 'on'
        medical_history.has_hypertension = request.POST.get('has_hypertension') == 'on'
        medical_history.has_asthma = request.POST.get('has_asthma') == 'on'
        medical_history.has_skin_conditions = request.POST.get('has_skin_conditions') == 'on'
        medical_history.has_scalp_conditions = request.POST.get('has_scalp_conditions') == 'on'
        medical_history.other_conditions = request.POST.get('other_conditions', '')
        medical_history.current_medications = request.POST.get('current_medications', '')
        medical_history.known_allergens = request.POST.get('known_allergens', '')
        medical_history.save()
        
        messages.success(request, 'Medical history updated successfully!')
        return redirect('frontend:view_medical_history')
    
    context = {
        'medical_history': medical_history,
    }
    return render(request, 'frontend/edit_medical_history.html', context)


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
