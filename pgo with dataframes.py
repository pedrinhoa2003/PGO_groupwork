# -*- coding: utf-8 -*-
"""
Created on Sat Nov  8 16:20:59 2025

@author: joana
"""

from pathlib import Path
import re
import ast
import pandas as pd

DATA_FILE = "instance_c1_30.dat"

# parameters
C_PER_SHIFT = 360   # minutes per shift (6h x 60)
CLEANUP = 17        # minutes for cleaning



# ------------------------------
# 1. Read file
# ------------------------------
text = Path(DATA_FILE).read_text(encoding="utf-8")


# ------------------------------
# 2. Functions
# ------------------------------
def get_int(name, alt_name=None):
    """Procura um inteiro tipo: int NumberPatients = 224;"""
    m = re.search(rf'int\s+{name}\s*=\s*(\d+)', text)
    if not m and alt_name:
        m = re.search(rf'int\s+{alt_name}\s*=\s*(\d+)', text)
    if not m:
        raise ValueError(f"Não encontrei o inteiro '{name}' em {DATA_FILE}")
    return int(m.group(1))

def get_array(name):
    """Procura um vetor tipo: Duration = [1,2,3,...];"""
    m = re.search(rf'{name}\s*=\s*(\[[\s\S]*?\])\s*;', text, re.DOTALL)
    if not m:
        raise ValueError(f"Não encontrei o array '{name}' em {DATA_FILE}")
    return ast.literal_eval(m.group(1))

# ------------------------------
# 3. Extract data from the file
# ------------------------------
n_patients = get_int("NumberPatients")
durations  = get_array("Duration")
priorities = get_array("Priority")
waitings   = get_array("Waiting")
surgeons   = get_array("Surgeon")
n_rooms = get_int("NumberOfRooms")
n_days  = get_int("NumberOfDays")
block_av = get_array("BlockAvailability")
n_surgeons = get_int("NumberSurgeons", alt_name="NumberOfSurgeons")
surg_av = get_array("SurgeonAvailability")


# ------------------------------
# 4. Dataframe for the patients
# ------------------------------
df_patients = pd.DataFrame({
    "patient_id": list(range(1, n_patients + 1)),
    "duration": durations,
    "priority": priorities,
    "waiting": waitings,
    "surgeon_id": surgeons
})


# ------------------------------
# 5. Dataframe for the rooms
# ------------------------------
rows = []
for r in range(n_rooms):        # rooms 0..R-1
    for d in range(n_days):     # days 0..D-1
        for turno in (1, 2):    # 1=AM, 2=PM
            available = int(block_av[d][r][turno-1])
            rows.append({
                "room": r + 1,          # 1-based
                "day": d + 1,           # 1-based
                "shift": turno,         # 1 ou 2
                "available": available  # 0/1
            })

df_rooms = pd.DataFrame(rows)


# ------------------------------
# 6.  Dataframe for the surgeons
# ------------------------------

rows = []
for s in range(n_surgeons):          
    for d in range(n_days):          
        for shift in (1, 2):         # 1=AM, 2=PM
            availability = int(surg_av[s][d][shift-1])
            rows.append({
                "surgeon_id": s + 1,          
                "day": d + 1,                 
                "shift": shift,               # 1 ou 2
                "available": availability
            })

df_surgeons = pd.DataFrame(rows)



# ------------------------------
# DISPATCHING RULE
# ------------------------------

# blocks that are available: (room, day, shift)
df_blocks_open = df_rooms[df_rooms["available"] == 1][["room", "day", "shift"]].copy()

# pairs (surgeon_id, day, shift) where the surgeon is available
df_surg_open = df_surgeons[df_surgeons["available"] == 1][["surgeon_id", "day", "shift"]].copy()


# a) expandir pacientes → (patient_id, surgeon_id, duration)
df_pmini = df_patients[["patient_id", "surgeon_id", "duration"]].copy()

# b) para cada paciente, quais (day, shift) o seu cirurgião pode trabalhar
df_p_time = df_pmini.merge(df_surg_open, on="surgeon_id", how="inner")

# c) cruzar com blocos de sala abertos no mesmo (day, shift)
df_p_blocks = df_p_time.merge(df_blocks_open, on=["day", "shift"], how="inner")

# d) capacidade simples do Step 1: duration + CLEANUP ≤ C_PER_SHIFT
df_p_blocks["fits_shift"] = (df_p_blocks["duration"] + CLEANUP) <= C_PER_SHIFT
df_p_blocks = df_p_blocks[df_p_blocks["fits_shift"] == True]

# get feasible block for each patient
df_feas_count = (
    df_p_blocks.groupby("patient_id", as_index=False)
               .agg(feasible_blocks=("room", "count"))
)

# add info to patient
df_patients_feasible_blocks = df_patients.merge(df_feas_count, on="patient_id", how="left")
df_patients_feasible_blocks["feasible_blocks"] = df_patients_feasible_blocks["feasible_blocks"].fillna(0).astype(int)














































