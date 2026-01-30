import os
import pandas as pd

PROJECT_DIR = r"C:\Users\Mahidha T\damsafe"
IN_CSV = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset.csv")
OUT_CSV = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset_with_coords.csv")

df = pd.read_csv(IN_CSV)

# Choose ONE coordinate style:
# A) Lat/Lon (WGS84)
for col in ["Blast_Lon", "Blast_Lat"]:
    if col not in df.columns:
        df[col] = ""   # empty cells

# B) UTM (EPSG:32643)
for col in ["Blast_Easting", "Blast_Northing"]:
    if col not in df.columns:
        df[col] = ""   # empty cells

df.to_csv(OUT_CSV, index=False)

print("✅ Added coordinate columns (empty).")
print("Saved:", OUT_CSV)
print("Now open this CSV and fill either Lat/Lon or Easting/Northing.")
