from pathlib import Path
import numpy as np
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error
import xgboost as xgb


BASE_DIR = Path(__file__).resolve().parent
X_TRAINVAL = BASE_DIR / "store" / "X_trainval.npy"
Y_TRAINVAL = BASE_DIR / "store" / "y_trainval.npy"

X_trainval = np.load(X_TRAINVAL)
y_trainval = np.load(Y_TRAINVAL)




print("=" * 50)
print("HYPERPARAMETER TUNING")
print("=" * 50)

param_grid = [
    {'n_estimators': 300, 'max_depth': 4, 'learning_rate': 0.05, 'subsample': 0.8},
    {'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.05, 'subsample': 0.8},
    {'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.03, 'subsample': 0.9},
    {'n_estimators': 500, 'max_depth': 5, 'learning_rate': 0.03, 'subsample': 0.8},
    {'n_estimators': 200, 'max_depth': 6, 'learning_rate': 0.10, 'subsample': 0.7},
]

kf = KFold(n_splits=5, shuffle=True, random_state=42)
best_mae    = float('inf')
best_params = None

for i, params in enumerate(param_grid, 1):
    model = xgb.XGBRegressor(
        **params,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        colsample_bytree=0.8,
        random_state=42,
        objective='reg:squarederror',
        n_jobs=-1,
    )
    fold_maes = []
    for tr_idx, val_idx in kf.split(X_trainval):
        model.fit(X_trainval[tr_idx], y_trainval[tr_idx], verbose=False)
        pred = model.predict(X_trainval[val_idx])
        fold_maes.append(mean_absolute_error(y_trainval[val_idx], pred))

    mean_mae = np.mean(fold_maes)
    print(f"  Config {i}: MAE={mean_mae:.1f}min | {params}")

    if mean_mae < best_mae:
        best_mae    = mean_mae
        best_params = params

store_dir = BASE_DIR / "store"
store_dir.mkdir(parents=True, exist_ok=True)

print(f"\n  Best config: {best_params}")
print(f"  Best CV MAE: {best_mae:.2f} min")

np.save(store_dir / "best_params.npy", best_params)
print(f"Saved: {store_dir / 'best_params.npy'}")
