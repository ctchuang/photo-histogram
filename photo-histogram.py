import argparse
from datetime import datetime
import json
import os
import pickle
import re
import pandas as pd
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


def plot(df):
  df['camera_with_maker'] = df['maker'] + ' ' + df['camera_model']

  # Create a single figure with 3 rows and 2 columns of subplots
  fig, axs = plt.subplots(3, 2, figsize=(90, 90))

  # 1. Histogram of top 15 camera_model (prefixed with 'maker' name)
  top_cameras = df['camera_with_maker'].value_counts(ascending=True).tail(15)
  top_cameras.plot(kind='barh', ax=axs[0, 0])
  axs[0, 0].set_title('Top 15 Camera Model Histogram')
  axs[0, 0].set_xlabel('Count')
  axs[0, 0].set_ylabel('Camera Model')

  # 2. Histogram of top 15 lens_model
  top_lenses = df['lens_model'].value_counts(ascending=True).tail(15)
  top_lenses.plot(kind='barh', ax=axs[0, 1])
  axs[0, 1].set_title('Top 15 Lens Model Histogram')
  axs[0, 1].set_xlabel('Count')
  axs[0, 1].set_ylabel('Lens Model')

  # 3. Line plot of focal_length_x100
  df['focal_length'] = df['focal_length_x100'] / 100.0
  df['focal_length'].plot.hist(bins=40, ax=axs[1, 0])
  # df['focal_length_x100'].value_counts().sort_index().plot(kind='barh', ax=axs[1, 0])
  axs[1, 0].set_title('Focal Length')
  axs[1, 0].set_xlabel('Focal Length')
  axs[1, 0].set_ylabel('Count')

  # 4. Line plot of iso
  df['iso'].value_counts().sort_index().plot(kind='barh', ax=axs[1, 1])
  axs[1, 1].set_title('ISO')
  axs[1, 1].set_xlabel('ISO')
  axs[1, 1].set_ylabel('Count')

  # 5. Trend of counting over time by camera_model
  df.groupby(['date_original', 'camera_with_maker']).size().unstack().plot(ax=axs[2, 0])
  axs[2, 0].set_title('Count Trend Over Time by Camera Model')
  axs[2, 0].set_xlabel('Date')
  axs[2, 0].set_ylabel('Count')

  # 6. Trend of counting over time by lens_model
  df.groupby(['date_original', 'lens_model']).size().unstack().plot(ax=axs[2, 1])
  axs[2, 1].set_title('Count Trend Over Time by Lens Model')
  axs[2, 1].set_xlabel('Date')
  axs[2, 1].set_ylabel('Count')

  # Adjust layout to ensure plots do not overlap
  plt.tight_layout()
  plt.subplots_adjust(wspace=1.0, hspace=0.5, left=0.2)
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

  df = pd.DataFrame(metadata, columns=["date_original", "maker", "camera_model", "lens_model", "aperture", "focal_length_x100", "iso"])
  plot(df)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--cached', action='store_true', help='Use data cached last time, do not scan all photos again.')
  args = parser.parse_args()
  main(args.cached)
