import os
import subprocess
import exifread
import matplotlib.pyplot as plt

def get_focal_lengths_and_models():
    focal_lengths = []
    camera_models = []

    # Iterate through files in the folder
    for root, _, files in os.walk('.'):
        for file in files:
            if not file.endswith(".jpeg"):
              continue
            file_path = os.path.join(root, file)

            with open(file_path, "rb") as f:
              tags = exifread.process_file(f)

            # Extract the FocalLength tag
            focal_length_tag = tags.get('EXIF FocalLength')
            if focal_length_tag:
                focal_length = float(focal_length_tag.values[0].num) / float(focal_length_tag.values[0].den)
                focal_lengths.append(focal_length)

            # Extract the Model tag
            model_tag = tags.get('Image Model')
            if model_tag:
                camera_model = str(model_tag)
                camera_models.append(camera_model)

    return focal_lengths, camera_models

def plot_histogram(focal_lengths, camera_models):
    # Plot Focal Length Histogram
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.hist(focal_lengths, bins=20, edgecolor='k')
    plt.title('Focal Length Histogram')
    plt.xlabel('Focal Length (mm)')
    plt.ylabel('Frequency')

    # Plot Camera Model Histogram
    plt.subplot(1, 2, 2)
    plt.hist(camera_models, bins=60, edgecolor='k')
    plt.title('Camera Model Histogram')
    plt.xlabel('Camera Model')
    plt.xticks(rotation=90)
    plt.ylabel('Frequency')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    focal_lengths, camera_models = get_focal_lengths_and_models()
    plot_histogram(focal_lengths, camera_models)
