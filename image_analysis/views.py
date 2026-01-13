from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.shortcuts import render
import os
import uuid

# Import your AI Logic
from core.ai_models.mediapipe_detector import FaceScalpDetector

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
            face_path, scalp_path = detector.process_and_crop(file_path, processed_dir)

            print(f"✅ SUCCESS: Face saved at: {face_path}")
            print(f"✅ SUCCESS: Scalp saved at: {scalp_path}")

            # 4. PREPARE DATA FOR YOUR HTML TEMPLATE
            # This dictionary fills in all the {{ variables }} in your results.html
            context = {
                # --- Image Links ---
                "original_image": f"/media/uploads/{unique_name}",
                "face_url": f"/media/processed/{os.path.basename(face_path)}",
                "scalp_url": f"/media/processed/{os.path.basename(scalp_path)}",
                
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

            # 5. Render the HTML Page with the Data
            return render(request, 'frontend/results.html', context)

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            # If something breaks, still show a JSON error so we know why
            return Response({"error": str(e), "message": "Analysis failed"}, status=400)