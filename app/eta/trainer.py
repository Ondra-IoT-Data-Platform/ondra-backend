# eta/trainer.py

import os
from pathlib import Path
from uuid import UUID

import numpy as np
from django.conf import settings
from django.utils import timezone

MODEL_STORAGE_DIR = getattr(settings, "ETA_MODEL_STORAGE_DIR", "/app/eta/store")
MINIMUM_TRAINING_RECORDS = getattr(settings, "ETA_MIN_TRAINING_RECORDS", 100)

# Point to your existing store folder where the .npy files live
STORE_DIR = Path(__file__).resolve().parent / "store"


def train_eta_model(organization_id: UUID) -> dict:
    """
    Trains the XGBoost ETA model using pre-split numpy arrays
    from the standalone training pipeline.
    Saves a new versioned model and creates an ETAModelVersion record.
    """
    import xgboost as xgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from eta.models import ETAModelVersion

    try:
        # Load pre-split data from standalone training pipeline
        X_trainval  = np.load(STORE_DIR / "X_trainval.npy")
        y_trainval  = np.load(STORE_DIR / "y_trainval.npy")
        X_test      = np.load(STORE_DIR / "X_test.npy")
        y_test      = np.load(STORE_DIR / "y_test.npy")
        best_params = np.load(
            STORE_DIR / "best_params.npy", allow_pickle=True
        ).item()

    except FileNotFoundError as e:
        return {
            "status": "failed",
            "reason": (
                f"Training data not found: {e}. "
                "Run the standalone training pipeline first to generate "
                "the .npy files in eta/store/."
            ),
        }

    records_used = len(X_trainval) + len(X_test)

    if records_used < MINIMUM_TRAINING_RECORDS:
        return {
            "status": "skipped",
            "reason": (
                f"Only {records_used} records available. "
                f"Minimum required: {MINIMUM_TRAINING_RECORDS}"
            ),
        }

    # Train final model
    final_model = xgb.XGBRegressor(
        **best_params,
        min_child_weight=5,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        colsample_bytree=0.8,
        random_state=42,
        objective="reg:squarederror",
        n_jobs=-1,
    )
    final_model.fit(X_trainval, y_trainval, verbose=False)

    # Evaluate on test set
    y_pred = final_model.predict(X_test)
    mae  = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mape = float(
        np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
    )
    ss_res = np.sum((y_test - y_pred) ** 2)
    ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
    r2 = float(1 - ss_res / ss_tot)

    # Version and save
    latest = ETAModelVersion.objects.filter(
        organization_id=organization_id
    ).order_by("-version").first()
    next_version = (latest.version + 1) if latest else 1

    os.makedirs(MODEL_STORAGE_DIR, exist_ok=True)
    model_path = os.path.join(
        MODEL_STORAGE_DIR,
        f"eta_model_org_{str(organization_id)[:8]}_v{next_version}.json",
    )
    final_model.save_model(model_path)

    # Retire previous active version
    ETAModelVersion.objects.filter(
        organization_id=organization_id,
        status=ETAModelVersion.Status.ACTIVE,
    ).update(status=ETAModelVersion.Status.RETIRED)

    # Create new version record
    ETAModelVersion.objects.create(
        organization_id=organization_id,
        version=next_version,
        status=ETAModelVersion.Status.ACTIVE,
        records_used=records_used,
        mae_minutes=round(mae, 3),
        rmse_minutes=round(rmse, 3),
        mape_percentage=round(mape, 3),
        model_file_path=model_path,
        trained_at=timezone.now(),
    )

    return {
        "status": "success",
        "version": next_version,
        "records_used": records_used,
        "mae_minutes": round(mae, 3),
        "rmse_minutes": round(rmse, 3),
        "mape_percentage": round(mape, 3),
        "r2": round(r2, 4),
        "model_path": model_path,
    }
