from flask import Flask, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import numpy as np

app = Flask(__name__)
CORS(app)

# 🔥 LOAD MODELS
fish_model = YOLO("best.pt")
person_model = YOLO("yolov8n.pt")

print("MODEL CLASSES:", fish_model.names)


@app.route("/detect", methods=["POST"])
def detect():
    try:
        file = request.files["image"]

        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        # 🔥 LOWER CONF FOR BETTER DETECTION
        fish_results = fish_model(img, conf=0.2)
        person_results = person_model(img)

        detections = []
        defects = []
        person_detected = False

        species = None
        best_conf = 0
        length_cm = 0

        labels_detected = []

        # -------- FISH DETECTION --------
        if len(fish_results[0].boxes) > 0:
            for box in fish_results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                label = fish_model.names[cls].lower()
                labels_detected.append(label)

                # 🔥 SEPARATE DEFECTS
                if "damage" in label:
                    defects.append(label)

                else:
                    # ✅ PICK BEST SPECIES
                    if conf > best_conf:
                        species = label
                        best_conf = conf
                        length_cm = float(x2 - x1) * 0.1

                detections.append({
                    "label": label,
                    "confidence": round(conf * 100, 2),
                    "box": [float(x1), float(y1), float(x2), float(y2)],
                    "type": "fish"
                })

        print("DETECTED LABELS:", labels_detected)

        # -------- PERSON DETECTION --------
        for r in person_results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = person_model.names[cls]

                if label.lower() == "person":
                    person_detected = True

        # -------- SAFETY --------
        if species is None:
            species = "Unknown Fish"
            confidence = 0
        else:
            confidence = round(best_conf * 100, 2)

        # -------- FRESHNESS LOGIC --------
        if len(defects) == 0:
            freshness = "Fresh"
        elif len(defects) <= 2:
            freshness = "Moderate"
        else:
            freshness = "Spoiled"

        return jsonify({
            "species": species,
            "freshness": freshness,
            "confidence": confidence,
            "length": {"value": round(length_cm, 2)},
            "defects": defects,
            "person_detected": person_detected,
            "detections": detections
        })

    except Exception as e:
        print("ERROR:", str(e))

        return jsonify({
            "species": "Error",
            "freshness": "Unknown",
            "confidence": 0,
            "length": {"value": 0},
            "defects": [],
            "person_detected": False,
            "detections": []
        })


if __name__ == "__main__":
    app.run(debug=True)
