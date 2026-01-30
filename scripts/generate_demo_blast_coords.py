import os
import numpy as np
import pandas as pd
from pyproj import Transformer

PROJECT_DIR = r"C:\damsafe"
IN_CSV = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset.csv")
OUT_CSV = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset_DEMOcoords.csv")

# DEM extent from your gdalinfo (UTM meters)
XMIN = 726451.515
YMIN = 1267736.280
XMAX = 733266.521
YMAX = 1272548.710

df = pd.read_csv(IN_CSV)
n = len(df)

# Keep points away from edges by margin
MARGIN_M = 100

rng = np.random.default_rng(42)
xs = rng.uniform(XMIN + MARGIN_M, XMAX - MARGIN_M, size=n)
ys = rng.uniform(YMIN + MARGIN_M, YMAX - MARGIN_M, size=n)

df["Blast_Easting"] = xs
df["Blast_Northing"] = ys

# Convert to lat/lon too (optional)
transformer = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)
lons, lats = transformer.transform(xs, ys)
df["Blast_Lon"] = lons
df["Blast_Lat"] = lats

df.to_csv(OUT_CSV, index=False)
print("✅ Demo blast coordinates generated inside DEM extent.")
print("Saved:", OUT_CSV)

