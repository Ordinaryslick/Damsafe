import os
import numpy as np
import pandas as pd

# =========================
# CONFIG
# =========================
PROJECT_DIR = r"C:\Users\Mahidha T\damsafe"
CSV_PATH = os.path.join(PROJECT_DIR, "data", "Bhavani_Sagar_Controlled_Blasting_Dataset.csv")
OUT_DIR = os.path.join(PROJECT_DIR, "outputs", "tables")
os.makedirs(OUT_DIR, exist_ok=True)

OUT_CSV = os.path.join(OUT_DIR, "modules_1_2_3_outputs.csv")

# ---- Weights (tune later) ----
# Module 1 (BVII): PPV + Distance + (optional) Charge_Factor
W_PPV = 0.65
W_DIST = 0.25
W_CHARGE = 0.10

# Module 2 (SDI): accumulation factor
SDI_GAIN = 1.0  # scale factor on accumulation

# Module 3 (RDI): PPV + Distance + (optional) Slope
W_RDI_PPV = 0.60
W_RDI_DIST = 0.25
W_RDI_SLOPE = 0.15

# If you don't have slope per blast yet, use a constant (degrees)
DEFAULT_SLOPE_DEG = 10.0

# =========================
# HELPERS
# =========================
def minmax(series: pd.Series, clip=True) -> pd.Series:
    """Min-max normalize to 0..1 safely."""
    s = series.astype(float)
    mn, mx = np.nanmin(s), np.nanmax(s)
    if mx - mn == 0:
        out = pd.Series(np.zeros(len(s)), index=s.index)
    else:
        out = (s - mn) / (mx - mn)
    return out.clip(0, 1) if clip else out

def inv_distance_norm(dist_m: pd.Series) -> pd.Series:
    """Convert distance to 'risk' (closer = higher), normalized 0..1."""
    d_norm = minmax(dist_m)
    return 1.0 - d_norm

# =========================
# MAIN
# =========================
df = pd.read_csv(CSV_PATH)

# ---- Basic checks (your dataset uses these names) ----
required = ["PPV_mm_per_s", "Distance_from_Dam_m"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns in CSV: {missing}")

# Optional features
has_charge = "Charge_Factor_kg_per_m" in df.columns
has_slope = "Slope_deg" in df.columns  # you can add later after sampling from raster

# If slope not present, create a demo slope column
if not has_slope:
    df["Slope_deg"] = DEFAULT_SLOPE_DEG

# -------------------------
# MODULE 1: BVII
# -------------------------
ppv_n = minmax(df["PPV_mm_per_s"])
dist_risk = inv_distance_norm(df["Distance_from_Dam_m"])

if has_charge:
    charge_n = minmax(df["Charge_Factor_kg_per_m"])
else:
    charge_n = 0.0  # if missing, contributes nothing

df["BVII"] = (W_PPV * ppv_n) + (W_DIST * dist_risk) + (W_CHARGE * charge_n)

# Optional label
df["BVII_Level"] = pd.cut(
    df["BVII"],
    bins=[-0.01, 0.33, 0.66, 1.01],
    labels=["Low", "Moderate", "High"]
)

# -------------------------
# MODULE 2: SDI (cumulative damage)
# -------------------------
# If you have real timestamps later, sort by time first.
# For now, we treat row order as blast order.
df["Delta_t"] = 1.0  # placeholder time step (can be hours/days later)

# SDI(t) = SDI(t-1) + SDI_GAIN * BVII(t) * Delta_t
df["SDI"] = (SDI_GAIN * df["BVII"] * df["Delta_t"]).cumsum()

# Threshold-based dam state (edit thresholds later)
Tsafe, Twarn, Tcrit = 50, 120, 200
df["Dam_State"] = np.select(
    [df["SDI"] < Tsafe, (df["SDI"] >= Tsafe) & (df["SDI"] < Twarn), (df["SDI"] >= Twarn) & (df["SDI"] < Tcrit), df["SDI"] >= Tcrit],
    ["Safe", "Warning", "Critical", "Failed"],
    default="Safe"
)

# -------------------------
# MODULE 3: RDI (rock mass disturbance)
# -------------------------
slope_n = minmax(df["Slope_deg"])
df["RDI"] = (W_RDI_PPV * ppv_n) + (W_RDI_DIST * dist_risk) + (W_RDI_SLOPE * slope_n)

df["RDI_Level"] = pd.cut(
    df["RDI"],
    bins=[-0.01, 0.33, 0.66, 1.01],
    labels=["Low", "Moderate", "High"]
)

# -------------------------
# SAVE OUTPUTS
# -------------------------
cols_to_save = list(df.columns)  # or choose specific columns
df.to_csv(OUT_CSV, index=False)

print("✅ Modules 1,2,3 computed successfully.")
print("Saved:", OUT_CSV)
print("\nQuick preview:")
print(df[["PPV_mm_per_s", "Distance_from_Dam_m", "BVII", "BVII_Level", "SDI", "Dam_State", "RDI", "RDI_Level"]].head(10))
