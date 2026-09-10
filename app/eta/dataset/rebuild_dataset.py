import pandas as pd
import numpy as np

np.random.seed(42)
df = pd.read_csv('eta_training_dataset.csv')

# Assign 15 drivers
df['driver_id'] = np.random.randint(1, 16, size=len(df)).astype(str)

# Driver behavior — some consistently faster, some slower
driver_factors = {
    '1': 1.05, '2': 0.92, '3': 1.12, '4': 0.88, '5': 1.00,
    '6': 1.08, '7': 0.95, '8': 1.15, '9': 0.90, '10': 1.03,
    '11': 0.97, '12': 1.10, '13': 0.93, '14': 1.06, '15': 0.99,
}

# Time of day effects
def hour_factor(h):
    if h in [7, 8]:           return 1.25  # morning rush
    elif h in [12, 13]:       return 1.10  # midday
    elif h in [14, 15]:       return 1.18  # afternoon rush
    elif h in [0,1,2,3,4,5]:  return 0.88  # overnight faster
    else:                     return 1.00

# Day of week effects
def day_factor(d):
    if d == 4:       return 1.15  # Friday
    elif d == 0:     return 1.08  # Monday
    elif d in [5,6]: return 0.90  # weekend
    else:            return 1.00

# Terminal road conditions
terminal_factors = {
    'Sapele Terminal':     1.08,
    'PHC Terminal':        1.12,
    'Gwagwalada Terminal': 0.95,
    'Kano Terminal':       1.05,
}

# Product handling time
product_factors = {
    'bitumen_60_70': 1.08, 'bitumen_80_100': 1.08, 'bitumen_40_50': 1.08,
    'polymer_modified_bitumen': 1.12, 'cationic_bitumen_emulsion': 1.10,
    'anionic_bitumen_emulsion': 1.10, 'cutback_bitumen': 1.06,
    'crumb_rubber_modified_bitumen': 1.15, 'liquefied_petroleum_gas': 1.20,
    'liquefied_natural_gas': 1.22, 'compressed_natural_gas': 1.18,
    'aviation_turbine_kerosene': 1.05, 'premium_motor_spirit': 1.03,
    'automotive_gas_oil': 1.02, 'heavy_fuel_oil': 1.08,
    'marine_gas_oil': 1.05, 'marine_diesel_oil': 1.04,
    'low_pour_fuel_oil': 1.06, 'natural_gas': 1.15,
    'engine_oil': 1.02, 'gear_oil': 1.02, 'hydraulic_oil': 1.02,
    'transmission_fluid': 1.02, 'base_oil': 1.03, 'paraffin_wax': 1.04,
    'grease': 1.03, 'solvent': 1.04, 'household_kerosene': 1.02,
    'dual_purpose_kerosene': 1.02,
}

def load_factor(u):
    if u > 0.90:   return 1.06
    elif u > 0.75: return 1.03
    else:          return 1.00

# Build realistic actual durations
actual_durations = []
for _, row in df.iterrows():
    base = row['base_eta_minutes']
    combined = (
        base
        * driver_factors.get(row['driver_id'], 1.0)
        * hour_factor(row['departure_hour'])
        * day_factor(row['day_of_week'])
        * terminal_factors.get(row['origin_terminal'], 1.0)
        * product_factors.get(row['product_name'], 1.03)
        * load_factor(row['load_utilization'])
    )
    # Random noise — 8% standard deviation
    noise = np.random.normal(0, base * 0.08)
    # 12% chance of a significant delay (roadblock, breakdown, fuel stop)
    if np.random.random() < 0.12:
        combined += np.random.uniform(30, 180)
    actual = max(combined + noise, base * 0.85)
    actual_durations.append(round(actual, 2))

df['actual_duration_minutes'] = actual_durations
df.to_csv('eta_training_v2.csv', index=False)

# Verify
corr = df['actual_duration_minutes'].corr(df['base_eta_minutes'])
print(f"Dataset saved: eta_training_v2.csv")
print(f"Shape: {df.shape}")
print(f"Correlation actual vs base: {corr:.4f}  (should be ~0.94, not 1.0)")
print(f"Actual duration mean: {df['actual_duration_minutes'].mean():.1f} min")
print(f"Actual duration std:  {df['actual_duration_minutes'].std():.1f} min")
