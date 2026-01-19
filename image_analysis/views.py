from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.shortcuts import render
import os
import uuid
import cv2

# Import your AI Logic
from core.ai_models.mediapipe_detector import FaceScalpDetector
from core.ai_models import process_image
import numpy as np

class AnalyzeImageView(APIView):
    # 1. Allow anyone to access this page (No login required for now)
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        """
        Displays the HTML Upload Page.
        """
        return render(request, 'frontend/upload.html')

    def post(self, request, *args, **kwargs):
        """
        Handles Upload, Crop, and sends detailed Dummy Data to the Report Page.
        """
        file_obj = request.FILES.get('image')
        
        if not file_obj:
            return Response({"error": "No image provided. Please select a file."}, status=400)

        # 1. Setup Folder Paths
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        processed_dir = os.path.join(settings.MEDIA_ROOT, 'processed')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        # 2. Save Original File with Unique Name
        unique_name = f"{uuid.uuid4().hex[:8]}_{file_obj.name}"
        file_path = os.path.join(upload_dir, unique_name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        print(f"\n📢 DEBUG: Image saved to: {file_path}")

        # 3. Run AI Detector (MediaPipe)
        detector = FaceScalpDetector()
        try:
            print("📢 DEBUG: Starting FaceScalpDetector...")
            # Determine requested analysis type (default to skin)
            image_type = request.data.get('image_type') or request.POST.get('image_type') or 'skin'

            face_path = None
            scalp_path = None

            # For skin treatment, face detection is mandatory
            if image_type == 'skin':
                try:
                    face_crop = detector.detect_and_crop_face(cv2.imread(file_path))
                    # save face crop
                    unique_face = f"face_{uuid.uuid4().hex[:8]}.jpg"
                    face_path = os.path.join(processed_dir, unique_face)
                    cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
                    print(f"✅ SUCCESS: Face saved at: {face_path}")
                except Exception as e:
                    print(f"❌ ERROR: Face detection failed: {e}")
                    return Response({"error": "Face not detected. For skin/face treatment please upload a valid image."}, status=400)

                # try to extract scalp optionally for display
                try:
                    scalp_crop = detector.detect_and_crop_scalp(cv2.imread(file_path))
                    unique_scalp = f"scalp_{uuid.uuid4().hex[:8]}.jpg"
                    scalp_path = os.path.join(processed_dir, unique_scalp)
                    cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
                    print(f"✅ SUCCESS: Scalp saved at: {scalp_path}")
                except Exception:
                    scalp_path = None

            else:
                # For scalp treatment, scalp detection is mandatory; face optional
                try:
                    scalp_crop = detector.detect_and_crop_scalp(cv2.imread(file_path))
                    unique_scalp = f"scalp_{uuid.uuid4().hex[:8]}.jpg"
                    scalp_path = os.path.join(processed_dir, unique_scalp)
                    cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
                    print(f"✅ SUCCESS: Scalp saved at: {scalp_path}")
                except Exception as e:
                    print(f"❌ ERROR: Scalp detection failed: {e}")
                    return Response({"error": "Scalp not detected. For scalp treatment please upload a valid image."}, status=400)

                # try to extract face optionally for display
                try:
                    face_crop = detector.detect_and_crop_face(cv2.imread(file_path))
                    unique_face = f"face_{uuid.uuid4().hex[:8]}.jpg"
                    face_path = os.path.join(processed_dir, unique_face)
                    cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
                    print(f"✅ SUCCESS: Face saved at: {face_path}")
                except Exception:
                    face_path = None

            # 4. PREPARE DATA FOR YOUR HTML TEMPLATE
            # This dictionary fills in all the {{ variables }} in your results.html
            context = {
                # --- Image Links ---
                "original_image": f"/media/uploads/{unique_name}",
                "face_url": f"/media/processed/{os.path.basename(face_path)}" if face_path else None,
                "scalp_url": f"/media/processed/{os.path.basename(scalp_path)}" if scalp_path else None,
                
                # --- Report Header Info ---
                "analysis_id": uuid.uuid4().hex[:8].upper(),
                "max_severity": 78,  # Example Score
                "recommend_dermatologist": True, # Triggers the "Consult Doctor" alert

                # --- Detected Conditions List ---
                "conditions": [
                    {
                        "name": "Acne Vulgaris (Face)",
                        "severity_level": "Moderate",
                        "severity_score": 45,
                    },
                    {
                        "name": "Seborrheic Dermatitis (Scalp)",
                        "severity_level": "Severe",
                        "severity_score": 78,
                    }
                ],

                # --- Personalized Recommendations ---
                "recommendations": [
                    "💡 Use a gentle, non-comedogenic cleanser twice daily.",
                    "⚠️ Avoid scratching the scalp to prevent infection.",
                    "📞 Schedule an appointment with a dermatologist for the severe scalp condition.",
                    "💧 Keep the affected areas moisturized with prescribed lotions."
                ]
            }

            # 5. Try to run the AI pipeline to produce a segmentation mask and
            # an overlay visualization so the results page can show UNet output.
            try:
                img = cv2.imread(file_path)
                if img is not None:
                    pipeline_result = process_image(img, analysis_type=image_type)
                    # segmentation_mask will be a list in the result; convert
                    if 'segmentation_mask' in pipeline_result:
                        seg = np.array(pipeline_result['segmentation_mask'], dtype=np.uint8)
                        if seg.max() <= 1:
                            seg = (seg * 255).astype(np.uint8)

                        # Save colored mask
                        mask_name = f"mask_{unique_name}.jpg"
                        mask_path = os.path.join(processed_dir, mask_name)
                        colored = cv2.applyColorMap(seg, cv2.COLORMAP_JET)
                        cv2.imwrite(mask_path, colored)
                        context['segmentation_mask'] = f"/media/processed/{mask_name}"

                        # Create overlay using available crop or resize
                        try:
                            if image_type == 'skin':
                                # face_crop may exist from earlier detection
                                overlay_crop = locals().get('face_crop')
                            else:
                                overlay_crop = locals().get('scalp_crop')
                        except Exception:
                            overlay_crop = None

                        if overlay_crop is None:
                            overlay_crop = cv2.resize(img, (256, 256), interpolation=cv2.INTER_LINEAR)

                        seg_resized = cv2.resize(seg, (overlay_crop.shape[1], overlay_crop.shape[0]), interpolation=cv2.INTER_NEAREST)
                        colored_seg = cv2.applyColorMap(seg_resized, cv2.COLORMAP_JET)
                        overlay = cv2.addWeighted(overlay_crop, 0.6, colored_seg, 0.4, 0)

                        vis_name = f"vis_{unique_name}.jpg"
                        vis_path = os.path.join(processed_dir, vis_name)
                        cv2.imwrite(vis_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
                        # store overlay under visualizations for consistency
                        vis_public = f"/media/visualizations/{vis_name}"
                        # move file into visualizations directory
                        viz_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
                        os.makedirs(viz_dir, exist_ok=True)
                        final_vis_path = os.path.join(viz_dir, vis_name)
                        try:
                            os.replace(vis_path, final_vis_path)
                            context['visualized_image'] = vis_public
                        except Exception:
                            # fallback: keep in processed if move failed
                            context['visualized_image'] = f"/media/processed/{vis_name}"

                    # replace placeholder conditions/severity with pipeline outputs if available
                    if 'detected_conditions' in pipeline_result:
                        # Convert to template-friendly structure
                        formatted = []
                        sev = pipeline_result.get('severity_scores', {})
                        for c in pipeline_result.get('detected_conditions', []):
                            name = c.get('name', 'normal')
                            s = sev.get(name, {'score': 0, 'level': 'Mild'})
                            try:
                                score_int = int(s.get('score', 0))
                            except Exception:
                                score_int = 0
                            formatted.append({'name': name.replace('_', ' ').title(), 'severity_level': s.get('level', 'Mild'), 'severity_score': score_int})
                        if formatted:
                            context['conditions'] = formatted
                    if 'severity_scores' in pipeline_result:
                        # compute max severity
                        context['max_severity'] = max([v.get('score', 0) for v in pipeline_result.get('severity_scores', {}).values()])

                    # Store last analysis for results view and later debugging
                    try:
                        request.session['last_analysis'] = {
                            'analysis_id': context.get('analysis_id'),
                            'image_type': image_type,
                            'original_image': context.get('original_image'),
                            'face_crop': context.get('face_url'),
                            'scalp_crop': context.get('scalp_url'),
                            'segmentation_mask': context.get('segmentation_mask', ''),
                            'visualized_image': context.get('visualized_image', ''),
                            'conditions': context.get('conditions', []),
                            'recommendations': context.get('recommendations', []),
                            'recommend_dermatologist': context.get('recommend_dermatologist', False),
                            'max_severity': context.get('max_severity', 0),
                        }
                    except Exception:
                        pass
            except Exception as e:
                print(f"[PIPELINE-ERROR] Failed to run pipeline during upload: {e}")

            # 6. Render the HTML Page with the Data
            return render(request, 'frontend/results.html', context)

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            # If something breaks, still show a JSON error so we know why
            return Response({"error": str(e), "message": "Analysis failed"}, status=400)