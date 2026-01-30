# ==========================================================
# Standalone PyQGIS Script (QGIS 3.40 LTR) — Robust & Working
# Outputs:
#  slope_deg.tif, dam_raster.tif, distance_to_dam.tif,
#  ppv_est.tif, bvii.tif, sdi.tif
# ==========================================================

import os
import sys

# --- QGIS module available because you run via python-qgis-ltr.bat ---
import qgis

# Locate QGIS python + plugins dynamically
qgis_python_dir = os.path.dirname(os.path.dirname(qgis.__file__))  # ...\apps\qgis-ltr\python
qgis_prefix_dir = os.path.dirname(qgis_python_dir)                 # ...\apps\qgis-ltr
plugins_dir = os.path.join(qgis_python_dir, "plugins")             # ...\apps\qgis-ltr\python\plugins
if plugins_dir not in sys.path:
    sys.path.insert(0, plugins_dir)

import processing

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsRectangle,
)
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from processing.algs.gdal.GdalAlgorithmProvider import GdalAlgorithmProvider


# =========================
# CONFIG (EDIT IF NEEDED)
# =========================
PROJECT_DIR = r"C:\Users\Mahidha T\damsafe"
DEM_PATH = os.path.join(PROJECT_DIR, r"data\dem\processed\bhavanisagar_dem_utm.tif")

OUT_DIR = os.path.join(PROJECT_DIR, "outputs", "rasters")
os.makedirs(OUT_DIR, exist_ok=True)

# Try Bhavanisagar dam (WGS84 lat/lon) — if outside DEM, script auto-uses DEM center
DAM_LAT = 11.470833
DAM_LON = 77.113889

# Desired analysis CRS (meters)
PROJECT_CRS = "EPSG:32643"

# ---- Scenario blast params (placeholders, tune later) ----
W_charge_kg = 50
K = 1500
alpha = 1.6

# BVII weights
w_ppv, w_dist, w_slope = 0.6, 0.25, 0.15

# Normalization ranges (placeholders)
PPV_MIN, PPV_MAX = 0.0, 50.0
DIST_MIN, DIST_MAX = 0.0, 2000.0
SLOPE_MIN, SLOPE_MAX = 0.0, 30.0


def ensure_provider(reg, provider_id, provider_obj):
    """Add provider only if not present (avoids duplicate warnings)."""
    if reg.providerById(provider_id) is None:
        reg.addProvider(provider_obj)


def main():
    if not os.path.exists(DEM_PATH):
        raise FileNotFoundError(f"❌ DEM not found:\n{DEM_PATH}")

    # --- IMPORTANT: fix initialization for headless ---
    QgsApplication.setPrefixPath(qgis_prefix_dir, True)

    qgs = QgsApplication([], False)
    qgs.initQgis()

    # Init Processing + providers
    Processing.initialize()
    reg = QgsApplication.processingRegistry()
    ensure_provider(reg, "native", QgsNativeAlgorithms())
    ensure_provider(reg, "gdal", GdalAlgorithmProvider())

    # Load DEM
    dem = QgsRasterLayer(DEM_PATH, "dem")
    if not dem.isValid():
        raise RuntimeError(f"❌ DEM failed to load:\n{DEM_PATH}")

    # Set project CRS to DEM CRS for safe raster operations
    QgsProject.instance().setCrs(dem.crs())

    # ----------------------------------------------------------
    # Determine a valid dam point IN DEM EXTENT
    # ----------------------------------------------------------
    dem_extent: QgsRectangle = dem.extent()

    # Create dam in WGS84 and transform into DEM CRS
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    dem_crs = dem.crs()

    xform = QgsCoordinateTransform(wgs84, dem_crs, QgsProject.instance())

    dam_point_dem = xform.transform(QgsPointXY(DAM_LON, DAM_LAT))

    dam_inside = dem_extent.contains(dam_point_dem)

    if not dam_inside:
        # Auto-pick DEM center so pipeline ALWAYS runs
        center = dem_extent.center()
        print("⚠️ WARNING: Given dam lat/lon is outside DEM extent.")
        print("✅ Using DEM CENTER as demo dam point so outputs can be generated.")
        dam_point_dem = center

    # Build dam point layer in DEM CRS (so rasterize aligns perfectly)
    dam_layer = QgsVectorLayer(f"Point?crs={dem_crs.authid()}", "dam_point", "memory")
    prov = dam_layer.dataProvider()
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPointXY(dam_point_dem))
    prov.addFeatures([f])
    dam_layer.updateExtents()

    # ----------------------------------------------------------
    # 1) Slope (degrees)
    # ----------------------------------------------------------
    slope_out = os.path.join(OUT_DIR, "slope_deg.tif")
    processing.run("gdal:slope", {
        "INPUT": dem,
        "BAND": 1,
        "AS_PERCENT": False,
        "COMPUTE_EDGES": True,
        "Z_FACTOR": 1.0,
        "OUTPUT": slope_out
    })
    slope_r = QgsRasterLayer(slope_out, "slope")
    if not slope_r.isValid():
        raise RuntimeError("❌ Slope raster failed.")

    # ----------------------------------------------------------
    # 2) Rasterize dam point onto DEM grid (robust)
    # ----------------------------------------------------------
    dam_ras = os.path.join(OUT_DIR, "dam_raster.tif")
    processing.run("gdal:rasterize", {
        "INPUT": dam_layer,
        "FIELD": None,
        "BURN": 1,
        "UNITS": 0,  # georeferenced units
        "WIDTH": dem.rasterUnitsPerPixelX(),
        "HEIGHT": dem.rasterUnitsPerPixelY(),
        "EXTENT": dem.extent(),
        "NODATA": 0,
        "DATA_TYPE": 5,  # Float32
        "INIT": 0,
        "INVERT": False,
        "OPTIONS": "",
        "EXTRA": "",
        "OUTPUT": dam_ras
    })

    dam_r = QgsRasterLayer(dam_ras, "dam")
    if not dam_r.isValid():
        raise RuntimeError("❌ Dam raster failed.")

    # ----------------------------------------------------------
    # 3) Distance to dam (proximity)
    # ----------------------------------------------------------
    dist_out = os.path.join(OUT_DIR, "distance_to_dam.tif")
    processing.run("gdal:proximity", {
        "INPUT": dam_ras,
        "BAND": 1,
        "VALUES": "1",
        "UNITS": 0,   # same units as DEM CRS (meters if UTM)
        "MAX_DISTANCE": 0,
        "REPLACE": 0,
        "NODATA": 0,
        "OPTIONS": "",
        "EXTRA": "",
        "OUTPUT": dist_out
    })

    dist_r = QgsRasterLayer(dist_out, "distance")
    if not dist_r.isValid():
        raise RuntimeError("❌ Distance raster failed.")

    # ----------------------------------------------------------
    # 4) PPV (use ^ operator, avoid pow() parsing issues)
    # PPV = K * (D / sqrt(W))^(-alpha)
    # ----------------------------------------------------------
    ppv_out = os.path.join(OUT_DIR, "ppv_est.tif")
    expr_ppv = f"{K} * ((\"distance@1\" / sqrt({W_charge_kg})) ^ (-{alpha}))"

    processing.run("qgis:rastercalculator", {
        "EXPRESSION": expr_ppv,
        "LAYERS": [dist_r],
        "CRS": dem.crs(),
        "EXTENT": dem.extent(),
        "CELL_SIZE": dem.rasterUnitsPerPixelX(),
        "OUTPUT": ppv_out
    })

    ppv_r = QgsRasterLayer(ppv_out, "ppv")
    if not ppv_r.isValid():
        raise RuntimeError("❌ PPV raster failed.")

    # ----------------------------------------------------------
    # 5) BVII (normalized weighted sum)
    # ----------------------------------------------------------
    bvii_out = os.path.join(OUT_DIR, "bvii.tif")
    expr_bvii = (
        f"{w_ppv} * ((\"ppv@1\" - {PPV_MIN}) / ({PPV_MAX}-{PPV_MIN})) + "
        f"{w_dist} * (1 - ((\"distance@1\" - {DIST_MIN}) / ({DIST_MAX}-{DIST_MIN}))) + "
        f"{w_slope} * ((\"slope@1\" - {SLOPE_MIN}) / ({SLOPE_MAX}-{SLOPE_MIN}))"
    )

    processing.run("qgis:rastercalculator", {
        "EXPRESSION": expr_bvii,
        "LAYERS": [ppv_r, dist_r, slope_r],
        "CRS": dem.crs(),
        "EXTENT": dem.extent(),
        "CELL_SIZE": dem.rasterUnitsPerPixelX(),
        "OUTPUT": bvii_out
    })

    bvii_r = QgsRasterLayer(bvii_out, "bvii")
    if not bvii_r.isValid():
        raise RuntimeError("❌ BVII raster failed.")

    # ----------------------------------------------------------
    # 6) SDI baseline (SDI = BVII)
    # ----------------------------------------------------------
    sdi_out = os.path.join(OUT_DIR, "sdi.tif")
    processing.run("qgis:rastercalculator", {
        "EXPRESSION": "\"bvii@1\"",
        "LAYERS": [bvii_r],
        "CRS": dem.crs(),
        "EXTENT": dem.extent(),
        "CELL_SIZE": dem.rasterUnitsPerPixelX(),
        "OUTPUT": sdi_out
    })

    print("\n✅ SUCCESS — Outputs created in:")
    print("   ", OUT_DIR)
    print("   slope_deg.tif")
    print("   dam_raster.tif")
    print("   distance_to_dam.tif")
    print("   ppv_est.tif")
    print("   bvii.tif")
    print("   sdi.tif")

    if not dam_inside:
        print("\n⚠️ NOTE:")
        print("   The Bhavanisagar lat/lon you provided was outside your DEM tile.")
        print("   Outputs were generated using the DEM center as a demo dam point.")
        print("   To use the real dam, download a DEM tile covering Bhavanisagar or update DEM_PATH.")

    qgs.exitQgis()


if __name__ == "__main__":
    main()
