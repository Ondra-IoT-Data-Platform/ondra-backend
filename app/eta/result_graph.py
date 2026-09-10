
from pathlib import Path
import numpy as np
import pandas as pd
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

LAB_ENCODERS = BASE_DIR / "store" / "label_encoders.pkl"


X_trainval = np.load(X_TRAINVAL)
X_test     = np.load(X_TEST)
y_trainval = np.load(Y_TRAINVAL)
y_test     = np.load(Y_TEST)
best_params = np.load(BEST_PARAMS, allow_pickle=True).item()



with open(LAB_ENCODERS, 'rb') as f:
    encoders = pickle.load(f)
FEATURE_COLS = encoders['feature_cols']

final_model = xgb.XGBRegressor(**best_params, min_child_weight=5,
    gamma=0.1, reg_alpha=0.1, reg_lambda=1.0, colsample_bytree=0.8,
    random_state=42, objective='reg:squarederror', n_jobs=-1)
final_model.fit(X_trainval, y_trainval, verbose=False)
y_pred = final_model.predict(X_test)

mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
r2   = 1 - np.sum((y_test-y_pred)**2) / np.sum((y_test-np.mean(y_test))**2)

# Figure 4 — Actual vs Predicted + Residuals
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('Figure 4 — XGBoost ETA Model — Test Set Results', fontsize=13, fontweight='bold')

axes[0].scatter(y_test/60, y_pred/60, alpha=0.4, color='#1E3A5F', s=15)
max_val = max(y_test.max(), y_pred.max()) / 60
axes[0].plot([0, max_val], [0, max_val], 'r--', linewidth=1.5, label='Perfect prediction')
axes[0].set_xlabel('Actual Duration (hours)')
axes[0].set_ylabel('Predicted Duration (hours)')
axes[0].set_title(f'Actual vs Predicted\nMAE={mae:.0f}min  RMSE={rmse:.0f}min  R²={r2:.3f}')
axes[0].legend()

residuals = y_test - y_pred
axes[1].hist(residuals/60, bins=40, color='#F5920A', edgecolor='white', alpha=0.85)
axes[1].axvline(0, color='red', linestyle='--', linewidth=1.5, label='Zero error')
axes[1].axvline(residuals.mean()/60, color='#1E3A5F', linestyle='--', linewidth=1.5,
                label=f'Mean: {residuals.mean()/60:.2f}h')
axes[1].set_xlabel('Residual (hours)')
axes[1].set_ylabel('Frequency')
axes[1].set_title('Residual Distribution')
axes[1].legend()

plt.tight_layout()
plt.savefig('fig4_actual_vs_predicted.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved: fig4_actual_vs_predicted.png")

# Figure 5 — Feature Importance
fig, ax = plt.subplots(figsize=(10, 7))
imp = pd.Series(final_model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=True)
colors = ['#F5920A' if v == imp.max() else '#1E3A5F' for v in imp.values]
imp.plot(kind='barh', ax=ax, color=colors, alpha=0.85)
ax.set_xlabel('Feature Importance Score')
ax.set_title('Figure 5 — XGBoost Feature Importance', fontweight='bold')
plt.tight_layout()
plt.savefig('fig5_feature_importance.png', dpi=150, bbox_inches='tight')
plt.show()
print("Saved: fig5_feature_importance.png")

print("\n" + "=" * 50)
print("FINAL RESULTS SUMMARY")
print("=" * 50)
print(f"Dataset:   1,500 trips | 16 features")
print(f"Train+Val: 1,050 (70%)  |  Test: 450 (30%)")
print(f"MAE:       {mae:.2f} min  ({mae/60:.2f} hrs)")
print(f"RMSE:      {rmse:.2f} min  ({rmse/60:.2f} hrs)")
print(f"MAPE:      {mape:.2f}%")
print(f"R²:        {r2:.4f}")
print()
print("Top 5 features:")
for feat, score in imp.sort_values(ascending=False).head(5).items():
    print(f"  {feat}: {score:.4f}")
