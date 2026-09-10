from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb

BASE_DIR = Path(__file__).resolve().parent
X_TRAINVAL = BASE_DIR / "store" / "X_trainval.npy"
Y_TRAINVAL = BASE_DIR / "store" / "y_trainval.npy"


X_trainval = np.load(X_TRAINVAL)
y_trainval = np.load(Y_TRAINVAL)

print("=" * 50)
print("5-FOLD CROSS VALIDATION")
print("=" * 50)

model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    objective='reg:squarederror',
    n_jobs=-1,
)

kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_mae, cv_rmse, cv_mape = [], [], []

for fold, (tr_idx, val_idx) in enumerate(kf.split(X_trainval), 1):
    X_tr, X_val = X_trainval[tr_idx], X_trainval[val_idx]
    y_tr, y_val = y_trainval[tr_idx], y_trainval[val_idx]

    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    y_pred = model.predict(X_val)

    mae  = mean_absolute_error(y_val, y_pred)
    rmse = np.sqrt(mean_squared_error(y_val, y_pred))
    mape = np.mean(np.abs((y_val - y_pred) / np.maximum(y_val, 1))) * 100

    cv_mae.append(mae)
    cv_rmse.append(rmse)
    cv_mape.append(mape)

    print(f"  Fold {fold}: MAE={mae:.1f}min  RMSE={rmse:.1f}min  MAPE={mape:.2f}%")

print(f"\n  Mean MAE:  {np.mean(cv_mae):.2f} ± {np.std(cv_mae):.2f} min")
print(f"  Mean RMSE: {np.mean(cv_rmse):.2f} ± {np.std(cv_rmse):.2f} min")
print(f"  Mean MAPE: {np.mean(cv_mape):.2f} ± {np.std(cv_mape):.2f}%")

# Plot CV results
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.suptitle('Figure 3 — 5-Fold Cross-Validation Results', fontsize=13, fontweight='bold')

folds = [f'Fold {i}' for i in range(1, 6)]
for scores, label, color, ax in [
    (cv_mae,  'MAE (minutes)',  '#1E3A5F', axes[0]),
    (cv_rmse, 'RMSE (minutes)', '#F5920A', axes[1]),
    (cv_mape, 'MAPE (%)',       '#2E7D52', axes[2]),
]:
    ax.bar(folds, scores, color=color, alpha=0.85, edgecolor='white')
    ax.axhline(np.mean(scores), color='red', linestyle='--', linewidth=1.5,
               label=f'Mean: {np.mean(scores):.1f}')
    ax.set_ylabel(label)
    ax.set_title(label)
    ax.legend(fontsize=9)
    ax.tick_params(axis='x', rotation=15)

plt.tight_layout()
plt.savefig('fig3_cv_scores.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nSaved: fig3_cv_scores.png")

np.save('cv_results.npy', {
    'mae': cv_mae, 'rmse': cv_rmse, 'mape': cv_mape
})
