from typing import Any, Dict, Optional
import numpy as np
import xgboost as xgb
from sklearn.base import BaseEstimator, ClassifierMixin


class ChurnXGBoostModel(BaseEstimator, ClassifierMixin):
    """XGBoost Classifier wrapper tailored for ISP Customer Churn prediction.
    
    Supports native imbalanced handling via automatic scale_pos_weight calculation.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        scale_pos_weight: Optional[float] = None,
        random_state: int = 42,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.scale_pos_weight = scale_pos_weight
        self.random_state = random_state

        self.model_: Optional[xgb.XGBClassifier] = None
        self.classes_: Optional[np.ndarray] = None

    def fit(self, X: Any, y: Any) -> "ChurnXGBoostModel":
        y_arr = np.asarray(y)
        self.classes_ = np.unique(y_arr)

        # Compute dynamic scale_pos_weight if not explicitly provided
        pos_weight = self.scale_pos_weight
        if pos_weight is None:
            n_pos = int(np.sum(y_arr == 1))
            n_neg = int(np.sum(y_arr == 0))
            if n_pos > 0:
                pos_weight = max(1.0, float(n_neg) / float(n_pos))
            else:
                pos_weight = 1.0

        self.model_ = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            scale_pos_weight=pos_weight,
            random_state=self.random_state,
            eval_metric="logloss",
        )

        self.model_.fit(X, y_arr)
        return self

    def predict(self, X: Any) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("Model belum dilatih. Panggil fit() terlebih dahulu.")
        return self.model_.predict(X)

    def predict_proba(self, X: Any) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("Model belum dilatih. Panggil fit() terlebih dahulu.")
        return self.model_.predict_proba(X)

    @property
    def feature_importances_(self) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("Model belum dilatih.")
        return self.model_.feature_importances_
