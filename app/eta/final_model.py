from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
import pickle

BASE_DIR = Path(__file__).resolve().parent

X_TRAINVAL = BASE_DIR / "store" / "X_trainval.npy"
Y_TRAINVAL = BASE_DIR / "store" / "y_trainval.npy"
X_TEST = BASE_DIR / "store" / "X_test.npy"
Y_TEST = BASE_DIR / "store" / "y_test.npy"

BEST_PARAMS = BASE_DIR / "store" / "best_params.npy"


X_trainval = np.load(X_TRAINVAL)
X_test     = np.load(X_TEST)
y_trainval = np.load(Y_TRAINVAL)
y_test     = np.load(Y_TEST)
best_params = np.load(BEST_PARAMS, allow_pickle=True).item()

print("=" * 50)
print("FINAL MODEL — TRAINING ON FULL TRAIN+VAL SET")
print("=" * 50)
print(f"Best params: {best_params}")

final_model = xgb.XGBRegressor(
    **best_params,
    min_child_weight=5,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    colsample_bytree=0.8,
    random_state=42,
    objective='reg:squarederror',
    n_jobs=-1,
)
final_model.fit(X_trainval, y_trainval, verbose=False)

y_pred = final_model.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
ss_res = np.sum((y_test - y_pred) ** 2)
ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
r2   = 1 - ss_res / ss_tot

print("\n" + "=" * 50)
print("FINAL TEST SET RESULTS")
print("=" * 50)
print(f"  MAE:  {mae:.2f} min  ({mae/60:.2f} hrs)")
print(f"  RMSE: {rmse:.2f} min  ({rmse/60:.2f} hrs)")
print(f"  MAPE: {mape:.2f}%")
print(f"  R²:   {r2:.4f}")

# Save model
final_model.save_model('eta_model_v1.json')
print("\nModel saved: eta_model_v1.json")
