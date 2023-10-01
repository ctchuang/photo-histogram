import argparse
from datetime import datetime
import json
import os
import pickle
import re
import subprocess
from typing import List, Tuple
import matplotlib.pyplot as plt


_PHOTO_LIBRARY_PATH = os.path.expanduser('~/Pictures/Photos Library.photoslibrary/originals/')
_CACHE_DB = "/tmp/photo-histogram.db"
_CAMERA_CROP_FACTORS = [
  # APS-C
  (re.compile(r'X-T\d+'), 1.5),
  (re.compile(r'Sony A6\d+'), 1.5),
  # M43
  (re.compile(r'Panasonic GH5'), 2.0),
  # iPhone
  (re.compile(r'iPhone 13 Pro'), 4.56),
  # GRD
  (re.compile(r'GR DIGITAL \d+'), 4.5),
  # ... Add other camera models and their crop factors as needed
]


def get_crop_factor(camera_model: str) -> float:
  for pattern, factor in _CAMERA_CROP_FACTORS:
    if pattern.match(camera_model):
      return value
  print('WARNING: unknown crop factor for camera model: ', camera_model)
  return 1.0


def get_exif(file_path: str) -> dict:
  cmd = ["exiftool", "-j", file_path]
  result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  return json.loads(result.stdout)[0]


def populate_data(metadata: List[Tuple[datetime, str, str, str, float, int, int]]) -> Tuple:
  pass


def get_exif_metadata(root_path: str) -> List[Tuple[datetime, str, str, str, float, int, int]]:
  results = []
  count = 1

  # Iterate through files in the folder
  for root, _, files in os.walk(root_path):
    for file in files:
      # Newer phone cameras usually output HEIC image format.
      if not (file.endswith(".jpeg") or file.endswith(".heic")): continue

      print("Photo: ", count); count += 1

      file_path = os.path.join(root, file)
      tags = get_exif(file_path)
      # for tag_key, tag_value in tags.items():
      #   print(f'{tag_key}: {tag_value}')

      # Remarks:
      #   - FocalLength35efl field cannot be trusted on some cameras. So we do not use this tag.
      date_original, maker, camera_model, lens_model, focal_length_x100, aperture, iso = (
        None, None, None, None, None, None, None)

      if 'DateTimeOriginal' in tags:
        try:
          date_original = datetime.strptime(tags['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
        except Exception as e:
          pass
      if 'Make' in tags:
        maker = str(tags['Make'])
      if 'Model' in tags:
        camera_model = str(tags['Model'])
      if 'LensModel' in tags:
        lens_model = str(tags['LensModel'])
      if 'Aperture' in tags:
        aperture = float(tags['Aperture'])
      if 'FocalLength' in tags:  # For smartphone, we need to use 0.01mm as
                                 # basic unit for focal lengths.
        focal_length_x100 = int(float(tags['FocalLength'].split(' ')[0]) * 100)  # ex: "70.0 mm" => 700
      if 'ISO' in tags:
        iso = int(tags['ISO'])

      results.append((date_original, maker, camera_model, lens_model, aperture, focal_length_x100, iso))

  return results


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
  metadata = None
  if cached:
    with open(_CACHE_DB, 'rb') as f:
      metadata = pickle.load(f)
  else:
    metadata = get_exif_metadata(_PHOTO_LIBRARY_PATH)
    try:
      os.unlink(_CACHE_DB)
    except Exception as e:
      pass
    with open(_CACHE_DB, 'wb') as f:
      pickle.dump(metadata, f)

  # plot_histogram(focal_lengths, camera_models)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--cached', action='store_true', help='Use data cached last time, do not scan all photos again.')
  args = parser.parse_args()
  main(args.cached)
