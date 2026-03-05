import cv2
import numpy as np
from joblib import load

# Load trained ML model
model = load("skin_model.pkl")

# ✅ EXACT label mapping based on training code
label_map = {
    0: "Dry Skin",
    1: "Normal Skin",
    2: "Oily Skin"
}

def detect_skin_type(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return "Image Error"

    # Resize same as training
    img = cv2.resize(img, (100, 100))

    # Extract SAME features as training
    hist = cv2.calcHist(
        [img],
        [0, 1, 2],
        None,
        [8, 8, 8],
        [0, 256, 0, 256, 0, 256]
    )
    hist = cv2.normalize(hist, hist).flatten()
    features = hist.reshape(1, -1)

    prediction = model.predict(features)[0]
    return label_map[int(prediction)]