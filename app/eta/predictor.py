# import os
# from datetime import timedelta
# from typing import Optional
# from uuid import UUID

# import httpx
# from django.conf import settings
# from django.utils import timezone


# GOOGLE_MAPS_API_KEY = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
# MINIMUM_TRAINING_RECORDS = getattr(settings, "ETA_MIN_TRAINING_RECORDS", 100)
# MODEL_STORAGE_DIR = getattr(settings, "ETA_MODEL_STORAGE_DIR", "/app/eta/models")


# async def get_routing_baseline(
#     origin_lat: str,
#     origin_lng: str,
#     dest_lat: str,
#     dest_lng: str,
# ) -> tuple[float, float]:
#     """
#     Calls Google Maps Distance Matrix API.
#     Returns (distance_km, duration_minutes) tuple.
#     Falls back to (0.0, 0.0) if API call fails.
#     """
#     try:
#         url = "https://maps.googleapis.com/maps/api/distancematrix/json"
#         params = {
#             "origins": f"{origin_lat},{origin_lng}",
#             "destinations": f"{dest_lat},{dest_lng}",
#             "mode": "driving",
#             "key": GOOGLE_MAPS_API_KEY,
#         }
#         async with httpx.AsyncClient(timeout=10.0) as client:
#             response = await client.get(url, params=params)
#             data = response.json()

#         element = data["rows"][0]["elements"][0]
#         if element["status"] != "OK":
#             return 0.0, 0.0

#         distance_km = element["distance"]["value"] / 1000
#         duration_minutes = element["duration"]["value"] / 60
#         return round(distance_km, 3), round(duration_minutes, 2)

#     except Exception:
#         return 0.0, 0.0


# def _load_active_model(organization_id: UUID):
#     """
#     Loads the active XGBoost model for an organization.
#     Returns the model object or None if no active model exists.
#     """
#     try:
#         import xgboost as xgb
#         from eta.models import ETAModelVersion

#         # Sync ORM call — called from sync context in trainer
#         # For async context wrap with sync_to_async at call site
#         version = ETAModelVersion.objects.filter(
#             organization_id=organization_id,
#             status=ETAModelVersion.Status.ACTIVE,
#         ).order_by("-version").first()

#         if not version or not version.model_file_path:
#             return None

#         if not os.path.exists(version.model_file_path):
#             return None

#         model = xgb.XGBRegressor()
#         model.load_model(version.model_file_path)
#         return model

#     except Exception:
#         return None


# def _predict_corrected_eta(
#     model,
#     distance_km: float,
#     base_eta_minutes: float,
#     hour_of_day: int,
#     day_of_week: int,
#     driver_id: UUID,
#     origin_terminal_id: int,
#     product_name: str,
#     quantity: float,
# ) -> float:
#     """
#     Runs Stage 2 XGBoost prediction.
#     Returns predicted duration in minutes.
#     """
#     import numpy as np

#     # Encode categoricals as integers
#     terminal_encoded = origin_terminal_id or 0
#     product_encoded = hash(product_name) % 100 if product_name else 0

#     features = np.array([[
#         distance_km,
#         base_eta_minutes,
#         hour_of_day,
#         day_of_week,
#         terminal_encoded,
#         product_encoded,
#         quantity or 0.0,
#     ]])

#     prediction = model.predict(features)[0]
#     return float(max(prediction, 1.0))


# async def compute_eta(
#     organization_id: UUID,
#     origin_lat: str,
#     origin_lng: str,
#     dest_lat: str,
#     dest_lng: str,
#     expected_departure,
#     driver_id: UUID,
#     origin_terminal_id: int,
#     product_name: str,
#     quantity: float,
# ) -> dict:
#     """
#     Main ETA computation function.
#     Called when a dispatch is created.
#     Returns a dict with distance_km, base_eta_minutes,
#     predicted_eta_datetime, and stage (1 or 2).
#     """
#     from asgiref.sync import sync_to_async

#     distance_km, base_eta_minutes = await get_routing_baseline(
#         origin_lat, origin_lng, dest_lat, dest_lng
#     )

#     departure = expected_departure or timezone.now()
#     hour_of_day = departure.hour
#     day_of_week = departure.weekday()

#     # Try Stage 2 first
#     model = await sync_to_async(_load_active_model)(organization_id)

#     if model is not None and distance_km > 0:
#         predicted_minutes = _predict_corrected_eta(
#             model=model,
#             distance_km=distance_km,
#             base_eta_minutes=base_eta_minutes,
#             hour_of_day=hour_of_day,
#             day_of_week=day_of_week,
#             driver_id=driver_id,
#             origin_terminal_id=origin_terminal_id,
#             product_name=product_name,
#             quantity=quantity,
#         )
#         stage = 2
#     else:
#         predicted_minutes = base_eta_minutes
#         stage = 1

#     eta_datetime = departure + timedelta(minutes=predicted_minutes)

#     return {
#         "distance_km": distance_km,
#         "base_eta_minutes": base_eta_minutes,
#         "predicted_minutes": predicted_minutes,
#         "eta_datetime": eta_datetime,
#         "stage": stage,
#     }




# import os
# import logging
# from datetime import timedelta
# from typing import Optional
# from uuid import UUID

# import httpx
# from django.conf import settings
# from django.utils import timezone

# logger = logging.getLogger(__name__)

# GOOGLE_MAPS_API_KEY = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
# MODEL_STORAGE_DIR   = getattr(settings, "ETA_MODEL_STORAGE_DIR", "/app/eta/store")


# async def get_routing_baseline(
#     origin_lat: str,
#     origin_lng: str,
#     dest_lat: str,
#     dest_lng: str,
# ) -> tuple[float, float]:
#     """
#     Calls Google Maps Distance Matrix API.
#     Returns (distance_km, duration_minutes).
#     Falls back to (0.0, 0.0) on failure.
#     """
#     if not GOOGLE_MAPS_API_KEY:
#         logger.warning("GOOGLE_MAPS_API_KEY not set — ETA Stage 1 unavailable")
#         return 0.0, 0.0

#     try:
#         url = "https://maps.googleapis.com/maps/api/distancematrix/json"
#         params = {
#             "origins":      f"{origin_lat},{origin_lng}",
#             "destinations": f"{dest_lat},{dest_lng}",
#             "mode":         "driving",
#             "key":          GOOGLE_MAPS_API_KEY,
#         }
#         async with httpx.AsyncClient(timeout=10.0) as client:
#             response = await client.get(url, params=params)
#             data = response.json()

#         element = data["rows"][0]["elements"][0]
#         if element["status"] != "OK":
#             logger.warning(f"Maps API status: {element['status']}")
#             return 0.0, 0.0

#         distance_km      = element["distance"]["value"] / 1000
#         duration_minutes = element["duration"]["value"] / 60
#         logger.info(f"Maps API: {distance_km:.1f}km — {duration_minutes:.0f}min baseline")
#         return round(distance_km, 3), round(duration_minutes, 2)

#     except Exception as e:
#         logger.error(f"Maps API call failed: {e}")
#         return 0.0, 0.0


# def _load_active_model(organization_id: UUID):
#     """
#     Loads the active XGBoost model for an organization.
#     Pure sync — safe to call inside asyncio.run() context.
#     """
#     try:
#         import xgboost as xgb
#         from eta.models import ETAModelVersion

#         version = ETAModelVersion.objects.filter(
#             organization_id=organization_id,
#             status=ETAModelVersion.Status.ACTIVE,
#         ).order_by("-version").first()

#         if not version:
#             logger.info(f"No active ETA model for org {organization_id} — Stage 1 only")
#             return None

#         if not version.model_file_path:
#             logger.warning("ETAModelVersion has no model_file_path")
#             return None

#         if not os.path.exists(version.model_file_path):
#             logger.warning(f"Model file not found: {version.model_file_path}")
#             return None

#         model = xgb.XGBRegressor()
#         model.load_model(version.model_file_path)
#         logger.info(f"Loaded ETA model v{version.version}")
#         return model

#     except Exception as e:
#         logger.error(f"Failed to load ETA model: {e}")
#         return None


# def _predict(
#     model,
#     distance_km: float,
#     base_eta_minutes: float,
#     hour_of_day: int,
#     day_of_week: int,
#     driver_id: UUID,
#     origin_terminal_id,
#     product_name: Optional[str],
#     quantity: float,
# ) -> float:
#     """Stage 2 XGBoost prediction. Returns predicted minutes."""
#     import numpy as np

#     driver_encoded   = hash(str(driver_id)) % 10000
#     terminal_encoded = int(origin_terminal_id) if origin_terminal_id else 0
#     product_encoded  = hash(str(product_name)) % 100 if product_name else 0

#     features = np.array([[
#         distance_km,
#         base_eta_minutes,
#         hour_of_day,
#         day_of_week,
#         1 if day_of_week >= 5 else 0,
#         1 if hour_of_day in [7, 8, 14, 15] else 0,
#         quantity,
#         0.85,   # load_utilization default
#         0.0,    # tare_weight placeholder
#         0.0,    # gross_weight placeholder
#         0.0,    # net_weight placeholder
#         150.0,  # loading_temp default
#         0.0,    # fuel placeholder
#         terminal_encoded,
#         product_encoded,
#         driver_encoded,
#     ]])

#     predicted = model.predict(features)[0]
#     return float(max(predicted, base_eta_minutes * 0.85))


# async def compute_eta(
#     organization_id: UUID,
#     origin_lat: str,
#     origin_lng: str,
#     dest_lat: str,
#     dest_lng: str,
#     expected_departure,
#     driver_id: UUID,
#     origin_terminal_id,
#     product_name: Optional[str],
#     quantity: float,
# ) -> dict:
#     """
#     Main ETA entry point.
#     Called via asyncio.run() from the sync dispatch service.
#     Returns dict with distance_km, base_eta_minutes,
#     predicted_minutes, eta_datetime, stage.
#     """
#     # Stage 1 — routing API
#     distance_km, base_eta_minutes = await get_routing_baseline(
#         origin_lat, origin_lng, dest_lat, dest_lng
#     )

#     departure   = expected_departure or timezone.now()
#     hour_of_day = departure.hour if hasattr(departure, 'hour') else 8
#     day_of_week = departure.weekday() if hasattr(departure, 'weekday') else 0

#     # Stage 2 — XGBoost correction
#     # _load_active_model is sync and safe to call directly here
#     model = _load_active_model(organization_id)

#     if model is not None and distance_km > 0:
#         predicted_minutes = _predict(
#             model=model,
#             distance_km=distance_km,
#             base_eta_minutes=base_eta_minutes,
#             hour_of_day=hour_of_day,
#             day_of_week=day_of_week,
#             driver_id=driver_id,
#             origin_terminal_id=origin_terminal_id,
#             product_name=product_name,
#             quantity=quantity,
#         )
#         stage = 2
#         logger.info(
#             f"Stage 2: base={base_eta_minutes:.0f}min "
#             f"corrected={predicted_minutes:.0f}min"
#         )
#     else:
#         predicted_minutes = base_eta_minutes if base_eta_minutes > 0 else 0.0
#         stage = 1
#         logger.info(f"Stage 1: base={predicted_minutes:.0f}min")

#     eta_datetime = departure + timedelta(minutes=predicted_minutes)

#     return {
#         "distance_km":      distance_km,
#         "base_eta_minutes": base_eta_minutes,
#         "predicted_minutes": predicted_minutes,
#         "eta_datetime":     eta_datetime,
#         "stage":            stage,
#     }



import os
import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
MODEL_STORAGE_DIR   = getattr(settings, "ETA_MODEL_STORAGE_DIR", "/app/eta/store")


print(f"MAPS KEY LOADED: {'YES' if GOOGLE_MAPS_API_KEY else 'NO - KEY MISSING'}")

def get_routing_baseline(
    origin_lat: str,
    origin_lng: str,
    dest_lat: str,
    dest_lng: str,
) -> tuple[float, float]:
    """
    Calls Google Maps Distance Matrix API synchronously.
    Returns (distance_km, duration_minutes).
    Falls back to (0.0, 0.0) on any failure.
    """
    print(f"ROUTING CALL: origin={origin_lat},{origin_lng} dest={dest_lat},{dest_lng}")

    if not GOOGLE_MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set — ETA Stage 1 unavailable")
        return 0.0, 0.0

    try:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins":      f"{origin_lat},{origin_lng}",
            "destinations": f"{dest_lat},{dest_lng}",
            "mode":         "driving",
            "key":          GOOGLE_MAPS_API_KEY,
        }
        response = httpx.get(url, params=params, timeout=10.0)
        data = response.json()

        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            logger.warning(f"Maps API status: {element['status']}")
            return 0.0, 0.0

        distance_km      = element["distance"]["value"] / 1000
        duration_minutes = element["duration"]["value"] / 60
        logger.info(
            f"Maps API: {distance_km:.1f}km — {duration_minutes:.0f}min baseline"
        )
        return round(distance_km, 3), round(duration_minutes, 2)

    except Exception as e:
        logger.error(f"Maps API call failed: {e}")
        return 0.0, 0.0


def _load_active_model(organization_id: UUID):
    """
    Loads the active XGBoost model for an organization.
    Pure sync — safe to call anywhere.
    """
    try:
        import xgboost as xgb
        from eta.models import ETAModelVersion

        version = ETAModelVersion.objects.filter(
            organization_id=organization_id,
            status=ETAModelVersion.Status.ACTIVE,
        ).order_by("-version").first()

        if not version:
            logger.info(
                f"No active ETA model for org {organization_id} — Stage 1 only"
            )
            return None

        if not version.model_file_path:
            logger.warning("ETAModelVersion has no model_file_path")
            return None

        if not os.path.exists(version.model_file_path):
            logger.warning(f"Model file not found: {version.model_file_path}")
            return None

        model = xgb.XGBRegressor()
        model.load_model(version.model_file_path)
        logger.info(f"Loaded ETA model v{version.version}")
        return model

    except Exception as e:
        logger.error(f"Failed to load ETA model: {e}")
        return None


def _predict(
    model,
    distance_km: float,
    base_eta_minutes: float,
    hour_of_day: int,
    day_of_week: int,
    driver_id: UUID,
    origin_terminal_id,
    product_name: Optional[str],
    quantity: float,
) -> float:
    """Stage 2 XGBoost prediction. Returns predicted minutes."""
    import numpy as np

    driver_encoded   = hash(str(driver_id)) % 10000
    terminal_encoded = int(origin_terminal_id) if origin_terminal_id else 0
    product_encoded  = hash(str(product_name)) % 100 if product_name else 0

    features = np.array([[
        distance_km,
        base_eta_minutes,
        hour_of_day,
        day_of_week,
        1 if day_of_week >= 5 else 0,
        1 if hour_of_day in [7, 8, 14, 15] else 0,
        quantity,
        0.85,
        0.0,
        0.0,
        0.0,
        150.0,
        0.0,
        terminal_encoded,
        product_encoded,
        driver_encoded,
    ]])

    predicted = model.predict(features)[0]

    max_allowed = base_eta_minutes * 1.40
    min_allowed = base_eta_minutes * 0.85
    predicted = float(min(max(predicted, min_allowed), max_allowed))

    return float(max(predicted, base_eta_minutes * 0.85))


def compute_eta(
    organization_id: UUID,
    origin_lat: str,
    origin_lng: str,
    dest_lat: str,
    dest_lng: str,
    expected_departure,
    driver_id: UUID,
    origin_terminal_id,
    product_name: Optional[str],
    quantity: float,
) -> dict:
    """
    Main ETA entry point — fully synchronous.
    Called directly from dispatch service.
    Returns dict with distance_km, base_eta_minutes,
    predicted_minutes, eta_datetime, stage.
    """
    # Stage 1 — routing API
    distance_km, base_eta_minutes = get_routing_baseline(
        origin_lat, origin_lng, dest_lat, dest_lng
    )

    departure   = expected_departure or timezone.now()
    hour_of_day = departure.hour if hasattr(departure, 'hour') else 8
    day_of_week = departure.weekday() if hasattr(departure, 'weekday') else 0

    # Stage 2 — XGBoost correction
    model = _load_active_model(organization_id)

    if model is not None and distance_km > 0:
        predicted_minutes = _predict(
            model=model,
            distance_km=distance_km,
            base_eta_minutes=base_eta_minutes,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            driver_id=driver_id,
            origin_terminal_id=origin_terminal_id,
            product_name=product_name,
            quantity=quantity,
        )
        stage = 2
        logger.info(
            f"Stage 2: base={base_eta_minutes:.0f}min "
            f"corrected={predicted_minutes:.0f}min"
        )
    else:
        predicted_minutes = base_eta_minutes if base_eta_minutes > 0 else 0.0
        stage = 1
        logger.info(f"Stage 1: base={predicted_minutes:.0f}min")

    eta_datetime = departure + timedelta(minutes=predicted_minutes)

    return {
        "distance_km":       distance_km,
        "base_eta_minutes":  base_eta_minutes,
        "predicted_minutes": predicted_minutes,
        "eta_datetime":      eta_datetime,
        "stage":             stage,
    }
