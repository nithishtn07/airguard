"""
AirGuard AI - Model Registry & Persistence Module (Phase 4)
-----------------------------------------------------------
Manages model persistence, metadata logging, in-memory model caching,
and model versioning.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import joblib

from config.settings import settings
from backend.utils.logger import logger


class ModelRegistry:
    """
    Lightweight model registry and caching layer.
    Ensures safe loading on startup, avoids repeated disk I/O per API call,
    and maintains versioning transparency.
    """
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = os.path.abspath(models_dir or settings.MODELS_DIR)
        os.makedirs(self.models_dir, exist_ok=True)
        self._cached_model_package: Optional[Dict[str, Any]] = None
        self._cached_metadata: Optional[Dict[str, Any]] = None
        self._model_path = os.path.join(self.models_dir, "airguard_aqi_model.joblib")
        self._metadata_path = os.path.join(self.models_dir, "model_metadata.json")

    def save_model(
        self,
        model: Any,
        imputer: Any,
        features: List[str],
        model_type: str,
        version: str,
        target: str,
        metrics: Dict[str, Any],
        feature_importances: List[Dict[str, Any]],
        counts: Dict[str, int],
        region_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Persists trained model artifact and human-readable metadata.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        package = {
            "model": model,
            "imputer": imputer,
            "features": features,
            "model_type": model_type,
            "model_version": version,
            "target": target,
            "trained_at": now_iso,
            "training_rows": counts.get("train", 0),
            "validation_rows": counts.get("val", 0),
            "test_rows": counts.get("test", 0),
            "metrics": metrics,
            "feature_importances": feature_importances,
            "region_id": region_id
        }

        # 1. Save binary model artifact
        joblib.dump(package, self._model_path)
        logger.info(f"Model artifact saved to {self._model_path}")

        # 2. Save JSON metadata (excluding binary object)
        metadata = {
            "model_type": model_type,
            "model_version": version,
            "target": target,
            "trained_at": now_iso,
            "training_rows": counts.get("train", 0),
            "validation_rows": counts.get("val", 0),
            "test_rows": counts.get("test", 0),
            "features": features,
            "feature_count": len(features),
            "metrics": metrics,
            "top_features": feature_importances[:7],
            "region_id": region_id,
            "model_file": os.path.basename(self._model_path)
        }

        with open(self._metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Model metadata saved to {self._metadata_path}")

        # 3. Update in-memory cache
        self._cached_model_package = package
        self._cached_metadata = metadata

        return metadata

    def load_active_model(self, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieves the active in-memory model package. Loads from disk if not yet cached.
        Returns None gracefully if no model has been trained.
        """
        if self._cached_model_package is not None and not force_reload:
            return self._cached_model_package

        if not os.path.exists(self._model_path):
            logger.debug(f"No trained model artifact found at {self._model_path}")
            return None

        try:
            package = joblib.load(self._model_path)
            self._cached_model_package = package
            logger.info(f"Loaded active model: {package.get('model_type')} ({package.get('model_version')})")
            return package
        except Exception as e:
            logger.error(f"Error loading model artifact from {self._model_path}: {e}")
            return None

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Returns metadata for the active model."""
        if self._cached_metadata is not None:
            return self._cached_metadata

        if os.path.exists(self._metadata_path):
            try:
                with open(self._metadata_path, "r", encoding="utf-8") as f:
                    self._cached_metadata = json.load(f)
                    return self._cached_metadata
            except Exception as e:
                logger.error(f"Error reading model metadata: {e}")
                return None

        # Fallback to model package if metadata file missing
        pkg = self.load_active_model()
        if pkg:
            return {
                "model_type": pkg.get("model_type"),
                "model_version": pkg.get("model_version"),
                "target": pkg.get("target"),
                "trained_at": pkg.get("trained_at"),
                "training_rows": pkg.get("training_rows"),
                "validation_rows": pkg.get("validation_rows"),
                "test_rows": pkg.get("test_rows"),
                "features": pkg.get("features", []),
                "metrics": pkg.get("metrics", {}),
                "top_features": pkg.get("feature_importances", [])[:7]
            }
        return None

    def is_available(self) -> bool:
        """Returns True if a valid trained model is loaded or accessible."""
        return self.load_active_model() is not None


# Global registry singleton
model_registry = ModelRegistry()
