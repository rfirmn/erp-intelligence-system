import argparse
import asyncio
import logging
import os
from pathlib import Path
import shutil
import sys

# Ensure backend root is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clean_ml_artifacts")

ARTIFACTS_DIR = BACKEND_DIR / "app" / "ml" / "artifacts"


def clean_disk_artifacts(dry_run: bool = False) -> int:
    """Remove all model weights, version folders, and manifests from app/ml/artifacts while keeping .gitkeep."""
    if not ARTIFACTS_DIR.exists():
        logger.info(f"Artifacts directory does not exist: {ARTIFACTS_DIR}")
        return 0

    deleted_count = 0
    logger.info(f"Scanning artifacts directory: {ARTIFACTS_DIR}")

    for item in ARTIFACTS_DIR.iterdir():
        if item.name == ".gitkeep":
            continue

        if dry_run:
            logger.info(f"[DRY-RUN] Would delete: {item.name}")
            deleted_count += 1
            continue

        if item.is_dir():
            shutil.rmtree(item)
            logger.info(f"Deleted directory: {item.name}")
            deleted_count += 1
        elif item.is_file():
            item.unlink()
            logger.info(f"Deleted file: {item.name}")
            deleted_count += 1

    # Ensure .gitkeep exists
    gitkeep = ARTIFACTS_DIR / ".gitkeep"
    if not gitkeep.exists() and not dry_run:
        gitkeep.write_text("# Marker file to preserve directory structure in Git while ignoring binary model artifacts\n")
        logger.info("Restored app/ml/artifacts/.gitkeep")

    logger.info(f"Total disk items cleaned: {deleted_count}")
    return deleted_count


async def clean_database_predictions():
    """Truncate or delete all prediction records from feature_store.prediction_customer_churn."""
    try:
        from sqlalchemy import text
        from app.core.session import engine

        logger.info("Cleaning prediction records from feature_store.prediction_customer_churn...")
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE feature_store.prediction_customer_churn CASCADE;"))
        logger.info("Database table feature_store.prediction_customer_churn truncated successfully.")
    except Exception as e:
        logger.warning(f"Could not truncate prediction_customer_churn: {e}")


def main():
    parser = argparse.ArgumentParser(description="Clean ML model artifacts and prediction records for pristine repository state.")
    parser.add_argument("--dry-run", action="store_true", help="Print items that would be deleted without actually deleting")
    parser.add_argument("--clean-db", action="store_true", help="Also truncate prediction records from database")
    args = parser.parse_args()

    clean_disk_artifacts(dry_run=args.dry_run)

    if args.clean_db and not args.dry_run:
        asyncio.run(clean_database_predictions())


if __name__ == "__main__":
    main()
