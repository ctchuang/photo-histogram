import argparse
import json
import os
import pickle
import subprocess
import matplotlib.pyplot as plt


_PHOTO_LIBRARY_PATH = os.path.expanduser('~/Pictures/Photos Library.photoslibrary/originals/')
_CACHE_DB = "/tmp/photo-histogram.db"


def get_exif(file_path):
  cmd = ["exiftool", "-j", file_path]
  result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  return json.loads(result.stdout)


def get_focal_lengths_and_models():
  focal_lengths = []
  camera_models = []
  count = 1

  # Iterate through files in the folder
  for root, _, files in os.walk(_PHOTO_LIBRARY_PATH):
    for file in files:
      if not (file.endswith(".jpeg") or file.endswith(".heic")):
        continue
      print('Photo: ', count)
      count += 1

      file_path = os.path.join(root, file)
      tags = get_exif(file_path)[0]

      if 'FocalLength' in tags:
        focal_lengths.append(float(tags['FocalLength'].split(' ')[0]))

      if 'Model' in tags:
        camera_model = str(tags['Model'])
        camera_models.append(camera_model)

  return focal_lengths, camera_models


def plot_histogram(focal_lengths, camera_models):
  # Plot Focal Length Histogram
  plt.figure(figsize=(12, 5))
  plt.subplot(1, 2, 1)
  plt.hist(focal_lengths, bins=200, edgecolor='k')
  plt.title('Focal Length Histogram')
  plt.xlabel('Focal Length (mm)')
  plt.ylabel('Count')

  # Plot Camera Model Histogram
  plt.subplot(1, 2, 2)
  plt.hist(camera_models, bins=100, edgecolor='k')
  plt.title('Camera Model Histogram')
  plt.xlabel('Camera Model')
  plt.xticks(rotation=90)
  plt.ylabel('Count')

  plt.tight_layout()
  plt.show()


def main(cached: bool) -> None:
  if cached:
    with open(_CACHE_DB, 'rb') as f:
      focal_lengths, camera_models = pickle.load(f)
  else:
    focal_lengths, camera_models = get_focal_lengths_and_models()
    try:
      os.unlink(_CACHE_DB)
    except Exception as e:
      pass
    with open(_CACHE_DB, 'wb') as f:
      pickle.dump((focal_lengths, camera_models), f)

  plot_histogram(focal_lengths, camera_models)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--cached', action='store_true', help='Use cached data last time')
  args = parser.parse_args()
  main(args.cached)
