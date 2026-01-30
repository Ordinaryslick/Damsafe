import os
import pandas as pd
from osgeo import gdal

# Make GDAL raise Python exceptions (future-proof)
gdal.UseExceptions()

PROJECT_DIR = r"C:\Users\Mahidha T\damsafe"
CSV_PATH = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset_DEMOcoords.csv")
SLOPE_TIF = os.path.join(PROJECT_DIR, "outputs", "rasters", "slope_deg.tif")
OUT_CSV = os.path.join(PROJECT_DIR, "outputs", "tables", "module3_rdi_terrain.csv")
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

# RDI weights
W_PPV = 0.60
W_DIST = 0.25
W_SLOPE = 0.15


def minmax(s):
    s = s.astype(float)
    mn, mx = s.min(), s.max()
    if mx - mn == 0:
        return s * 0.0
    return (s - mn) / (mx - mn)


def inv_dist_norm(d):
    return 1.0 - minmax(d)


def inv_geotransform(gt):
    """
    Robust inverse geotransform across GDAL versions.
    Returns inverse GT tuple or None.
    """
    inv = gdal.InvGeoTransform(gt)

    # Possible return styles:
    # 1) (success_bool, inv_gt)
    # 2) inv_gt only
    # 3) (inv_gt, success_bool) in some builds (rare)
    if isinstance(inv, tuple) and len(inv) == 2 and isinstance(inv[0], (bool, int)):
        ok, inv_gt = inv
        return inv_gt if ok else None
    if isinstance(inv, tuple) and len(inv) == 2 and isinstance(inv[1], (bool, int)):
        inv_gt, ok = inv
        return inv_gt if ok else None
    if isinstance(inv, tuple) and len(inv) == 6:
        return inv

    return None


def sample_raster(ds, x, y):
    gt = ds.GetGeoTransform()
    inv_gt = inv_geotransform(gt)
    if inv_gt is None:
        return None

    # Pixel coordinates
    px = int(inv_gt[0] + inv_gt[1] * x + inv_gt[2] * y)
    py = int(inv_gt[3] + inv_gt[4] * x + inv_gt[5] * y)

    if px < 0 or py < 0 or px >= ds.RasterXSize or py >= ds.RasterYSize:
        return None

    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray(px, py, 1, 1)
    if arr is None:
        return None
    return float(arr[0, 0])


def main():
    df = pd.read_csv(CSV_PATH)

    # Required columns
    for col in ["PPV_mm_per_s", "Distance_from_Dam_m", "Blast_Easting", "Blast_Northing"]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    ds = gdal.Open(SLOPE_TIF)
    if ds is None:
        raise FileNotFoundError("Cannot open slope raster: " + SLOPE_TIF)

    slopes = []
    missing = 0

    for _, r in df.iterrows():
        x = float(r["Blast_Easting"])
        y = float(r["Blast_Northing"])
        s = sample_raster(ds, x, y)
        if s is None:
            missing += 1
            slopes.append(None)
        else:
            slopes.append(s)

    s_series = pd.Series(slopes, dtype="float64")
    if s_series.notna().sum() == 0:
        raise RuntimeError("All slope samples are None. Check that blast coordinates fall inside the slope raster extent.")

    df["Slope_deg"] = s_series.fillna(s_series.median())

    # Compute terrain-based RDI
    ppv_n = minmax(df["PPV_mm_per_s"])
    dist_risk = inv_dist_norm(df["Distance_from_Dam_m"])
    slope_n = minmax(df["Slope_deg"])

    df["RDI"] = (W_PPV * ppv_n) + (W_DIST * dist_risk) + (W_SLOPE * slope_n)
    df["RDI_Level"] = pd.cut(df["RDI"], [-0.01, 0.33, 0.66, 1.01], labels=["Low", "Moderate", "High"])

    df.to_csv(OUT_CSV, index=False)

    print("✅ Module 3 Terrain-based RDI computed.")
    print("Saved:", OUT_CSV)
    print("Missing slope samples auto-filled:", missing)


if __name__ == "__main__":
    main()
