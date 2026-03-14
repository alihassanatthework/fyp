from matplotlib.style import context
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.shortcuts import render
import os
import uuid
import cv2
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

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

        # 3. Run AI Detector (MediaPipe / fallback rules)
        detector = FaceScalpDetector()
        print("📢 DEBUG: Starting FaceScalpDetector...")

        # Determine requested analysis type (default to skin)
        image_type = request.data.get('image_type') or request.POST.get('image_type') or 'skin'
        print("IMAGE TYPE RECEIVED:", image_type)

        face_path = None
        scalp_path = None
        face_crop = None
        scalp_crop = None

        img = cv2.imread(file_path)
        if img is None:
            return Response({"error": "Could not read uploaded image."}, status=400)

        if image_type == 'skin':
            # Skin mode:
            # allow face OR scalp OR skin-only fallback

            face_crop = None
            scalp_crop = None

            # Try face detection
            try:
                face_crop = detector.detect_and_crop_face(img)

                unique_face = f"face_{uuid.uuid4().hex[:8]}.jpg"
                face_path = os.path.join(processed_dir, unique_face)
                cv2.imwrite(face_path, cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR))
                print(f"✅ SUCCESS: Face saved at: {face_path}")

            except Exception as e:
                print(f"Face not detected: {e}")

            # Try scalp detection
            try:
                scalp_crop = detector.detect_and_crop_scalp(img)

                unique_scalp = f"scalp_{uuid.uuid4().hex[:8]}.jpg"
                scalp_path = os.path.join(processed_dir, unique_scalp)
                cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))
                print(f"✅ SUCCESS: Scalp saved at: {scalp_path}")

            except Exception as e:
                print(f"Scalp not detected: {e}")

            # Skin presence detection
            skin_present = detector.detect_skin_presence(img)

            # Decide which crop to use
            if face_crop is not None:
                normalized_crop = face_crop

            elif scalp_crop is not None:
                normalized_crop = scalp_crop

            elif skin_present:
                normalized_crop = cv2.resize(img, (256, 256), interpolation=cv2.INTER_LINEAR)

            else:
                return Response(
                    {"error": "No skin or face detected in the image."},
                    status=400
                )
            
        elif image_type == 'scalp':
            # Scalp mode
            # Try MediaPipe scalp detection first

            try:
                scalp_crop = detector.detect_and_crop_scalp(img)

                unique_scalp = f"scalp_{uuid.uuid4().hex[:8]}.jpg"
                scalp_path = os.path.join(processed_dir, unique_scalp)

                cv2.imwrite(scalp_path, cv2.cvtColor(scalp_crop, cv2.COLOR_RGB2BGR))

                print(f"✅ SUCCESS: Scalp saved at: {scalp_path}")

                normalized_crop = scalp_crop

            except Exception as e:

                print("⚠️ MediaPipe scalp detection failed. Using automatic scalp detection.")

                # ---------- NEW: automatic scalp fallback ----------
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # detect hair region (dark pixels)
                _, hair_mask = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)

                # remove noise
                kernel = np.ones((5,5), np.uint8)
                hair_mask = cv2.morphologyEx(hair_mask, cv2.MORPH_CLOSE, kernel)

                scalp_crop = cv2.bitwise_and(img, img, mask=hair_mask)

                normalized_crop = cv2.resize(scalp_crop, (256,256), interpolation=cv2.INTER_LINEAR)

                unique_scalp = f"scalp_auto_{uuid.uuid4().hex[:8]}.jpg"
                scalp_path = os.path.join(processed_dir, unique_scalp)

                cv2.imwrite(scalp_path, normalized_crop)

                print("✅ Fallback scalp detection used.")


        else:
            return Response({"error": "Invalid image_type. Must be 'skin' or 'scalp'."}, status=400)

        normalized_crop = normalized_crop.astype(np.uint8)

                # 4. PREPARE DATA FOR YOUR HTML TEMPLATE
        context = {
            "original_image": f"/media/uploads/{unique_name}",
            "face_url": f"/media/processed/{os.path.basename(face_path)}" if face_path else None,
            "scalp_url": f"/media/processed/{os.path.basename(scalp_path)}" if scalp_path else None,

            "analysis_id": uuid.uuid4().hex[:8].upper(),
            "max_severity": 78,
            "recommend_dermatologist": True,

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

            "recommendations": [
                "💡 Use a gentle, non-comedogenic cleanser twice daily.",
                "⚠️ Avoid scratching the scalp to prevent infection.",
                "📞 Schedule an appointment with a dermatologist for the severe scalp condition.",
                "💧 Keep the affected areas moisturized with prescribed lotions."
            ]
        }

        # 5. Try to run the AI pipeline to produce a segmentation mask and overlay
        try:
            pipeline_result = process_image(normalized_crop, analysis_type=image_type)
            print(f"✅ Pipeline result keys: {pipeline_result.keys()}")
            

            # Add EfficientNet classification scores
            if image_type == "skin" and 'classification_scores' in pipeline_result:

                scores = pipeline_result['classification_scores']

                context['classification'] = scores

                labels = list(scores.keys())
                values = [round(v*100,2) for v in scores.values()]
                plt.ylabel("Probability (%)")

                plt.figure(figsize=(4,3))
                plt.bar(labels, values)
                plt.title("EfficientNet Classification")
                plt.ylabel("Probability")

                viz_name = f"efficientnet_{unique_name}.png"
                viz_path = os.path.join(processed_dir, viz_name)

                plt.savefig(viz_path)
                plt.close()

                context['efficientnet_visualization'] = f"/media/processed/{viz_name}"


            if image_type == "scalp" and 'yolo_detections' in pipeline_result:
                detections = pipeline_result['yolo_detections']
                print("YOLO TEXT SOURCE:", detections)
                print("PIPELINE DETECTED CONDITIONS:", pipeline_result.get('detected_conditions'))

                try:

                    labels = []
                    values = []

                    for det in detections:
                        label = det.get("condition") or det.get("class", "unknown")
                        conf = det.get("confidence", 0)

                        labels.append(label)
                        values.append(conf * 100)

                    if labels:

                        

                        plt.figure(figsize=(4,3))
                        plt.bar(labels, values)
                        plt.title("YOLOv8 Scalp Detection")
                        plt.ylabel("Confidence (%)")
                        plt.ylim(0,100)

                        yolo_graph_name = f"yolo_chart_{unique_name}.png"
                        yolo_graph_path = os.path.join(processed_dir, yolo_graph_name)

                        plt.savefig(yolo_graph_path)
                        plt.close()

                        context["yolo_chart"] = f"/media/processed/{yolo_graph_name}"

                except Exception as e:
                    print("YOLO graph error:", e)



                scalp_vis = scalp_crop if scalp_crop is not None else normalized_crop
                vis_img = scalp_vis.copy()

                for det in detections:
                    bbox = det.get("bbox")
                    if bbox is None:
                        continue

                    x1, y1, x2, y2 = map(int, bbox)

                    # FIX: use condition instead of class
                    label = det.get("class") or det.get("condition", "unknown")
                    conf = det.get("confidence", 0)

                    cv2.rectangle(vis_img,(x1,y1),(x2,y2),(0,255,0),2)

                    cv2.putText(
                        vis_img,
                        f"{label}:{conf:.2f}",
                        (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0,255,0),
                        2
                    )

                    

                yolo_name = f"yolo_{unique_name}.jpg"
                yolo_path = os.path.join(processed_dir,yolo_name)

                cv2.imwrite(yolo_path,cv2.cvtColor(vis_img,cv2.COLOR_RGB2BGR))

                context["yolo_visualization"] = f"/media/processed/{yolo_name}"

            if pipeline_result.get('segmentation_mask') is not None:
                print("Segmentation mask received from pipeline")

                seg = np.array(pipeline_result['segmentation_mask'], dtype=np.uint8)
                # ---------- Severity calculation from segmentation ----------
                total_pixels = seg.size
                affected_pixels = np.count_nonzero(seg)


                coverage_ratio = affected_pixels / total_pixels
                severity_percent = int(min(coverage_ratio * 100, 100))
                print("YOLO DETECTIONS RECEIVED:", pipeline_result.get('yolo_detections'))

                print("SEGMENTATION COVERAGE:", severity_percent, "%")

                context["segmentation_severity"] = severity_percent
                # Attach segmentation coverage to detected conditions
                if "conditions" in context:
                    for cond in context["conditions"]:
                        cond["coverage"] = severity_percent


                if seg.max() <= 1:
                    seg = (seg * 255).astype(np.uint8)

                # Save colored mask
                mask_name = f"mask_{unique_name}.jpg"
                mask_path = os.path.join(processed_dir, mask_name)

                # normalize segmentation mask for heatmap
                heatmap = cv2.normalize(seg, None, 0, 255, cv2.NORM_MINMAX)

                heatmap = heatmap.astype(np.uint8)

                # create severity heatmap
                colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_TURBO)

                cv2.imwrite(mask_path, colored)

                context['segmentation_mask'] = f"/media/processed/{mask_name}"
                print("SEGMENTATION MASK URL:", context['segmentation_mask'])

                
                # Create overlay using selected crop
                if image_type == "skin":

                    if face_crop is not None:
                        overlay_crop = face_crop

                    elif scalp_crop is not None:
                        overlay_crop = scalp_crop

                    else:
                        overlay_crop = normalized_crop

                elif image_type == "scalp":

                    if scalp_crop is not None:
                        overlay_crop = scalp_crop

                    else:
                        overlay_crop = normalized_crop
                # ensure RGB format
                overlay_crop = overlay_crop.astype(np.uint8)

                seg_resized = cv2.resize(
                    seg,
                    (overlay_crop.shape[1], overlay_crop.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                )
                colored_seg = cv2.applyColorMap(seg_resized, cv2.COLORMAP_JET)
                overlay = cv2.addWeighted(overlay_crop, 0.65, colored_seg, 0.35, 0)


                vis_name = f"vis_{unique_name}.jpg"
                viz_dir = os.path.join(settings.MEDIA_ROOT, 'visualizations')
                os.makedirs(viz_dir, exist_ok=True)
                final_vis_path = os.path.join(viz_dir, vis_name)

                cv2.imwrite(final_vis_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
                context['visualized_image'] = f"/media/visualizations/{vis_name}"
                print("SEGMENTATION OVERLAY URL:", context['visualized_image'])

            

            # --- For scalp: build text from YOLO detections directly ---
            if image_type == "scalp" and pipeline_result.get('yolo_detections'):

                formatted = []

                for det in pipeline_result.get('yolo_detections', []):
                    name = det.get('condition') or det.get('class') or "normal"
                    confidence = float(det.get('confidence', 0))
                    score_int = int(confidence * 100)

                    if score_int < 30:
                        level = "Mild"
                    elif score_int < 70:
                        level = "Moderate"
                    else:
                        level = "Severe"

                    formatted.append({
                        'name': name.replace('_', ' ').title(),
                        'severity_level': level,
                        'severity_score': score_int
                    })

                if formatted:
                    context['conditions'] = formatted

            # --- For skin: use detected_conditions as before ---
            elif 'detected_conditions' in pipeline_result:

                formatted = []
                sev = pipeline_result.get('severity_scores', {})

                for c in pipeline_result.get('detected_conditions', []):
                    name = c.get('name') or c.get('condition') or "normal"
                    confidence = c.get('confidence', 0)

                    s = sev.get(name, {'score': confidence * 100, 'level': 'Detected'})

                    try:
                        score_int = int(s.get('score', confidence * 100))
                    except Exception:
                        score_int = int(confidence * 100)

                    formatted.append({
                        'name': name.replace('_', ' ').title(),
                        'severity_level': s.get('level', 'Detected'),
                        'severity_score': score_int
                    })

                if formatted:
                    context['conditions'] = formatted


            if 'severity_scores' in pipeline_result:
                context['max_severity'] = max(
                    [v.get('score', 0) for v in pipeline_result.get('severity_scores', {}).values()],
                    default=0
                )

            # Store last analysis for results view
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