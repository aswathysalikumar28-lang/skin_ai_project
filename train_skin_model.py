import os
import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from joblib import dump

dataset_path = "dataset"
skin_types = ["dry", "normal", "oily", "non_skin"]  # ✅ add non-skin

X = []
y = []

for label, skin in enumerate(skin_types):
    folder = os.path.join(dataset_path, skin)
    for file in os.listdir(folder):
        img_path = os.path.join(folder, file)
        img = cv2.imread(img_path)
        if img is None:
            continue

        img = cv2.resize(img, (100, 100))

        # Color histogram features
        hist = cv2.calcHist([img], [0,1,2], None, [8,8,8], [0,256,0,256,0,256])
        hist = cv2.normalize(hist, hist).flatten()

        X.append(hist)
        y.append(label)

X = np.array(X)
y = np.array(y)

model = RandomForestClassifier(n_estimators=200)
model.fit(X, y)

dump(model, "skin_model.pkl")
print("MODEL TRAINED")