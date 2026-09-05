import json
import logging
import re
from typing import Any, Dict
from pydantic import ValidationError

from app.schemas.insights import InsightPackage

logger = logging.getLogger("erp_insights.validator")


def sanitize_and_parse_json(text: str) -> Dict[str, Any]:
    """Strip markdown code fences and clean formatting before JSON decoding."""
    clean_text = text.strip()

    # Remove markdown code fences like ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if match:
        clean_text = match.group(1).strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}. Raw text: {text[:200]}")
        raise ValueError(f"Output tidak dapat diurai sebagai JSON valid: {str(e)}")


def validate_insight_package(payload: Dict[str, Any]) -> InsightPackage:
    """Validate payload against InsightPackage Pydantic schema."""
    try:
        package = InsightPackage(**payload)
        return package
    except ValidationError as ve:
        logger.error(f"InsightPackage validation failed: {ve}")
        raise ValueError(f"Validasi skema InsightPackage gagal: {str(ve)}")
