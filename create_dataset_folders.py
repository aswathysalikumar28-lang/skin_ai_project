import os

# Path to your project folder (change if needed)
project_folder = os.getcwd()  # This will create folders in the current folder

# Main dataset folder
dataset_folder = os.path.join(project_folder, "dataset")
os.makedirs(dataset_folder, exist_ok=True)

# Skin type subfolders
skin_types = ["dry", "normal", "non_skin", "oily"]

for skin in skin_types:
    path = os.path.join(dataset_folder, skin)
    os.makedirs(path, exist_ok=True)

print("Dataset folders created successfully!")