"""Machine Learning Code-First Configuration Module.

This module centralizes all Machine Learning specifications, training hyperparameters,
experimentation presets, hyperparameter tuning grids, and risk classification thresholds
directly in Python code.

This design decouples ML experimentation from environment variables (.env), allowing
data scientists and ML engineers to dynamically tune, modify, or extend models in code
or via API parameters.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChurnHyperparameters:
    """XGBoost hyperparameters for ISP Customer Churn prediction."""

    n_estimators: int = 100
    max_depth: int = 4
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    scale_pos_weight: Optional[float] = None
    random_state: int = 42

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Pre-defined hyperparameter profiles for dynamic experimentation
HYPERPARAMETER_PRESETS: Dict[str, Dict[str, Any]] = {
    "default": {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    },
    "fast_prototype": {
        "n_estimators": 30,
        "max_depth": 3,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
    },
    "deep_tuned": {
        "n_estimators": 250,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.75,
        "colsample_bytree": 0.75,
        "random_state": 42,
    },
    "high_recall": {
        "n_estimators": 120,
        "max_depth": 4,
        "learning_rate": 0.04,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "scale_pos_weight": 2.5,
        "random_state": 42,
    },
}


@dataclass
class RiskThresholds:
    """Decision and risk categorization thresholds."""

    classification_threshold: float = 0.50
    high_risk: float = 0.70
    medium_risk: float = 0.30

    def categorize(self, probability: float) -> str:
        """Classify churn probability into human-readable risk tier."""
        if probability >= self.high_risk:
            return "HIGH"
        elif probability >= self.medium_risk:
            return "MEDIUM"
        return "LOW"


@dataclass
class TrainingConfig:
    """Dataset splitting, random seed, and temporal validation parameters."""

    test_size_ratio: float = 0.20
    random_state: int = 42
    auto_generate_labels_if_empty: bool = True


@dataclass
class TuningSearchSpace:
    """Hyperparameter search spaces for dynamic GridSearch / Optuna tuning."""

    param_grid: Dict[str, List[Any]] = field(
        default_factory=lambda: {
            "n_estimators": [50, 100, 150, 200],
            "max_depth": [3, 4, 5, 6],
            "learning_rate": [0.01, 0.03, 0.05, 0.10],
            "subsample": [0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
        }
    )


@dataclass
class MLModelIdentity:
    """Identity and metadata defaults for active churn model."""

    model_name: str = "churn_xgboost"
    default_version: str = "1.0.0"
    algorithm: str = "XGBClassifier"
    prediction_window: str = "30_days"


@dataclass
class MLConfig:
    """Central ML configuration object combining all sub-specifications."""

    model_identity: MLModelIdentity = field(default_factory=MLModelIdentity)
    hyperparameters: ChurnHyperparameters = field(default_factory=ChurnHyperparameters)
    risk_thresholds: RiskThresholds = field(default_factory=RiskThresholds)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    tuning: TuningSearchSpace = field(default_factory=TuningSearchSpace)
    artifacts_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent / "artifacts"
    )

    def resolve_hyperparameters(
        self,
        preset: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Resolve hyperparameters from a preset with optional ad-hoc overrides.
        
        Args:
            preset: Name of the preset profile (e.g. 'default', 'fast_prototype', 'deep_tuned', 'high_recall')
            overrides: Custom dictionary of hyperparameters to override specific fields.
        """
        base_params = self.hyperparameters.to_dict()
        if preset and preset in HYPERPARAMETER_PRESETS:
            base_params.update(HYPERPARAMETER_PRESETS[preset])

        if overrides:
            for k, v in overrides.items():
                if v is not None:
                    base_params[k] = v

        return base_params


# Global code-driven ML configuration singleton
ml_config = MLConfig()
