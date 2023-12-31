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
import matplotlib.ticker as ticker


_PHOTO_LIBRARY_PATH = os.path.expanduser('~/Pictures/Photos Library.photoslibrary/originals/')
_CACHE_DB = "/tmp/photo-histogram.db"
_CAMERA_CROP_FACTORS = [
  # Full-Frame
  (re.compile(r'EOS\s+\d+D'), 1.0),
  (re.compile(r'EOS\s+RP'), 1.0),
  (re.compile(r'EOS\s+R\d+'), 1.0),
  # APS-C
  (re.compile(r'X-T\d+'), 1.5),
  (re.compile(r'Sony A6\d+'), 1.5),
  (re.compile(r'Canon EOS Kiss Digital N'), 1.6),
  # M43
  (re.compile(r'Panasonic GH5'), 2.0),
  (re.compile(r'D-LUX \(Typ 109\)'), 2.0),
  # Sub 1-inch
  (re.compile(r'GR DIGITAL \d+'), 4.5),  # 1/1.7" CCD
  (re.compile(r'PowerShot S80'), 4.8),  # 1/1.8" CCD
  (re.compile(r'IXUS 200'), 5.6),  # 1/2.3" CCD
  (re.compile(r'IXUS 860'), 6.0), # 1/2.5" CCD
  (re.compile(r'IXUS v'), 6.56),  # 1/2.7" CCD
  (re.compile(r'E2500'), 6.56),
  # ... Add your own camera models and crop factors as needed.
]


def get_crop_factor(camera_model: str) -> float:
  for pattern, factor in _CAMERA_CROP_FACTORS:
    if pattern.search(camera_model):
      return factor
  print('WARNING: unknown crop factor for camera model: ', camera_model)
  return 1.0


def convert_focal_length(row):
  if pd.isna(row['focal_length_x100']) or pd.isna(row['camera_model']):
    return 0
  crop_factor = get_crop_factor(row['camera_model'])
  return int(row['focal_length_x100'] * crop_factor / 100.0)


def get_exif(file_path: str) -> dict:
  cmd = ["exiftool", "-j", file_path]
  result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  return json.loads(result.stdout)[0]


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
  non_phone_df = df[~df['camera_with_maker'].str.contains(r'(phone|pad|pixel|samsung|nexus|htc)', case=False,
                                                          na=False, regex=True)]

  # Create a single figure with 3 rows and 2 columns of subplots
  fig, axs = plt.subplots(3, 2, figsize=(40, 25))

  # 1. Histogram of top 15 camera_model (prefixed with 'maker' name)
  top_cameras = df['camera_with_maker'].value_counts(ascending=True).tail(15)
  top_cameras.plot(kind='barh', ax=axs[0, 0])
  axs[0, 0].set_title('Top 15 Camera Models')
  axs[0, 0].set_xlabel('Photo Count')
  axs[0, 0].set_ylabel('')  # limited space

  # 2. Histogram of top 15 lens_model (non-phone)
  top_lenses = non_phone_df['lens_model'].value_counts(ascending=True).tail(15)
  top_lenses.plot(kind='barh', ax=axs[0, 1])
  axs[0, 1].set_title('Top 15 Lens Models (excl. phones)')
  axs[0, 1].set_xlabel('Photo Count')
  axs[0, 1].set_ylabel('')  # limited space

  # 3. Histogram of focal length (non-phone)
  non_phone_df['focal_length_35_equiv'] = non_phone_df.apply(convert_focal_length, axis=1)
  non_phone_df['focal_length_35_equiv'].plot.hist(bins=50, ax=axs[1, 0])
  axs[1, 0].set_title('Focal Length - 35mm equivalent (excl. phones)')
  axs[1, 0].set_xlabel('Focal Length')
  axs[1, 0].set_ylabel('Count')
  axs[1, 0].xaxis.set_major_locator(ticker.FixedLocator([16, 24, 35, 50, 70, 85, 135, 200]))
  axs[1, 0].set_xticklabels(axs[1, 0].get_xticks(), rotation=90)

  # 4. Histogram of ISO (non-phone)
  low_iso = non_phone_df[non_phone_df['iso'] <= 3200]
  low_iso['iso'].plot.hist(bins=40, ax=axs[1, 1])
  axs[1, 1].set_title('ISO 0~3200 (excl. phones)')
  axs[1, 1].set_xlabel('ISO')
  axs[1, 1].set_ylabel('Count')
  axs[1, 1].xaxis.set_major_locator(ticker.FixedLocator([100, 200, 400, 640, 800, 1280, 1600, 3200]))
  axs[1, 1].set_xticklabels(axs[1, 1].get_xticks(), rotation=45)

  # 5. Trend of counting over time by camera_model
  df.set_index('date_original', inplace=True)
  top_10_cameras = df['camera_with_maker'].value_counts().head(10).index
  yearly_counts = df.groupby([pd.Grouper(freq='Y'), 'camera_with_maker']).size().unstack(fill_value=0)
  yearly_counts = yearly_counts[top_10_cameras]
  yearly_counts.plot.bar(ax=axs[2, 0], stacked=True)
  axs[2, 0].set_xticklabels([x.year for x in yearly_counts.index])
  axs[2, 0].set_title('Top 10 Camera Models over Time')
  axs[2, 0].set_xlabel('Date')
  axs[2, 0].set_ylabel('')  # Save screen estate.
  axs[2, 0].set_yscale('log')
  axs[2, 0].legend(loc='upper right', bbox_to_anchor=(-0.08, 1), ncol=1)

  # 6. Trend of counting over time by lens_model (non-phone)
  non_phone_df.set_index('date_original', inplace=True)
  top_10_lens = non_phone_df['lens_model'].value_counts().head(10).index
  yearly_counts = non_phone_df.groupby([pd.Grouper(freq='Y'), 'lens_model']).size().unstack(fill_value=0)
  yearly_counts = yearly_counts[top_10_lens]
  yearly_counts.plot.bar(ax=axs[2, 1], stacked=True)
  axs[2, 1].set_xticklabels([x.year for x in yearly_counts.index])
  axs[2, 1].set_title('Top 10 Lens over Time (excl. phones)')
  axs[2, 1].set_xlabel('Date')
  axs[2, 1].set_ylabel('')  # Save screen estate.
  axs[2, 1].set_yscale('log')
  axs[2, 1].legend(loc='upper right', bbox_to_anchor=(-0.08, 1), ncol=1)

  # Adjust layout to ensure plots do not overlap
  plt.tight_layout()
  plt.subplots_adjust(wspace=0.77, hspace=0.43, left=0.17, right=0.99, top=0.96, bottom=0.07)
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
  print(df)
  plot(df)


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--cached', action='store_true', help='Use data cached last time, do not scan all photos again.')
  args = parser.parse_args()
  main(args.cached)
