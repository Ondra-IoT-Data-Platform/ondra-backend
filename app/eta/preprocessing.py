from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import pickle



BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset" / "eta_training_v2.csv"

df = pd.read_csv(DATASET_PATH)

print("=" * 50)
print("PREPROCESSING")
print("=" * 50)

# Encode categorical columns
le_terminal = LabelEncoder()
le_product  = LabelEncoder()
le_driver   = LabelEncoder()

df['terminal_enc'] = le_terminal.fit_transform(df['origin_terminal'])
df['product_enc']  = le_product.fit_transform(df['product_name'])
df['driver_enc']   = le_driver.fit_transform(df['driver_id'].astype(str))

print(f"Terminals encoded: {dict(zip(le_terminal.classes_, le_terminal.transform(le_terminal.classes_)))}")
print(f"Products: {len(le_product.classes_)} unique values")
print(f"Drivers:  {len(le_driver.classes_)} unique values")

# Feature columns
FEATURE_COLS = [
    'distance_km',
    'base_eta_minutes',
    'departure_hour',
    'day_of_week',
    'is_weekend',
    'is_peak_hour',
    'quantity_litres',
    'load_utilization',
    'tare_weight_tonnes',
    'gross_weight_tonnes',
    'net_weight_tonnes',
    'loading_temperature_c',
    'fuel_at_departure_litres',
    'terminal_enc',
    'product_enc',
    'driver_enc',
]

TARGET = 'actual_duration_minutes'

X = df[FEATURE_COLS].values
y = df[TARGET].values

print(f"\nFeatures: {len(FEATURE_COLS)}")
print(f"X shape: {X.shape}")
print(f"y shape: {y.shape}")
print(f"y mean: {y.mean():.1f} min  std: {y.std():.1f} min")

# 70/30 split
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42
)

print(f"\nTrain+Val: {X_trainval.shape[0]} rows")
print(f"Test:      {X_test.shape[0]} rows")

# Save everything
np.save('X_trainval.npy', X_trainval)
np.save('X_test.npy', X_test)
np.save('y_trainval.npy', y_trainval)
np.save('y_test.npy', y_test)

with open('label_encoders.pkl', 'wb') as f:
    pickle.dump({
        'terminal': le_terminal,
        'product':  le_product,
        'driver':   le_driver,
        'feature_cols': FEATURE_COLS,
    }, f)

print("\nSaved: X_trainval.npy, X_test.npy, y_trainval.npy, y_test.npy")
print("Saved: label_encoders.pkl")
