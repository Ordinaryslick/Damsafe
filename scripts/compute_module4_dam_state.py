import pandas as pd
from pathlib import Path

# ---------------- CONFIG ----------------
PROJDIR = Path(r"C:\Users\Mahidha T\damsafe")
INPUT_CSV = PROJDIR / "outputs" / "tables" / "modules_1_2_3_outputs.csv"
OUTPUT_CSV = PROJDIR / "outputs" / "tables" / "module4_dam_state.csv"

# SDI thresholds
SDI_SAFE = 0.30
SDI_WARNING = 0.60
FAILURE_PERSISTENCE = 3   # consecutive events

# ---------------- LOAD DATA ----------------
df = pd.read_csv(INPUT_CSV)

if "SDI" not in df.columns:
    raise ValueError("SDI column not found. Run Module 2 first.")

# ---------------- DAM STATE COMPUTATION ----------------
states = []
failure_counter = 0

for sdi in df["SDI"]:
    if sdi < SDI_SAFE:
        states.append("Intact")
        failure_counter = 0

    elif SDI_SAFE <= sdi < SDI_WARNING:
        states.append("Damaged")
        failure_counter = 0

    else:
        failure_counter += 1
        if failure_counter >= FAILURE_PERSISTENCE:
            states.append("Failed")
        else:
            states.append("Damaged")

df["Dam_State_M4"] = states
df["Failure_Flag_M4"] = df["Dam_State_M4"].apply(lambda x: 1 if x == "Failed" else 0)

# ---------------- SAVE ----------------
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False)

print("✅ Module 4 completed: Dam State computed")
print("Saved:", OUTPUT_CSV)
print("\nPreview:")
print(df[["SDI", "Dam_State_M4", "Failure_Flag_M4"]].head(10))
