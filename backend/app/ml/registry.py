import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib

from app.ml.config import ml_config

logger = logging.getLogger("erp_ml.registry")

ARTIFACTS_ROOT_DIR = ml_config.artifacts_dir
_PIPELINE_CACHE: Optional[Any] = None
_CACHED_VERSION: Optional[str] = None


def get_active_manifest_path() -> Path:
    return ARTIFACTS_ROOT_DIR / "active_model.json"


def get_active_model_metadata() -> Optional[Dict[str, Any]]:
    """Read metadata dictionary of currently active model."""
    manifest_file = get_active_manifest_path()
    if not manifest_file.exists():
        return None

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        version = manifest.get("active_version")
        model_name = manifest.get("model_name", ml_config.model_identity.model_name)
        version_dir = ARTIFACTS_ROOT_DIR / f"{model_name}_v{version}"
        meta_file = version_dir / "metadata.json"

        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as mf:
                return json.load(mf)
        return manifest
    except Exception as e:
        logger.error(f"Failed to read active model metadata: {e}")
        return None


def get_active_model_pipeline() -> Any:
    """Retrieve in-memory cached Scikit-Learn pipeline for currently active model."""
    global _PIPELINE_CACHE, _CACHED_VERSION

    manifest_file = get_active_manifest_path()
    if not manifest_file.exists():
        raise FileNotFoundError(
            "Tidak ditemukan model aktif. Silakan jalankan pelatihan model terlebih dahulu "
            "melalui endpoint POST /api/v1/ml/models/churn/train"
        )

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    active_version = manifest.get("active_version")
    if _PIPELINE_CACHE is not None and _CACHED_VERSION == active_version:
        return _PIPELINE_CACHE

    pipeline_path = Path(manifest.get("pipeline_path", ""))
    if not pipeline_path.exists():
        # Fallback relative to ARTIFACTS_ROOT_DIR
        model_name = manifest.get("model_name", ml_config.model_identity.model_name)
        pipeline_path = ARTIFACTS_ROOT_DIR / f"{model_name}_v{active_version}" / "pipeline.joblib"

    if not pipeline_path.exists():
        raise FileNotFoundError(f"File artifact model tidak ditemukan di: {pipeline_path}")

    logger.info(f"Loading ML pipeline artifact from: {pipeline_path}")
    pipeline = joblib.load(pipeline_path)

    _PIPELINE_CACHE = pipeline
    _CACHED_VERSION = active_version
    return _PIPELINE_CACHE


def reload_active_model() -> None:
    """Clear in-memory cache to force reloading from disk."""
    global _PIPELINE_CACHE, _CACHED_VERSION
    _PIPELINE_CACHE = None
    _CACHED_VERSION = None
    logger.info("Cleared in-memory ML pipeline cache.")


def list_available_models() -> List[Dict[str, Any]]:
    """List all trained model releases in local artifact directory."""
    if not ARTIFACTS_ROOT_DIR.exists():
        return []

    releases: List[Dict[str, Any]] = []
    active_manifest = get_active_model_metadata() or {}
    active_version = active_manifest.get("model_version")
    model_name = ml_config.model_identity.model_name

    for p in ARTIFACTS_ROOT_DIR.iterdir():
        if p.is_dir() and (p.name.startswith(f"{model_name}_v") or "_v" in p.name):
            meta_path = p / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
                        meta["is_active"] = (meta.get("model_version") == active_version)
                        releases.append(meta)
                except Exception:
                    pass

    return releases
